import argparse
import time
from itertools import cycle

from lib import Button
from lib import Color
from lib import Frame
from lib import LOADING_SCREEN_POS
from lib import RequirementsAction
from lib.pokemon.bdsp import BDSPScript
from lib.pokemon.bdsp import OWN_POKEMON_POS


_Requirements: tuple[str, ...] = (
	"Stand in a patch of grass with enough tiles (could take some time otherwise)",
	"No repel active",
)
Parser = argparse.ArgumentParser(add_help=False)
Parser.add_argument("-r", "--requriements", action=RequirementsAction, help="print out the requirements for a script", requirements=_Requirements)
Parser.add_argument("direction", type=str, choices=("h", "v"), help="direction to run in {(h)orizontal, (v)ertical} direction")
Parser.add_argument("delay", type=float, help="delay betweeen changing direction")


class Script(BDSPScript):
	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)

		direction: str = kwargs.pop("direction")
		assert direction in ("h", "v")

		if direction == "h":
			directions = (Button.L_LEFT, Button.L_RIGHT)
		else:
			directions = (Button.L_UP, Button.L_DOWN)

		self._directions = cycle(directions)

		self._delay = float(kwargs.pop("delay"))

		self.logDebug(f"directions: {directions}")
		self.logDebug(f"delay: {self._delay}")

	@property
	def target(self) -> str:
		return "Random"

	def main(self, e: int) -> tuple[int, Frame]:
		tEnd = time.time()

		while self.getframe().colorAt(LOADING_SCREEN_POS) != Color.White():
			if time.time() > tEnd:
				self._ser.write(next(self._directions).encode())
				tEnd = time.time() + self._delay
		print("encounter!")
		self._ser.write(b"0")

		self.awaitNotColor(LOADING_SCREEN_POS, Color.White())

		# -1 so the +1 later makes it 0
		encounterFrame = self.checkShinyDialog(-1, 1.5)

		self.whileNotColor(OWN_POKEMON_POS, Color.White(), 0.5, lambda: self.press(Button.BUTTON_B))
		self.waitAndRender(1.5)

		self.runFromEncounter()

		return (e + 1, encounterFrame)
