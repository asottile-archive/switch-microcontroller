from __future__ import annotations

from scripts.engine import do
from scripts.engine import Press
from scripts.engine import Wait

reset = do(Press('H'), Wait(1), Press('X'), Wait(.5), Press('A'), Wait(2))
