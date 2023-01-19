import argparse
import importlib
import logging
import pathlib
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Final
from typing import final
from typing import Optional
from typing import Type

import lib
from lib import Button
from lib import Color
from lib import DB
from lib import Frame
from lib import LOADING_SCREEN_POS
from lib import log
from lib import Pos
from lib.pokemon import ExecShiny
from lib.pokemon import PokemonRunner
from lib.pokemon import RunnerAction
from lib.pokemon.bdsp import BDSPScript


_scripsPath = pathlib.Path(__file__).parent
_scripts = (
	s.name[:-3] for s in filter(
		lambda p: p.is_file() and not p.name.startswith("_") and p.name.endswith(".py"),
		_scripsPath.iterdir(),
	)
)


Parser = argparse.ArgumentParser(add_help=False)
_ScriptsParser = Parser.add_subparsers(dest="script")
for script in _scripts:
	try:
		_p: argparse.ArgumentParser = importlib.import_module(f"scripts.pokemon.bdsp.{script}").Parser
	except ModuleNotFoundError:
		log(logging.WARNING, f"failed to import {script}")
	except AttributeError:
		log(logging.WARNING, f"failed to get Parser from {script}")
	else:
		_ScriptsParser.add_parser(script, parents=(_p,))


def _stripTD(delta: timedelta) -> timedelta:
	return timedelta(days=delta.days, seconds=delta.seconds)


