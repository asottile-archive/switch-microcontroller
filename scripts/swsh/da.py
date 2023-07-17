from __future__ import annotations

import argparse
import collections
import functools
import os.path
import re

import cv2
import numpy
import serial

from scripts._alarm import alarm
from scripts._reset import reset
from scripts.engine import all_match
from scripts.engine import always_matches
from scripts.engine import any_match
from scripts.engine import Color
from scripts.engine import do
from scripts.engine import get_text
from scripts.engine import getframe
from scripts.engine import make_vid
from scripts.engine import match_px
from scripts.engine import match_px_exact
from scripts.engine import match_text
from scripts.engine import Point
from scripts.engine import Press
from scripts.engine import run
from scripts.engine import SERIAL_DEFAULT
from scripts.engine import States
from scripts.engine import Wait

WORD = re.compile('[a-z]+')
TYPES = frozenset((
    'normal', 'fire', 'water', 'grass', 'electric', 'ice', 'fighting',
    'poison', 'ground', 'flying', 'psychic', 'bug', 'rock', 'ghost', 'dark',
    'dragon', 'steel', 'fairy',
))


@functools.lru_cache(maxsize=1)
def _arrow_mask() -> tuple[numpy.ndarray, numpy.ndarray]:
    here = os.path.dirname(__file__)
    tmpl = cv2.imread(os.path.join(here, 'templates', 'move_arrow.png'))
    mask = 255 - cv2.inRange(tmpl, tmpl[0][0], tmpl[0][0])
    return tmpl, mask


