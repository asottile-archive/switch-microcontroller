import argparse
from typing import Optional

from lib import Button
from lib import Color
from lib import Frame
from lib import LOADING_SCREEN_POS
from lib import RequirementsAction
from lib.pokemon.bdsp import BDSPScript


_Requirements: tuple[str, ...] = ("Stand in front of Regigigas",)
Parser = argparse.ArgumentParser(add_help=False)
Parser.add_argument("-r", "--requriements", action=RequirementsAction, help="print out the requirements for a script", requirements=_Requirements)


class Script(BDSPScript):
	@property
	def target(self) -> str:
		return "Regigigas"

	def getName(self) -> Optional[str]:
		return "Regigigas"

	def main(self, e: int) -> tuple[int, Frame]:
		self.resetGame()
		self.awaitInGame()

		self.waitAndRender(1.5)

		self.whileNotColor(LOADING_SCREEN_POS, Color.White(), 0.5, lambda: self.press(Button.BUTTON_A))

		self.waitAndRender(3)

		self.awaitFlash(LOADING_SCREEN_POS, Color.White())
		self.waitAndRender(0.3)

		return (e + 1, self.checkShinyDialog(e, 1))
