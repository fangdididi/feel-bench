#!/usr/bin/env python3
"""feel-bench helper: turn a feel spec into numbers you can check.

Standard library only. Subcommands:
  derive   physics values from a feel spec (tiles, seconds)
  sim      step the jump at the real physics rate, tick by tick
  reach    check every gap/ledge in the spec against the jump envelope
  windows  convert grace windows (coyote, buffer, ...) to whole ticks
  smooth   convert a per-frame lerp constant into a frame-rate-free rate
  latency  input-to-photon from slow-motion video frame counts
  abtest   exact sign test for a blind A/B playtest
  lint     sanity-check a feel spec before anyone tunes by hand
"""
import argparse
import json
import math
import sys

# ---------------------------------------------------------------- physics


def derive(spec):
    """Derive engine values from outcome values. y axis points UP here."""
    u = spec.get("units", {})
    tile = float(u.get("tile", 1.0))
    j = spec["jump"]
    h = float(j["height_tiles"]) * tile
    t = float(j["time_to_apex"])
    g = 2.0 * h / (t * t)
    v0 = 2.0 * h / t
    fall_mult = float(j.get("fall_multiplier", 1.0))
    out = {
        "tile": tile,
        "physics_hz": float(u.get("physics_hz", 60)),
        "rise_gravity": g,
        "fall_gravity": g * fall_mult,
        "jump_velocity": v0,
        "cut_multiplier": float(j.get("cut_multiplier", 1.0)),
        "max_fall_speed": float(j.get("max_fall_tiles_per_s", 0) or 0) * tile,
        "ideal_apex_s": t,
        "ideal_height": h,
        "ideal_fall_s": t / math.sqrt(fall_mult) if fall_mult > 0 else None,
    }
    run = spec.get("run")
    if run:
        top = float(run["top_speed_tiles_per_s"]) * tile
        out["run_speed"] = top
        if run.get("accel_time"):
            out["run_accel"] = top / float(run["accel_time"])
        if run.get("decel_time"):
            out["run_decel"] = top / float(run["decel_time"])
        out["air_control"] = float(run.get("air_control", 1.0))
    return out


def simulate(d, release_tick=None, land_height=0.0, max_ticks=100000):
    """Semi-implicit Euler at the fixed physics rate, like most engines.

    release_tick: tick on which the jump button is let go (None = held).
    land_height: height (world units, up positive) of the surface we land on.
    Returns peak height, ticks to apex, ticks until landing (or None).
    """
    dt = 1.0 / d["physics_hz"]
    y = 0.0
    vy = d["jump_velocity"]
    peak = 0.0
    apex_tick = None
    cut_done = False
    for tick in range(1, max_ticks + 1):
        if release_tick is not None and not cut_done and tick >= release_tick and vy > 0:
            vy *= d["cut_multiplier"]
            cut_done = True
        g = d["rise_gravity"] if vy > 0 else d["fall_gravity"]
        vy -= g * dt
        if d.get("max_fall_speed") and vy < -d["max_fall_speed"]:
            vy = -d["max_fall_speed"]
        y += vy * dt
        if y > peak:
            peak = y
        if apex_tick is None and vy <= 0:
            apex_tick = tick
        if vy < 0:
            if peak < land_height:
                return {"peak": peak, "apex_tick": apex_tick, "land_tick": None,
                        "air_s": None}
            if y <= land_height:
                return {"peak": peak, "apex_tick": apex_tick, "land_tick": tick,
                        "air_s": tick * dt}
    return {"peak": peak, "apex_tick": apex_tick, "land_tick": None, "air_s": None}


