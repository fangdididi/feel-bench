import io
import json
import math
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import feelbench as fb  # noqa: E402

EXAMPLE = os.path.join(os.path.dirname(__file__), "..", "examples", "feel.json")


def base_spec(**over):
    spec = {
        "units": {"tile": 16, "physics_hz": 60},
        "jump": {"height_tiles": 4, "time_to_apex": 0.4, "fall_multiplier": 2.0,
                 "cut_multiplier": 0.5},
        "run": {"top_speed_tiles_per_s": 8},
        "assists": {"coyote_s": 0.1, "buffer_s": 0.12},
    }
    spec.update(over)
    return spec


class DeriveTests(unittest.TestCase):
    def test_gravity_and_velocity_from_height_and_time(self):
        d = fb.derive(base_spec())
        h = 64.0
        self.assertAlmostEqual(d["rise_gravity"], 2 * h / 0.16)
        self.assertAlmostEqual(d["jump_velocity"], 2 * h / 0.4)
        self.assertAlmostEqual(d["fall_gravity"], d["rise_gravity"] * 2)

    def test_continuous_peak_matches_target(self):
        d = fb.derive(base_spec())
        v, g = d["jump_velocity"], d["rise_gravity"]
        self.assertAlmostEqual(v * v / (2 * g), d["ideal_height"])

    def test_fall_time_shrinks_with_multiplier(self):
        d = fb.derive(base_spec())
        self.assertAlmostEqual(d["ideal_fall_s"], 0.4 / math.sqrt(2))

    def test_run_accel_from_time(self):
        spec = base_spec(run={"top_speed_tiles_per_s": 10, "accel_time": 0.1})
        self.assertAlmostEqual(fb.derive(spec)["run_accel"], 1600.0)


class SimTests(unittest.TestCase):
    def test_stepped_peak_is_close_but_not_exact(self):
        r = fb.sim_report(base_spec())
        self.assertNotEqual(r["full_peak_tiles"], r["target_peak_tiles"])
        self.assertLess(abs(r["peak_error_pct"]), 6)

    def test_higher_tick_rate_is_more_accurate(self):
        lo = fb.sim_report(base_spec(units={"tile": 16, "physics_hz": 30}))
        hi = fb.sim_report(base_spec(units={"tile": 16, "physics_hz": 240}))
        self.assertLess(abs(hi["peak_error_pct"]), abs(lo["peak_error_pct"]))

    def test_corrected_velocity_hits_target(self):
        spec = base_spec()
        d = fb.derive(spec)
        v = fb.corrected_velocity(d)
        peak = fb.simulate(dict(d, jump_velocity=v))["peak"]
        self.assertAlmostEqual(peak, d["ideal_height"], places=3)

    def test_release_early_gives_lower_hop(self):
        r = fb.sim_report(base_spec())
        self.assertLess(r["min_hop_tiles"], r["full_peak_tiles"])
        self.assertLess(r["hop_ratio"], 1)

    def test_no_cut_means_same_height(self):
        spec = base_spec()
        spec["jump"]["cut_multiplier"] = 1.0
        r = fb.sim_report(spec)
        self.assertEqual(r["hop_ratio"], 1.0)

    def test_terminal_velocity_clamps_fall(self):
        spec = base_spec()
        spec["jump"]["max_fall_tiles_per_s"] = 5
        d = fb.derive(spec)
        r = fb.simulate(d, land_height=-2000)
        free = fb.simulate(fb.derive(base_spec()), land_height=-2000)
        self.assertGreater(r["land_tick"], free["land_tick"])


class ReachTests(unittest.TestCase):
    def test_verdicts(self):
        spec = base_spec(gaps=[
            {"name": "easy", "width_tiles": 2},
            {"name": "far", "width_tiles": 40},
            {"name": "high", "width_tiles": 1, "rise_tiles": 10},
        ])
        rows = {r["name"]: r for r in fb.reach_report(spec)}
        self.assertEqual(rows["easy"]["verdict"], "CLEAR")
        self.assertEqual(rows["far"]["verdict"], "IMPOSSIBLE")
        self.assertEqual(rows["high"]["verdict"], "TOO HIGH")

    def test_tight_inside_margin(self):
        d = fb.derive(base_spec())
        dist, _ = fb.reach(d)
        width = dist / 16 - 0.5
        rows = fb.reach_report(base_spec(gaps=[{"name": "t", "width_tiles": width}]))
        self.assertEqual(rows[0]["verdict"], "TIGHT")

    def test_ledge_above_shortens_reach(self):
        d = fb.derive(base_spec())
        flat, _ = fb.reach(d, 0)
        up, _ = fb.reach(d, 3 * 16)
        self.assertLess(up, flat)

    def test_reach_needs_run_section(self):
        spec = base_spec()
        del spec["run"]
        with self.assertRaises(ValueError):
            fb.reach(fb.derive(spec))

    def test_example_flags_the_long_pit(self):
        with open(EXAMPLE, encoding="utf-8") as fh:
            rows = {r["name"]: r for r in fb.reach_report(json.load(fh))}
        self.assertFalse(rows["1-3 long pit"]["matches_intent"])
        self.assertTrue(rows["1-5 wall"]["matches_intent"])


