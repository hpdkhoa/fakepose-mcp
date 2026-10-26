"""The bar's own holds captured: the game's AR-15 mended idle (right hand on the grip, left on the handguard) read
with Pose Lab's lab, each hand's matrix relative to the gun's frame and its finger turns, written as fakepose
captured presets for the Model Lab AR15 (the hand placed against the AR15's grip and support marks the same way it
sits against the pack gun's).
    blender -b --factory-startup -P capture_ar_holds.py -- <project> <facts.json> <out dir>"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, r"K:\epic\ToangTown\ToangTown\Tools\poselab")
import lab  # noqa: E402
from mathutils import Matrix, Quaternion, Vector  # noqa: E402

project, facts_path, out_dir = sys.argv[sys.argv.index("--") + 1:][:3]
facts = json.load(open(facts_path, encoding="utf-8"))
L = lab.Lab(project)
L.load_rig("ar")
# the mended idle (2026-10-10: the pack's idle with its anatomy faults mended), bone data
mend = json.load(open(os.path.join(project, "Saved", "PoseLab", "grip", "mend", "ar_idle_mended.pose.json")))
fr = mend["frames"][0]
for pb in L.arm.pose.bones:
    if pb.name in fr:
        l0, q0 = fr[pb.name]
        pb.location, pb.rotation_quaternion = Vector(l0), Quaternion(q0)
import bpy  # noqa: E402
bpy.context.view_layer.update()
L._place_rifle()
Ginv = L._gun().inverted()
print("ue(1,2,3) =", list(lab.ue((1.0, 2.0, 3.0))))
# the rifle's points in the gun frame (Unreal cm: +X left, +Y along the barrel, +Z up)
dg = bpy.context.evaluated_depsgraph_get()
ev = L.rifle_mesh.evaluated_get(dg)
me = ev.to_mesh()
P = np.array([list(lab.ue_back(Ginv @ (ev.matrix_world @ v.co))) for v in me.vertices])
ev.to_mesh_clear()
hand = {s: lab.ue_back(Ginv @ L._bw("hand_" + s).translation) for s in ("r", "l")}
print("hand_r in gun frame", [round(v, 2) for v in hand["r"]], "hand_l", [round(v, 2) for v in hand["l"]])
# the grip: the rifle's points below the receiver near the right hand; its right face (least x: +X is left) at its middle
hr = np.array(list(hand["r"]))
g = P[(P[:, 2] < hr[2] + 2.0) & (np.abs(P[:, 1] - hr[1]) < 6.0) & (P[:, 2] > hr[2] - 8.0)]     # the grip body, under the receiver
if len(g) == 0:
    raise SystemExit("no grip points found near the right hand")
xr = np.percentile(g[:, 0], 5)
face = g[g[:, 0] < xr + 0.4]
grip_game = [float(xr), float(np.median(face[:, 1])), float(np.median(face[:, 2]))]
# the support: the handguard's underside at the left hand's station, its middle across
hl = np.array(list(hand["l"]))
s_ = P[(np.abs(P[:, 1] - hl[1]) < 3.0) & (P[:, 2] < 6.0)]
zb = np.percentile(s_[:, 2], 3)
bottom = s_[s_[:, 2] < zb + 0.5]
support_game = [float(np.median(bottom[:, 0])), float(hl[1]), float(zb)]
print("grip (game, gun cm)", [round(v, 2) for v in grip_game], "support", [round(v, 2) for v in support_game], "points", len(g), len(s_))
FINGERS = ("thumb", "index", "middle", "ring", "pinky")
out = {}
for s, mark, game_pt in (("r", "grip", grip_game), ("l", "support", support_game)):
    rel = Ginv @ L._bw("hand_" + s)                      # the hand in the gun's Blender-local frame (as Gun Kit's Root bone)
    ours = facts["marks"][mark]
    # both points against their bore line: the pack gun's frame has its bore 3 cm over its origin (rigs.json ar
    # "bore": [0, 0, 3]), the AR15's facts frame has the bore at z 0; the raw frames put the hand 3 cm too low
    bore_z = L.R.get("points", {}).get("bore", [0.0, 0.0, 0.0])[2]
    game_rel = [game_pt[0], game_pt[1], game_pt[2] - bore_z]
    shift = lab.ue(ours) - lab.ue(game_rel)
    rel2 = Matrix.Translation(shift) @ rel
    fingers = {pb.name: list(pb.rotation_quaternion) for pb in L.arm.pose.bones
               if any(pb.name.startswith(f + "_") for f in FINGERS) and pb.name.endswith("_" + s)}
    an = L.anatomy(s)[s]
    rec = {"contract": "fakepose-captured/1", "gun": facts["name"], "side": s, "mark": mark, "fingers_fit": False,
           "rel_to_mark_bone": [list(r) for r in rel2], "fingers": fingers,
           "source": "the game's AR-15 idle (the pack's hold, mended 2026-10-10), read with Pose Lab (rig ar) on 2026-10-26: the owner's bar (POSE_RULES.md); "
                     "the hand's frame against the gun's, moved from the pack gun's %s point %s to the AR15's %s mark %s (gun cm)" % (mark, [round(v, 2) for v in game_pt], mark, ours),
           "readings": {"hand_in_gun_frame_cm": [round(v, 2) for v in hand[s]], "wrist_bend_deg": an.get("wrist_bend_deg"), "elbow_bend_deg": an.get("elbow_bend_deg"),
                        "elbow_below_shoulder_cm": an.get("elbow_below_shoulder_cm"), "bad": an.get("bad")}}
    path = os.path.join(out_dir, "%s_%s_%s.json" % (facts["name"], s, mark))
    json.dump(rec, open(path, "w", encoding="utf-8"), indent=1)
    out[s] = path
    print("CAPTURED", s, mark, path, rec["readings"])
