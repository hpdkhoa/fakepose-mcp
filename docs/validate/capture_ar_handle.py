"""The bar's charging-handle pinch captured: the game's AR-15 charge clip at its pull (0.47 s), the left hand against
the handle point (rigs.json t_mark, against the bore line), as a fakepose captured hold for the AR15 (kind pinch).
    blender -b --factory-startup -P capture_ar_handle.py -- <project> <facts.json> <out dir>"""
import json, os, sys
sys.path.insert(0, r"K:\epic\ToangTown\ToangTown\Tools\poselab")
import lab
from mathutils import Matrix, Vector
import bpy
project, facts_path, out_dir = sys.argv[sys.argv.index("--") + 1:][:3]
facts = json.load(open(facts_path, encoding="utf-8"))
L = lab.Lab(project); L.load_rig("ar")
# the pull's moment: the time the left hand's middle knuckle sits nearest the handle point, scanned over the clip
n = L._clip_len("charge")
best = None
for k in range(int(n / 0.0167) + 1):
    t = k * 0.0167
    L.pose_clip("charge", t)
    d = (L._bw("middle_01_l").translation - L._point("t_mark")).length * 100.0
    if best is None or d < best[0]:
        best = (d, t)
print("NEAREST knuckle to the handle: %.1f cm at %.2f s" % best)
L.pose_clip("charge", best[1])
Ginv = L._gun().inverted()
bore_z = L.R["points"]["bore"][2]
tm = L.R["points"]["t_mark"]
game_rel = [tm[0], tm[1], tm[2] - bore_z]
ours = facts["marks"]["handle"]
hand = lab.ue_back(Ginv @ L._bw("hand_l").translation)
rel = Ginv @ L._bw("hand_l")
rel2 = Matrix.Translation(lab.ue(ours) - lab.ue(game_rel)) @ rel
an = L.anatomy("l")["l"]
rec = {"contract": "fakepose-captured/1", "gun": facts["name"], "side": "l", "mark": "handle", "kind": "pinch", "fingers_fit": False,
       "rel_to_mark_bone": [list(r) for r in rel2],
       "fingers": {pb.name: list(pb.rotation_quaternion) for pb in L.arm.pose.bones if pb.name.endswith("_l") and any(pb.name.startswith(f + "_") for f in ("thumb", "index", "middle", "ring", "pinky"))},
       "source": "the game's AR-15 charge clip at the pull (the left knuckle nearest the handle), read with Pose Lab (rig ar) on 2026-10-26: the owner's bar; the hand's frame against the gun's, moved from the pack gun's handle point %s (against its bore line) to the AR15's handle mark %s" % ([round(v, 2) for v in game_rel], ours),
       "readings": {"hand_in_gun_frame_cm": [round(v, 2) for v in hand], "wrist_bend_deg": an.get("wrist_bend_deg"), "elbow_bend_deg": an.get("elbow_bend_deg"), "bad": an.get("bad")}}
path = os.path.join(out_dir, "%s_l_handle.json" % facts["name"])
json.dump(rec, open(path, "w", encoding="utf-8"), indent=1)
print("CAPTURED l handle", path, rec["readings"])
