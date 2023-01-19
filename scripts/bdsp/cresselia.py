import argparse
from typing import Optional

from lib import Button
from lib import Color
from lib import Frame
from lib import LOADING_SCREEN_POS
from lib import RequirementsAction
from lib.pokemon.bdsp import BDSPScript
from lib.pokemon.bdsp import SHORT_DIALOG_POS_2


_Requirements: tuple[str, ...] = (
	"Stand in front of cresselia",
	"Map app active in poketch",
	"Repel in first slot in bag",
	"First pokemon in party Level < 50 but > 10 (to only encounter cresselia with repel)",
	"X menu",
	"   Map tile at (2, 1)",
	"   Bag tile at (1, 3)",
)
Parser = argparse.ArgumentParser(add_help=False)
Parser.add_argument("-r", "--requriements", action=RequirementsAction, help="print out the requirements for a script", requirements=_Requirements)


class Script(BDSPScript):
	@property
	def target(self) -> str:
		return "Cresselia"

	def getName(self) -> Optional[str]:
		return "Cresselia"

	def main(self, e: int) -> tuple[int, Frame]:
		self.resetGame()
		self.awaitInGame()

		self.press(Button.BUTTON_A)
		self.awaitFlash(LOADING_SCREEN_POS, Color.Black(), 5)
		self.waitAndRender(1)
		self.awaitColor(SHORT_DIALOG_POS_2, Color.White())

		self.waitAndRender(1)
		self.press(Button.BUTTON_A)
		self.waitAndRender(1)
		self.press(Button.BUTTON_A)

		self.awaitFlash(LOADING_SCREEN_POS, Color.Black())

		self.waitAndRender(1)

		self._ser.write(b"s")
		self.awaitFlash(LOADING_SCREEN_POS, Color.White())
		self.press(Button.EMPTY)

		return (e + 1, self.resetRoamer(e))
