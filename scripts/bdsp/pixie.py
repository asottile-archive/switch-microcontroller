import argparse
from typing import Optional

from lib import Button
from lib import Color
from lib import Frame
from lib import LOADING_SCREEN_POS
from lib import RequirementsAction
from lib.pokemon.bdsp import BDSPScript


_Requirements: tuple[str, ...] = ("Stand in front of Azelf/Uxie",)
Parser = argparse.ArgumentParser(add_help=False)
Parser.add_argument("-r", "--requriements", action=RequirementsAction, help="print out the requirements for a script", requirements=_Requirements)
Parser.add_argument("target", type=str, choices=("Azelf", "Uxie"), help="pixie to hunt (used for tracking)")


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

		self.press(Button.BUTTON_A)
		self.waitAndRender(2)
		self.press(Button.BUTTON_A)
		self.waitAndRender(2.5)

		self.awaitFlash(LOADING_SCREEN_POS, Color.White())

		# encounter dialog
		return (e + 1, self.checkShinyDialog(e, 1.5))
