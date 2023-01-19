import argparse

from lib import Frame
from lib import RequirementsAction
from lib.pokemon.bdsp import BDSPScript


_Requirements: tuple[str, ...] = ()
Parser = argparse.ArgumentParser(add_help=False)
Parser.add_argument("-r", "--requriements", action=RequirementsAction, help="<TODO>", requirements=_Requirements)


class Script(BDSPScript):
	@property
	def target(self) -> str:
		raise NotImplementedError

	def main(self, e: int) -> tuple[int, Frame]:
		raise NotImplementedError
