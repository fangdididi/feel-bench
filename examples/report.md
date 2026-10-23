# Feel report - Moss Hop, basic jump (fictional example)

All numbers below are real output of `scripts/feelbench.py` on the files in this folder.
The game, the playtest and the latency counts are made up for the example.

## Brief

- Verb tuned: **jump** (players jump about 9 times per minute).
- Words: *snappy, light, fair*. Must not feel: *floaty*.
- Complaints, verbatim: "the jump feels like the moon", "I fall off ledges I was sure I was on".
- Physics rate: 60 Hz (from project settings). Tile = 16 px.

## Change (spec diff)

| Value | Before (`feel.before.json`) | After (`feel.json`) |
|---|---|---|
| jump.time_to_apex | 0.42 s | 0.34 s |
| jump.fall_multiplier | 1.3 | 1.8 |
| assists.coyote_s | 0.01 s | 0.10 s |

Strictly that is three changes. The coyote fix is a bug fix (lint error), so it went in first
on its own and was checked on the ledge from the complaint. The two jump values were tested
together as one candidate "jump B" against "jump A".

## Bench

`lint` before:

```
ERROR assists.coyote_s is shorter than one tick at 60 Hz
```

`sim` before -> after:

```
before: full_peak_tiles=3.362  peak_error_pct=-3.94  apex_ticks=26  airtime_ticks=47  airtime_s=0.7833  hop_ratio=0.193
after:  full_peak_tiles=3.33   peak_error_pct=-4.84  apex_ticks=21  airtime_ticks=36  airtime_s=0.6     hop_ratio=0.19
        formula_jump_velocity=329.412  stepped_jump_velocity=337.55
```

Airtime drops from 0.78 s to 0.60 s. The stepped peak is 4.8% short of 3.5 tiles, so the
controller uses 337.55 px/s, not the formula's 329.41. `hop_ratio` 0.19 is a little low. That is
noted as the next lever (cut_multiplier 0.45 -> 0.55), not changed in this round.

`windows` after:

```
window=buffer_s  seconds=0.12  exact_ticks=7.2  ticks=7  effective_s=0.1167  warning=None
window=coyote_s  seconds=0.1   exact_ticks=6.0  ticks=6  effective_s=0.1     warning=None
```

`reach` after (exit code 1):

```
name=1-1 first pit  reach_tiles=4.8   spare_tiles=1.8   verdict=CLEAR       intent=CLEAR     matches_intent=True
name=1-3 long pit   reach_tiles=4.8   spare_tiles=-1.2  verdict=IMPOSSIBLE  intent=TIGHT     matches_intent=False
name=1-4 step up    reach_tiles=3.33  spare_tiles=0.33  verdict=TIGHT       intent=TIGHT     matches_intent=True
name=1-5 wall       reach_tiles=None  spare_tiles=None  verdict=TOO HIGH    intent=TOO HIGH  matches_intent=True
```

The shorter airtime turns `1-3 long pit` from TIGHT (0.27 spare before) into IMPOSSIBLE. The
level designer chose to narrow it to 4.2 tiles rather than give back the airtime. Re-run with
4.2: `verdict=TIGHT spare_tiles=0.6`, exit code 0. As a bonus, `1-4 step up` was CLEAR before
(1.27 spare) against an intent of TIGHT. It now matches.

## Measurements

- Trace check, 10 full jumps: peak 3.5 tiles on the overlay, airtime 36 ticks every time.
- Latency, 240 fps phone video, 12 presses, budget 100 ms:

```
trials=12  median_ms=97.9  p90_ms=112.1  min_ms=87.5  max_ms=116.7  resolution_ms=4.2  verdict=OVER
```

  Over budget, and not caused by the jump values. Vsync with triple buffering is the suspect.
  It is filed as a separate task and not mixed into this round.

## Playtest

18 players, blind (Green = A, Orange = B, order alternated), same 90 s course on a gamepad.

```
prefer_a=3  prefer_b=13  no_preference=2  decisive=16  p_value=0.0213  alpha=0.05  verdict=B PREFERRED
```

(Run as `abtest 3 13 --ties 2`.) Words for B: "quick", "tight", "bouncy" (x2). Words for A:
"slow", "moon", "floaty" (x3).

## Decision

Ship jump B with the stepped velocity, coyote 0.10 s, and pit 1-3 at 4.2 tiles.

## Not tested yet

- 30 Hz physics on the low-end build (`windows` at 30 Hz: buffer 3.6 ticks rounds to 4).
- Keyboard players. All playtest sessions used a gamepad.
- Moving platforms and slopes.
- The latency fix.
