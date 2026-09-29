"""REALITY — two observers, one universe, one law.

A point turns on a hidden circle. Neither player sees the point; each sees only
its shadow cast on their own axis. A reads cos(theta), B reads sin(theta).

The whole game rests on one fact. A single player never knows the starting
angle, so for any forward-spinning universe there is a backward-spinning one
whose shadows are *identical* on their axis:

    cos(t0 + kd) == cos((-t0) - kd)      for every step k
    sin(t0 + kd) == sin((pi - t0) - kd)  for every step k

So SPIN_FORWARD and SPIN_BACKWARD are indistinguishable from one shadow — not
merely hard, but provably the same sequence. Direction lives in the pairing of
the two axes and nowhere else. To win, you need a reading from the other
observer, and asking for one hands them the same key.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum

STEP = math.radians(40)   # how far the point turns each advance
LOCK_REWARD = 3           # points for naming the law correctly
LOCK_PENALTY = 2          # points lost for naming it wrong
TRADE_COST = 1            # points each observer pays to exchange readings
MAX_STEPS = 24            # the universe runs down


class Law(str, Enum):
    """How the hidden point moves each step."""

    SPIN_FORWARD = "spin_forward"    # theta increases
    SPIN_BACKWARD = "spin_backward"  # theta decreases
    FROZEN = "frozen"                # theta holds

    @property
    def description(self) -> str:
        return {
            Law.SPIN_FORWARD: "The point turns one way.",
            Law.SPIN_BACKWARD: "The point turns the other way.",
            Law.FROZEN: "The point does not turn.",
        }[self]


AXES = {"A": 0.0, "B": math.pi / 2}  # A reads cos(theta), B reads sin(theta)


@dataclass
class Reading:
    step: int
    value: float
    source: str  # "self" for your own axis, or the other player's id


@dataclass
class Player:
    id: str
    score: int = 0
    readings: list[Reading] = field(default_factory=list)
    hypothesis: Law | None = None
    locked: bool = False
    trade_offer: bool = False  # standing offer to swap readings

    @property
    def last_own(self) -> Reading | None:
        return next(
            (r for r in reversed(self.readings) if r.source == "self"),
            None,
        )


@dataclass
class World:
    law: Law
    theta: float
    step: int = 0

    def advance(self) -> None:
        if self.law is Law.SPIN_FORWARD:
            self.theta += STEP
        elif self.law is Law.SPIN_BACKWARD:
            self.theta -= STEP
        self.step += 1

    def shadow(self, player_id: str) -> float:
        """The point's projection onto one player's axis."""
        return round(math.cos(self.theta - AXES[player_id]), 4)


class RealityGame:
    def __init__(self, seed: int | None = None):
        rng = random.Random(seed)
        self.world = World(
            law=rng.choice(list(Law)),
            theta=rng.uniform(0, 2 * math.pi),
        )
        self.players = {pid: Player(pid) for pid in AXES}
        self.finished = False
        self.winner: str | None = None
        self.log: list[str] = []

    # -- actions ---------------------------------------------------------

    def observe(self, player_id: str) -> float | None:
        """Read your own shadow. Free, but it costs a step of the clock."""
        player = self._active(player_id)
        if player is None:
            return None

        value = self.world.shadow(player_id)
        player.readings.append(Reading(self.world.step, value, "self"))
        self._note(f"{player_id} observed")
        return value

    def advance(self, player_id: str) -> None:
        """Turn the universe. Both observers feel it."""
        if self._active(player_id) is None:
            return
        self.world.advance()
        self._note(f"{player_id} advanced reality to step {self.world.step}")
        if self.world.step >= MAX_STEPS:
            self._end(None, "the universe ran down")

    def offer_trade(self, player_id: str) -> None:
        """Offer your current reading for theirs.

        The moment both observers have offered, each receives the other's latest
        reading — which is the only way either of them can ever see direction.
        """
        player = self._active(player_id)
        if player is None:
            return

        player.trade_offer = True
        other = self.players[self._other(player_id)]

        if not other.trade_offer:
            self._note(f"{player_id} offered a trade")
            return

        mine, theirs = player.last_own, other.last_own
        if mine is None or theirs is None:
            self._note("trade failed — both observers need a reading first")
            player.trade_offer = other.trade_offer = False
            return

        player.readings.append(Reading(theirs.step, theirs.value, other.id))
        other.readings.append(Reading(mine.step, mine.value, player.id))
        player.score -= TRADE_COST
        other.score -= TRADE_COST
        player.trade_offer = other.trade_offer = False
        self._note("readings exchanged — both observers paid")

    def hypothesize(self, player_id: str, law: Law) -> None:
        player = self._active(player_id)
        if player is not None:
            player.hypothesis = law

    def lock(self, player_id: str) -> bool:
        """Commit. Right ends the game; wrong takes you out of it."""
        player = self._active(player_id)
        if player is None or player.hypothesis is None:
            return False

        player.locked = True
        correct = player.hypothesis is self.world.law

        if correct:
            player.score += LOCK_REWARD
            self._end(player_id, f"{player_id} named the law")
            return True

        player.score -= LOCK_PENALTY
        self._note(f"{player_id} locked wrong and is out")

        if all(p.locked for p in self.players.values()):
            self._end(None, "both observers were wrong")
        return False

    # -- state -----------------------------------------------------------

    def state(self, viewer: str | None = None) -> dict:
        return {
            "step": self.world.step,
            "max_steps": MAX_STEPS,
            "finished": self.finished,
            "winner": self.winner,
            "log": self.log[-6:],
            "laws": [
                {"id": law.value, "description": law.description}
                for law in Law
            ],
            "players": {
                pid: {
                    "score": p.score,
                    "locked": p.locked,
                    "trade_offer": p.trade_offer,
                    "hypothesis": p.hypothesis.value if p.hypothesis else None,
                    # Readings stay private until the game ends or they're traded.
                    "readings": (
                        [vars(r) for r in p.readings]
                        if viewer in (pid, None) or self.finished
                        else []
                    ),
                    "reading_count": len(p.readings),
                }
                for pid, p in self.players.items()
            },
            **({"law": self.world.law.value} if self.finished else {}),
        }

    # -- internals -------------------------------------------------------

    def _active(self, player_id: str) -> Player | None:
        if player_id not in self.players:
            raise ValueError(f"Unknown player: {player_id}")
        player = self.players[player_id]
        return None if self.finished or player.locked else player

    def _other(self, player_id: str) -> str:
        return next(p for p in self.players if p != player_id)

    def _note(self, message: str) -> None:
        self.log.append(message)

    def _end(self, winner: str | None, reason: str) -> None:
        self.finished = True
        self.winner = winner
        self._note(reason)
