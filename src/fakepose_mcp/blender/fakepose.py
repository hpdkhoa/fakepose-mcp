"""fakepose: the hand hold the way games make it (the owner, 2026-10-23: "this one will do the hand hold like the
current game market is doing").

A hold is an authored preset placed on a socket of the gun (a mark), not solved from anatomy; each finger closes until
it touches (curl to contact); the arm reaches the hand by two-bone IK with a pole. The clipping rule is the owner's
choice (b): zero clipping seen from the first-person camera; clipping the eye cannot see is measured and listed.

It runs inside Gun Kit's Blender job and works on the rig Gun Kit loaded (`L`, its arms, skin, gun and caches);
Gun Kit hands it its own helpers (the facts, the gun frame, the marks' places, moving the gun)."""
import json
import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
DIGITS = ("thumb", "index", "middle", "ring", "pinky")


def unit(v):
    v = np.asarray(v, dtype=float)
    return v / max(1e-12, float(np.linalg.norm(v)))


def frame_turn(a_now, b_now, a_want, b_want):
    """The turn that takes the pair of directions (a_now, b_now) onto (a_want, b_want): a exactly, b as near as the
    turn allows (both pairs made square first)."""
    def basis(a, b):
        a = unit(a)
        b = unit(np.asarray(b, dtype=float) - a * float(np.dot(a, b)))
        return np.stack([a, b, np.cross(a, b)], 1)
    return basis(a_want, b_want) @ basis(a_now, b_now).T


