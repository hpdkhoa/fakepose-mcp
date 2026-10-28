"""One authoring attempt on one hold: write the shift into the gun's overlay, run the hold's clip only, print the
gate, save a crop of the views at the hold. python tune_hold.py <gun> <side:mark> <clip> <forward> <up> <left> [curl]
Environment: TUNE_VIEWS (right,left,top), HANDS_OPTIONS (a JSON of job options), TUNE_TAG (a suffix on the picture)."""
import json, os, sys
from pathlib import Path
from PIL import Image
from weaponlab.gunkit import run as R
gun, key, clip = sys.argv[1], sys.argv[2], sys.argv[3]
fwd, up, left = (float(x) for x in sys.argv[4:7])
curl = sys.argv[7] if len(sys.argv) > 7 else "together"
VIEWS = (os.environ.get("TUNE_VIEWS") or "right").split(",")
ov = Path("K:/Projects/gitHub/fakepose-mcp/src/fakepose_mcp/data/presets/guns") / (gun + ".json")
d = json.loads(ov.read_text(encoding="utf-8"))
d["holds"].setdefault(key, {}).update({"shift_cm": {"forward": fwd, "up": up, "left": left}, "curl": curl})   # the hold's other keys (facing) stay
ov.write_text(json.dumps(d, indent=1), encoding="utf-8")
G = Path("K:/epic/ToangTown/ToangTown/Saved/Gate/gunkit") / gun
opts = dict({"out": str(G / "hands_tune"), "anim_clips": {clip: VIEWS}, "anim_size": [960, 540]}, **json.loads(os.environ.get("HANDS_OPTIONS") or "{}"))
h = R.hands(str(G / "gunfacts.json"), clips=[clip], options=opts)
v = h["fakepose"]["holds"].get(key + ":palm") or h["fakepose"]["holds"].get(key + ":pinch") or h["fakepose"]["holds"].get(key + ":cup") or {}
g = v.get("gate") or {}
print("TUNE", gun, key, "shift", [fwd, up, left], curl, "pass", g.get("pass"), "fails", g.get("fails"), "fixed", json.dumps(g.get("fixed"))[:160])
frames = (h.get("fakepose_animations") or {}).get(clip, {}).get("frames") or []
if frames:
    fr = frames[len(frames) // 2]
    out = Path("K:/Projects/Claude/cc/report/tune") / ("%s_%s_%s%s.png" % (gun, key.replace(":", "_"), "f%.1f_u%.1f_l%.1f" % (fwd, up, left), os.environ.get("TUNE_TAG", "")))
    out.parent.mkdir(parents=True, exist_ok=True)
    ims = [Image.open(fr[v_]).convert("RGB") for v_ in VIEWS if v_ in fr]
    W = sum(i.width for i in ims); H = max(i.height for i in ims)
    sheet = Image.new("RGB", (W, H)); x = 0
    for i in ims:
        sheet.paste(i, (x, 0)); x += i.width
    sheet.save(out)
    print("PIC", out)
gd = (g.get("after") or {}).get("digits") or {}
print("gate digits", {k: (x["tip_gap_cm"], x["touch"], x["inside"]) for k, x in gd.items()})
print("limits", v.get("limits"))
