# Feel words -> levers

People describe feel in words. This table turns each common word into the levers that usually
cause it, and the direction to move them. Change **one** lever per round and re-run the bench.
The ranges are starting points for a 2D character at 60 Hz. They are not targets.

| Word heard | Usually caused by | Try first | Then |
|---|---|---|---|
| floaty | long time to apex, fall as slow as the rise | fall_multiplier up (1.5-2.2) | time_to_apex down (0.28-0.38 s) |
| heavy / sluggish | long accel_time, low jump velocity | accel_time down (0.03-0.10 s) | time_to_apex down |
| slippery / on ice | long decel_time, high air control at turnaround | decel_time down (0.03-0.08 s) | extra decel when input reverses |
| twitchy / nervous | instant accel, tiny deadzone, camera with no deadzone | accel_time up a little | camera deadzone, stick deadzone 0.15-0.25 radial |
| stiff / no control in air | air_control low | air_control up (0.6-1.0) | apex hang (lower gravity near the top) |
| unfair / "I pressed it!" | no coyote time or jump buffer, latency | coyote 0.08-0.12 s, buffer 0.10-0.15 s | measure latency, corner correction 2-4 px |
| can't do small hops | cut_multiplier missing or 1.0 | cut_multiplier 0.4-0.6 | check hop_ratio 0.25-0.6 |
| jump is random | mixed fixed/variable step, double gravity, slope snap | trace check vs `sim` | debug overlay of timers and peak |
| mushy / delayed | input-to-photon latency, input read on wrong frame | measure latency | see measuring.md budget |
| weak / no impact | feedback tier too low, no hit-stop | move event up one tier | add a sound layer before shake |
| noisy / tiring | big feedback on frequent events, too many channels | frequent events to `small` | cap channels; drop shake first |
| nauseating | shake roll, zoom punches, camera with no smoothing | reduce shake roll and zoom | exp-smoothed camera, deadzone |

## Reading the bench numbers as feel

- **Airtime** for a full jump of about 0.5-0.8 s reads as "normal". Over 1 s reads as floaty
  unless the game wants that (moon level, glide).
- **hop_ratio** (shortest tap-jump / full jump): below 0.25 feels like tripping. Above 0.7 the
  button feels binary.
- **Spare tiles** in `reach`: under half a tile is a skill check. Use it on purpose and rarely
  in early levels.
- **Stepped peak error**: a few percent is normal at 60 Hz. If a level relies on an exact height
  (a ceiling you just touch), use the stepped velocity.

## Words that are not about controls

"Boring", "too hard", "too long" and "confusing" are usually level design, balance or pacing.
Note them in the report and hand them off. Do not chase them with gravity.
