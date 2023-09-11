from __future__ import annotations

from scripts._game_crash import GameCrash
from scripts.engine import Color
from scripts.engine import do
from scripts.engine import match_px
from scripts.engine import match_text
from scripts.engine import Point
from scripts.engine import Press
from scripts.engine import States
from scripts.engine import Wait

world = match_px(Point(y=598, x=1160), Color(b=17, g=203, r=244))


def bootup(start: str, success: str, fail: str) -> States:
    game_crash = GameCrash()

    return {
        start: (
            (
                match_text(
                    'Start',
                    Point(y=669, x=1158),
                    Point(y=700, x=1228),
                    invert=False,
                ),
                do(Press('A'), Wait(1)),
                f'{start}__CONTINUE',
            ),
        ),
        f'{start}__CONTINUE': (
            (
                match_text(
                    'PRESS',
                    Point(y=489, x=802),
                    Point(y=530, x=898),
                    invert=True,
                ),
                do(Wait(2), Press('A'), Wait(1), game_crash.record),
                f'{start}__WORLD',
            ),
        ),
        f'{start}__WORLD': (
            (world, do(), success),
            (game_crash.check, do(Press('A'), Wait(1)), fail),
        ),
    }
