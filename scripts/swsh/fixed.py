from __future__ import annotations

import argparse
import time

import serial

from scripts._alarm import alarm
from scripts._reset import reset
from scripts.engine import Action
from scripts.engine import all_match
from scripts.engine import always_matches
from scripts.engine import Color
from scripts.engine import do
from scripts.engine import make_vid
from scripts.engine import match_px_exact
from scripts.engine import Point
from scripts.engine import Press
from scripts.engine import run
from scripts.engine import SERIAL_DEFAULT
from scripts.engine import States
from scripts.engine import Wait
from scripts.swsh._bootup import bootup


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default=SERIAL_DEFAULT)
    parser.add_argument('--quiet', action='store_true')
    parser.add_argument(
        '--mode',
        choices=('fixed', 'runup', 'whistle'),
        default='fixed',
    )
    args = parser.parse_args()

    vid = make_vid()

    if args.mode == 'fixed':
        startup: tuple[Action, ...] = ()
    elif args.mode == 'runup':
        startup = (
            Press('w', duration=.25),
            Press('B', duration=.05),
            Press('w', duration=1.05),
        )
    elif args.mode == 'whistle':
        startup = (Press('{', duration=.05), Wait(1)) * 7
    else:
        raise NotImplementedError(args.mode)

    dialog = all_match(
        match_px_exact(Point(y=587, x=20), Color(b=48, g=48, r=48)),
        match_px_exact(Point(y=672, x=1233), Color(b=48, g=48, r=48)),
        match_px_exact(Point(y=683, x=1132), Color(b=59, g=59, r=59)),
        match_px_exact(Point(y=587, x=107), Color(b=59, g=59, r=59)),
    )

    t_timeout = 0.

    def encounter_timeout_start(vid: object, ser: object) -> None:
        nonlocal t_timeout
        t_timeout = time.monotonic()

    def encounter_timeout(frame: object) -> bool:
        return time.monotonic() - t_timeout > 10

    t0 = t1 = 0.

    def record_start(vid: object, ser: object) -> None:
        nonlocal t0
        t0 = time.monotonic()

    def record_end(vid: object, ser: object) -> None:
        nonlocal t1
        t1 = time.monotonic()

    def is_shiny(frame: object) -> bool:
        print(f'delay: {t1 - t0:.3f}')
        if t1 - t0 >= 8:
            raise AssertionError('fuckup')
        return t1 - t0 > 1

    states: States = {
        **bootup('INITIAL', 'STARTUP'),
        'STARTUP': (
            (
                always_matches,
                do(*startup, encounter_timeout_start),
                'WAIT_FOR_DIALOG',
            ),
        ),
        'WAIT_FOR_DIALOG': (
            (encounter_timeout, reset, 'INITIAL'),
            (dialog, do(), 'DIALOG'),
            (always_matches, do(), 'WAIT_FOR_DIALOG'),
        ),
        'DIALOG': (
            (dialog, record_start, 'DIALOG'),
            (always_matches, do(), 'ANIMATION_END'),
        ),
        'ANIMATION_END': (
            (dialog, record_end, 'CHECK'),
        ),
        'CHECK': (
            (is_shiny, do(), 'ALARM'),
            (always_matches, reset, 'INITIAL'),
        ),
        **alarm('ALARM', quiet=args.quiet),
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=vid, ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
