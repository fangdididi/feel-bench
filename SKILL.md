---
name: feel-bench
description: Tune how a game's controls feel with numbers instead of guesses. Turns words like "snappy", "floaty" or "unfair" into a written feel spec (jump height in tiles, time to apex, fall weight, run ramp, grace windows, feedback tiers), checks it at the real physics tick rate, tests every gap in the level against the jump, measures input-to-screen latency from slow-motion video, and settles "which feels better" with a blind A/B playtest and an exact sign test. Use when a mechanic works but feels wrong, when tuning a platformer or action controller, when someone says "make it feel tighter / punchier / less floaty", or before changing feel values that level design depends on.
---

# feel-bench

**Measure the feel before you touch it, change one thing, measure again, and let blind players decide.**

## What this skill is

"Game feel" is the moment-to-moment response of a game to the player's hands: how fast a
jump rises, how hard it falls, how forgiving a ledge is, how quickly the screen answers a
button, how loud a hit lands. Feel work usually goes like this: someone says "it feels
floaty", a developer nudges gravity, plays for ten seconds, says "better", and ships. Two
weeks later a level that used to be possible is not, the jump is different at 144 Hz, and
nobody can say what changed or why.

feel-bench turns that loop into a bench test. Feel is written down as a small spec in
units a designer can picture (tiles, seconds, ticks, tiers). The spec is checked the way the
engine actually runs it (fixed physics steps, not the textbook formula). Level geometry is
checked against the jump envelope before players hit an impossible pit. Latency is measured
with a phone camera, not felt. And "A feels better than B" is only claimed after a blind,
counterbalanced playtest has enough votes for the claim to mean anything.

It ships with `scripts/feelbench.py`, a standard-library helper (no installs) that does the
arithmetic: derive, step-simulate, reach check, grace windows to ticks, frame-rate-safe
smoothing, latency from video frames, the A/B sign test, and a spec linter.

## The problem it solves

- **Words are not values.** "Snappy" means a short rise, a heavy fall and a fast run ramp to
  one person and bigger screen shake to another. Without a translation step, two people
  tune two different things.
- **Formulas lie by a few percent.** `g = 2h/t²` is exact in continuous time. Engines step at
  a fixed rate, so the real peak lands a few percent short and the apex arrives on a whole
  tick. At 30 Hz the error doubles. Level design built on the formula is off by that much.
- **Feel changes break levels silently.** Shortening the jump by half a tile turns a "tight"
  pit into an impossible one, and nobody notices until a tester rage-quits.
- **Grace windows round.** A 0.12 s jump buffer is 7.2 ticks at 60 Hz and 3.6 at 30 Hz. A
  0.01 s window is zero ticks: it does nothing at all.
- **Smoothing that depends on frame rate.** `lerp(a, b, 0.1)` once per frame is twice as slow
  at 30 fps as at 60 and much faster at 144. The game feels different on every machine.
- **Latency is invisible until measured.** Players feel 100+ ms from press to screen as
  "mushy", but developers adapt to their own build and stop noticing.
- **"Better" is suggestion.** The person who made the change wants it to be better. Without
  blind labels and a counted vote, preference follows whoever spoke last.

## When to use

- A mechanic works but feels wrong: floaty, heavy, sluggish, slippery, unfair, weak, mushy.
- You are building or retuning a platformer, action, or character controller.
- Someone asks to make a jump, dash, hit or pickup feel tighter, punchier or more forgiving.
- Before changing any value that level design depends on (jump height, run speed, gravity).
- When a game feels different at different frame rates or on different machines.
- When two variants are on the table and the team cannot agree which is better.

**When not to use:** balance and economy (damage numbers, drop rates), art direction,
narrative pacing, or network netcode. For those, use a balance or netcode workflow; this
skill only covers the hand-to-screen loop.

## Ground rules

1. **Spec first.** Every tunable value lives in one feel spec (`feel.json`) in outcome units.
   The engine reads from it, or the spec is the record of what the engine holds. No magic
   numbers in scripts.
2. **One change per round.** Change one lever, re-run the bench, compare. Two changes at once
   teach you nothing about either.
3. **Simulate at the real tick rate.** Read the physics rate from the project settings. Never
   assume 60.
4. **Feedback never moves the simulation.** Shake moves the camera, hit-stop scales time,
   squash scales the sprite. The body's position and the collision math stay untouched.
5. **Say what you saw.** In reports, separate *measured* (numbers, traces, video counts) from
   *inferred* (what you think the player feels). Never write "feels better" without a measure
   or a blind vote behind it.
6. **Accessibility ships with the juice.** Every shake, flash or zoom has a reduce toggle.
7. **Do not copy another game's numbers or code.** Describe a reference moment in your own
   words ("the jump should reach the top in about a third of a second") and derive your own.

## Step-by-step

### Step 1 - Feel brief (10 minutes, in words)

Ask, or write from what the user said:

- **Verbs.** Which actions matter? (run, jump, dash, attack, land, pick up). Pick **one** to tune
  first, usually the one the player does most.