@final
class Runner(PokemonRunner):
	def __init__(self, scriptClass: Type[BDSPScript], args: dict[str, Any], db: DB) -> None:
		self.script: BDSPScript[tuple[int, Frame]]
		super().__init__(scriptClass, args, db)

		self._target: Final[str] = self.script.target
		log(logging.INFO, f"Target: {self._target}")

		self.sendNth: Final[int] = args.pop("sendNth")

		stat: dict[str, int] = self.db.getOrInsert(self.key, {"encounters": 0, "totalTime": 0})
		encountersStart: Final[int] = stat.pop("encounters")
		self._totalTime: Final[int] = stat.pop("totalTime")

		stopAt: Optional[int] = args.pop("stopAt")
		if stopAt is not None:
			if stopAt <= encountersStart:
				stopAt = None
			else:
				log(logging.INFO, f"running until encounters reach {stopAt}")

		self.encountersTotal = encountersStart
		self.encountersCurrent = 0

		self.stopAt: Final[Optional[int]] = stopAt

		self.crashes = 0
		self.lastDuration = timedelta(0, 0)

		self.runStart = datetime.now()

	def __del__(self) -> None:
		self.serial.close()

	@property
	def key(self) -> str:
		return f"pokemon.bdsp.{self._target.lower()}"

	@property
	def encounters(self) -> int:
		return self.encountersTotal

	@property
	def totalTime(self) -> int:
		return int(self._totalTime + (datetime.now() - self.scriptStart).total_seconds())

	def idle(self) -> None:
		self.script.waitAndRender(5)

	def run(self) -> None:
		self.runStart = datetime.now()
		self.encountersTotal, encFrame = self.script(self.encountersTotal)

		if (
			self.script.sendAllEncounters is True or (
				self.script.sendAllEncounters is False and
				self.sendNth >= 2 and
				self.encountersCurrent % self.sendNth == 0
			)
		):
			self.script.logDebug("send screenshot")
			self.script.sendScreenshot(encFrame)

	def runPost(self) -> None:
		self.lastDuration = datetime.now() - self.runStart
		self._runs.append(self.lastDuration.total_seconds())
		self.encountersCurrent += 1

		if self.stopAt is not None and self.encountersTotal >= self.stopAt:
			self.script.logInfo(f"reached target of {self.stopAt} encounters")
			raise lib.ExecStop(self.encountersTotal)

	def onCrash(self, crash: lib.ExecCrash) -> RunnerAction:
		self.crashes += 1

		# to negate that +1 in runPost()
		self.encountersCurrent -= 1

		self.script.log(logging.WARNING, "script crashed, reset state and press Ctrl+C to continue")
		self.script.sendMsg("Script crashed!")
		self.script.idle()

		self.script.waitAndRender(1)

		return RunnerAction.Continue

	def onLock(self, lock: lib.ExecLock) -> RunnerAction:
		self.crashes += 1

		frame = self.script.getframe()
		if all(
			frame.colorAt(Pos(x, y)).distance(Color.Black()) == 0
			for x, y in ((420, 69), (150, 100), (555, 111), (111, 333))
		) and sum(
			frame.colorAt(Pos(x, y)).distance(Color.White()) <= 75
			for x, y in ((360, 90), (360, 100), (370, 60), (376, 80), (376, 99))
		) >= 2:
			self.script.log(logging.WARNING, "Game crashed. Resolving..")
			self.script.press(Button.BUTTON_A)
			self.script.waitAndRender(1)
			self.script.whileNotColor(LOADING_SCREEN_POS, Color.Black(), 0.5, lambda: self.script.press(Button.BUTTON_A))
			return RunnerAction.Continue
		del frame

		ctx = f" (context: {lock.ctx})" if lock.ctx is not None else ""
		msg = f"script locked up{ctx}"

		self.script.sendMsg(msg)
		self.script.log(logging.WARNING, msg)
		self.script.log(logging.WARNING, "reset state and press Ctrl+C to continue")

		try:
			while True:
				self.script.waitAndRender(5)
		except KeyboardInterrupt:
			pass

		self.script.waitAndRender(1)

		return RunnerAction.Continue

	def onShiny(self, shiny: ExecShiny) -> RunnerAction:
		self.script._cap.stopCapture()

		name = ("SHINY " + (self.script.getName() or "")).strip()

		dur = _stripTD(timedelta(seconds=self.totalTime))
		msg = f"found a {name.strip()} after {self.encountersTotal + 1} encounters and {dur}!"

		print("\a")

		self.script._maxDelay = 0.0
		self.script.logInfo(msg)
		self.script.sendMsg(msg)
		self.script.sendScreenshot(shiny.encounterFrame)
		try:
			self.script.sendVideo("encounter.avi")
		except FileNotFoundError:
			pass

		self.encountersTotal = shiny.encounter
		print("Press Ctrl+C for further actions")
		self.script.idle()
		if input("continue? (y/n)").strip().lower() not in ("y", "yes"):
			return RunnerAction.Stop
		else:
			return RunnerAction.Continue

	@property
	def stats(self) -> tuple[tuple[str, Any], ...]:
		now = datetime.now()
		runDuration = now - self.scriptStart

		avg = timedelta(seconds=sum(self.runs) / (len(self.runs) or 1))

		stats: list[tuple[str, Any]] = [
			("Target", self._target),
			("Total runtime", _stripTD(timedelta(seconds=self.totalTime))),
			("Running for", _stripTD(runDuration)),
			("Average per reset", _stripTD(avg)),
			("Encounters", f"{self.encountersCurrent:>04}/{self.encountersTotal:>05}"),
			("Crashes", self.crashes),
		]

		if self.stopAt is not None:
			remainingEncounters: int = self.stopAt - self.encountersTotal
			remainingTime = avg * remainingEncounters
			estEnd = (now + remainingTime).strftime("%Y/%m/%d - %H:%M:%S")

			stats.extend((
				("Stop at", self.stopAt),
				("Remaining", remainingEncounters),
				("Est. time remaining", _stripTD(remainingTime)),
				("Est. end", estEnd),
			))

		if self.script.showLastRunDuration is True:
			stats.append(("Last run duration", _stripTD(self.lastDuration)))

		if self.script.showBnp is True:
			stats.append(("B(n, p)", f"{((1 - ((4095 / 4096) ** self.encountersTotal)) * 100):.2f}%"))

		_last = self.script._lastDelay
		_max = self.script._maxDelay

		stats.append(("Delays (last/max)", f"{_last:>.03f}s | {_max:>.03f}s"))

		stats.extend(self.script.extraStats)

		return tuple(stats)
