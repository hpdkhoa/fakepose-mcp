"""The game's AR-15 clips measured with Pose Lab's lab (the owner's quality bar for fakepose): where the gun sits in
the eye's view, its angles, the port's facing, each hand's place on screen, the arms against the anatomy rules.
    blender -b --factory-startup -P measure_ar_game.py -- <project> <out.json>"""
import json
import math
import os
import sys

sys.path.insert(0, r"K:\epic\ToangTown\ToangTown\Tools\poselab")
import lab  # noqa: E402
from mathutils import Vector  # noqa: E402

project, out = sys.argv[sys.argv.index("--") + 1:][:2]
L = lab.Lab(project)
L.load_rig("ar")
H_FOV, ASPECT = lab.H_FOV, lab.ASPECT
t_ = math.tan(math.radians(H_FOV / 2.0))


def screen_of(p_world):
    p = L._to(p_world, "view")
    if p.y <= 0:
        return None
    return [round(p.x / p.y / t_, 3), round(p.z / p.y / (t_ / ASPECT), 3)]


def gun_angles():
    q = L._gun().to_quaternion()
    fwd = (q @ Vector((0.0, -1.0, 0.0))).normalized()          # the barrel (gun +Y is Blender -Y)
    left = (q @ Vector((1.0, 0.0, 0.0))).normalized()           # the gun's left (Unreal +X = Blender +X? ue() maps)
    up = (q @ Vector((0.0, 0.0, 1.0))).normalized()
    # yaw: the barrel's turn left of the view (about up); pitch: its climb; roll: the gun's up tipped right (+) or left
    yaw = math.degrees(math.atan2(fwd.dot(-lab.VIEW_RIGHT), fwd.dot(lab.VIEW_FWD)))
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, fwd.dot(lab.VIEW_UP)))))
    roll = math.degrees(math.atan2(up.dot(lab.VIEW_RIGHT), up.dot(lab.VIEW_UP)))
    return {"yaw_left_deg": round(yaw, 1), "pitch_up_deg": round(pitch, 1), "roll_right_deg": round(roll, 1),
            "barrel_off_view_deg": round(L._barrel_off(), 1)}


def measure(tag):
    row = {"pose": tag, "gun": gun_angles(), "screen": {}, "view_cm": {}}
    for n in ("muzzle", "bore", "stock", "t_mark", "port", "hand_l", "hand_r", "lowerarm_l", "lowerarm_r"):
        try:
            p = L._point(n)
        except Exception as e:
            row["screen"][n] = str(e)
            continue
        row["screen"][n] = screen_of(p)
        row["view_cm"][n] = [round(v, 1) for v in L._to(p, "view")]
    row["port"] = L.faces_eye("port")
    try:
        row["port_visible"] = L.visible("port")
    except Exception as e:
        row["port_visible"] = str(e)
    an = L.anatomy("both")
    row["anatomy"] = {s: {"ok": not an[s]["bad"], "bad": an[s]["bad"],
                          "numbers": {k: v for k, v in an[s].items() if k not in ("bad",)}} for s in ("l", "r")}
    # the gun's share of the screen: a coarse grid of rays from the eye
    dg = __import__("bpy").context.evaluated_depsgraph_get()
    hits, tot = 0, 0
    for i in range(48):
        for j in range(27):
            x = (i + 0.5) / 48 * 2 - 1
            y = 1 - (j + 0.5) / 27 * 2
            d = (lab.VIEW_RIGHT * (x * t_) + lab.VIEW_FWD + lab.VIEW_UP * (y * t_ / ASPECT)).normalized()
            hit = L.sc.ray_cast(dg, L.eye, d, distance=3.0)[0]
            hits += 1 if hit else 0
            tot += 1
    row["cover_share"] = round(hits / tot, 3)
    return row


rows = [dict(measure("idle"), clip="idle")]
L.pose_idle()
for clip in ("check", "charge"):
    n = L._clip_len(clip)
    for k in range(5):
        t = n * k / 4
        L.pose_clip(clip, t)
        rows.append(dict(measure("%s %.2fs" % (clip, t)), clip=clip, t=round(t, 3), length=round(n, 3)))
json.dump({"rig": "ar", "fov": [H_FOV, ASPECT], "rows": rows}, open(out, "w"), indent=1, default=str)
print("MEASURED", len(rows))