- **Three words** for how it should feel (e.g. *snappy, light, fair*) and **one word it must
  not feel** (e.g. *slippery*).
- **The complaint**, verbatim, if there is one ("I fall off ledges I was sure I was on").
- **Reference moment**, described in your own words, not as numbers copied from a game.
- **Platform and rate.** Target devices, render fps range, and the engine's physics tick rate.

Translate each word into levers with `references/word-to-lever.md`. Example: *snappy* = shorter
time to apex, higher fall multiplier, short accel time; *fair* = coyote time + jump buffer +
corner correction; *weak hit* = feedback tier too low, not physics.

### Step 2 - Write the feel spec

Create `feel.json` (see `examples/feel.json` for a full one):

```json
{
  "units": {"tile": 16, "physics_hz": 60},
  "jump": {"height_tiles": 3.5, "time_to_apex": 0.34, "fall_multiplier": 1.8,
           "cut_multiplier": 0.45, "max_fall_tiles_per_s": 28},
  "run": {"top_speed_tiles_per_s": 8, "accel_time": 0.07, "decel_time": 0.05, "air_control": 0.8},
  "assists": {"coyote_s": 0.1, "buffer_s": 0.12},
  "gaps": [{"name": "1-3 long pit", "width_tiles": 6.0, "rise_tiles": 0, "intent": "TIGHT"}],
  "feedback": [{"event": "land", "tier": "small", "frequent": true, "channels": ["sfx", "dust"]}],
  "accessibility": ["shake", "flash", "zoom"]
}
```

Units: heights in tiles, times in seconds, speeds in tiles per second. `intent` on a gap is what
the level designer wants it to be: `CLEAR`, `TIGHT`, `IMPOSSIBLE` or `TOO HIGH` (walls).

Lint it:

```bash
python3 scripts/feelbench.py lint feel.json
```

The linter catches frames typed as seconds, windows shorter than one tick, a coyote window as
long as the rise, frequent events with screen shake or a large tier, more than 8 stacked
channels, and loud channels with no accessibility toggle.

### Step 3 - Derive and step-check

```bash
python3 scripts/feelbench.py derive feel.json   # engine values: gravity, jump velocity, accel
python3 scripts/feelbench.py sim feel.json      # what the fixed-step engine really does
python3 scripts/feelbench.py windows feel.json  # grace windows in whole ticks
```

Read `sim` carefully:

- `peak_error_pct`: how far the stepped peak misses the target. If level design needs the exact
  height, use `stepped_jump_velocity` instead of the formula value.
- `apex_ticks` vs `target_apex_ticks`: the apex lands on a whole tick.
- `min_hop_tiles` / `hop_ratio`: the shortest tap-jump. Below about 0.25 the tap feels like a
  stumble; above about 0.7 tap and hold feel the same.

If `windows` warns, choose a value that is a whole number of ticks at the slowest supported
physics rate.

### Step 4 - Check the level against the jump

```bash
python3 scripts/feelbench.py reach feel.json
```

Every gap gets `CLEAR` (one tile or more to spare by default), `TIGHT` (under the margin),
`IMPOSSIBLE` or `TOO HIGH`. The command exits non-zero if any verdict differs from the gap's
`intent`. Reach assumes the player is at top speed and jumps from the very edge. Coyote time
adds a little, so a `TIGHT` gap can depend on it. Say so in the report.

Run this **before and after every change** to a jump or run value. A feel change that breaks a
level intent is not done until the level or the value is adjusted on purpose.

### Step 5 - Wire it in, the safe way

