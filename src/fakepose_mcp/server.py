"""fakepose-mcp: first-person hands on a gun, posed the way games do it.

A hold is an authored preset placed on a mark (a socket) of the gun; each finger closes until it touches; the arms reach
by two-bone IK. The one rule is the market's: no clipping the first-person camera can see. The posing runs inside
Weapon Lab's Gun Kit hands step (pose_engine "fakepose"), which writes the clips; these tools list and edit the presets,
run that step, and read its results.
"""
import json
import os
from pathlib import Path
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from . import __version__

HERE = Path(__file__).resolve().parent
PRESETS = HERE / "data" / "presets"

mcp = MCPServer("fakepose", title="fakepose", version=__version__, instructions=(
    "fakepose poses first-person hands on a gun the way games do: authored grip presets on the gun's marks, fingers "
    "curled to contact, two-bone IK, the eye at the head bone (Epic's first-person template offset). Its rule: zero "
    "clipping seen from the first-person camera; anatomy is reported, not enforced. Call list_presets, then run_hands "
    "with a Gun Kit facts file; read results with hold_report and clip_report. The pictures are in the gun's "
    "hands/fakepose_eye folder."))

FactsPath = Annotated[str, Field(description="a Gun Kit facts file (gunfacts.json) of the gun")]


def _facts(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hands_json(path):
    p = Path(path).parent / "hands" / "hands.json"
    if not p.exists():
        raise FileNotFoundError("no hands.json beside %s: run run_hands first" % path)
    return json.loads(p.read_text(encoding="utf-8"))


@mcp.tool()
def list_presets() -> dict:
    """The preset families (pistol, rifle ...), each hold in them (side:mark[:kind]) with its source, and the captured
    grips (a hand-to-gun pose kept from an approved hold)."""
    out = {}
    for p in sorted(PRESETS.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        out[p.stem] = {k: v.get("source", "") for k, v in d.get("holds", {}).items()}
    cap = PRESETS / "captured"
    out["captured"] = sorted(x.name for x in cap.glob("*.json")) if cap.exists() else []
    return out


@mcp.tool()
def show_preset(family: Annotated[str, Field(description="pistol or rifle")],
                hold: Annotated[str, Field(description="side:mark or side:mark:kind, e.g. l:support:palm")]) -> dict:
    """One preset in full: where the hand sits on the mark (palm facing, finger direction, offsets, push out) and each
    digit's rule (keep, or curl to contact toward the fist)."""
    d = json.loads((PRESETS / (family + ".json")).read_text(encoding="utf-8"))
    if hold not in d.get("holds", {}):
        raise KeyError("no hold %r in %s: %s" % (hold, family, sorted(d.get("holds", {}))))
    return d["holds"][hold]


@mcp.tool()
def set_preset(family: Annotated[str, Field(description="pistol or rifle")],
               hold: Annotated[str, Field(description="side:mark or side:mark:kind")],
               preset: Annotated[dict, Field(description="the hold: source, contact (palm_skin or pinch), palm_into and "
                                                         "fingers_toward (weights on forward, up, left), offset_cm, "
                                                         "push_out, fingers {digit: {rule, target_deg, other_hand}}")]) -> dict:
    """Adds or replaces one authored hold. The next run_hands uses it."""
    for k in ("source", "palm_into", "fingers_toward"):
        if k not in preset:
            raise ValueError("a preset needs %r" % k)
    p = PRESETS / (family + ".json")
    d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"contract": "fakepose-presets/1", "family": family, "holds": {}}
    d["holds"][hold] = preset
    p.write_text(json.dumps(d, indent=1), encoding="utf-8")
    return {"saved": hold, "file": str(p)}


@mcp.tool()
def run_hands(facts: FactsPath,
              clips: Annotated[list[str] | None, Field(description="clip ids to make (default: every clip of the gun's action)")] = None) -> dict:
    """Runs Weapon Lab's Gun Kit hands step with fakepose (Blender, at most 10 minutes): the gun at aim, the holds from
    the presets, every clip keyed and written, the eye's clipping checked. Returns the summary."""
    from weaponlab.gunkit import run as R
    h = R.hands(facts, clips=clips, options={"pose_engine": "fakepose", "fakepose": str(HERE / "blender")})
    return _summary(h)


def _summary(h):
    f = h.get("fakepose", {})
    return {"engine": h.get("pose_engine"), "eye": f.get("eye"), "aim": f.get("aim"),
            "home_eye_clip_pixels": (f.get("eye_clip") or {}).get("clip_pixels"),
            "clips": {k: {"frames": v.get("frames"), "frames_checked": v.get("frames_checked"),
                          "frames_with_clip": v.get("frames_with_clip"), "most_pixels": v.get("most_pixels")}
                      for k, v in (h.get("fakepose_clips_eye") or {}).items()},
            "written": [k for k, v in (h.get("clips") or {}).items() if isinstance(v, dict) and v.get("written")],
            "budget_cut": h.get("budget_cut")}


@mcp.tool()
def hold_report(facts: FactsPath) -> dict:
    """The last run's holds: each preset's source, the fingers' curls and what stopped them, the arm's angles (reported,
    not enforced), how far a hand was set down off the surface."""
    return (_hands_json(facts).get("fakepose") or {}).get("holds", {})


@mcp.tool()
def clip_report(facts: FactsPath) -> dict:
    """The last run's clips: frames, the eye's clipping per clip (frames checked, frames with clipping, the most
    pixels, the deepest seen), and the first-person pictures (start, middle, end)."""
    h = _hands_json(facts)
    return {"summary": _summary(h), "pictures": h.get("fakepose_eye_pictures")}


def main():
    mcp.run()


if __name__ == "__main__":
    main()