def get_int(
        frame: numpy.ndarray,
        tl: Point,
        br: Point,
        *,
        invert: bool,
        default: int,
) -> int:
    s = get_text(frame, tl, br, invert=invert)
    # sometimes this text has garbage on it
    match = re.search(r'\d+', s)
    if match is not None:
        return int(match[0])
    else:
        print(f'!!! could not match int: {s=}')
        return default


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default=SERIAL_DEFAULT)
    parser.add_argument('--pokemon', required=True)
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    pokemon = set()
    types: collections.Counter[str] = collections.Counter()
    with open(args.pokemon) as f:
        for line in f:
            parts = line.split()
            pokemon.add(tuple(parts))
            types.update(parts[1:])

    vid = make_vid()

    should_reset = True

    def should_reset_record(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        nonlocal should_reset

        frame = getframe(vid)
        current_ore_text = get_text(
            frame,
            Point(y=5, x=1209),
            Point(y=42, x=1276),
            invert=True,
        )
        # sometimes the ocr engine gets 1 and l confused
        current_ore = int(current_ore_text.replace('l', '1'))
        request_text = get_text(
            frame,
            Point(y=590, x=575),
            Point(y=635, x=939),
            invert=False,
        )
        requested_ore = int(request_text.split()[0])

        next_ore = min(10, requested_ore + 1)
        should_reset = (current_ore - requested_ore - next_ore) >= 0
        print(f'current ore: {current_ore}, requested: {requested_ore}')
        print(f'should reset? {should_reset}')

    def should_reset_check(frame: object) -> bool:
        return should_reset

    def should_reset_clear(vid: object, ser: object) -> None:
        nonlocal should_reset
        should_reset = True

    def pick_pokemon(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        frame = getframe(vid)

        chosen_pokemon = 0
        max_stat = -1

        for i, ((pok_tl, pok_br), locs) in enumerate((
            (
                (Point(y=209, x=623), Point(y=235, x=748)),
                (
                    (Point(y=140, x=1193), Point(y=166, x=1244)),
                    (Point(y=178, x=978), Point(y=204, x=1028)),
                ),
            ),
            (
                (Point(y=395, x=620), Point(y=423, x=758)),
                (
                    (Point(y=327, x=1193), Point(y=353, x=1244)),
                    (Point(y=365, x=974), Point(y=390, x=1025)),
                ),
            ),
            (
                (Point(y=580, x=622), Point(y=607, x=745)),
                (
                    (Point(y=513, x=1198), Point(y=541, x=1246)),
                    (Point(y=551, x=972), Point(y=578, x=1023)),
                ),
            ),
        )):
            name = get_text(frame, pok_tl, pok_br, invert=i == 0)
            print(f'pokemon({i}): {name}')
            if name in {'Unfezant', 'Whiscash', 'Mr. Mime', 'Lilligant'}:
                print('=> skipping bad pokemon')
                continue

            for tl, br in locs:
                stat = get_int(frame, tl, br, invert=False, default=0)
                if stat > max_stat:
                    chosen_pokemon = i
                    max_stat = stat

        print(f'picking pokemon: {chosen_pokemon}')
        for _ in range(chosen_pokemon):
            do(Press('s'), Wait(.5))(vid, ser)
        Press('A')(vid, ser)

    def route(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        def _info() -> tuple[int, int]:
            frame = getframe(vid)
            bw = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            m = cv2.inRange(bw, (0, 0, 230), (255, 20, 255))
            # blot out the sun
            cv2.rectangle(m, (0, 0), (180, len(m)), (0, 0, 0), -1)
            cv2.rectangle(m, (0, 0), (len(m[0]), 130), (0, 0, 0), -1)
            cv2.rectangle(m, (0, 400), (len(m[0]), len(m)), (0, 0, 0), -1)

            kernel = numpy.ones((10, 10), numpy.uint8)
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kernel)

            contours, _ = cv2.findContours(
                m, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE,
            )

            rects = []
            arrow_pos = Point(0, 0)
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if h >= 15 and w / h >= 1.5:
                    rects.append((
                        Point(y=y - 5, x=x - 5),
                        Point(y=y + h + 3, x=x + w + 3),
                    ))
                elif w >= 30 and h >= 30:
                    arrow_pos = Point(y=y, x=x)

            rects.sort(key=lambda p1_p2: p1_p2[0].x)
            pos = int((arrow_pos.x - 200) / (len(frame[0]) - 200) * len(rects))

            text = get_text(frame, *rects[pos], invert=True).lower()
            # sometimes the ocr engine sucks
            match = WORD.search(text)
            assert match is not None
            type_name = match[0]
            n = types[type_name]
            print(f'@{pos}: {type_name} (score={n})')

            return pos, n

        seen = set()
        best_pos = -1
        best_n = -1
        while True:
            pos, n = _info()
            if pos in seen:
                break
            else:
                seen.add(pos)

            if n > best_n:
                best_pos, best_n = pos, n

            do(Press('d'), Wait(.5))(vid, ser)

        pos, _ = _info()
        while pos != best_pos:
            do(Press('d'), Wait(.5))(vid, ser)
            pos, _ = _info()

        do(Press('A'), Wait(5))(vid, ser)

    def best_move(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        frame = getframe(vid)

        crop = frame[427:705, 813:893]
        arrow, mask = _arrow_mask()
        match = cv2.matchTemplate(crop, arrow, cv2.TM_CCOEFF_NORMED, mask=mask)
        _, _, _, (_, arrow_y) = cv2.minMaxLoc(match)
        current_move = int(arrow_y / len(crop) * 4)

        print(f'moving from {current_move=}')
        for _ in range(current_move):
            do(Press('w'), Wait(.25))(vid, ser)

        do(Press('Y'), Wait(.75))(vid, ser)

        max_text = get_text(
            frame,
            Point(y=444, x=920),
            Point(y=467, x=963),
            invert=True,
        )
        invert_effective = max_text == 'Max'

        powers = []

        for i in range(4):
            frame = getframe(vid)

            try:
                power = 1. * get_int(
                    frame,
                    Point(y=324, x=190),
                    Point(y=351, x=238),
                    invert=False,
                    default=0,
                )
            except ValueError:
                power = 0.

            effective_text = get_text(
                frame,
                Point(y=467 + i * 70, x=918),
                Point(y=492 + i * 70, x=1091),
                invert=invert_effective,
            ).replace(' ', '').lower()
            print(f'move {i}: {effective_text}')

            if effective_text == 'supereffective':
                power *= 2
            elif effective_text == 'notveryeffective':
                power /= 2
            elif effective_text == 'noeffect':
                power = 0.

            pp_s = get_text(
                frame,
                Point(y=221, x=705),
                Point(y=260, x=812),
                invert=True,
            ).split('/')[0].strip()
            try:
                pp = int(pp_s)
            except ValueError:
                print(f'!!! had trouble parsing pp: {pp_s=}')
                pp = 0

            if pp > 0:
                powers.append(power)
            else:
                powers.append(-1.)

            do(Press('s'), Wait(.5))(vid, ser)

        target_move = powers.index(max(powers))

        print(f'choosing move: {target_move}')

        for _ in range(target_move):
            do(Press('s'), Wait(.25))(vid, ser)

        do(Press('A'), Wait(.75), Press('A'))(vid, ser)

    catch = False

    def catch_record(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        nonlocal catch

        frame = getframe(vid)

        name = get_text(
            frame,
            Point(y=78, x=259),
            Point(y=117, x=445),
            invert=False,
        ).lower()

        def get_type(tl: Point, br: Point) -> str:
            text = get_text(frame, tl, br, invert=True).lower()
            match = WORD.search(text)
            assert match is not None
            return match[0]

        type1 = get_type(Point(y=128, x=306), Point(y=153, x=399))
        type2 = get_type(Point(y=128, x=448), Point(y=153, x=545))

        print(f'raw: {(name, type1, type2)}')
        if type2 in TYPES:
            key: tuple[str, ...] = (name, type1, type2)
        else:
            key = (name, type1)

        catch = key in pokemon
        print(f'encountered: {key}')
        print(f'will be catching? {catch}')

    def catch_check(frame: object) -> bool:
        return catch

    swap = False

    def swap_record(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        nonlocal swap

        frame = getframe(vid)

        old = max(
            get_int(frame, tl, br, invert=False, default=0)
            for tl, br in (
                (Point(y=181, x=1195), Point(y=205, x=1240)),
                (Point(y=216, x=973), Point(y=244, x=1021)),
            )
        )
        new = max(
            get_int(frame, tl, br, invert=False, default=0)
            for tl, br in (
                (Point(y=366, x=1195), Point(y=390, x=1240)),
                (Point(y=401, x=973), Point(y=429, x=1021)),
            )
        )
        swap = new > old
        print(f'is new pokemon better? {swap}')

    def swap_check(frame: object) -> bool:
        return swap

    summary_counter = 0

    def summary_counter_reset(vid: object, ser: object) -> None:
        nonlocal summary_counter
        summary_counter = 0

    def summary_counter_increment(vid: object, ser: object) -> None:
        nonlocal summary_counter
        summary_counter += 1

    def summary_counter_enough(frame: object) -> bool:
        return summary_counter == 3

    def is_shiny(frame: numpy.ndarray) -> bool:
        crop = frame[382:417, 97:184]
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        thres = cv2.inRange(hsv, (168, 25, 25), (172, 255, 255))
        count = numpy.count_nonzero(thres)
        ret = count > 0
        print(f'is shiny? {ret} ({count} reds)')
        return ret

    reward_header = all_match(
        match_px(Point(y=61, x=665), Color(b=16, g=16, r=16)),
        match_text(
            'Reward',
            Point(y=66, x=874),
            Point(y=101, x=992),
            invert=True,
        ),
    )

    states: States = {
        'INITIAL': (
            (
                all_match(
                    match_px(Point(y=701, x=31), Color(b=239, g=88, r=44)),
                    match_px(Point(y=701, x=14), Color(b=234, g=234, r=234)),
                ),
                do(Wait(.5), Press('A')),
                'MAYBE_PAY_TAX',
            ),
        ),
        'MAYBE_PAY_TAX': (
            (
                match_text(
                    'Would you like to embark upon a',
                    Point(y=596, x=272),
                    Point(y=637, x=763),
                    invert=False,
                ),
                do(
                    Press('A'), Wait(.75),
                    Press('A'), Wait(.75),
                    Press('A'), Wait(.75),
                    Press('A'), Wait(.75),
                ),
                'NO_INVITE',
            ),
            (
                match_text(
                    'you quit your last',
                    Point(y=591, x=333),
                    Point(y=637, x=596),
                    invert=False,
                ),
                do(
                    Press('A'), Wait(.75),
                    Press('A'), Wait(.75),
                    Press('A'), Wait(.75),
                ),
                'INITIAL',
            ),
            (
                match_text(
                    'It seems that you keep quitting your',
                    Point(y=596, x=272),
                    Point(y=636, x=799),
                    invert=False,
                ),
                do(
                    Press('A'), Wait(.75),
                    Press('A'), Wait(.75),
                    Press('A'), Wait(.75),
                    Press('A'), Wait(.75),
                    should_reset_record,
                    Press('A'), Wait(1),
                    Press('A'), Wait(1),
                ),
                'INITIAL',
            ),
        ),
        'NO_INVITE': (
            (
                match_text(
                    'Invite Others',
                    Point(y=496, x=930),
                    Point(y=529, x=1086),
                    invert=True,
                ),
                do(Press('s'), Wait(.5), Press('A')),
                'WAIT_FOR_SELECT_POKEMON',
            ),
        ),
        'WAIT_FOR_SELECT_POKEMON': (
            (
                match_text(
                    'Selecting',
                    Point(y=250, x=344),
                    Point(y=278, x=434),
                    invert=False,
                ),
                do(Press('+'), Wait(.5), pick_pokemon),
                'OVERWORLD',
            ),
        ),
        'OVERWORLD': (
            (
                all_match(
                    match_px(Point(y=87, x=767), Color(b=29, g=233, r=36)),
                    match_px(Point(y=364, x=1150), Color(b=16, g=16, r=16)),
                    match_px(Point(y=364, x=1164), Color(b=234, g=234, r=234)),
                    match_text(
                        'Info',
                        Point(y=360, x=1196),
                        Point(y=381, x=1236),
                        invert=False,
                    ),
                ),
                do(
                    Press('Y'), Wait(1),
                    Press('w'), Wait(.5),
                    Press('A'), Wait(1),
                    catch_record,
                    Press('B'), Wait(1),
                    Press('B'), Wait(1),
                ),
                'BATTLE',
            ),
            (
                all_match(
                    match_px(Point(y=709, x=1111), Color(b=16, g=16, r=16)),
                    match_px(Point(y=646, x=503), Color(b=59, g=59, r=59)),
                    match_text(
                        'Vote',
                        Point(y=693, x=1222),
                        Point(y=716, x=1271),
                        invert=True,
                    ),
                ),
                route,
                'OVERWORLD',
            ),
            (
                all_match(
                    match_px(Point(y=524, x=1034), Color(b=234, g=234, r=234)),
                    match_px(Point(y=614, x=868), Color(b=59, g=59, r=59)),
                    match_text(
                        'you interested in swapping',
                        Point(y=591, x=406),
                        Point(y=626, x=713),
                        invert=True,
                    ),
                ),
                do(Press('B'), Wait(3)),
                'OVERWORLD',
            ),
            (
                all_match(
                    match_px(Point(y=173, x=1207), Color(b=228, g=170, r=27)),
                    match_text(
                        'hold one item!',
                        Point(y=64, x=347),
                        Point(y=97, x=517),
                        invert=True,
                    ),
                ),
                do(Press('A'), Wait(3)),
                'OVERWORLD',
            ),
        ),
        'BATTLE': (
            (
                all_match(
                    match_px(Point(y=516, x=1241), Color(b=208, g=164, r=27)),
                    match_text(
                        'Cheer',
                        Point(y=503, x=1054),
                        Point(y=538, x=1138),
                        invert=True,
                    ),
                ),
                Press('A'),
                'BATTLE',
            ),
            (reward_header, do(), 'REWARD'),
            (
                all_match(
                    match_px(Point(y=61, x=665), Color(b=16, g=16, r=16)),
                    match_text(
                        'Caught',
                        Point(y=64, x=947),
                        Point(y=107, x=1064),
                        invert=True,
                    ),
                ),
                do(
                    Press('A'), Wait(.5),
                    Press('s'), Wait(.5),
                    Press('A'), Wait(2),
                    summary_counter_reset,
                ),
                'CHECK_SUMMARY',
            ),
            (
                all_match(
                    match_px(Point(y=600, x=901), Color(b=234, g=234, r=234)),
                    match_text(
                        'a bit of a letdown',
                        Point(y=594, x=419),
                        Point(y=629, x=688),
                        invert=False,
                    ),
                ),
                do(),
                'DO_NOT_REMEMBER',
            ),
            (
                all_match(
                    match_px(Point(y=619, x=1075), Color(b=16, g=16, r=16)),
                    match_text(
                        'Catch',
                        Point(y=611, x=1108),
                        Point(y=642, x=1187),
                        invert=True,
                    ),
                ),
                do(),
                'DECIDE_CATCH',
            ),
            (
                all_match(
                    any_match(
                        match_px(
                            Point(y=492, x=1196),
                            Color(b=103, g=74, r=243),
                        ),
                        # different color while dynamaxed for some reason???
                        match_px(
                            Point(y=493, x=1195),
                            Color(b=52, g=0, r=175),
                        ),
                    ),
                    match_px(Point(y=498, x=1169), Color(b=16, g=16, r=16)),
                    match_text(
                        'Fight',
                        Point(y=502, x=1056),
                        Point(y=539, x=1123),
                        invert=True,
                    ),
                ),
                do(Press('A'), Wait(.75)),
                'MAYBE_DMAX',
            ),
        ),
        'MAYBE_DMAX': (
            (
                all_match(
                    match_px(Point(y=585, x=729), Color(b=77, g=0, r=195)),
                    match_text(
                        'DYNAMAX',
                        Point(y=615, x=694),
                        Point(y=647, x=825),
                        invert=True,
                    ),
                ),
                do(Press('a'), Wait(.5), Press('A'), Wait(.75)),
                'BEST_MOVE',
            ),
            (always_matches, do(), 'BEST_MOVE'),
        ),
        'BEST_MOVE': (
            (always_matches, best_move, 'BATTLE'),
        ),
        'DECIDE_CATCH': (
            (
                catch_check,
                do(Press('A'), Wait(.75), Press('A')),
                'WAIT_FOR_DECIDE_SWAP',
            ),
            (
                always_matches,
                do(Press('s'), Wait(.75), Press('A')),
                'OVERWORLD',
            ),
        ),
        'WAIT_FOR_DECIDE_SWAP': (
            (
                all_match(
                    match_px(Point(y=22, x=485), Color(b=184, g=89, r=217)),
                    match_text(
                        'want to swap',
                        Point(y=558, x=807),
                        Point(y=588, x=957),
                        invert=True,
                    ),
                ),
                do(Press('+'), Wait(.75), swap_record),
                'DECIDE_SWAP',
            ),
        ),
        'DECIDE_SWAP': (
            (swap_check, Press('A'), 'OVERWORLD'),
            (always_matches, Press('B'), 'OVERWORLD'),
        ),
        'REWARD': (
            (
                reward_header,
                do(Press('A'), Wait(5), should_reset_clear),
                'WAIT_FOR_AFTER_TEXT',
            ),
        ),
        'WAIT_FOR_AFTER_TEXT': (
            (
                match_px(Point(y=585, x=289), Color(b=234, g=234, r=234)),
                do(),
                'DO_NOT_REMEMBER',
            ),
        ),
        'DO_NOT_REMEMBER': (
            (
                match_px(Point(y=585, x=289), Color(b=234, g=234, r=234)),
                do(Press('B'), Wait(.75)),
                'DO_NOT_REMEMBER',
            ),
            (always_matches, do(), 'INITIAL'),
        ),
        'CHECK_SUMMARY': (
            (
                summary_counter_enough,
                do(),
                'SHOULD_WE_RESET',
            ),
            (is_shiny, do(), 'ALARM'),
            (
                always_matches,
                do(Press('s'), Wait(.5), summary_counter_increment),
                'CHECK_SUMMARY',
            ),
        ),
        'SHOULD_WE_RESET': (
            (should_reset_check, reset, 'STARTUP'),
            (
                always_matches,
                do(
                    Press('B'), Wait(2),
                    Press('B'), Wait(1.5),
                    Press('A'), Wait(.75),
                    Press('A'), Wait(.75),
                ),
                'REWARD',
            ),
        ),
        'STARTUP': (
            (
                all_match(
                    match_px(Point(y=61, x=745), Color(b=217, g=217, r=217)),
                    match_text(
                        'Start',
                        Point(y=669, x=1158),
                        Point(y=700, x=1228),
                        invert=False,
                    ),
                ),
                do(Press('A'), Wait(1.5)),
                'WAIT_FOR_START',
            ),
        ),
        'WAIT_FOR_START': (
            (
                match_px_exact(Point(700, 30), Color(b=16, g=16, r=16)),
                do(),
                'START',
            ),
            (
                match_text(
                    'Downloadable content cannot be played.',
                    Point(y=266, x=374),
                    Point(y=312, x=904),
                    invert=False,
                ),
                do(Press('a'), Wait(.2), Press('A'), Wait(.5)),
                'STARTUP',
            ),
        ),
        'START': (
            (
                match_px_exact(Point(700, 30), Color(b=16, g=16, r=16)),
                do(),
                'START',
            ),
            (
                always_matches,
                do(
                    Wait(.5),
                    Press('A'),
                    Wait(1),
                    Press('A'),
                ),
                'INITIAL',
            ),
        ),
        **alarm('ALARM', quiet=args.quiet),
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=vid, ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
