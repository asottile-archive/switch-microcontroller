import argparse
import time
from typing import Any
from typing import Optional

from lib import Button
from lib import Color
from lib import Frame
from lib import RequirementsAction
from lib.pokemon import ExecShiny
from lib.pokemon import LOG_DELAY
from lib.pokemon.bdsp import BDSPScript
from lib.pokemon.bdsp import ENCOUNTER_DIALOG_POS_2
from lib.pokemon.bdsp import OWN_POKEMON_POS


_Requirements: tuple[str, ...] = ("Stand in front of transition into Lake Verity",)
Parser = argparse.ArgumentParser(add_help=False)
Parser.add_argument("-r", "--requriements", action=RequirementsAction, help="print out the requirements for a script", requirements=_Requirements)
Parser.add_argument("target", type=str, choices=("Chimchar", "Piplup", "Turtwig"), help="starter to reset for")


class Script(BDSPScript):
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)

		self._target: str = kwargs.pop("target")
		self._starterOffset = {
			"Turtwig": 0,
			"Chimchar": 1,
			"Piplup": 2,
		}[self._target]

	@property
	def extraStats(self) -> tuple[tuple[str, Any], ...]:
		return super().extraStats + (("Resetting for", self._target),)

	@property
	def target(self) -> str:
		return self._target

	def getName(self) -> Optional[str]:
		return self._target

	def main(self, e: int) -> tuple[int, Frame]:
		self.resetGame()
		self.awaitInGame()

		self.press(Button.L_UP, 0.5)
		self.waitAndRender(1)

		# TODO replace with self.whileColor
		self.pressN(Button.BUTTON_A, 12, 2, render=True)
		self.pressN(Button.BUTTON_A, 4, 5.5, render=True)
		self.pressN(Button.BUTTON_A, 3, 2, render=True)

		print("move to bag")
		for v in (7, 2, 2, 5, 2, 5):
			self.waitAndRender(v)
			self.press(Button.BUTTON_A)

		print("select starter")
		self.press(Button.BUTTON_B)
		self.waitAndRender(2)
		self.pressN(Button.L_RIGHT, self._starterOffset, 1, 0.2, render=True)

		self.press(Button.BUTTON_A)
		self.waitAndRender(2)
		self.press(Button.L_UP)
		self.waitAndRender(0.5)
		self.press(Button.BUTTON_A)

		self.awaitFlash(ENCOUNTER_DIALOG_POS_2, Color.White())

		self.waitAndRender(5)

		self.awaitFlash(ENCOUNTER_DIALOG_POS_2, Color.White())
		self.awaitFlash(ENCOUNTER_DIALOG_POS_2, Color.White())

		encounterFrame = self.getframe()

		t0 = time.time()
		self.awaitColor(OWN_POKEMON_POS, Color.White())
		diff = time.time() - t0

		self.log(LOG_DELAY, f"dialog delay: {diff:.3f}s")

		if 15 > diff > 2:
			raise ExecShiny(e + 1, encounterFrame)
		else:
			return (e + 1, encounterFrame)