- Physics values go into the fixed step (`_physics_process`, `FixedUpdate`, the engine's tick),
  integrated with that step's `dt`.
- Grace windows are counted in ticks, or in seconds that are known to round well. Jumping
  consumes both timers (no double jump from coyote plus buffer).
- The variable-jump cut applies only while rising, and only once.
- Camera follow and UI smoothing use `t = 1 - exp(-rate * dt)`. If you find a per-frame lerp
  constant, convert it:

  ```bash
  python3 scripts/feelbench.py smooth 0.15 --ref-fps 60 --fps 30,60,144
  ```

  The output gives the rate that keeps today's 60 fps feel at every frame rate.
- Add a debug overlay: tick counter, grounded flag, coyote/buffer timers, current height in
  tiles, and the peak of the last jump. Most "the jump is random" reports die here.

Engine pointers (where the tick rate lives, the fixed-step callback, time scale) are in
`references/engine-notes.md`.

### Step 6 - Measure in the running build

- **Trace check.** Do ten full-hold jumps on flat ground with the overlay on. The peak and the
  airtime ticks should match `sim` within one tick and a couple of percent. If they do not,
  something else touches velocity (a second gravity, a slope snap, an animation root motion).
- **Latency.** Film the controller and the screen together with a phone's slow-motion mode
  (240 fps is common). For each of at least 10 presses, count the frames from the button
  visibly bottoming out to the first changed pixel. Then:

  ```bash
  python3 scripts/feelbench.py latency --camera-fps 240 --budget-ms 100 22 25 21 27 23 26 22 24 28 23 25 22
  ```

  The verdict is `WITHIN`, `OVER` or `TOO CLOSE TO CALL`. One camera frame is the error bar, so
  the verdict takes it into account. Measure with vsync and frame caps set as players will have
  them. Steps for cutting latency are in `references/measuring.md`.

### Step 7 - Feedback ledger

List every event that gets feedback with a tier (`small`, `medium`, `large`) and its channels
(sfx, particles, squash, dust, hitstop, shake, flash, zoom, number pop, rumble). Rules of thumb:

- Frequent events (footsteps, landing, coins) stay `small` and never use shake or hit-stop.
- Hit-stop and shake are for impact. Their size scales with the event's importance.
- Juice is brief. Everything returns to rest. Nothing blocks input.
- Every loud channel has a reduce toggle listed in `accessibility`.

Re-run `lint` after editing the ledger.

### Step 8 - Blind A/B playtest

When the question is "is B better than A?":

1. **One difference only.** The builds differ in exactly the value under test.
2. **Neutral labels.** Call them by colors or random letters. The person running the session
   does not say which is new.
3. **Counterbalance.** Half the players play A first, half B first. Each plays the same short
   course (60-120 s) in both.
4. **Ask one forced question,** "Which felt better to control?", with "no difference" allowed.
   Ask for one word about each.
5. **Decide the rule before you look:** alpha (usually 0.05), and what you do on no result
   (keep the current one).
6. Count and test:

   ```bash
   python3 scripts/feelbench.py abtest 13 3 --ties 2
   ```

   With fewer than 6 decisive answers, nothing can reach p < 0.05, and the tool says so. "No
   detectable preference" is a real answer: the change may be below what players notice.
   Then keep whichever is cheaper or safer for level design.

### Step 9 - Feel report

Write a short report (template in `examples/report.md`):

- The brief (words, complaint, verb tuned).
- The change, as a spec diff (old -> new value).
- Bench results before and after: `sim`, `windows`, `reach` (including any intent broken and how
  it was resolved), `lint`.
- Measurements: trace check, latency median/p90 with verdict.
- Playtest: counts, p-value, verdict, the words players used.
- What is **not** tested yet (other frame rates, gamepad vs keyboard, slopes, moving platforms).

## Examples

**"The jump feels floaty."** Brief: *snappy, light, fair*, not *floaty*. Spec time to apex
0.42 s -> 0.34 s, fall multiplier 1.3 -> 1.8. `sim` shows the stepped peak 4.8% short of 3.5
tiles, so the controller uses the stepped jump velocity. `reach` then flags `1-3 long pit`
`IMPOSSIBLE` (4.8 tiles of reach, 6 wide; it was `TIGHT` before). The designer narrows the pit to 4.2 tiles
(`TIGHT`) instead of making the jump floaty again. The blind test goes 13 to 3 for the new
jump, p = 0.021.

**"I fall off ledges I was sure I was on."** The overlay shows coyote time set to 0.01 s.
`lint` flags it as shorter than one tick at 60 Hz, and `windows` shows it only survives by
rounding up. It is changed to 0.1 s (exactly 6 ticks at 60 Hz) and the complaint is re-tested on
the same ledge.

**"Camera feels laggy on my laptop but fine on my PC."** `smooth 0.1` shows the per-frame lerp
takes twice as long to settle at 30 fps as at 60. It is replaced by `1 - exp(-6.32 * dt)`.

**"Hits feel weak."** The ledger shows enemy hit at tier `small` with only sfx. It moves to
`medium` (sfx, 0.05 s hit-stop, small shake, particles, flash), with shake and flash toggles
added. Physics is untouched.

## Tips

- Tune the verb the player does most first. A perfect wall-jump does not rescue a bad basic jump.
- Fall multiplier is usually the biggest single lever against "floaty". Time to apex is next.
- Keep a `feel.json` per character or vehicle, and commit it, so feel changes show up in review.
- Watch players' hands, not only the screen. Mashing means the game did not answer the first press.
- A value that only works at 60 Hz is a bug waiting for a 30 Hz phone or a 50 Hz server.
- If testers cannot tell A from B, stop tuning that lever and move to the next complaint.
- Keep the before-build around. Feel memory fades in minutes, so compare side by side.

## Files

- `scripts/feelbench.py` - the helper (Python 3.8+, standard library only).
- `tests/test_feelbench.py` - unit tests: `python3 -m unittest discover -s tests`.
- `examples/feel.json` - a full spec for a fictional platformer.
- `examples/report.md` - a worked feel report with real tool output.
- `references/word-to-lever.md` - feel words mapped to levers and starting ranges.
- `references/measuring.md` - traces, latency filming, a latency budget, playtest script.
- `references/engine-notes.md` - tick rate, fixed step, time scale and smoothing per engine.
