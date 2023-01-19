import argparse
from typing import Optional

from lib import Button
from lib import Color
from lib import Frame
from lib import LOADING_SCREEN_POS
from lib import RequirementsAction
from lib.pokemon.bdsp import BDSPScript


_Requirements: tuple[str, ...] = ("Stand in front of Dialga/Palkia",)
Parser = argparse.ArgumentParser(add_help=False)
Parser.add_argument("-r", "--requriements", action=RequirementsAction, help="print out the requirements for a script", requirements=_Requirements)
Parser.add_argument("target", type=str, choices=("Dialga", "Palkia"), help="legendary to hunt (used for tracking)")


class Script(BDSPScript):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self._target = kwargs.pop("target")

	@property
	def target(self) -> str:
		return self._target

	def getName(self) -> Optional[str]:
		return self._target

	def main(self, e: int) -> tuple[int, Frame]:
		self.resetGame()
		self.awaitInGame()

		# walk towards legendary
		self.press(Button.L_UP, duration=0.5)
		self.waitAndRender(2)
		self.pressN(Button.BUTTON_B, 3, 0.5, render=True)

		# flash to enter battle
		self.awaitFlash(LOADING_SCREEN_POS, Color.White())

		# flash inside battle
		self.awaitFlash(LOADING_SCREEN_POS, Color.White())

		# encounter dialog
		return (e + 1, self.checkShinyDialog(e, 1.5))
