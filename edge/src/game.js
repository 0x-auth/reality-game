// REALITY engine. Port of engine/reality/game.py, which stays as the reference
// implementation with its test suite.
//
// A point turns on a hidden circle. Neither player sees the point, only its
// shadow on their own axis. A reads cos(theta), B reads sin(theta).
//
// The game rests on one fact: a player never knows the starting angle, so for
// any forward-spinning universe there is a backward-spinning one casting an
// identical shadow on their axis:
//
//   cos(t0 + kd) === cos(-t0 - kd)         for every step k
//   sin(t0 + kd) === sin((PI - t0) - kd)   for every step k
//
// Direction lives in the pairing of the two axes and nowhere else. You cannot
// win alone, and asking for the other reading hands them the same key.

export const STEP = (40 * Math.PI) / 180;
export const LOCK_REWARD = 3;
export const LOCK_PENALTY = 2;
export const TRADE_COST = 1;
export const MAX_STEPS = 24;

export const LAWS = [
  { id: "spin_forward",  description: "The point turns one way." },
  { id: "spin_backward", description: "The point turns the other way." },
  { id: "frozen",        description: "The point does not turn." },
];

const AXES = { A: 0, B: Math.PI / 2 };

const round4 = (n) => Math.round(n * 1e4) / 1e4;

export function createGame(seed) {
  const rng = seed === undefined ? Math.random : mulberry32(seed);
  return {
    law: LAWS[Math.floor(rng() * LAWS.length)].id,
    theta: rng() * 2 * Math.PI,
    step: 0,
    finished: false,
    winner: null,
    log: [],
    players: {
      A: newPlayer("A"),
      B: newPlayer("B"),
    },
  };
}

const newPlayer = (id) => ({
  id,
  score: 0,
  readings: [],
  hypothesis: null,
  locked: false,
  tradeOffer: false,
});

function shadow(game, playerId) {
  return round4(Math.cos(game.theta - AXES[playerId]));
}

function lastOwn(player) {
  for (let i = player.readings.length - 1; i >= 0; i--) {
    if (player.readings[i].source === "self") return player.readings[i];
  }
  return null;
}

function active(game, playerId) {
  const player = game.players[playerId];
  if (!player) return null;
  return game.finished || player.locked ? null : player;
}

function note(game, message) {
  game.log.push(message);
  if (game.log.length > 40) game.log.shift();
}

function end(game, winner, reason) {
  game.finished = true;
  game.winner = winner;
  note(game, reason);
}

const other = (playerId) => (playerId === "A" ? "B" : "A");

// -- actions ---------------------------------------------------------------

export function observe(game, playerId) {
  const player = active(game, playerId);
  if (!player) return;
  player.readings.push({ step: game.step, value: shadow(game, playerId), source: "self" });
  note(game, `${playerId} observed`);
}

export function advance(game, playerId) {
  if (!active(game, playerId)) return;
  if (game.law === "spin_forward") game.theta += STEP;
  else if (game.law === "spin_backward") game.theta -= STEP;
  game.step += 1;
  note(game, `${playerId} advanced reality to step ${game.step}`);
  if (game.step >= MAX_STEPS) end(game, null, "the universe ran down");
}

export function offerTrade(game, playerId) {
  const player = active(game, playerId);
  if (!player) return;

  player.tradeOffer = true;
  const them = game.players[other(playerId)];

  if (!them.tradeOffer) {
    note(game, `${playerId} offered a trade`);
    return;
  }

  const mine = lastOwn(player);
  const theirs = lastOwn(them);
  if (!mine || !theirs) {
    note(game, "trade failed, both observers need a reading first");
    player.tradeOffer = them.tradeOffer = false;
    return;
  }

  player.readings.push({ step: theirs.step, value: theirs.value, source: them.id });
  them.readings.push({ step: mine.step, value: mine.value, source: player.id });
  player.score -= TRADE_COST;
  them.score -= TRADE_COST;
  player.tradeOffer = them.tradeOffer = false;
  note(game, "readings exchanged, both observers paid");
}

export function hypothesize(game, playerId, law) {
  const player = active(game, playerId);
  if (player && LAWS.some((l) => l.id === law)) player.hypothesis = law;
}

export function lock(game, playerId) {
  const player = active(game, playerId);
  if (!player || !player.hypothesis) return;

  player.locked = true;
  if (player.hypothesis === game.law) {
    player.score += LOCK_REWARD;
    end(game, playerId, `${playerId} named the law`);
    return;
  }

  player.score -= LOCK_PENALTY;
  note(game, `${playerId} locked wrong and is out`);
  if (Object.values(game.players).every((p) => p.locked)) {
    end(game, null, "both observers were wrong");
  }
}

// -- state -----------------------------------------------------------------

export function view(game, viewer, seated = 0) {
  const players = {};
  for (const [id, p] of Object.entries(game.players)) {
    players[id] = {
      score: p.score,
      locked: p.locked,
      trade_offer: p.tradeOffer,
      hypothesis: p.hypothesis,
      // Readings stay private until traded or the game ends.
      readings: viewer === id || game.finished ? p.readings : [],
      reading_count: p.readings.length,
    };
  }
  return {
    step: game.step,
    max_steps: MAX_STEPS,
    seated,                 // how many observers are in the room right now
    finished: game.finished,
    winner: game.winner,
    log: game.log.slice(-6),
    laws: LAWS,
    players,
    ...(game.finished ? { law: game.law } : {}),
  };
}

// Deterministic RNG so seeded games can be reproduced in tests.
function mulberry32(a) {
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
