import argparse
from typing import Optional

from lib import Button
from lib import Color
from lib import ExecCrash
from lib import Frame
from lib import LOADING_SCREEN_POS
from lib import RequirementsAction
from lib.pokemon.bdsp import BDSPScript
from lib.pokemon.bdsp import SHORT_DIALOG_POS_2


_Requirements: tuple[str, ...] = ("Stand in front of Heatran",)
Parser = argparse.ArgumentParser(add_help=False)
Parser.add_argument("-r", "--requriements", action=RequirementsAction, help="print out the requirements for a script", requirements=_Requirements)


class Script(BDSPScript):
	@property
	def target(self) -> str:
		return "Heatran"

	def getName(self) -> Optional[str]:
		return "Heatran"

	def awaitInGame(self) -> None:
		self.awaitColor(LOADING_SCREEN_POS, Color.Black())
		self.logDebug("startup screen")

		self.whileColor(LOADING_SCREEN_POS, Color.Black(), 0.5, lambda: self.press(Button.BUTTON_A))
		self.logDebug("after startup")

		self.waitAndRender(1)

		if self.getframe().colorAt(LOADING_SCREEN_POS) == Color(41, 41, 41):
			raise ExecCrash

		self.press(Button.BUTTON_A)
		self.waitAndRender(3)

		# loading screen to game
		self.awaitFlash(LOADING_SCREEN_POS, Color.Black())

		self.logDebug("in game")
		self.waitAndRender(1)

	def main(self, e: int) -> tuple[int, Frame]:
		self.resetGame()
		self.awaitInGame()

		self.waitAndRender(2)

		self.press(Button.BUTTON_A)
		self.awaitColor(SHORT_DIALOG_POS_2, Color.White())
		self.waitAndRender(0.5)
		self.press(Button.BUTTON_A)
		self.waitAndRender(0.5)
		self.press(Button.BUTTON_A)

		self.waitAndRender(3)
		self.awaitFlash(LOADING_SCREEN_POS, Color.White())

		self.logDebug("waiting for dialog")

		return (e + 1, self.checkShinyDialog(e, 1.5))
