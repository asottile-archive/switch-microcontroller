from __future__ import annotations

from scripts.engine import always_matches
from scripts.engine import bye
from scripts.engine import do
from scripts.engine import Press
from scripts.engine import States
from scripts.engine import Wait


def alarm(name: str, *, quiet: bool) -> States:
    if quiet:
        return {
            name: (
                (
                    always_matches,
                    do(
                        Press('H'), Wait(1),
                        Press('H', duration=1), Wait(.5),
                        Press('A'),
                        bye,
                    ),
                    'UNREACHABLE',
                ),
            ),
        }
    else:
        return {
            name: (
                (
                    always_matches,
                    do(Press('!'), Wait(.25), Press('.'), Wait(.25)),
                    name,
                ),
            ),
        }
