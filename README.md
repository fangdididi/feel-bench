# feel-bench

**English** | [简体中文](README.zh-CN.md)

> Tune game feel like a bench test: write the feel down in tiles and seconds, check it at the real physics tick rate, test every gap in the level against the jump, measure latency with a phone camera, and let a blind A/B playtest decide what "better" means.

## What it is

`feel-bench` is an agent skill for game developers who want controls that feel right and stay
right. When someone says the jump is "floaty", the camera is "laggy" or hits feel "weak", the
agent does not guess at gravity. It writes a short brief, translates the words into levers,
puts every value into one feel spec (`feel.json`), and runs a standard-library helper that
shows what the engine will actually do, tick by tick. Then it checks the level against the new
jump, measures the running build, and runs a blind playtest with an exact sign test before
anyone says "it's better now".

### The problem

Feel tuning is usually a loop of nudging a number, playing for ten seconds and saying "better".
That loop has known failure modes:

- textbook jump formulas miss the stepped peak by several percent;
- a 0.01 s coyote window is less than one tick, so it does nothing;
- `lerp(a, b, 0.1)` per frame feels twice as slow at 30 fps;
- a shorter jump quietly makes a pit impossible;
- 110 ms of input latency nobody measured;
- a "clear improvement" that blind players cannot tell apart.

feel-bench turns each of those into a check you run before and after every change.

## Features

- **Feel brief -> levers.** Three words, one forbidden word, the verbatim complaint and the one
  verb to tune, mapped to concrete levers with a word-to-lever table.
- **One feel spec.** Jump, run, grace windows, gaps with design intent, feedback tiers and
  accessibility toggles in one JSON file, in tiles and seconds.
- **Stepped simulation.** Semi-implicit Euler at the project's real physics rate: stepped
  peak, apex tick, airtime, shortest tap-hop, and the jump velocity that hits the target height
  exactly.
- **Level reach check.** Every gap and ledge gets `CLEAR`, `TIGHT`, `IMPOSSIBLE` or `TOO HIGH`,
  and the command fails if any verdict breaks the designer's intent.
- **Grace windows in ticks.** Coyote time, jump buffer and friends converted to whole ticks,
  with warnings for zero-tick windows and heavy rounding.
- **Frame-rate-safe smoothing.** Converts a per-frame lerp constant into an exponential rate
  that keeps today's feel at 30, 60 or 144 fps.
- **Latency from video.** Slow-motion frame counts -> median, p90 and a verdict that respects
  the camera's one-frame error bar.
- **Blind A/B with a real test.** Exact two-sided sign test, a minimum-sample warning, and an
  explicit "no detectable preference" outcome.
- **Spec linter.** Catches frames typed as seconds, sub-tick windows, over-long coyote time,
  shake on frequent events, channel overload and missing accessibility toggles.
- **Feel report template** with a worked, fictional example built from real tool output.
- Full English and Chinese versions of the skill and this README.

## Install

The skill is a folder with `SKILL.md`. Clone it where your agent looks for skills:

```bash
git clone https://github.com/fangdididi/feel-bench.git
```

| Agent | Where to put it |
|---|---|
| **Claude Code** | `~/.claude/skills/feel-bench/` (personal) or `.claude/skills/feel-bench/` (per project) |
| **Codex CLI** | `~/.codex/skills/feel-bench/` or `.agents/skills/feel-bench/` in the repo; or reference `SKILL.md` from `AGENTS.md` |
| **Cursor** | `.cursor/skills/feel-bench/`, or add `SKILL.md` as a project rule / `@`-mention it in chat |
| **Gemini CLI, Copilot, Kiro, Windsurf, others** | Put the folder in the repo and point the agent's instruction file (`GEMINI.md`, `.github/copilot-instructions.md`, etc.) at `feel-bench/SKILL.md` |

Example:

```bash
mkdir -p ~/.claude/skills && git clone https://github.com/fangdididi/feel-bench.git ~/.claude/skills/feel-bench
```

Requirements: Python 3.8+ for the helper (standard library only). Any engine: Godot, Unity,
Unreal, Phaser, or a hand-rolled loop. A phone with slow-motion video if you want latency
numbers.

## Usage

Ask your agent things like:

- "The jump feels floaty. Fix it without breaking the levels."
- "Write a feel spec for this character controller and check it at 50 Hz."
- "Is this gap still possible after the change?"
- "Our camera feels different on laptops. Find out why."
- "Set up a blind playtest between these two dash settings."
- "这个跳跃手感太飘了，帮我用数据调一下，别把关卡弄坏。"

