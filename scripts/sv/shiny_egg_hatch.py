from __future__ import annotations

import argparse
import functools
import os.path
import time

import cv2
import numpy
import serial

from scripts.engine import all_match
from scripts.engine import any_match
from scripts.engine import always_matches
from scripts.engine import Color
from scripts.engine import do
from scripts.engine import getframe
from scripts.engine import match_px
from scripts.engine import match_text
from scripts.engine import Point
from scripts.engine import Press
from scripts.engine import require_tesseract
from scripts.engine import run
from scripts.engine import SERIAL_DEFAULT
from scripts.engine import Wait

# Initial State: 
# IMPORTANT: Plese read all steps here to insure the script functions normally:
# 1) Have the parents you want in your party (you may have up to 6)
# 2) Make sure you have all sandwich recipes and that you have enough ingredients
# for sandwich 25.
# 3) Have your Flame Body / Magma Armor Pokemon in slot 1 of the box before the
# currently saved one
# 4) Have x number of boxes empty starting at the current one.
# 5) Have nicknames off and auto send to boxes
# 6) Save in front of Area Zero Gate (the rocky section outside)
# 7) Progress up to overworld.
# 8) IMPORTANT: to detect shinies, set the background color of boxes that will
# recieve shinies to BACKGROUND 15, or change the images in shiny_check_images.
# 9) Start script, including connecting to controller

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--serial', default=SERIAL_DEFAULT)
    parser.add_argument('--boxes', type=int, required=True)
    parser.add_argument('--silent', type=bool, default=False)
    args = parser.parse_args()

    require_tesseract()

    vid = cv2.VideoCapture(0)
    vid.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    vid.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    start_time = 0.0
    shiny = False
    alarm = False
    box = 0
    check_box = 0
    column = 0
    egg_count = 0
    eggs = 5

    def set_start(vid: object, ser: object) -> None:
        nonlocal start_time
        start_time = time.monotonic()

    def increment_egg_count(vid: object, ser: object) -> None:
        nonlocal egg_count
        egg_count += 1
        print(f'DEBUG: You have {egg_count} eggs currently')

    def reset_egg_count(vid: object, ser: object) -> None:
        nonlocal egg_count
        egg_count = 0

    def restart_eggs(frame: object) -> bool:
        return time.monotonic() > start_time + 30 * 60 
     

    def set_shiny() -> None:
        nonlocal shiny, alarm
        if not shiny:
            shiny = True
        if shiny and not args.silent and not alarm: 
            # alarm
            do(Press('!'),
            Wait(1),
            Press('.'),
            Wait(.5),
            Press('!'),
            Wait(1),
            Press('.'),
            Wait(.5),
            Press('!'),
            Wait(1),
            Press('.'),
            Wait(.5),
            )(vid, ser)
            alarm = True
            print('DEBUG: *****SHINY DETECTED!*****')

    def are_we_done(frame: object) -> bool:
        return egg_count >= args.boxes * 30

    def bye(vid: object, ser: object) -> None:
        do(# save the game, exit
            Press('B'), Wait(2),
            Press('R'), Wait(2),
            Press('A'), Wait(3),
            Press('A'), Wait(1),
            Press('H'))(vid, ser)
        raise SystemExit

    def eggs_done(frame: object) -> bool:
        return eggs == 0

    def egg_hatched(vid: object, ser: object) -> None:
        nonlocal eggs
        eggs -= 1

    def tap_w(vid: object, ser: serial.Serial) -> None:
        ser.write(b'w0')

    def tap_s(vid: object, ser: serial.Serial) -> None:
        ser.write(b's0')

    def start_left(vid: object, ser: serial.Serial) -> None:
        ser.write(b'#')

    def clear_left(vid: object, ser: serial.Serial) -> None:
        ser.write(b'0')

    def move_to_column(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        for _ in range(column):
            do(Press('d'), Wait(.4))(vid, ser)

    def pick_up_new_column(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        nonlocal box, column, eggs
        eggs = 5
        if column == 5:
            column = 0
            box += 1
            do(
                Press('R'), Wait(.5),
                Press('d'), Wait(.4),
                Press('d'), Wait(.4),
            )(vid, ser)
        else:
            column += 1
            do(Press('d'), Wait(.5))(vid, ser)

        select(vid, ser)

        for _ in range(column + 1):
            do(Press('a'), Wait(.4))(vid, ser)

        do(Press('s'), Wait(.4), Press('A'), Wait(.5))(vid, ser)

    def hatched_all_eggs(frame: object) -> bool:
        return box == args.boxes - 1 and column == 5 and eggs == 0

    def reset_vars(vid: object, ser: object) -> None:
        nonlocal box, check_box, column, eggs, egg_count
        box = 0
        check_box = 0
        column = 0
        egg_count = 0
        eggs = 5
        print('DEBUG: REACHED RESTART')

    def _extract_shiny_icon(
        im: numpy.ndarray,
        dims: tuple[int, int, int],
        ) -> numpy.ndarray:
            im = cv2.resize(im, (dims[1], dims[0]))

            top_left = Point(y=60, x=1112).norm(dims)
            bottom_right = Point(y=92, x=1163).norm(dims)
            crop = im[top_left.y:bottom_right.y, top_left.x:bottom_right.x]

            color = numpy.array([71, 51, 39])
            t = numpy.array([1, 1, 1])
            return cv2.inRange(crop, color - t * 20, color + t * 20)

    @functools.lru_cache
    def _get_shiny_images(
            dims: tuple[int, int, int],
    ) -> tuple[tuple[str, numpy.ndarray], ...]:
        types_dir = os.path.join(os.path.dirname(__file__), 'shiny_check_images')

        return tuple(
            (tp, _extract_shiny_icon(cv2.imread(os.path.join(types_dir, tp)), dims))
            for tp in os.listdir(types_dir)
        )

    def check_shiny(vid: cv2.VideoCapture, ser: serial.Serial) -> None:
        nonlocal check_box

        def _detect_shiny() -> None:
            frame = getframe(vid)

            shiny_images = _get_shiny_images(frame.shape)

            sh_im = _extract_shiny_icon(frame, frame.shape)
            _, sh = max(((im == sh_im).mean(), fname) for fname, im in shiny_images)
            print(f'{sh}')
            if sh == 'shiny.png':
                set_shiny()

        for direction in 'dadad':
            _detect_shiny()
            for _ in range(5):
                do(Press(direction), Wait(1))(vid, ser)
                _detect_shiny()
            do(Press('s'), Wait(.75))(vid, ser)

        for _ in range(2):
            do(Press('s'), Wait(.75))(vid, ser)
        for _ in range(5):
            do(Press('a'), Wait(.75))(vid, ser)

        do(Press('R'), Wait(.75))(vid, ser)
        check_box += 1

    def check_done(frame: object) -> bool:
        return check_box == args.boxes

    def check_done_w_shiny(frame: object) -> bool:
        return shiny and (check_box == args.boxes)

    reorient = do(
        Wait(1),
        Press('+'), Wait(1),
        Press('z'), Wait(.5), Press('L'), Wait(.5),
        Press('w', duration=2.5),
        # center camera
        Press('L'), Wait(.1),
    )

    tap_all_directions = do(
        Press('d'), Wait(.5), 
        Press('a'), Wait(.5),
        Press('w'), Wait(.5),
        Press('s'), Wait(.5), 
    )

    select = do(
        Press('-'), Wait(.5), Press('s', duration=.8), Wait(.4),
        Press('A'), Wait(.5),
    )

    states = {
        'INITIAL': (
            (
                any_match(
                    match_px(Point(y=598, x=1160), Color(b=17, g=203, r=244)),
                    match_px(Point(y=598, x=1160), Color(b=0, g=205, r=255)),
                ),
                do(
                    Wait(1),
                    # center camera
                    Press('L'), Wait(.1),
                    # open menu
                    Press('X'), Wait(1), Press('d'), Wait(1),
                ),
                'MENU',
            ),
        ),
        'MENU': (
            (
                any_match(
                    match_px(Point(y=292, x=1085), Color(b=30, g=185, r=210)),
                    match_px(Point(y=288, x=1027), Color(b=0, g=204, r=255)),
                ),
                do(
                    # press A on picnic menu
                    Wait(1), Press('A'), Wait(10),
                    # walk up to picnic
                    Press('w', duration=.5),
                    # sandwich time
                    Press('A'), Wait(1.5), Press('A'), Wait(5),
                ),
                'FIND_25',
            ),
            (always_matches, do(Press('s'), Wait(.5)), 'MENU'),
        ),
        'FIND_25': (
            (
                match_text(
                    '25',
                    Point(y=376, x=21),
                    Point(y=403, x=58),
                    invert=True,
                ),
                do(
                    # select sandwich
                    Press('A'), Wait(2),
                    # select pick
                    Press('A'), Wait(10),
                    # cheese 1
                    Press('w', duration=1),
                    Press('s', duration=.2),
                    Press('@', duration=.5),
                    Wait(1),
                    # cheese 2
                    Press('w', duration=1),
                    Press('s', duration=.2),
                    Press('@', duration=.5),
                    Wait(1),
                    # cheese 3
                    Press('w', duration=1),
                    Press('s', duration=.2),
                    Press('@', duration=.5),
                    Wait(3),
                    # bread
                    Press('A'), Wait(3),
                    # pick
                    Press('A'), Wait(10),
                    # confirm
                    Press('A'), Wait(25),
                    # noice
                    Press('A'), Wait(5),
                    # move around the table
                    Wait(.5),
                    Press('d', duration=.1), Wait(.2),
                    Press('L'), Wait(.2),
                    Press('w', duration=.4), Wait(.5),

                    Press('a', duration=.1), Wait(.2),
                    Press('L'), Wait(.2),
                    Press('w', duration=.7), Wait(.5),

                    Press('z', duration=.1), Wait(.2),
                    Press('L'), Wait(.2),
                    Press('w', duration=.5), Wait(.5),

                    Press('A'), Wait(1),
                ),
                'VERIFY_BASKET',
            ),
            (always_matches, do(Press('s'), Wait(1)), 'FIND_25'),
        ),
        'VERIFY_BASKET': (
            (
                match_text(
                    'You peeked inside the basket!',
                    Point(y=546, x=353),
                    Point(y=588, x=706),
                    invert=True,
                ),
                do(set_start, Wait(.1)),
                'MASH_A',
            ),
            (
                # if it fails, go back to the beginning
                always_matches,
                do(Press('B'), Wait(2), Press('Y'), Wait(.5), Press('A'), Wait(10),),
                'INITIAL',
            ),
        ),
        'MASH_A': (
            ( 
                match_text(
                    'You took the Egg!',
                    Point(y=540, x=351),
                    Point(y=640, x=909),
                    invert=True,
                ),
                do(increment_egg_count, Press('A'), Wait(1)),
                'MASH_A',
            ),
            (
                all_match(
                    match_px(Point(y=628, x=351), Color(b=49, g=43, r=30)),
                    match_px(Point(y=630, x=893), Color(b=49, g=43, r=30)),
                    match_px(Point(y=546, x=348), Color(b=49, g=43, r=30)),
                ),
                do(Press('A'), Wait(1)),
                'MASH_A',
            ),
            (always_matches, do(), 'WAIT'),
        ),
        'WAIT': (
            (
                # if we have either equal or more eggs than our boxes, go to hatching stage
                are_we_done,
                do(
                    reset_egg_count,
                    # exit picnic
                    Press('Y'), Wait(.5), Press('A'), Wait(10),
                    # open menu
                    Press('X'), Wait(1)
                ),
                'MENU_SWITCH',
            ),
            (
                # if the timer runs out, restart the egg grabbing sequence
                restart_eggs,
                do(Press('Y'), Wait(.5), Press('A'), Wait(10)),
                'INITIAL',
            ),
            (always_matches, do(Wait(30), Press('A'), Wait(.5)), 'MASH_A'),
        ),

        'MENU_SWITCH': (
            (
                any_match(
                    match_px(Point(y=241, x=1161), Color(b=28, g=183, r=209)),
                    match_px(Point(y=234, x=1151), Color(b=0, g=204, r=255)),
                ),
                do(
                    # press A on boxes
                    Wait(1), Press('A'), Wait(3),
                    # go back to previous box
                    Press('L'), Wait(.5),
                    # select mon
                    Press('A'), Wait(.5), Press('A'), Wait(.5),
                    # switch first mon
                    Press('a'), Wait(.5), Press('A'), Wait(.5),
                    Press('s'), Wait(.5),
                    # move second mon
                    select,
                    Press('d'), Wait(.5), Press('d'), Wait(.5), Press('w'), Wait(.5), Press('A'), Wait(.5),
                    # re-orient, exit menu
                    Press('a'), Wait(.5), Press('R'), Wait(.5), Press('B'), Wait(3), Press('B'), Wait(3),
                ),
                'INITIAL_HATCH',
            ),
            (always_matches, do(Press('s'), Wait(.5)), 'MENU_SWITCH'),

        ),


        'INITIAL_HATCH': (
            (
                any_match(
                    match_px(Point(y=598, x=1160), Color(b=17, g=203, r=244)),
                    match_px(Point(y=598, x=1160), Color(b=0, g=205, r=255)),
                ),
                do(Press('Y'), Wait(5),
                # do the wiggle wiggle
                tap_all_directions,
                Press('l'), Wait(1), Wait(.5), Wait(.5)),
                'REORIENT_INITIAL',
            ),
        ),
        'REORIENT_INITIAL': (
            (
                match_text(
                    'Map',
                    Point(y=90, x=226),
                    Point(y=124, x=276),
                    invert=False,
                ),
                do(Press('A'), Wait(.1)),
                'REORIENT_INITIAL',
            ),
            (
                any_match(
                    match_px(Point(y=598, x=1160), Color(b=17, g=203, r=244)),
                    match_px(Point(y=598, x=1160), Color(b=0, g=205, r=255)),
                ),
                do(
                    reorient,
                    # open menu
                    Press('X'), Wait(1),
                ),
                'MENU_HATCH',
            ),
        ),
        'MENU_HATCH': (
            (
                any_match(
                    match_px(Point(y=241, x=1161), Color(b=28, g=183, r=209)),
                    match_px(Point(y=234, x=1151), Color(b=0, g=204, r=255)),
                ),
                do(
                   # press A on boxes menu
                    Wait(1), Press('A'), Wait(3),
                    # select first column
                    select,
                    # move it over
                    Press('a'), Wait(.4), Press('s'), Wait(.4),
                    Press('A'), Wait(.5),
                    # out to main menu
                    Press('B'), Wait(2),
                    Press('B'), Wait(1),
                ),
                'HATCH_5',
            ),
            (always_matches, do(Press('s'), Wait(.5)), 'MENU_HATCH'),
        ),
        'HATCH_5': (
            (
                all_match(
                    match_px(Point(y=541, x=930), Color(b=49, g=43, r=30)),
                    match_text(
                        'Oh?',
                        Point(y=546, x=353),
                        Point(y=586, x=410),
                        invert=True,
                    ),
                ),
                do(Press('A'), Wait(8)),
                'HATCH_1',
            ),
            (eggs_done, clear_left, 'NEXT_COLUMN'),
            (always_matches, do(start_left, Wait(1)), 'HATCH_5'),
        ),
        'HATCH_1': (
            (
                all_match(
                    match_px(Point(y=541, x=930), Color(b=49, g=43, r=30)),
                    match_px(Point(y=624, x=370), Color(b=49, g=43, r=30)),
                    match_px(Point(y=523, x=330), Color(b=37, g=202, r=241)),
                ),
                do(Wait(1), Press('A'), Wait(5), egg_hatched),
                'HATCH_5',
            ),
        ),
        'NEXT_COLUMN': (
            (hatched_all_eggs, do(
                # we need to move the last eggs into the column for checking
                # open menu, into boxes
                Wait(1), Press('X'), Wait(2), Press('A'), Wait(3),
                # select party to put it back
                Press('a'), Wait(.5), Press('s'), Wait(.5),
                select,
                # position in first column of box
                Press('d'), Wait(.5), Press('w'), Wait(.5),
                # put the hatched ones back
                move_to_column, Press('A'), Wait(.5),
                # out to main menu
                Press('B'), Wait(3),
            ), 'CHECK_SHINY_MENU'),
            (
                always_matches,
                do(
                    # open menu, into boxes
                    Wait(1), Press('X'), Wait(2), Press('A'), Wait(3),
                    # select party to put it back
                    Press('a'), Wait(.5), Press('s'), Wait(.5),
                    select,
                    # position in first column of box
                    Press('d'), Wait(.5), Press('w'), Wait(.5),
                    # put the hatched ones back and pick up new column
                    move_to_column, Press('A'), Wait(.5),
                    pick_up_new_column,

                ),
                'TO_OVERWORLD',
            ),
        ),
        'TO_OVERWORLD': (
            (
                any_match(
                    match_px(Point(y=598, x=1160), Color(b=17, g=203, r=244)),
                    match_px(Point(y=598, x=1160), Color(b=0, g=205, r=255)),
                ),
                do(Press('Y'), Wait(5), tap_w, tap_s, Wait(.5)),
                'REORIENT_HATCH',
            ),
            (always_matches, do(Press('B'), Wait(1)), 'TO_OVERWORLD'),
        ),
        'REORIENT_HATCH': (
            (
                match_text(
                    'Map',
                    Point(y=90, x=226),
                    Point(y=124, x=276),
                    invert=False,
                ),
                do(Press('A'), Wait(.1)),
                'REORIENT_HATCH',
            ),
            (
                match_px(Point(y=598, x=1160), Color(b=0, g=205, r=255)),
                reorient,
                'HATCH_5',
            ),
        ),
        'CHECK_SHINY_MENU': (
            (
                any_match(
                    match_px(Point(y=241, x=1161), Color(b=28, g=183, r=209)),
                    match_px(Point(y=234, x=1151), Color(b=0, g=204, r=255)),
                ),
                # press A on boxes menu
                do(Wait(1), Press('A'), Wait(3), 
                # action to make sure wallpaper shows up
                Press('A'), Wait(1), Press('A'), Wait(1), Press('A'), Wait(1)),
                'CHECK_SHINY',
            ),
            (always_matches, do(Press('s'), Wait(.75)), 'CHECK_SHINY_MENU'),
        ),
        'CHECK_SHINY': (
            (check_done_w_shiny, bye, 'EXIT'),
            (check_done, reset_vars, 'RESET_SEQUENCE'),
            (always_matches, check_shiny, 'RESET_TIMEOUT'),
        ),
        'RESET_TIMEOUT': (
            (always_matches, do(Wait(1)), 'CHECK_SHINY'),
        ),
        'RESET_SEQUENCE': (
            (
                # only restart the game if no shiny
                lambda frame: not shiny, 
                do(
                    # hard reset the game via home
                    Press('H'), Wait(1),
                    Press('X'), Wait(.5),
                    Press('A'), Wait(4),
                    # restart the game
                    Press('A'), Wait(2),
                    Press('A'), Wait(20),
                    Press('A'), Wait(22)
                ),
                'INITIAL'
            ),
            # catch all in case for some god forsaken reason it enters this stage with a shiny detected
            (always_matches, bye, 'INVALID')
        )
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=vid, ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
