from __future__ import annotations

from scripts._game_crash import GameCrash
from scripts.engine import all_match
from scripts.engine import always_matches
from scripts.engine import Color
from scripts.engine import do
from scripts.engine import match_px
from scripts.engine import match_px_exact
from scripts.engine import match_text
from scripts.engine import Point
from scripts.engine import Press
from scripts.engine import States
from scripts.engine import Wait

game_start = all_match(
    match_px(Point(y=61, x=745), Color(b=217, g=217, r=217)),
    match_text(
        'Start',
        Point(y=669, x=1158),
        Point(y=700, x=1228),
        invert=False,
    ),
)
world = all_match(
    match_px(Point(y=701, x=31), Color(b=239, g=88, r=44)),
    match_px(Point(y=701, x=14), Color(b=234, g=234, r=234)),
)


def bootup(begin: str, end: str) -> States:
    game_crash = GameCrash()

    return {
        begin: (
            (game_start, do(Press('A'), Wait(1.5)), 'BOOTUP_WAIT_FOR_START'),
        ),
        'BOOTUP_WAIT_FOR_START': (
            (
                match_px_exact(Point(700, 30), Color(b=16, g=16, r=16)),
                do(),
                'BOOTUP_START',
            ),
            (
                match_text(
                    'Downloadable content cannot be played.',
                    Point(y=266, x=374),
                    Point(y=312, x=904),
                    invert=False,
                ),
                do(Press('a'), Wait(.2), Press('A'), Wait(.5)),
                begin,
            ),
        ),
        'BOOTUP_START': (
            (
                match_px_exact(Point(700, 30), Color(b=16, g=16, r=16)),
                do(),
                'BOOTUP_START',
            ),
            (
                always_matches,
                do(
                    Wait(.5),
                    Press('A'),
                    Wait(1),
                    Press('A'),
                    game_crash.record,
                ),
                'BOOTUP_WORLD',
            ),
        ),
        'BOOTUP_WORLD': (
            (world, do(), end),
            (game_crash.check, do(Press('A'), Wait(1)), begin),
        ),
    }