def corrected_velocity(d, iters=60):
    """Jump velocity that makes the STEPPED peak hit the target height."""
    target = d["ideal_height"]
    lo, hi = d["jump_velocity"] * 0.5, d["jump_velocity"] * 2.0
    for _ in range(iters):
        mid = (lo + hi) / 2.0
        if simulate(dict(d, jump_velocity=mid))["peak"] < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def sim_report(spec):
    d = derive(spec)
    full = simulate(d)
    hop = simulate(d, release_tick=1)
    tile = d["tile"]
    hz = d["physics_hz"]
    return {
        "physics_hz": hz,
        "full_peak_tiles": round(full["peak"] / tile, 3),
        "target_peak_tiles": round(d["ideal_height"] / tile, 3),
        "peak_error_pct": round(100.0 * (full["peak"] - d["ideal_height"]) / d["ideal_height"], 2),
        "apex_ticks": full["apex_tick"],
        "target_apex_ticks": round(d["ideal_apex_s"] * hz, 2),
        "airtime_ticks": full["land_tick"],
        "airtime_s": round(full["air_s"], 4) if full["air_s"] else None,
        "min_hop_tiles": round(hop["peak"] / tile, 3),
        "hop_ratio": round(hop["peak"] / full["peak"], 3) if full["peak"] else None,
        "formula_jump_velocity": round(d["jump_velocity"], 3),
        "stepped_jump_velocity": round(corrected_velocity(d), 3),
    }


def reach(d, rise=0.0, start_speed=None):
    """Horizontal distance covered at run speed before landing at height rise."""
    speed = d.get("run_speed") if start_speed is None else start_speed
    if not speed:
        raise ValueError("spec needs run.top_speed_tiles_per_s for reach checks")
    r = simulate(d, land_height=rise)
    if r["land_tick"] is None:
        return None, r
    return speed * r["air_s"], r


def reach_report(spec):
    d = derive(spec)
    tile = d["tile"]
    margin_ok = float(spec.get("reach_margin_tiles", 1.0))
    rows = []
    for gap in spec.get("gaps", []):
        width = float(gap["width_tiles"])
        rise = float(gap.get("rise_tiles", 0.0))
        dist, r = reach(d, rise * tile)
        if dist is None:
            verdict, spare = "TOO HIGH", None
        else:
            spare = dist / tile - width
            if spare < 0:
                verdict = "IMPOSSIBLE"
            elif spare < margin_ok:
                verdict = "TIGHT"
            else:
                verdict = "CLEAR"
        want = gap.get("intent")
        rows.append({
            "name": gap.get("name", "?"), "width_tiles": width, "rise_tiles": rise,
            "reach_tiles": None if dist is None else round(dist / tile, 2),
            "spare_tiles": None if spare is None else round(spare, 2),
            "verdict": verdict,
            "intent": want,
            "matches_intent": (want is None) or (want == verdict),
        })
    return rows


def windows_report(spec):
    hz = float(spec.get("units", {}).get("physics_hz", 60))
    rows = []
    for name, secs in sorted(spec.get("assists", {}).items()):
        secs = float(secs)
        exact = secs * hz
        ticks = int(round(exact))
        rows.append({
            "window": name, "seconds": secs, "exact_ticks": round(exact, 3),
            "ticks": ticks, "effective_s": round(ticks / hz, 4),
            "warning": ("rounds to zero ticks: the window does nothing" if ticks == 0 else
                        "rounding changes it by more than 20%" if abs(ticks - exact) / exact > 0.2
                        else None),
        })
    return rows

# ---------------------------------------------------------------- smoothing


def smooth(k, ref_fps, fps_list):
    """A per-frame lerp(a, b, k) at ref_fps behaves like exp smoothing with
    rate = -ln(1-k) * ref_fps. Show what the same k does at other frame rates."""
    if not 0 < k < 1:
        raise ValueError("k must be between 0 and 1")
    rate = -math.log(1.0 - k) * ref_fps
    rows = []
    for fps in fps_list:
        # time to close 90% of the gap if k is applied once per frame at fps
        per_frame_rate = -math.log(1.0 - k) * fps
        t90_naive = math.log(10) / per_frame_rate
        rows.append({"fps": fps, "t90_naive_s": round(t90_naive, 4),
                     "t90_fixed_s": round(math.log(10) / rate, 4),
                     "naive_vs_fixed": round(t90_naive / (math.log(10) / rate), 3)})
    return {"rate_per_s": round(rate, 4),
            "replacement": f"t = 1 - exp(-{rate:.3f} * dt)", "rows": rows}

# ---------------------------------------------------------------- latency


