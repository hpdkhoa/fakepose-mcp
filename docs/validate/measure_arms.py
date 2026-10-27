"""The arms rig measured: bone lengths (upper arm, forearm, hand, each finger), the hand's breadth across the
knuckles, and the skin's girth at the upper arm's and forearm's middles, cm. blender -b rig.blend -P measure_arms.py"""
import bpy, json, math
import numpy as np
from mathutils import Vector
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
pb = arm.pose.bones
W = lambda n: arm.matrix_world @ pb[n].matrix
head = lambda n: W(n).translation
out = {}
for s in ("r", "l"):
    d = {}
    d["upper_arm_cm"] = round((head("lowerarm_" + s) - head("upperarm_" + s)).length * 100, 2)
    d["forearm_cm"] = round((head("hand_" + s) - head("lowerarm_" + s)).length * 100, 2)
    tip = arm.matrix_world @ pb["middle_03_" + s].tail
    d["hand_length_cm"] = round((tip - head("hand_" + s)).length * 100, 2)         # wrist to the middle finger's tip (bone)
    d["hand_breadth_knuckles_cm"] = round((head("index_01_" + s) - head("pinky_01_" + s)).length * 100, 2)
    for f in ("thumb", "index", "middle", "ring", "pinky"):
        segs = [((arm.matrix_world @ pb["%s_%s_%s" % (f, j, s)].tail) - (arm.matrix_world @ pb["%s_%s_%s" % (f, j, s)].head)).length * 100 for j in ("01", "02", "03")]
        d[f + "_segments_cm"] = [round(x, 2) for x in segs]
    out[s] = d
# the skin girth: the mesh's vertices weighted to the upper arm / forearm, sliced at the bone's middle
mesh = next((o for o in bpy.data.objects if o.type == 'MESH' and o.find_armature() == arm), None)
if mesh is not None:
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh.evaluated_get(dg); me = ev.to_mesh()
    P = np.array([list(ev.matrix_world @ v.co) for v in me.vertices])
    for s in ("r",):
        for bone, nxt, key in (("upperarm_" + s, "lowerarm_" + s, "upper_arm_girth_cm"), ("lowerarm_" + s, "hand_" + s, "forearm_girth_cm")):
            a, b = np.array(list(head(bone))), np.array(list(head(nxt)))
            ax = (b - a) / np.linalg.norm(b - a); mid = 0.5 * (a + b)
            t = (P - mid) @ ax
            ring = P[np.abs(t) < 0.004]
            if len(ring) > 8:
                r = ring - mid - np.outer((ring - mid) @ ax, ax)
                # the girth as the convex hull's perimeter in the slice plane
                u = r / np.maximum(np.linalg.norm(r, axis=1)[:, None], 1e-9)
                e1 = u[0]; e2 = np.cross(ax, e1)
                xy = np.stack([r @ e1, r @ e2], 1)
                pts = sorted(set(map(tuple, np.round(xy, 6))))
                def cross(o, a, b):
                    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
                lower, upper = [], []
                for q in pts:
                    while len(lower) >= 2 and cross(lower[-2], lower[-1], q) <= 0:
                        lower.pop()
                    lower.append(q)
                for q in reversed(pts):
                    while len(upper) >= 2 and cross(upper[-2], upper[-1], q) <= 0:
                        upper.pop()
                    upper.append(q)
                hull = lower[:-1] + upper[:-1]
                per = sum(math.dist(hull[i], hull[(i + 1) % len(hull)]) for i in range(len(hull)))
                out[s][key] = round(float(per) * 100, 2)
            else:
                out[s][key] = "no ring (%d)" % len(ring)
    ev.to_mesh_clear()
print("ARMS " + json.dumps(out))