class WindowTests(unittest.TestCase):
    def test_ticks_and_warnings(self):
        spec = base_spec(units={"tile": 16, "physics_hz": 30},
                         assists={"coyote_s": 0.01, "buffer_s": 0.05, "ok_s": 0.1})
        rows = {r["window"]: r for r in fb.windows_report(spec)}
        self.assertEqual(rows["coyote_s"]["ticks"], 0)
        self.assertIn("zero", rows["coyote_s"]["warning"])
        self.assertIn("20%", rows["buffer_s"]["warning"])
        self.assertEqual(rows["ok_s"]["ticks"], 3)
        self.assertIsNone(rows["ok_s"]["warning"])


class SmoothTests(unittest.TestCase):
    def test_rate_reproduces_reference(self):
        res = fb.smooth(0.1, 60, [60])
        self.assertAlmostEqual(res["rows"][0]["naive_vs_fixed"], 1.0)
        self.assertAlmostEqual(1 - math.exp(-res["rate_per_s"] / 60), 0.1, places=4)

    def test_naive_lerp_doubles_at_half_fps(self):
        res = fb.smooth(0.2, 60, [30, 120])
        self.assertAlmostEqual(res["rows"][0]["naive_vs_fixed"], 2.0)
        self.assertAlmostEqual(res["rows"][1]["naive_vs_fixed"], 0.5)

    def test_bad_k(self):
        with self.assertRaises(ValueError):
            fb.smooth(1.0, 60, [60])


class LatencyTests(unittest.TestCase):
    def test_conversion_and_verdicts(self):
        frames = [20] * 10
        self.assertEqual(fb.latency(frames, 240, 100)["verdict"], "WITHIN")
        self.assertEqual(fb.latency([30] * 10, 240, 100)["verdict"], "OVER")
        self.assertEqual(fb.latency([24] * 10, 240, 100)["verdict"], "TOO CLOSE TO CALL")
        self.assertAlmostEqual(fb.latency(frames, 240)["median_ms"], 83.3)

    def test_few_trials_warn(self):
        self.assertIn("warning", fb.latency([20, 21], 240))


class ABTests(unittest.TestCase):
    def test_sign_test_values(self):
        self.assertAlmostEqual(fb.sign_test(5, 5), 1.0)
        self.assertAlmostEqual(fb.sign_test(6, 0), 2 / 64)
        self.assertAlmostEqual(fb.sign_test(0, 6), 2 / 64)

    def test_verdicts_and_minimum(self):
        self.assertEqual(fb.abtest(12, 2)["verdict"], "A PREFERRED")
        self.assertEqual(fb.abtest(2, 12)["verdict"], "B PREFERRED")
        self.assertEqual(fb.abtest(11, 3)["verdict"], "NO DETECTABLE PREFERENCE")
        self.assertIn("warning", fb.abtest(5, 0))
        self.assertEqual(fb.min_n_for(0.05), 6)

    def test_many_ties_note(self):
        self.assertIn("note", fb.abtest(2, 1, ties=9))


class LintTests(unittest.TestCase):
    def levels(self, spec):
        return [(i["level"], i["msg"]) for i in fb.lint(spec)]

    def test_example_is_clean(self):
        with open(EXAMPLE, encoding="utf-8") as fh:
            self.assertEqual(fb.lint(json.load(fh)), [])

    def test_missing_sections(self):
        msgs = self.levels({"jump": {}})
        self.assertTrue(any(l == "error" and "units" in m for l, m in msgs))

    def test_frames_mistaken_for_seconds(self):
        spec = base_spec()
        spec["jump"]["time_to_apex"] = 20
        self.assertTrue(any("frames" in m for _, m in self.levels(spec)))

    def test_feedback_rules(self):
        spec = base_spec(feedback=[
            {"event": "step", "tier": "large", "frequent": True, "channels": ["shake"]},
            {"event": "hit", "tier": "huge", "channels": ["flash"]},
        ])
        msgs = " | ".join(m for _, m in self.levels(spec))
        self.assertIn("tire players", msgs)
        self.assertIn("tier must be", msgs)
        self.assertIn("'shake' reduce toggle", msgs)
        self.assertIn("'flash' reduce toggle", msgs)

    def test_coyote_longer_than_rise(self):
        spec = base_spec(assists={"coyote_s": 0.5})
        self.assertTrue(any("thin air" in m for _, m in self.levels(spec)))


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = fb.main(list(argv))
        return code, buf.getvalue()

    def test_reach_exit_code_reflects_intent(self):
        code, out = self.run_cli("reach", EXAMPLE)
        self.assertEqual(code, 1)
        self.assertIn("IMPOSSIBLE", out)

    def test_lint_exit_code_on_error(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump({"units": {}, "jump": {"height_tiles": 3, "time_to_apex": 0.3}}, fh)
        try:
            code, out = self.run_cli("lint", fh.name)
        finally:
            os.unlink(fh.name)
        self.assertEqual(code, 1)
        self.assertIn("physics_hz", out)

    def test_json_output(self):
        code, out = self.run_cli("--json", "abtest", "9", "1")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["verdict"], "A PREFERRED")


if __name__ == "__main__":
    unittest.main()