def percentile(values, p):
    s = sorted(values)
    if not s:
        raise ValueError("no values")
    if len(s) == 1:
        return s[0]
    pos = (len(s) - 1) * p
    lo = math.floor(pos)
    hi = math.ceil(pos)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def latency(frames, camera_fps, budget_ms=None):
    if camera_fps <= 0:
        raise ValueError("camera_fps must be positive")
    ms = [f * 1000.0 / camera_fps for f in frames]
    step = 1000.0 / camera_fps
    med = percentile(ms, 0.5)
    p90 = percentile(ms, 0.9)
    out = {"trials": len(ms), "median_ms": round(med, 1), "p90_ms": round(p90, 1),
           "min_ms": round(min(ms), 1), "max_ms": round(max(ms), 1),
           "resolution_ms": round(step, 1)}
    if len(ms) < 10:
        out["warning"] = "fewer than 10 trials: p90 is a guess"
    if budget_ms is not None:
        if p90 + step <= budget_ms:
            out["verdict"] = "WITHIN"
        elif p90 - step > budget_ms:
            out["verdict"] = "OVER"
        else:
            out["verdict"] = "TOO CLOSE TO CALL"
        out["budget_ms"] = budget_ms
    return out

# ---------------------------------------------------------------- A/B


def sign_test(a, b):
    """Exact two-sided binomial sign test, ties already removed."""
    n = a + b
    if n == 0:
        return 1.0
    k = min(a, b)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / 2.0 ** n
    return min(1.0, 2.0 * tail)


def min_n_for(alpha):
    n = 1
    while sign_test(n, 0) >= alpha:
        n += 1
        if n > 1000:
            break
    return n


def abtest(a, b, ties=0, alpha=0.05):
    p = sign_test(a, b)
    n = a + b
    out = {"prefer_a": a, "prefer_b": b, "no_preference": ties, "decisive": n,
           "p_value": round(p, 4), "alpha": alpha}
    if p < alpha:
        out["verdict"] = "A PREFERRED" if a > b else "B PREFERRED"
    else:
        out["verdict"] = "NO DETECTABLE PREFERENCE"
    need = min_n_for(alpha)
    if n < need:
        out["warning"] = (f"with {n} decisive answers no result can reach p<{alpha}; "
                          f"you need at least {need} unanimous ones")
    if ties > n:
        out["note"] = "most players felt no difference: the change may be below notice"
    return out

# ---------------------------------------------------------------- lint

TIERS = ("small", "medium", "large")
LOUD = {"shake", "flash", "zoom", "hitstop"}


