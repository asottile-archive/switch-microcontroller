from __future__ import annotations

import argparse
import time

import serial

from scripts._alarm import alarm
from scripts._reset import reset
from scripts.engine import Action
from scripts.engine import always_matches
from scripts.engine import do
from scripts.engine import make_vid
from scripts.engine import Press
from scripts.engine import run
from scripts.engine import SERIAL_DEFAULT
from scripts.engine import States
from scripts.engine import Wait
from scripts.swsh._bootup import bootup
from scripts.swsh._dialog_shiny_check import dialog
from scripts.swsh._dialog_shiny_check import dialog_shiny_check


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

    t_timeout = 0.

    def encounter_timeout_start(vid: object, ser: object) -> None:
        nonlocal t_timeout
        t_timeout = time.monotonic()

    def encounter_timeout(frame: object) -> bool:
        return time.monotonic() - t_timeout > 10

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
        ),
        **dialog_shiny_check('DIALOG', 'RESET', 'ALARM'),
        'RESET': (
            (always_matches, reset, 'INITIAL'),
        ),
        **alarm('ALARM', quiet=args.quiet),
    }

    with serial.Serial(args.serial, 9600) as ser:
        run(vid=make_vid(), ser=ser, initial='INITIAL', states=states)


if __name__ == '__main__':
    raise SystemExit(main())
