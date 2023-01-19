import argparse

from lib import Button
from lib import Color
from lib import Frame
from lib import LOADING_SCREEN_POS
from lib import RequirementsAction
from lib.pokemon.bdsp import BDSPScript


_Requirements: tuple[str, ...] = ("stand in front of encounter",)
Parser = argparse.ArgumentParser(add_help=False, description="Reset static encounters in Ramanas Park")
Parser.add_argument("-r", "--requriements", action=RequirementsAction, help="print out the requirements for a script", requirements=_Requirements)
Parser.add_argument("-t", "--target", type=str, action="store", dest="target", default="ramanas", help="manually overwrite target for better displaying")


class Script(BDSPScript):
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)

		self._target = kwargs.pop("target")

	@property
	def target(self) -> str:
		return self._target

	def main(self, e: int) -> tuple[int, Frame]:
		self.resetGame()
		self.awaitInGame()

		self.press(Button.BUTTON_A)
		self.waitAndRender(1.5)
		self.press(Button.BUTTON_A)
		self.waitAndRender(3)

		self.awaitFlash(LOADING_SCREEN_POS, Color.White())

		return (e + 1, self.checkShinyDialog(e, 1))