class FakePose:
    def __init__(self, L, gk):
        """L: Gun Kit's loaded rig (Pose Lab's lab). gk: Gun Kit's helpers: facts, g, bone_world, mark_bone,
        mark_world, move_gun (a world matrix applied to the gun's rest), finger_bones, glove_cm, view (VIEW_RIGHT,
        VIEW_FWD, VIEW_UP), fov (H_FOV, ASPECT)."""
        self.L = L
        self.gk = gk
        self.facts = gk["facts"]
        self.glove = float(gk.get("glove_cm", 0.0))
        self.presets = self._load_presets()
        self.report = {"engine": "fakepose", "holds": {}}
        # a skinned mesh that is not the posed arms (the idle file's own copy, at rest in front of the eye) is hidden:
        # the camera must see only what the game draws
        hid = []
        for o in bpy.context.scene.objects:
            if o.type == "MESH" and o not in L.meshes and o.vertex_groups.get("hand_r") is not None:
                o.hide_render = True
                o.hide_viewport = True
                hid.append(o.name)
        self.report["hidden_meshes"] = hid

    # --- presets --------------------------------------------------------------------------------------------------
    def _load_presets(self):
        fam = "pistol" if "slide" in self.facts.get("parts", {}) else "rifle"
        p = os.path.join(DATA, "presets", fam + ".json")
        out = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"holds": {}}
        cap = os.path.join(DATA, "presets", "captured", "%s_r_grip.json" % self.facts["name"])
        if os.path.exists(cap):
            out.setdefault("captured", {})["r:grip"] = json.load(open(cap, encoding="utf-8"))
        out["file"] = p
        return out

    def preset(self, side, mark, kind):
        hs = self.presets.get("holds", {})
        for k in ("%s:%s:%s" % (side, mark, kind), "%s:%s" % (side, mark)):
            if k in hs:
                return k, hs[k]
        return None, None

    # --- the gun's frame ------------------------------------------------------------------------------------------
    def gun_axes(self):
        """The gun's forward (the bore, toward the muzzle), up and left, world (facts: +y ahead, +z up, +x left)."""
        R = np.array(self.gk["bone_world"]("Root").to_3x3())
        g = self.gk["g"]
        ax = lambda v: unit(R @ np.array(list(g(v))))        # noqa: E731
        return ax((0.0, 100.0, 0.0)), ax((0.0, 0.0, 100.0)), ax((100.0, 0.0, 0.0))

    def to_world(self, c):
        return np.array(list(self.gk["bone_world"]("Root") @ self.gk["g"](c)))

    def sights(self):
        """The sights' tops, measured on the gun: rays straight down the gun's middle plane onto its mesh, every 1 mm
        over the slide's rear 3 cm and front 3 cm; the highest hit of each (the rear and the front sight)."""
        bvh = self.L._object_now()[0]
        F, U, _Lf = self.gun_axes()
        m = self.facts["marks"]
        out = {}
        for name, y0, y1 in (("rear", m["slide_rear"][1], m["slide_rear"][1] + 3.0),
                             ("front", m["slide_front"][1] - 3.0, m["slide_front"][1])):
            best = None
            for y in np.arange(y0, y1 + 1e-9, 0.1):
                o = self.to_world((0.0, float(y), 10.0))
                hit = bvh.ray_cast(Vector(list(o)), Vector(list(-U)), 0.2)
                if hit[0] is None:
                    continue
                h = np.array(list(hit[0]))
                if best is None or float(h @ U) > float(best @ U):
                    best = h
            if best is None:
                raise ValueError("fakepose: no %s sight found on the gun's top" % name)
            out[name] = best
        return out

    # --- the body and the eye (the owner, 2026-10-23: "use 1, for fakepose-mcp only") ------------------------------
    BODY_BONES = ("pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "neck_01", "neck_02", "head",
                  "clavicle_l", "clavicle_r")
    # Epic's first-person template (Unreal Engine 5.6, FirstPersonCharacter): the camera on the "head" bone at
    # (-2.8, 5.89, 0) cm, 5.89 ahead of the head joint and 2.8 below it
    EYE_FROM_HEAD_CM = {"forward": 5.89, "up": -2.8, "source": "Unreal Engine 5.6 First Person template: "
                        "FirstPersonCameraComponent attached to the mesh's head bone at FVector(-2.8, 5.89, 0)"}

    def body_rest(self):
        """The body (pelvis, spine, neck, head, collarbones) at the rig's rest pose: an anatomical body, the shoulders
        below the eye. The first-person template's idle lifts the right shoulder 30 cm, to above the head, so arms at
        aim crossed the view."""
        L = self.L
        done = []
        for n in self.BODY_BONES:
            pb = L.arm.pose.bones.get(n)
            if pb is not None:
                pb.matrix_basis.identity()
                done.append(n)
        bpy.context.view_layer.update()
        self.report["body_rest"] = done
        return done

    def set_eye(self):
        """The eye measured from the rig's head bone (as posed now) with the template's camera offset; Gun Kit's eye
        kept in the report for comparison."""
        L, gk = self.L, self.gk
        VR, VF, VU = (Vector(list(v)) for v in gk["view"])
        hb = L.arm.pose.bones.get("head")
        if hb is None:
            self.report["eye"] = {"kept": [round(x, 4) for x in L.eye], "why": "the rig has no head bone"}
            return L.eye
        h = L.arm.matrix_world @ hb.head
        old = L.eye.copy()
        L.eye = h + VF * (self.EYE_FROM_HEAD_CM["forward"] / 100.0) + VU * (self.EYE_FROM_HEAD_CM["up"] / 100.0)
        self.report["eye"] = {"head_bone": [round(x, 4) for x in h], "eye": [round(x, 4) for x in L.eye],
                              "gun_kit_eye": [round(x, 4) for x in old], "moved_cm": round((L.eye - old).length * 100.0, 2),
                              "source": self.EYE_FROM_HEAD_CM["source"]}
        return L.eye

    # --- the aim place --------------------------------------------------------------------------------------------
    def aim_place(self, side="r", elbow_deg=5.0):
        """The gun at aim (the owner: "we start with the aim position first"): its sight line through the eye, the
        bore along the view, no cant; its distance from the eye set so the firing arm, holding its grip preset,
        reaches the hand with the elbow at elbow_deg (5: the arm rules' least bend, "arms fully extended" in the
        isosceles stance, FM 3-23.35)."""
        L, gk = self.L, self.gk
        VR, VF, VU = (np.array(list(v)) for v in gk["view"])
        eye = np.array(list(L.eye))
        s = self.sights()
        F, U, _Lf = self.gun_axes()
        Rd = frame_turn(unit(s["front"] - s["rear"]), U, VF, VU)

        def place(d):
            t = eye + VF * d - Rd @ s["rear"]
            D = np.eye(4)
            D[:3, :3], D[:3, 3] = Rd, t
            return D
        # the hand's wrist where the grip preset puts it, with the gun at a trial distance; then the distance solved
        self.gk["move_gun"](Matrix(place(0.5).tolist()))
        Hw = self.hand_on("r", "grip", "palm")[0]
        w0 = np.array(list(Hw.translation))
        S = np.array(list(L._bw(L._n("upperarm", side)).translation))
        E = np.array(list(L._bw(L._n("lowerarm", side)).translation))
        W = np.array(list(L._bw(L._n("hand", side)).translation))
        l1, l2 = float(np.linalg.norm(E - S)), float(np.linalg.norm(W - E))
        reach = math.sqrt(l1 * l1 + l2 * l2 + 2.0 * l1 * l2 * math.cos(math.radians(elbow_deg)))
        b = float(VF @ (w0 - S))
        c = float((w0 - S) @ (w0 - S)) - reach * reach
        disc = b * b - c
        if disc < 0.0:
            raise ValueError("fakepose: the arm cannot reach the grip anywhere along the sight line")
        dd = -b + math.sqrt(disc)                     # how far the gun moves on along the view from the trial place
        # the market way, both hands on the gun: the support arm must reach its hold too; the nearer of the two
        # distances (each arm at elbow_deg) is kept
        both = {"r": round(dd * 100.0, 2)}
        if self.preset("l", "support", "palm")[1] is not None and "support" in self.facts["marks"]:
            Hl = self.hand_on("l", "support", "palm")[0]
            wl = np.array(list(Hl.translation))
            Sl = np.array(list(L._bw(L._n("upperarm", "l")).translation))
            El = np.array(list(L._bw(L._n("lowerarm", "l")).translation))
            Wl = np.array(list(L._bw(L._n("hand", "l")).translation))
            m1, m2 = float(np.linalg.norm(El - Sl)), float(np.linalg.norm(Wl - El))
            rl = math.sqrt(m1 * m1 + m2 * m2 + 2.0 * m1 * m2 * math.cos(math.radians(elbow_deg)))
            bl = float(VF @ (wl - Sl))
            cl = float((wl - Sl) @ (wl - Sl)) - rl * rl
            if bl * bl - cl >= 0.0:
                ddl = -bl + math.sqrt(bl * bl - cl)
                both["l"] = round(ddl * 100.0, 2)
                dd = min(dd, ddl)
        self.report["aim_both_arms_cm"] = both
        # the gun at the trial place now: move it on by dd along the view
        D2 = np.eye(4)
        D2[:3, 3] = VF * dd
        self.gk["move_gun"](Matrix(D2.tolist()))
        s2 = self.sights()
        out = {"eye_to_rear_sight_cm": round(float(np.linalg.norm(s2["rear"] - eye)) * 100.0, 2),
               "sight_line_off_the_eye_cm": round(float(np.linalg.norm(np.cross(s2["rear"] - eye, unit(s2["front"] - s2["rear"])))) * 100.0, 3),
               "bore_to_view_deg": round(math.degrees(math.acos(min(1.0, float(unit(s2["front"] - s2["rear"]) @ VF)))), 3),
               "elbow_target_deg": elbow_deg, "reach_cm": round(reach * 100.0, 2)}
        self.report["aim"] = out
        return out

    # --- a hand on a mark -----------------------------------------------------------------------------------------
    def hand_on(self, side, mark, kind):
        """The hand's world matrix and its starting finger turns for a preset on a mark."""
        L, gk = self.L, self.gk
        cap = self.presets.get("captured", {}).get("%s:%s" % (side, mark))
        if cap is not None and kind in ("palm", None):
            rel = Matrix(cap["rel_to_mark_bone"])
            H = gk["bone_world"](gk["mark_bone"](mark)) @ rel
            return H, {n: tuple(q) for n, q in cap["fingers"].items()}, "captured: " + cap["source"]
        key, p = self.preset(side, mark, kind)
        if p is None:
            raise KeyError("fakepose: no preset for %s %s %s" % (side, mark, kind))
        if p.get("mirror_of"):
            return self.mirrored(side, p), None, key + ": " + p.get("source", "")
        F, U, Lf = self.gun_axes()
        basis = {"forward": F, "up": U, "left": Lf}
        vec = lambda d: unit(sum(basis[k] * float(w) for k, w in d.items()))       # noqa: E731
        into, toward = vec(p["palm_into"]), vec(p["fingers_toward"])
        hn = L._n("hand", side)
        H0 = np.array(L._bw(hn))
        f_now = unit(np.array(list(L._palm_facing(side))))
        w_ = np.array(list(L._bw(hn).translation))
        d_now = unit(np.array(list(L._bw(L._n("finger", side, "middle", "01")).translation)) - w_)
        R = frame_turn(f_now, d_now, into, toward)
        anc = self.anchor(side, p.get("contact", "palm_skin"))
        at = np.array(list(gk["mark_world"](mark))) + np.asarray(
            [float(p.get("offset_cm", {}).get(k, 0.0)) / 100.0 for k in ("forward", "up", "left")]) @ np.stack([F, U, Lf])
        at = at - into * ((self.glove + float(p.get("standoff_cm", 0.0))) / 100.0)
        M = np.eye(4)
        M[:3, :3] = R @ H0[:3, :3]
        M[:3, 3] = at - R @ (anc - H0[:3, 3])
        return Matrix(M.tolist()), None, key + ": " + p.get("source", "")

    def mirrored(self, side, p):
        """A hold authored as the mirror of another hand's hold across the gun's middle plane (the way a support grip
        is made from the firing grip), moved by shift_cm in the gun's axes. The mirror keeps the rig's own left/right
        bone convention: the turn between a hand's rest and its mirrored twin's rest is carried over."""
        L, gk = self.L, self.gk
        o_side, o_mark = p["mirror_of"].split(":")
        Ho = self.hand_on(o_side, o_mark, "palm")[0]
        A = L.arm.matrix_world
        mr = A @ L.arm.data.bones[L._n("hand", o_side)].matrix_local
        ml = A @ L.arm.data.bones[L._n("hand", side)].matrix_local
        Srig = A @ Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0)) @ A.inverted()
        K = mr.inverted() @ Srig.inverted() @ ml
        F, U, Lf = self.gun_axes()
        o = Vector(list(self.to_world((0.0, 0.0, 0.0))))
        n = Vector(list(Lf))
        Sg = Matrix.Translation(o) @ (Matrix.Identity(4) - 2.0 * Matrix([[n.x * n.x, n.x * n.y, n.x * n.z, 0], [n.y * n.x, n.y * n.y, n.y * n.z, 0],
                                                                          [n.z * n.x, n.z * n.y, n.z * n.z, 0], [0, 0, 0, 0]])) @ Matrix.Translation(-o)
        M = Sg @ Ho @ K
        sh = p.get("shift_cm", {})
        d = (F * float(sh.get("forward", 0.0)) + U * float(sh.get("up", 0.0)) + Lf * float(sh.get("left", 0.0))) / 100.0
        M = Matrix.Translation(Vector(list(d))) @ M
        loc, rot, _sc = M.decompose()
        return Matrix.LocRotScale(loc, rot, L._unit())

    def hand_axes(self, p):
        F, U, Lf = self.gun_axes()
        basis = {"forward": F, "up": U, "left": Lf}
        vec = lambda d: unit(sum(basis[k] * float(w) for k, w in d.items()))       # noqa: E731
        return vec(p["palm_into"]), vec(p["fingers_toward"])

    def push_out(self, side, into, step_cm=0.1, max_cm=5.0):
        """The hand set down onto what is under it, the way games solve a hand to a surface: moved back against its
        palm's facing (out of the gun and the other hand) in step_cm steps until its palm and its knuckles clear both
        by the glove's thickness, then the arm by IK. Returns how far it moved (cm)."""
        L = self.L
        hn = L._n("hand", side)
        # set down onto the gun: the other hand's fingertips under the palm are the support grip itself (the
        # eye's check decides whether any of that shows)
        oth = None
        _b, _T, sidev, kind, _s = L._skin_static()
        sc = 1 if side == "r" else 2
        sel = np.nonzero((sidev == sc) & (kind == 2))[0]          # the palm's skin

        log = []

        def gap():
            P = L._skin_arrays()[0]
            X = P[sel]
            D = np.asarray(L.sdf_query(X, want_normal=False)[0], dtype=float)
            gg = float(np.min(D))
            go = float(np.min(oth(X))) if oth is not None else 99.0
            log.append([round(moved, 2), round(gg, 3), round(go, 3), round(float(np.linalg.norm(np.array(list(L._bw(hn).translation)) - np.array(list(H0.translation)))) * 100, 2)])
            return min(gg, go)
        H0 = L._bw(hn).copy()
        moved = 0.0
        while gap() < self.glove and moved < max_cm:
            moved += step_cm
            L._put_hand(side, Matrix.Translation(Vector(list(-into * moved / 100.0))) @ H0)
        self.report.setdefault("push_log", {})[side] = log[::5] + log[-1:]
        return round(moved, 2)

    def anchor(self, side, name):
        L = self.L
        if name == "pinch":
            a = np.array(list(L._finger_tip("index", side)))
            b = np.array(list(L._anchor(side, "thumb_tip")))
            return 0.5 * (a + b)
        return np.array(list(L._anchor(side, name)))

    # --- the fingers ----------------------------------------------------------------------------------------------
    def _gaps(self, side, digit, other):
        """The least gap of each segment of a digit to the gun (and the other hand, when other), cm; the skin as
        posed now."""
        L = self.L
        P = L._skin_arrays()[0]
        _b, _T, sidev, kind, segi = L._skin_static()
        k = DIGITS.index(digit)
        sc = 1 if side == "r" else 2
        out = []
        for j in range(3):
            idx = np.nonzero((sidev == sc) & (kind == 3) & (segi == k * 3 + j))[0]
            if not len(idx):
                out.append(99.0)
                continue
            D = np.asarray(L.sdf_query(P[idx], want_normal=False)[0], dtype=float) * 1.0
            gap = float(np.min(D))
            if other is not None:
                gap = min(gap, float(np.min(other(P[idx]))))
            out.append(gap)
        return out

    def _other_hand(self, side):
        """The other hand's skin as a signed distance (cm, below 0 inside), by its nearest face."""
        L = self.L
        P, N = L._skin_arrays()[:2]
        _b, T, sidev, kind, _s = L._skin_static()
        sc = 2 if side == "r" else 1
        keep = (sidev == sc) & (kind >= 2)              # the other hand's palm and digits (not its forearm)
        tri = [t for t in T if keep[t[0]] and keep[t[1]] and keep[t[2]]]
        if not tri:
            return None
        bvh = BVHTree.FromPolygons([tuple(p) for p in P], [tuple(int(i) for i in t) for t in tri])

        def dist(X):
            out = np.empty(len(X))
            for i, x in enumerate(X):
                loc, nrm, _i, d = bvh.find_nearest(Vector(list(x)))
                if loc is None:
                    out[i] = 99.0
                    continue
                # the nearest face's side says inside only near the skin (1 cm); further off, a point is outside
                inside = d < 0.01 and float((Vector(list(x)) - loc).dot(nrm)) < 0.0
                out[i] = (-d if inside else d) * 100.0
            return out
        return dist

    def curl_to_contact(self, side, digit, target, other=False, steps=24):
        """A digit closed the way games do it: every joint turned together from where it is toward its target bend
        (target: the three joints' bends, degrees, added to the open pose), in equal steps; a segment that touches
        (its gap at or under the glove's thickness) stops its joint and the ones before it, the joints after it go
        on; nothing goes past the target. Returns each joint's bend and what stopped it."""
        L = self.L
        names = [L._n("finger", side, digit, j) for j in ("01", "02", "03")]
        base = [L._bw(n).copy() for n in names]
        FL = L._limits()[1]
        planes = L._finger_report(side, FL)[2] if digit != "thumb" else None
        hinge = []
        for j, n in enumerate(names):
            if digit == "thumb":
                ax_ = L._thumb_report(side, L._thumb_limits())[2].get(("01", "02", "03")[j])
                hinge.append(np.array(list(ax_)) if ax_ is not None else None)
            else:
                hinge.append(np.array(list(planes[digit])))
        # the sign that curls toward the palm, read once per joint on the open pose
        sign = []
        for j, n in enumerate(names):
            if hinge[j] is None:
                sign.append(0.0)
                continue
            f0 = np.array(list(L._palm_facing(side)))
            tip0 = np.array(list(L._finger_tip(digit, side) if digit != "thumb" else L._anchor(side, "thumb_tip")))
            L._turn_about(n, Vector(list(hinge[j])), 5.0, base[j].translation)
            tip1 = np.array(list(L._finger_tip(digit, side) if digit != "thumb" else L._anchor(side, "thumb_tip")))
            sign.append(1.0 if float((tip1 - tip0) @ f0) > 0.0 else -1.0)
            for n_, M_ in zip(names, base):
                L._set_world(n_, M_)
        oth = self._other_hand(side) if other else None
        if target == "fist":
            # toward the fist: each joint to the most bend its range allows (the arm rules' finger and thumb ranges),
            # from the bend it has now
            if digit == "thumb":
                TL = L._thumb_limits()
                now = L._thumb_report(side, TL)[0]
                target = [0.0] + [float(TL[j][1]) - float((now.get("thumb_" + j) or [0.0])[0]) for j in ("02", "03")]
            else:
                now = L._finger_report(side, FL)[0]
                target = [float(FL[j][1]) - float(now["%s_%s" % (digit, j)][0]) for j in ("01", "02", "03")]
            target = [max(0.0, t_) for t_ in target]
        tgt = np.asarray(target, dtype=float)
        ang = np.zeros(3)
        frozen = [False, False, False]
        why = [None, None, None]
        # a segment already touching on the preset holds its own joint (the preset put it there); the joints past it
        # close on
        g0 = self._gaps(side, digit, oth)
        for j in range(3):
            if g0[j] <= self.glove:
                frozen[j] = True
                why[j] = "already touching on the preset (%.2f cm)" % g0[j]

        def pose(a):
            for n_, M_ in zip(names, base):
                L._set_world(n_, M_)
            for j, n in enumerate(names):
                if hinge[j] is None or abs(a[j]) < 1e-9:
                    continue
                # the hinge rides the joints before it: turned with them
                h = Vector(list(hinge[j]))
                for i in range(j):
                    if hinge[i] is not None:
                        h = (Matrix.Rotation(math.radians(sign[i] * a[i]), 3, Vector(list(hinge[i]))) @ h)
                L._turn_about(n, h, sign[j] * a[j], L._bw(n).translation.copy())
        for s in range(1, steps + 1):
            trial = ang.copy()
            for j in range(3):
                if not frozen[j]:
                    trial[j] = tgt[j] * s / steps
            pose(trial)
            gaps = self._gaps(side, digit, oth)
            hit = [g <= self.glove and g0[j] > self.glove for j, g in enumerate(gaps)]
            if any(hit):
                # the touch found to a tenth of the step by halving between the last clear bend and this one
                lo_, hi_ = ang.copy(), trial.copy()
                for _ in range(4):
                    mid = 0.5 * (lo_ + hi_)
                    pose(mid)
                    gm = self._gaps(side, digit, oth)
                    if any(g <= self.glove and g0[j] > self.glove for j, g in enumerate(gm)):
                        hi_ = mid
                    else:
                        lo_ = mid
                ang = lo_
                k = hit.index(True)
                for j in range(k + 1):
                    if not frozen[j]:
                        frozen[j] = True
                        why[j] = "touch at segment %d" % (k + 1)
                if all(frozen):
                    break
                continue
            ang = trial
        pose(ang)
        for j in range(3):
            if why[j] is None:
                why[j] = "target" if abs(ang[j] - tgt[j]) < 1e-6 else "stopped"
        return {"bend_deg": [round(float(a), 1) for a in ang], "stopped_by": why,
                "gaps_cm": [round(g, 3) for g in self._gaps(side, digit, oth)]}

    # --- the clipping the eye sees --------------------------------------------------------------------------------
    def eye_clip(self, res=(192, 108), sides=("r", "l")):
        """The owner's rule (b): clipping seen from the first-person camera. A ray from the eye through every pixel
        of the 90 degree, 16:9 view; the first surface it meets, the gun's or the skin's. A pixel clips when that
        surface is the gun inside the skin (deeper than the glove) or the skin inside the gun (deeper than the glove).
        Returns the clipping pixels, where they are, and the pixels the hands and the gun cover."""
        L, gk = self.L, self.gk
        VR, VF, VU = (Vector(list(v)) for v in gk["view"])
        H_FOV, ASPECT = gk["fov"]
        P, N = L._skin_arrays()[:2]
        _b, T, sidev, kind, _s = L._skin_static()
        # the hands' and forearms' skin only (the eye sits inside the arms mesh's body shell); the triangle list once
        tri = getattr(self, "_eye_tri", None)
        if tri is None:
            keep = (kind > 0)
            tri = self._eye_tri = [tuple(int(i) for i in t) for t in T if keep[t[0]] and keep[t[1]] and keep[t[2]]]
        skin = BVHTree.FromPolygons(P.tolist(), tri)
        gun = L._object_now()[0]
        eye = L.eye
        t = math.tan(math.radians(H_FOV / 2.0))
        nx, ny = res
        lim = self.glove / 100.0
        clip, seen_gun, seen_skin, where = 0, 0, 0, []
        for iy in range(ny):
            y = (1.0 - 2.0 * (iy + 0.5) / ny) * t / ASPECT
            for ix in range(nx):
                x = (2.0 * (ix + 0.5) / nx - 1.0) * t
                d = (VF + VR * x + VU * y).normalized()
                hs = skin.ray_cast(eye, d, 3.0)
                k_ = 0
                while hs[0] is not None and hs[1].dot(d) > 0.0 and k_ < 4:     # a face turned away: look past it
                    o_ = hs[0] + d * 1e-5
                    hs = skin.ray_cast(o_, d, 3.0)
                    if hs[0] is not None:
                        hs = (hs[0], hs[1], hs[2], (hs[0] - eye).length)
                    k_ += 1
                hg = gun.ray_cast(eye, d, 3.0)
                if hs[0] is None and hg[0] is None:
                    continue
                if hg[0] is not None and (hs[0] is None or hg[3] < hs[3]):
                    seen_gun += 1
                    q = hg[0]
                    loc, nrm, _i, dist = skin.find_nearest(q)
                    if loc is not None and (q - loc).dot(nrm) < 0.0 and dist > lim:
                        clip += 1
                        where.append(("gun in skin", ix, iy, round(dist * 100.0, 2)))
                else:
                    seen_skin += 1
                    q = hs[0]
                    D = float(np.asarray(L.sdf_query(np.array([list(q)]), want_normal=False)[0])[0])
                    if D < -self.glove:
                        clip += 1
                        where.append(("skin in gun", ix, iy, round(-D, 2)))
        return {"clip_pixels": clip, "pixels": nx * ny, "gun_pixels": seen_gun, "skin_pixels": seen_skin,
                "deepest_seen_cm": max((w[3] for w in where), default=0.0), "where": where[:40],
                "rule": "the owner's choice (b), 2026-10-23: zero clipping seen from the first-person camera"}

    def eye_blockers(self, res=(96, 54)):
        """What the eye sees first, over the whole arms mesh (front faces only): pixels per bone (each skin vertex's
        heaviest bone), and the nearest hit's distance. Finds what fills the first-person view."""
        L, gk = self.L, self.gk
        VR, VF, VU = (Vector(list(v)) for v in gk["view"])
        H_FOV, ASPECT = gk["fov"]
        P = L._skin_arrays()[0]
        bone, T, _sv, _k, _s = L._skin_static()
        bvh = BVHTree.FromPolygons([tuple(p) for p in P], [tuple(int(i) for i in t) for t in T])
        eye = L.eye
        t = math.tan(math.radians(H_FOV / 2.0))
        nx, ny = res
        by, near = {}, 99.0
        for iy in range(ny):
            y = (1.0 - 2.0 * (iy + 0.5) / ny) * t / ASPECT
            for ix in range(nx):
                d = (VF + VR * ((2.0 * (ix + 0.5) / nx - 1.0) * t) + VU * y).normalized()
                o, k_ = eye, 0
                h = bvh.ray_cast(o, d, 3.0)
                while h[0] is not None and h[1].dot(d) > 0.0 and k_ < 6:
                    o = h[0] + d * 1e-5
                    h = bvh.ray_cast(o, d, 3.0)
                    k_ += 1
                if h[0] is None:
                    continue
                tri = T[h[2]]
                b_ = bone[int(tri[0])]
                by[b_] = by.get(b_, 0) + 1
                near = min(near, (h[0] - eye).length * 100.0)
        # and over the whole scene as drawn: which objects the eye meets first
        dg = bpy.context.evaluated_depsgraph_get()
        sc = bpy.context.scene
        objs, onear = {}, {}
        for iy in range(0, ny, 2):
            y = (1.0 - 2.0 * (iy + 0.5) / ny) * t / ASPECT
            for ix in range(0, nx, 2):
                d = (VF + VR * ((2.0 * (ix + 0.5) / nx - 1.0) * t) + VU * y).normalized()
                hit, loc, _n, _i, ob, _m = sc.ray_cast(dg, eye, d, distance=3.0)
                if hit:
                    objs[ob.name] = objs.get(ob.name, 0) + 1
                    onear[ob.name] = min(onear.get(ob.name, 99.0), round((loc - eye).length * 100.0, 2))
        return {"pixels": nx * ny, "by_bone": dict(sorted(by.items(), key=lambda kv: -kv[1])), "nearest_cm": round(near, 2),
                "eye": [round(x, 4) for x in eye], "scene_objects_seen_first": objs, "scene_objects_nearest_cm": onear,
                "scene_samples": ((nx + 1) // 2) * ((ny + 1) // 2)}

    # --- the hold -------------------------------------------------------------------------------------------------
    def grasp(self, side, mark, kind="palm"):
        """A hold the market way: the hand on its preset, the arm by IK, each digit closed to contact by its preset's
        rule; then the eye's clip check. Returns (the hand's world matrix, the fingers' turns, the readings)."""
        L = self.L
        H, fingers, src = self.hand_on(side, mark, kind)
        if fingers:
            for n, q in fingers.items():
                L.arm.pose.bones[n].rotation_quaternion = q
            bpy.context.view_layer.update()
        short = L._put_hand(side, H)
        key, p = self.preset(side, mark, kind)
        pushed = None
        if p and p.get("push_out"):
            into_ = np.asarray(self.hand_axes(p)[0]) if "palm_into" in p else -np.asarray(self.gun_axes()[2]) * (1.0 if side == "l" else -1.0)
            pushed = self.push_out(side, into_)
        rules = (p or {}).get("fingers") or self.presets.get("captured_fingers", {}).get("%s:%s" % (side, mark), {})
        curls = {}
        for digit in DIGITS:
            r = rules.get(digit)
            if not r or r.get("rule") == "keep":
                continue
            if r["rule"] == "curl_to_contact":
                curls[digit] = self.curl_to_contact(side, digit, r["target_deg"], other=bool(r.get("other_hand")))
        Hn = L._bw(L._n("hand", side)).copy()
        out = {"preset": src, "arm_short_cm": round(short, 2), "curls": curls, "pushed_out_cm": pushed,
               "arm": {k: v for k, v in L._arm_report(side, L._limits()[0])[0].items()
                       if k in ("elbow_bend_deg", "wrist_bend_deg", "wrist_flexion_deg", "wrist_radial_deg")}}
        self.report["holds"]["%s:%s:%s" % (side, mark, kind)] = out
        fq = {n: L.arm.pose.bones[n].rotation_quaternion.copy() for n in self.gk["finger_bones"][side]}
        return Hn, fq, out