Helper commands:

```bash
python3 scripts/feelbench.py lint feel.json
python3 scripts/feelbench.py derive feel.json
python3 scripts/feelbench.py sim feel.json
python3 scripts/feelbench.py windows feel.json
python3 scripts/feelbench.py reach feel.json          # exit 1 if a gap breaks its intent
python3 scripts/feelbench.py smooth 0.15 --ref-fps 60 --fps 30,60,144
python3 scripts/feelbench.py latency --camera-fps 240 --budget-ms 100 22 25 21 27 23 26 22 24 28 23
python3 scripts/feelbench.py abtest 13 3 --ties 2
python3 scripts/feelbench.py --json sim feel.json     # machine-readable output
python3 -m unittest discover -s tests                 # 32 tests
```

## Example

From the fictional platformer in `examples/` (the numbers are real tool output):

```text
$ python3 scripts/feelbench.py sim examples/feel.json
physics_hz=60.0  full_peak_tiles=3.33  target_peak_tiles=3.5  peak_error_pct=-4.84  apex_ticks=21
target_apex_ticks=20.4  airtime_ticks=36  airtime_s=0.6  min_hop_tiles=0.633  hop_ratio=0.19
formula_jump_velocity=329.412  stepped_jump_velocity=337.55

$ python3 scripts/feelbench.py reach examples/feel.json
name=1-1 first pit  reach_tiles=4.8   spare_tiles=1.8   verdict=CLEAR       intent=CLEAR  matches_intent=True
name=1-3 long pit   reach_tiles=4.8   spare_tiles=-1.2  verdict=IMPOSSIBLE  intent=TIGHT  matches_intent=False
name=1-4 step up    reach_tiles=3.33  spare_tiles=0.33  verdict=TIGHT       intent=TIGHT  matches_intent=True
name=1-5 wall       reach_tiles=None  spare_tiles=None  verdict=TOO HIGH    intent=TOO HIGH  matches_intent=True

$ python3 scripts/feelbench.py abtest 3 13 --ties 2
prefer_a=3  prefer_b=13  no_preference=2  decisive=16  p_value=0.0213  alpha=0.05  verdict=B PREFERRED
```

The snappier jump wins the blind test. The bench also shows it would have made pit 1-3
impossible, so the pit was narrowed before shipping. The full story is in
[`examples/report.md`](examples/report.md).

## How it works

1. **Brief** - verbs, three words, the forbidden word, the complaint, platform and tick rate.
2. **Spec** - write `feel.json` and `lint` it.
3. **Derive and step-check** - `derive`, `sim`, `windows`.
4. **Level check** - `reach` before and after every jump or run change.
5. **Wire it in** - fixed step, ticks for windows, exp smoothing, debug overlay.
6. **Measure** - trace check against `sim`, latency from slow-motion video.
7. **Feedback ledger** - tiers, channels, accessibility toggles.
8. **Blind A/B** - one difference, neutral labels, counterbalanced, rule fixed in advance, `abtest`.
9. **Report** - spec diff, bench before/after, measurements, vote, what is not tested yet.

## File structure

```text
feel-bench/
├── SKILL.md                    # skill instructions (English)
├── SKILL.zh-CN.md              # skill instructions (Chinese)
├── README.md
├── README.zh-CN.md
├── LICENSE
├── scripts/
│   └── feelbench.py            # stdlib helper: derive, sim, reach, windows, smooth, latency, abtest, lint
├── tests/
│   └── test_feelbench.py       # 32 unit tests
├── examples/
│   ├── feel.json               # spec after the change (fictional platformer)
│   ├── feel.before.json        # spec before the change
│   └── report.md               # worked feel report
└── references/
    ├── word-to-lever.md        # feel words -> levers and starting ranges
    ├── measuring.md            # overlay, trace check, latency filming, budget, playtest script
    └── engine-notes.md         # tick rate, fixed step, time scale, smoothing per engine
```

## Limits

- The simulation covers a single jump on a character controller with constant run speed. It
  does not model slopes, moving platforms, wall jumps or rigid-body physics. Check those in the
  build.
- Reach assumes takeoff at top speed from the edge. Coyote time adds a little more.
- Latency numbers are only as good as the video. Use at least 10 presses and the players'
  display settings.
- A sign test answers "do players prefer one?", not "how much better is it?".

## License

MIT © 2026 fangdididi
