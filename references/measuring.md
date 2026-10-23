# Measuring feel in a running build

## 1. Debug overlay (build this first)

Show on screen, updated every physics tick:

- tick counter and physics rate
- grounded flag, coyote timer, buffer timer (in ticks)
- current height above takeoff, in tiles, and the peak of the last jump
- horizontal speed in tiles per second
- the last input event and the tick it was read on

Toggle it with a debug key and strip it from release builds.

## 2. Trace check

1. Stand on flat ground. Hold jump fully, ten times.
2. Note peak (tiles) and airtime (ticks) from the overlay.
3. Compare with `feelbench.py sim`. Expect a match within one tick and about 2% height.
4. A mismatch means something else changes velocity: a second gravity source, slope snapping,
   root motion, a velocity clamp, or physics running in the render update.

Do the same for a tap-jump (compare `min_hop_tiles`) and for a run to top speed (compare
`accel_time`).

## 3. Input-to-photon latency with a phone

What you need: a phone with slow-motion video (240 fps is common; 120 works with a wider error
bar), the controller or keyboard in the same shot as the screen, and good light.

1. Set the game as players will run it: same vsync, frame cap, fullscreen mode, display.
2. Pick an action with an obvious first pixel (a jump from standing, a menu highlight).
3. Film at least 10 presses, separated by a second or so.
4. Step frame by frame. Count from the frame where the key or button visibly bottoms out to the
   first frame where the screen changes.
5. Run `feelbench.py latency --camera-fps 240 --budget-ms <budget> <counts...>`.

The error bar is one camera frame (4.2 ms at 240 fps). The tool's verdict only says `WITHIN`
or `OVER` when the p90 clears the budget by more than that.

### A rough budget

Each layer adds delay. Find the biggest one before optimizing the rest:

| Layer | Typical | Things to check |
|---|---|---|
| device + OS input | 1-10 ms | wireless vs wired, polling rate |
| game reads input | 0-1 frame | input read before simulation in the same frame? |
| simulation | 0-1 tick | action applied on the tick it was read, not the next |
| render queue | 1-3 frames | frames in flight, triple buffering |
| vsync / compositor | 0-1 frame | fullscreen vs windowed, VRR |
| display | 5-30 ms | TV game mode, panel response |

For fast action games, about 50-80 ms total is good and over 120 ms is felt by most players.
Rhythm and fighting games need tighter numbers. Set the budget in the spec
(`latency_budget_ms`) and keep it.

## 4. Blind A/B playtest script

Read the same words to every player:

> "You'll play the same short course twice, as Green and as Orange. Play each the way you
> normally would. Afterwards I'll ask which one felt better to control. 'No difference' is a
> fine answer."

- The session runner does not know which build is new, if that can be arranged.
- Alternate the order: odd players start Green, even players start Orange.
- Same course, same length (60-120 s), same input device.
- Record: preference (Green / Orange / none), one word for each build, and anything said
  aloud while playing.
- Unblind only after all sessions. Then run `feelbench.py abtest <a> <b> --ties <n>`.

Sample size: with alpha 0.05 you need at least 6 decisive answers even for a unanimous result,
and around 15-25 to detect a clear but not unanimous preference. If players keep saying "no
difference", the change is probably below notice. That is useful to know.

## 5. Frame-rate sweep

Run the trace check with the render rate capped at 30, 60 and the highest your target hardware
reaches (e.g. 144). The jump must be identical in ticks. If the camera or UI feel different,
look for per-frame lerps and convert them with `feelbench.py smooth`.
