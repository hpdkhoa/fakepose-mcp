"""Rule 7 re-measured on the bar: the share of the game's check and charge frames with the left hand bone on screen."""
import json, math, sys
sys.path.insert(0, r"K:\epic\ToangTown\ToangTown\Tools\poselab")
import lab
project = sys.argv[sys.argv.index("--") + 1]
L = lab.Lab(project); L.load_rig("ar")
out = {}
for clip in ("check", "charge"):
    n = L._clip_len(clip); on = tot = 0; rows = []
    for k in range(int(n / 0.05) + 1):
        t = k * 0.05; L.pose_clip(clip, t)
        sc = L.screen("hand_l"); tot += 1; on += 1 if sc.get("on_screen") else 0
        rows.append([round(t, 2), sc.get("x"), sc.get("y")])
    out[clip] = {"share_on_screen": round(on / tot, 2), "frames": tot, "rows": rows}
print("HAND_ON", json.dumps({k: {"share": v["share_on_screen"], "rows": v["rows"][::4]} for k, v in out.items()}))