def lint(spec):
    issues = []

    def add(level, msg):
        issues.append({"level": level, "msg": msg})

    for key in ("units", "jump"):
        if key not in spec:
            add("error", f"missing section '{key}'")
    if any(i["level"] == "error" for i in issues):
        return issues
    u, j = spec["units"], spec["jump"]
    if "physics_hz" not in u:
        add("error", "units.physics_hz missing: windows and sim need the real tick rate")
    for f in ("height_tiles", "time_to_apex"):
        if f not in j:
            add("error", f"jump.{f} missing")
    if any(i["level"] == "error" for i in issues):
        return issues
    t = float(j["time_to_apex"])
    if not 0.15 <= t <= 0.8:
        add("warn", f"time_to_apex {t}s is outside 0.15-0.8s; check it is seconds, not frames")
    fm = float(j.get("fall_multiplier", 1.0))
    if fm < 1.0:
        add("warn", "fall_multiplier < 1 makes the fall floatier than the rise")
    elif fm > 3.0:
        add("warn", "fall_multiplier > 3 tends to read as a slam, not a jump")
    cut = j.get("cut_multiplier")
    if cut is not None and not 0 < float(cut) <= 1:
        add("error", "cut_multiplier must be in (0, 1]")
    if cut is None:
        add("info", "no cut_multiplier: tap and hold give the same jump")
    hz = float(u["physics_hz"])
    for name, secs in spec.get("assists", {}).items():
        if float(secs) * hz < 1:
            add("error", f"assists.{name} is shorter than one tick at {hz:g} Hz")
        if name.startswith("coyote") and float(secs) >= t:
            add("warn", f"assists.{name} is as long as the rise: it allows jumping off thin air")
    names = set()
    for ev in spec.get("feedback", []):
        e = ev.get("event", "?")
        if e in names:
            add("warn", f"feedback event '{e}' listed twice")
        names.add(e)
        tier = ev.get("tier")
        if tier not in TIERS:
            add("error", f"feedback '{e}': tier must be one of {', '.join(TIERS)}")
        chans = set(ev.get("channels", []))
        if ev.get("frequent") and tier == "large":
            add("warn", f"feedback '{e}' is frequent but tier large: it will tire players")
        if ev.get("frequent") and chans & {"shake", "hitstop"}:
            add("warn", f"feedback '{e}' is frequent and uses {sorted(chans & {'shake','hitstop'})}")
        if len(chans) > 8:
            add("warn", f"feedback '{e}' stacks {len(chans)} channels; past 8 it turns to noise")
    used_loud = set()
    for ev in spec.get("feedback", []):
        used_loud |= set(ev.get("channels", [])) & LOUD
    toggles = set(spec.get("accessibility", []))
    for ch in sorted(used_loud & {"shake", "flash", "zoom"}):
        if ch not in toggles:
            add("warn", f"channel '{ch}' is used but there is no '{ch}' reduce toggle in accessibility")
    if spec.get("gaps") and "run" not in spec:
        add("error", "gaps listed but no run section: reach cannot be checked")
    return issues

# ---------------------------------------------------------------- CLI


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _print(obj, as_json):
    if as_json:
        print(json.dumps(obj, ensure_ascii=False, indent=2))
        return
    rows = obj if isinstance(obj, list) else [obj]
    for r in rows:
        print("  ".join(f"{k}={v}" for k, v in r.items()))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="feelbench", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="print JSON")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("derive", "sim", "reach", "windows", "lint"):
        s = sub.add_parser(name)
        s.add_argument("spec")
    s = sub.add_parser("smooth")
    s.add_argument("k", type=float)
    s.add_argument("--ref-fps", type=float, default=60)
    s.add_argument("--fps", default="30,60,144")
    s = sub.add_parser("latency")
    s.add_argument("--camera-fps", type=float, required=True)
    s.add_argument("--budget-ms", type=float)
    s.add_argument("frames", nargs="+", type=float)
    s = sub.add_parser("abtest")
    s.add_argument("a", type=int)
    s.add_argument("b", type=int)
    s.add_argument("--ties", type=int, default=0)
    s.add_argument("--alpha", type=float, default=0.05)
    args = ap.parse_args(argv)

    if args.cmd == "derive":
        _print({k: (round(v, 4) if isinstance(v, float) else v)
                for k, v in derive(_load(args.spec)).items()}, args.json)
    elif args.cmd == "sim":
        _print(sim_report(_load(args.spec)), args.json)
    elif args.cmd == "reach":
        rows = reach_report(_load(args.spec))
        _print(rows, args.json)
        return 0 if all(r["matches_intent"] for r in rows) else 1
    elif args.cmd == "windows":
        _print(windows_report(_load(args.spec)), args.json)
    elif args.cmd == "lint":
        issues = lint(_load(args.spec))
        if args.json:
            _print(issues, True)
        else:
            for i in issues:
                print(f"{i['level'].upper():5} {i['msg']}")
            if not issues:
                print("OK    no issues")
        return 1 if any(i["level"] == "error" for i in issues) else 0
    elif args.cmd == "smooth":
        fps = [float(x) for x in args.fps.split(",") if x]
        res = smooth(args.k, args.ref_fps, fps)
        if args.json:
            _print(res, True)
        else:
            print(f"rate={res['rate_per_s']}/s  use: {res['replacement']}")
            _print(res["rows"], False)
    elif args.cmd == "latency":
        _print(latency(args.frames, args.camera_fps, args.budget_ms), args.json)
    elif args.cmd == "abtest":
        _print(abtest(args.a, args.b, args.ties, args.alpha), args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
