# Handshake submission: Create a Multiplayer Game

Copy each block into the matching field. Nothing else to prepare.

---

## 1. Project title

```
REALITY
```

---

## 2. Your project  (Paste link)

```
https://reality-game.consciousness-portal.workers.dev
```

---

## 3. Preview image

Upload this file:

```
/Users/space/play/mpg/reality-game/docs/cover.png
```

Already 1200x630. It is also live at https://0x-auth.github.io/reality-game/cover.png

Note: the form asks for "a screenshot of one of your game's key screens". This
cover is a designed card rather than a literal screenshot, though its content is
the door screen. If you would rather play safe, open the game and screenshot the
first screen instead, it shows the same two shadow traces.

---

## 4. Description   (494 characters, limit is 500)

```
Two observers, one hidden universe. Each sees only a shadow of it, cast on their own axis.

The catch: a universe turning forward and one turning backward cast identical shadows. Not similar, identical, forever. So neither player can solve it alone. You have to buy a reading off your opponent, which hands them the same key.

Hardest part was making that provable, not flavour text. There's a test asserting it, since the game collapses without it.

Next: more laws, and bluffing on the trade.
```

---

## 5. Share to Showcase

**Leave this ticked.** The fine print says Showcase projects are the only ones
entered in this month's challenge. Untick it and the project publishes to your
Handshake profile but wins nothing.

---

## 6. Submit

---

# Reference

Not needed for the form, kept here in case anything asks.

| | |
|---|---|
| Play | https://reality-game.consciousness-portal.workers.dev |
| Pages mirror | https://0x-auth.github.io/reality-game/ |
| Code | https://github.com/0x-auth/reality-game |

## Requirements, and where each is met

| Brief says | Status |
|---|---|
| At least two players join from separate devices | Room codes, any device, no accounts or installs |
| Real rules a player could follow without you explaining | The door screen shows why a second player is needed before you click anything |
| Live at a URL other people can actually reach | Cloudflare Worker, plus a GitHub Pages mirror |

## What was tested against the live deployment

- Room codes generate and are shareable
- Two players get separate axes (A reads cos, B reads sin)
- Readings stay private until traded
- Trading requires both sides and charges both
- Advancing the world is felt by both players
- Win detection correct, wrong lock removes only that player
- Third player refused with "room full"
- Restart resets step, scores, and the hidden law
- A seat frees up when a player leaves

Not verified: how it looks on a real phone screen. Play one round before or
after submitting and tell me if anything looks wrong.

## If someone asks how it works

A point turns on a hidden circle. Neither player sees the point, only its shadow
on their own axis. A reads `cos θ`, B reads `sin θ`.

Because neither knows the starting angle, for any universe turning forward there
is one turning backward casting an identical shadow on that axis, step for step:

```
cos(t0 + kd) = cos(-t0 - kd)         for every step k
sin(t0 + kd) = sin((pi - t0) - kd)   for every step k
```

Direction is not hard to see from a single axis. It is not present there at all.
It exists only in how the two axes relate. So the only way to recover it is to
trade a reading with your opponent, and that hands them the same key you paid for.

`tests/test_game.py` asserts this directly, because the game becomes solitaire
if it ever stops being true.
