from __future__ import annotations

import argparse
import os
import time

import cv2
import numpy
import serial

from scripts._alarm import alarm
from scripts._reset import reset
from scripts.engine import always_matches
from scripts.engine import do
from scripts.engine import make_vid
from scripts.engine import match_text
from scripts.engine import Point
from scripts.engine import Press
from scripts.engine import run
from scripts.engine import SERIAL_DEFAULT
from scripts.engine import States
from scripts.engine import Wait
from scripts.sv._pixels import world_matches


def crop_count(crop: numpy.ndarray, *, store: bool = False) -> int:
    # blank out the sky (sunset can be orange)
    corner = numpy.array([[0, 0], [55, 0], [0, 70]])
    cv2.fillConvexPoly(crop, corner, (0, 0, 0))

    # quantize colors
    pxs = numpy.float32(crop.reshape((-1, 3)))
    k = 10
    criteria = (cv2.TERM_CRITERIA_MAX_ITER, 25, None)
    flags = cv2.KMEANS_RANDOM_CENTERS
    _, labels, colors = cv2.kmeans(pxs, k, None, criteria, 10, flags)

    # black out any colors which are too common
    for i, count in zip(*numpy.unique(labels, return_counts=True)):
        if count > 1500:
            colors[i] = numpy.array([0, 0, 0])

    colors = numpy.uint8(colors)
    crop = colors[labels.flatten()].reshape(crop.shape)
    if store:
        cv2.imwrite('crop-bg.png', crop)

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    thres = cv2.inRange(hsv, (5, 25, 25), (25, 255, 255))
    if store:
        cv2.imwrite('thres.png', thres)
    return numpy.count_nonzero(thres)


def nonshiny_matches(frame: numpy.ndarray) -> bool:
    tl = Point(y=170, x=438).norm(frame.shape)
    br = Point(y=281, x=660).norm(frame.shape)
    crop = frame[tl.y:br.y, tl.x:br.x]
    cv2.imwrite('crop.png', crop)
    os.makedirs('crops', exist_ok=True)
    cv2.imwrite(f'crops/crop-{int(time.time())}.png', crop)
    count = crop_count(crop, store=True)
    print(f'matched pixels: {count}')
    return count >= 340


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default=SERIAL_DEFAULT)
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    vid = make_vid()

    states: States = {
        'INITIAL': (
            (
                match_text(
                    'Start',
                    Point(y=669, x=1158),
                    Point(y=700, x=1228),
                    invert=False,
                ),
                do(Press('A'), Wait(1)),
                'START',
            ),
        ),
        'START': (
            (
                match_text(
                    'PRESS',
                    Point(y=489, x=802),
                    Point(y=530, x=898),
                    invert=True,
                ),
                do(Wait(2), Press('A'), Wait(1)),
                'WORLD',
            ),
        ),
        'WORLD': (
            (world_matches, Wait(7.25), 'CHECK'),
        ),
        'CHECK': (
            (nonshiny_matches, reset, 'INITIAL'),
            (always_matches, do(Press('H'), Wait(1)), 'ALARM'),
        ),
        **alarm('ALARM', quiet=args.quiet),
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=vid, ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
