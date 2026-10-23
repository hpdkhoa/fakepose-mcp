"""The presets are data: each hold names its source, says how the hand sits, and gives every rule a known name."""
import json
from pathlib import Path

PRESETS = Path(__file__).resolve().parents[1] / "src" / "fakepose_mcp" / "data" / "presets"
RULES = {"keep", "curl_to_contact"}
AXES = {"forward", "up", "left"}


def families():
    return sorted(PRESETS.glob("*.json"))


def test_a_family_exists():
    assert families(), "no preset family"


def test_every_hold_is_complete():
    for p in families():
        d = json.loads(p.read_text(encoding="utf-8"))
        for name, h in d["holds"].items():
            assert h.get("source"), (p.name, name, "no source")
            placed = "mirror_of" in h or ("palm_into" in h and "fingers_toward" in h) or name == "r:grip:palm"
            assert placed, (p.name, name, "no way to place the hand")
            for k in ("palm_into", "fingers_toward"):
                if k in h:
                    assert set(h[k]) <= AXES, (name, k)
            for digit, r in h.get("fingers", {}).items():
                assert r["rule"] in RULES, (name, digit, r["rule"])
                if r["rule"] == "curl_to_contact":
                    t = r["target_deg"]
                    assert t == "fist" or (isinstance(t, list) and len(t) == 3), (name, digit)


def test_mirrors_point_at_a_hold():
    for p in families():
        d = json.loads(p.read_text(encoding="utf-8"))
        for name, h in d["holds"].items():
            if "mirror_of" in h:
                side, mark = h["mirror_of"].split(":")
                assert side in ("l", "r") and mark


def test_captured_grips_are_whole():
    for p in sorted((PRESETS / "captured").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        assert len(d["rel_to_mark_bone"]) == 4 and all(len(r) == 4 for r in d["rel_to_mark_bone"])
        assert d["fingers"] and d["source"]
