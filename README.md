# REALITY

**Two observers. One universe. One law. Neither of you can win alone.**

Play: https://reality-game.consciousness-portal.workers.dev

A point turns on a hidden circle. You never see the point, only its shadow cast
on your own axis. Player A reads `cos θ`, player B reads `sin θ`. Your job is to
name the law governing the point: turning forward, turning backward, or frozen.

## The idea

You do not know the starting angle. That single missing fact is the game, because
for any universe turning forward there is one turning backward that casts an
**identical** shadow on your axis, step for step, forever:

```
cos(t₀ + kδ) ≡ cos(−t₀ − kδ)          for every step k
sin(t₀ + kδ) ≡ sin((π − t₀) − kδ)     for every step k
```

Direction is not hard to see from one axis. It is *invisible*. It exists only in
how the two axes relate, so a single observer can never recover it no matter how
long they watch.

Which means you have to trade a reading with your opponent. And the moment you
do, you hand them the same key you just bought.

`tests/test_game.py` asserts this property directly, since if it ever broke the
game would collapse into solitaire.

## Playing

Create a room, send the four character code to someone, they join from any device.
No accounts, no installs, works on phones.

| Action | Effect |
|---|---|
| Observe | read your own shadow, privately |
| Turn the universe | advance the world, which both of you feel |
| Offer a trade | swap latest readings, costs you both a point |
| Lock it in | name the law. Right ends the game. Wrong ends you. |

## Layout

```
edge/          Cloudflare Worker, one Durable Object per room  (deployed)
docs/          static mirror for GitHub Pages
engine/        Python reference implementation
tests/         22 tests, including the indistinguishability proof
server/        local FastAPI server for development
```

The Worker serves the page and the sockets from one origin. The GitHub Pages
copy is a mirror that points back at the Worker for realtime.

## Development

```bash
python -m pytest tests/ -q          # engine tests
cd edge && npx wrangler dev         # worker locally
cd edge && npx wrangler deploy      # ship it
```
