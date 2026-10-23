# Engine notes

Where to find the values the bench needs. Names change between versions, so check the
installed engine's documentation before relying on an exact property name.

| Engine | Physics tick rate | Fixed-step callback | Time scale for hit-stop | Notes |
|---|---|---|---|---|
| Godot 4 | Project Settings > Physics > Common > Physics Ticks per Second | `_physics_process(delta)` | `Engine.time_scale`; use a timer that ignores time scale to restore | Turn on physics interpolation for smooth rendering. |
| Unity | Project Settings > Time > Fixed Timestep (seconds; 0.02 = 50 Hz) | `FixedUpdate()` | `Time.timeScale`; restore with a real-time wait | Default is 50 Hz, not 60. Rigidbody interpolation smooths rendering. |
| Unreal | Physics substepping / async physics tick settings | async physics tick or substep callback | global time dilation | Character movement may run on the frame. Check which mode the project uses. |
| Phaser (arcade) | physics world `fps` setting | world step | scale the scene's time | Default often follows the display rate. Pin it for consistent jumps. |
| Hand-rolled loop | your accumulator's fixed dt | your fixed update | your own multiplier | Use an accumulator: simulate in fixed steps, render with the leftover fraction. |

## Units

The bench works in tiles and seconds. Convert at the edge:

- pixels = tiles x tile size (e.g. 16 or 32)
- 3D: pick a "tile" equal to the character's height or one meter, and say which
- Y axis: the bench uses up as positive. Many 2D engines use down as positive, so flip the
  sign of velocity and gravity when you paste values in.

## Smoothing

Replace any `lerp(current, target, k)` that runs once per frame with
`lerp(current, target, 1 - exp(-rate * dt))`. Get `rate` from `feelbench.py smooth k --ref-fps
<fps it was tuned at>` so the feel at the original frame rate stays the same.
