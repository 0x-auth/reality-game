import math

import pytest

from engine.reality.game import (
    AXES,
    MAX_STEPS,
    STEP,
    Law,
    LOCK_PENALTY,
    LOCK_REWARD,
    RealityGame,
    TRADE_COST,
    World,
)


def shadows(law, theta, player_id, steps=12):
    """The sequence one observer would read under a given universe."""
    world = World(law=law, theta=theta)
    out = [world.shadow(player_id)]
    for _ in range(steps):
        world.advance()
        out.append(world.shadow(player_id))
    return out


# -- the claim the whole game rests on ------------------------------------


@pytest.mark.parametrize("theta", [0.3, 1.1, 2.7, 4.2, 5.9])
def test_one_observer_cannot_see_direction(theta):
    """For any forward universe there is a backward one with identical shadows.

    A reads cos(theta - 0); the mirror universe starts at -theta.
    B reads cos(theta - pi/2) = sin(theta); its mirror starts at pi - theta.
    If this ever fails, a player could win alone and the game is pointless.
    """
    assert shadows(Law.SPIN_FORWARD, theta, "A") == pytest.approx(
        shadows(Law.SPIN_BACKWARD, -theta, "A")
    )
    assert shadows(Law.SPIN_FORWARD, theta, "B") == pytest.approx(
        shadows(Law.SPIN_BACKWARD, math.pi - theta, "B")
    )


@pytest.mark.parametrize("theta", [0.3, 1.1, 2.7, 4.2])
def test_both_observers_together_do_see_direction(theta):
    """Two axes at once pin the angle, so the pair resolves what one cannot."""
    for law, expected in (
        (Law.SPIN_FORWARD, STEP),
        (Law.SPIN_BACKWARD, -STEP),
    ):
        world = World(law=law, theta=theta)
        before = math.atan2(world.shadow("B"), world.shadow("A"))
        world.advance()
        after = math.atan2(world.shadow("B"), world.shadow("A"))
        delta = (after - before + math.pi) % (2 * math.pi) - math.pi
        # Shadows are rounded to 4dp for display, which caps how precisely the
        # angle can be rebuilt from them. The sign — the direction — is exact.
        assert delta == pytest.approx(expected, abs=1e-3)
        assert (delta > 0) is (law is Law.SPIN_FORWARD)


def test_frozen_is_solvable_alone():
    """The easy case: a still shadow gives the law away without help."""
    assert len(set(shadows(Law.FROZEN, 1.0, "A"))) == 1


# -- actions ---------------------------------------------------------------


def test_observe_records_a_private_reading():
    game = RealityGame(seed=1)
    value = game.observe("A")
    assert value == game.state(viewer="A")["players"]["A"]["readings"][0]["value"]
    # B learns that A looked, but not what A saw.
    assert game.state(viewer="B")["players"]["A"]["readings"] == []
    assert game.state(viewer="B")["players"]["A"]["reading_count"] == 1


def test_advance_moves_the_shared_world():
    game = RealityGame(seed=2)
    game.advance("A")
    assert game.state()["step"] == 1


def test_trade_needs_both_sides_and_costs_both():
    game = RealityGame(seed=3)
    game.observe("A")
    game.observe("B")

    game.offer_trade("A")
    assert game.state()["players"]["A"]["trade_offer"] is True
    assert len(game.players["B"].readings) == 1  # nothing moved yet

    game.offer_trade("B")
    for pid in ("A", "B"):
        player = game.players[pid]
        assert len(player.readings) == 2
        assert player.readings[-1].source != "self"
        assert player.score == -TRADE_COST
        assert player.trade_offer is False


def test_trade_without_readings_is_refused():
    game = RealityGame(seed=4)
    game.offer_trade("A")
    game.offer_trade("B")
    assert all(not p.readings for p in game.players.values())


def test_correct_lock_wins_and_ends_it():
    game = RealityGame(seed=5)
    game.hypothesize("A", game.world.law)
    assert game.lock("A") is True
    assert game.finished and game.winner == "A"
    assert game.players["A"].score == LOCK_REWARD
    assert game.state()["law"] == game.world.law.value


def test_wrong_lock_takes_you_out_but_leaves_the_game_running():
    game = RealityGame(seed=6)
    wrong = next(law for law in Law if law is not game.world.law)
    game.hypothesize("A", wrong)

    assert game.lock("A") is False
    assert game.players["A"].locked and not game.finished
    assert game.players["A"].score == -LOCK_PENALTY

    game.observe("A")  # locked players are inert
    assert not game.players["A"].readings


def test_game_ends_when_both_are_wrong():
    game = RealityGame(seed=7)
    wrong = next(law for law in Law if law is not game.world.law)
    for pid in ("A", "B"):
        game.hypothesize(pid, wrong)
        game.lock(pid)
    assert game.finished and game.winner is None


def test_lock_needs_a_hypothesis():
    game = RealityGame(seed=8)
    assert game.lock("A") is False
    assert not game.players["A"].locked


def test_universe_runs_down():
    game = RealityGame(seed=9)
    for _ in range(MAX_STEPS):
        game.advance("A")
    assert game.finished and game.winner is None


def test_readings_open_up_once_it_is_over():
    game = RealityGame(seed=10)
    game.observe("B")
    game.hypothesize("A", game.world.law)
    game.lock("A")
    assert game.state(viewer="A")["players"]["B"]["readings"]


def test_unknown_player_is_rejected():
    with pytest.raises(ValueError):
        RealityGame(seed=11).observe("Z")


def test_axes_are_a_quarter_turn_apart():
    """Perpendicular axes are what make the pair informative."""
    assert AXES["B"] - AXES["A"] == pytest.approx(math.pi / 2)
