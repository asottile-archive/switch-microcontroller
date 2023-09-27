from __future__ import annotations

import argparse
import contextlib
import datetime

import cv2
import serial

from scripts._alarm import alarm
from scripts._clock import clock
from scripts._clock import current_dt
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
from scripts.engine import match_text
from scripts.engine import Point
from scripts.engine import Press
from scripts.engine import run
from scripts.engine import SERIAL_DEFAULT
from scripts.engine import States
from scripts.engine import Wait
from scripts.swsh._bootup import bootup
from scripts.swsh._bootup import game_start
from scripts.swsh._bootup import world
from scripts.swsh._dialog_shiny_check import dialog
from scripts.swsh._dialog_shiny_check import dialog_shiny_check


class Done(RuntimeError):
    pass


def done(vid: object, ser: object) -> None:
    raise Done


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default=SERIAL_DEFAULT)
    parser.add_argument('--quiet', action='store_true'),
    args = parser.parse_args()

    dt = datetime.datetime.today()

    def determine_date(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        nonlocal dt
        dt = current_dt(vid, ser).replace(hour=1, minute=0)
        print(f'current date is {dt.date()}')

    def increment_date(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        nonlocal dt
        dt = dt + datetime.timedelta(days=1)

        states: States = {
            **clock(dt, 'CLOCK_INITIAL', 'CLOCK_END'),
            'CLOCK_END': ((always_matches, done, 'UNREACHABLE'),),
        }

        with contextlib.suppress(Done):
            run(vid=vid, ser=ser, initial='CLOCK_INITIAL', states=states)

    try_ore = any_match(
        world,
        all_match(
            match_px(Point(y=10, x=1083), Color(b=47, g=175, r=218)),
            match_px(Point(y=10, x=1104), Color(b=18, g=164, r=200)),
        ),
    )

    invite_others = all_match(
        match_px(Point(y=457, x=1180), Color(b=16, g=16, r=16)),
        match_text(
            'Invite Others',
            Point(y=440, x=931),
            Point(y=472, x=1093),
            invert=True,
        ),
    )

    ready_to_battle = all_match(
        match_px(Point(y=568, x=1150), Color(b=16, g=16, r=16)),
        match_text(
            'Ready to Battle!',
            Point(y=494, x=902),
            Point(y=531, x=1114),
            invert=False,
        ),
    )

    def do_increment_date(start: str, end: str) -> States:
        return {
            start: (
                (try_ore, do(Press('A'), Wait(.75)), start),
                (invite_others, do(Press('A'), Wait(1)), f'{start}__WAIT'),
            ),
            f'{start}__WAIT': (
                (
                    ready_to_battle,
                    do(Wait(1), Press('H'), Wait(1), increment_date),
                    f'{start}__WAIT_FOR_HOME',
                ),
            ),
            f'{start}__WAIT_FOR_HOME': (
                (
                    all_match(
                        match_px(
                            Point(y=705, x=13),
                            Color(b=217, g=217, r=217),
                        ),
                        match_text(
                            'Continue',
                            Point(y=668, x=1113),
                            Point(y=703, x=1224),
                            invert=False,
                        ),
                    ),
                    do(Press('A'), Wait(.5)),
                    f'{start}__WAIT_FOR_RETURN',
                ),
            ),
            f'{start}__WAIT_FOR_RETURN': (
                (
                    ready_to_battle,
                    do(Wait(1), Press('B'), Wait(.75), Press('A'), Wait(1)),
                    end,
                ),
            ),
        }

    pokemon = ''

    def record_pokemon(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        nonlocal pokemon

        while True:
            text = get_text(
                getframe(vid),
                Point(y=592, x=108),
                Point(y=640, x=497),
                invert=True,
            )
            print(f'raw text: {text}')
            if text.endswith(' appeared!'):
                break

        pokemon = text.removesuffix(' appeared!').lower()

    def is_2_75(frame: object) -> bool:
        return pokemon in {'dragapult'}

    def is_2_5(frame: object) -> bool:
        return pokemon in {'dusknoir', 'togekiss'}

    def is_2_0(frame: object) -> bool:
        return pokemon in {'aromatisse', 'dottler', 'drampa'}

    def is_1_75(frame: object) -> bool:
        return pokemon in {
            'ribombee', 'shiinotic', 'golisopod', 'sliggoo', 'drakloak',
        }

    states: States = {
        'INITIAL': (
            (game_start, determine_date, 'BOOTUP'),
        ),
        **bootup('BOOTUP', 'INCREMENT1'),
        **do_increment_date('INCREMENT1', 'SAVE'),
        'SAVE': (
            (
                world,
                do(
                    Press('X'), Wait(1),
                    Press('R'), Wait(1),
                    Press('A'), Wait(1),
                ),
                'SKIP1',
            ),
        ),
        **do_increment_date('SKIP1', 'SKIP2'),
        **do_increment_date('SKIP2', 'SKIP3'),
        **do_increment_date('SKIP3', 'ENCOUNTER'),
        'ENCOUNTER': (
            (try_ore, do(Press('A'), Wait(.75)), 'ENCOUNTER'),
            (
                invite_others,
                do(
                    Press('s'), Wait(.5),
                    Press('A'), Wait(.75),
                    Press('A'), Wait(5),
                ),
                'WAIT_FOR_DIALOG',
            ),
        ),
        'WAIT_FOR_DIALOG': (
            (dialog, record_pokemon, 'CHOOSE_DIALOG'),
        ),
        'CHOOSE_DIALOG': (
            (is_2_75, do(), 'DIALOG_2_75'),
            (is_2_5, do(), 'DIALOG_2_5'),
            (is_2_0, do(), 'DIALOG_2_0'),
            (is_1_75, do(), 'DIALOG_1_75'),
            (always_matches, do(), 'DIALOG'),
        ),
        **dialog_shiny_check('DIALOG_2_75', 'RESET', 'ALARM', cutoff=2.75),
        **dialog_shiny_check('DIALOG_2_5', 'RESET', 'ALARM', cutoff=2.5),
        **dialog_shiny_check('DIALOG_2_0', 'RESET', 'ALARM', cutoff=2.0),
        **dialog_shiny_check('DIALOG_1_75', 'RESET', 'ALARM', cutoff=1.75),
        **dialog_shiny_check('DIALOG', 'RESET', 'ALARM', cutoff=1.25),
        'RESET': (
            (always_matches, reset, 'BOOTUP'),
        ),
        **alarm('ALARM', quiet=args.quiet),
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=make_vid(), ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
