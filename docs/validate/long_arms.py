"""Run: blender -b --factory-startup -P Tools/blender/long_arms.py -- 32.8
The shared Gun Kit arms (Saved/PoseLab/ar_slim/Arms.fbx) with each upper arm lengthened to a man's (the owner,
2026-10-27: "upper arm will need to lengthen"): the elbow joint and everything below it moved out along the upper
arm's line, the upper arm's skin stretched along that line, the forearm and hand carried out whole. ANSUR II men,
50th percentile: shoulder joint to elbow joint about 32.8 cm (36.3 from the acromion, minus about 3.5). The file is
written back in place; the old one is kept as Arms.pre_long_upperarm.fbx. The skeleton edit also goes to
bone_edits.json ("upperarm": the factor) for Pose Lab, which drives the mesh with the idle clip's skeleton.
Arg after --: the target upper arm length in cm (the bone, shoulder joint to elbow joint)."""
import sys, json, os, shutil
import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TARGET = float(args[0]) if args else 32.8
F = r"K:\epic\ToangTown\ToangTown\Saved\PoseLab\ar_slim"
SRC = os.path.join(F, "Arms.fbx")
KEEP = os.path.join(F, "Arms.pre_long_upperarm.fbx")
if not os.path.exists(KEEP):
    shutil.copy2(SRC, KEEP)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
me = max((o for o in bpy.data.objects if o.type == "MESH"), key=lambda o: len(o.data.vertices))
W = me.matrix_world
Wi = W.inverted()
B = lambda n: arm.matrix_world @ arm.data.bones[n].head_local     # noqa: E731
names = {g.index: g.name for g in me.vertex_groups}
LOWER = ("lowerarm", "hand", "index", "middle", "ring", "pinky", "thumb", "ik")   # carried out whole, below the elbow
UPPER = ("upperarm",)                                                               # stretched along the upper arm
frames = {}
for s in ("l", "r"):
    S, E = B("upperarm_" + s), B("lowerarm_" + s)
    L = (E - S).length
    k = TARGET / (L * 100.0)
    frames[s] = (S, (E - S).normalized(), L, k)
report = {"target_cm": TARGET, "before_cm": {s: round(frames[s][2] * 100, 2) for s in frames}, "factor": {s: round(frames[s][3], 4) for s in frames}}

def shift(p, s, kind):
    S, d, L, k = frames[s]
    if kind == "lower":
        return d * (L * (k - 1.0))
    return d * (min(max((p - S).dot(d), 0.0), L) * (k - 1.0))

moved = 0
for v in me.data.vertices:
    if not v.groups:
        continue
    tot = sum(g.weight for g in v.groups) or 1.0
    p = W @ v.co
    q = p.copy()
    for g in v.groups:
        n = names.get(g.group, "")
        bits = n.split("_")
        if bits[-1] not in ("l", "r"):
            continue
        if bits[0] in UPPER:
            q = q + shift(p, bits[-1], "upper") * (g.weight / tot)
        elif bits[0] in LOWER:
            q = q + shift(p, bits[-1], "lower") * (g.weight / tot)
    if (q - p).length > 1e-7:
        v.co = Wi @ q
        moved += 1
# the skeleton: the upper arm's tail out by the factor, its twist bones along the line, the elbow's subtree whole
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
Mi, Mw = arm.matrix_world.inverted(), arm.matrix_world
for s in ("l", "r"):
    S, d, L, k = frames[s]
    up = arm.data.edit_bones["upperarm_" + s]
    lower = set(b.name for b in arm.data.edit_bones["lowerarm_" + s].children_recursive) | {"lowerarm_" + s}
    for eb in list(up.children_recursive) + [up]:
        roll = eb.roll
        h, t = Mw @ eb.head, Mw @ eb.tail
        if eb.name == up.name:
            eb.tail = Mi @ (h + (t - h) * k)
        elif eb.name in lower:
            eb.head, eb.tail = Mi @ (h + shift(h, s, "lower")), Mi @ (t + shift(t, s, "lower"))
        else:
            eb.head, eb.tail = Mi @ (h + shift(h, s, "upper")), Mi @ (t + shift(t, s, "upper"))
        eb.roll = roll
bpy.ops.object.mode_set(mode="OBJECT")
report["after_cm"] = {s: round((B("lowerarm_" + s) - B("upperarm_" + s)).length * 100, 2) for s in ("l", "r")}
report["forearm_cm"] = {s: round((B("hand_" + s) - B("lowerarm_" + s)).length * 100, 2) for s in ("l", "r")}
report["moved"] = moved
bpy.ops.object.select_all(action="DESELECT")
for o in bpy.data.objects:
    if o.type in ("MESH", "ARMATURE"):
        o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.fbx(filepath=SRC, use_selection=True, object_types={"ARMATURE", "MESH"}, add_leaf_bones=False,
                         bake_anim=False, global_scale=1.0, apply_unit_scale=True)
be_p = os.path.join(F, "bone_edits.json")
be = json.load(open(be_p, encoding="utf-8")) if os.path.exists(be_p) else {}
be["upperarm"] = round(frames["r"][3], 4)
be["upperarm_why"] = "long_arms.py: each upper arm bone to %.1f cm (ANSUR II men, 50th), the elbow's subtree carried out whole (the same edits the mesh got)" % TARGET
json.dump(be, open(be_p, "w"), indent=1)
print("LONG " + json.dumps(report))
