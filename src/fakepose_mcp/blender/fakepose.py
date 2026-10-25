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
from mathutils import Matrix, Quaternion, Vector
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
        self.family = fam
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

    # --- the gun's surface, read straight off its meshes (no gun read needed: rifles and pistols alike) ----------
    def gun_bvh(self):
        """The gun's surface as posed now (every mesh that is not the arms), world, cached while nothing moves."""
        L = self.L
        obs = [o for o in bpy.context.scene.objects if o.type == "MESH" and o not in L.meshes and not o.hide_viewport
               and o.vertex_groups.get("hand_r") is None]
        dg = bpy.context.evaluated_depsgraph_get()
        key = tuple(tuple(round(v, 6) for row in o.matrix_world for v in row) for o in obs)
        key = key + tuple(tuple(round(v, 6) for v in pb.matrix.to_translation()) + tuple(round(v, 6) for v in pb.matrix.to_quaternion())
                          for pb in getattr(L, "rifle_arm").pose.bones)
        c = getattr(self, "_gbvh", None)
        if c is not None and c[0] == key:
            return c[1]
        verts, tris = [], []
        for o in obs:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            M = ev.matrix_world
            base = len(verts)
            verts.extend([tuple(M @ v.co) for v in me.vertices])
            me.calc_loop_triangles()
            tris.extend([tuple(base + i for i in t.vertices) for t in me.loop_triangles])
            ev.to_mesh_clear()
        bvh = BVHTree.FromPolygons(verts, tris)
        self._gbvh = (key, bvh)
        self._gverts = np.array(verts)
        return bvh

    def gun_signed(self, X):
        """Each point's distance to the gun's surface, cm, below 0 inside (the nearest face's side, trusted within
        3 cm of the surface; further off a point counts as outside)."""
        bvh = self.gun_bvh()
        out = np.empty(len(X))
        for i, x in enumerate(np.asarray(X, dtype=float)):
            v = Vector((float(x[0]), float(x[1]), float(x[2])))
            loc, nrm, _i, d = bvh.find_nearest(v)
            if loc is None:
                out[i] = 99.0
                continue
            inside = d < 0.03 and (v - loc).dot(nrm) < 0.0
            out[i] = (-d if inside else d) * 100.0
        return out

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
        bvh = self.gun_bvh()
        F, U, _Lf = self.gun_axes()
        m = self.facts["marks"]
        out = {}
        if "rear_sight" in m and "front_sight" in m:
            # a rifle's sights are marks: the rear aperture's middle and the front post's tip
            return {"rear": self.to_world(m["rear_sight"]), "front": self.to_world(m["front_sight"])}
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

    # a rifle's rear sight in front of the eye at the cheek weld: a guess (8 cm), near the "nose to the charging
    # handle" cue; TC 3-22.9 prints no eye relief for iron sights
    EYE_RELIEF_CM = 8.0

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
        if self.family == "rifle":
            # a shouldered rifle at the cheek weld (TC 3-22.9, 2016, 6-4: "bring the rifle up to your head ... the bony
            # portion of the cheek placed on the stock"): the rear sight EYE_RELIEF_CM in front of the eye along the
            # view; the arms reach the gun where it is, the butt's place against the shoulder reported
            s1 = self.sights()
            relief = float(((self.gk.get("facts") or {}).get("sights") or {}).get("eye_relief_cm") or self.EYE_RELIEF_CM)
            dd = float((eye + VF * (relief / 100.0) - s1["rear"]) @ VF)
            D2 = np.eye(4)
            D2[:3, 3] = VF * dd
            self.gk["move_gun"](Matrix(D2.tolist()))
            s2 = self.sights()
            out = {"eye_to_rear_sight_cm": round(float(np.linalg.norm(s2["rear"] - eye)) * 100.0, 2),
                   "sight_line_off_the_eye_cm": round(float(np.linalg.norm(np.cross(s2["rear"] - eye, unit(s2["front"] - s2["rear"])))) * 100.0, 3),
                   "bore_to_view_deg": round(math.degrees(math.acos(min(1.0, float(unit(s2["front"] - s2["rear"]) @ VF)))), 3),
                   "rule": "the cheek weld: the rear sight %.1f cm in front of the eye (%s)" % (
                       relief, "the gun's sourced eye relief" if relief != self.EYE_RELIEF_CM else "a guess")}
            self.gun_bvh()
            Sh = np.array(list(L._bw(L._n("upperarm", side)).translation))
            out["butt_ahead_of_shoulder_joint_cm"] = round((float(np.min(self._gverts @ VF)) - float(Sh @ VF)) * 100.0, 2)
            self.report["aim"] = out
            return out
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

    # --- joint limits in the IK (the owner, 2026-10-25: "go with the joint limits") -----------------------------------
    WRIST_MAX, ELBOW_MIN, ELBOW_MAX, ELBOW_UNDER_CM = 30.0, 5.0, 150.0, 2.0

    def install_limits(self):
        """Pose Lab's _put_hand replaced by the limited one for every later placement (the holds and every clip
        frame): the market's IK, with the joint limits a mocap body has. Nothing is refused; the elbow is chosen so the
        wrist bends least, under the shoulder and inside its hinge."""
        L = self.L
        if getattr(L, "_put_hand_unlimited", None) is None:
            L._put_hand_unlimited = L._put_hand
            L._put_hand = self.limited_put_hand
        self.report["joint_limits"] = {"wrist_max_deg": self.WRIST_MAX, "elbow_bend_deg": [self.ELBOW_MIN, self.ELBOW_MAX],
                                       "elbow_under_shoulder_cm": self.ELBOW_UNDER_CM,
                                       "source": "Tools/blender/anatomy.py (the owner's rules of 2026-10-08, AAOS ranges); in the IK as limits, not walls"}

    def _knuckle_dir(self, side, M):
        """The hand's line (wrist to the middle knuckle) as the hand matrix M would set it."""
        L = self.L
        Hn = L._bw(L._n("hand", side))
        k_local = Hn.inverted() @ L._bw(L._n("finger", side, "middle", "01")).translation
        return unit(np.array(list(M.to_3x3() @ k_local)))

    def best_elbow(self, side, M):
        """The elbow on its IK circle (the shoulder to the wrist's goal) where the wrist bends least off the forearm,
        among the places that keep the elbow under the shoulder and its bend inside the hinge; the least violation
        when none does. Returns (elbow point, wrist bend deg, elbow bend deg, elbow under the shoulder cm)."""
        L = self.L
        S = np.array(list(L._bw(L._n("upperarm", side)).translation))
        E0 = np.array(list(L._bw(L._n("lowerarm", side)).translation))
        W0 = np.array(list(L._bw(L._n("hand", side)).translation))
        l1, l2 = float(np.linalg.norm(E0 - S)), float(np.linalg.norm(W0 - E0))
        G = np.array(list(M.translation))
        d = min(float(np.linalg.norm(G - S)), l1 + l2 - 1e-4)
        axis = unit(G - S)
        x = (l1 * l1 - l2 * l2 + d * d) / (2.0 * d)
        h = max(l1 * l1 - x * x, 0.0) ** 0.5
        u = np.cross(axis, [0.0, 0.0, 1.0])
        u = unit(u) if np.linalg.norm(u) > 1e-6 else np.array([1.0, 0.0, 0.0])
        v = np.cross(axis, u)
        hd = self._knuckle_dir(side, M)
        W = S + axis * d
        best = None
        for k in range(72):
            a = 2.0 * math.pi * k / 72
            E = S + axis * x + (u * math.cos(a) + v * math.sin(a)) * h
            fore = unit(W - E)
            wrist = math.degrees(math.acos(max(-1.0, min(1.0, float(fore @ hd)))))
            bend = 180.0 - math.degrees(math.acos(max(-1.0, min(1.0, float(unit(S - E) @ fore)))))
            under = float((S - E)[2]) * 100.0
            viol = max(0.0, self.ELBOW_UNDER_CM - under) + max(0.0, self.ELBOW_MIN - bend) + max(0.0, bend - self.ELBOW_MAX)
            key = (round(viol, 2), round(wrist, 1))
            if best is None or key < best[0]:
                best = (key, E, wrist, bend, under)
        _key, E, wrist, bend, under = best
        return E, wrist, bend, under

    def limited_put_hand(self, side, M):
        """Pose Lab's _put_hand with the joint limits: the elbow from best_elbow, the hand set to M, the roll into the
        forearm. Returns the reach short (cm) as _put_hand does; the readings go to self.last_limits[side]."""
        L = self.L
        E, wrist, bend, under = self.best_elbow(side, M)
        turned = 0.0
        if wrist > self.WRIST_MAX and getattr(self, "turn_per_frame", True):
            # no elbow place keeps the wrist inside: the hand turns on its palm's normal (it stays on the mark), the
            # least that brings the wrist in, as a real wrist and hand share a reach
            M, turned, _w = self.turn_hand_within(side, M)
            E, wrist, bend, under = self.best_elbow(side, M)
        hn = L._n("hand", side)
        up, lo = L._n("upperarm", side), L._n("lowerarm", side)
        S, E0, W0 = L._bw(up).translation, L._bw(lo).translation, L._bw(hn).translation
        short = max(0.0, (M.translation - S).length - (E0 - S).length - (W0 - E0).length) * 100.0
        L._two_bone(side, M.translation, pole_world=Vector(E.tolist()))
        L._set_world(hn, Matrix.LocRotScale(L._bw(hn).translation, M.to_quaternion(), L._unit()))
        L._roll_forearm(side)
        if not hasattr(self, "last_limits"):
            self.last_limits = {}
        self.last_limits[side] = {"wrist_bend_deg": round(wrist, 1), "elbow_bend_deg": round(bend, 1), "elbow_under_cm": round(under, 1),
                                  "hand_turned_deg": round(turned, 1)}
        return short

    def rest_shift(self):
        """Where the rest hold moves the gun from the aim (the preset idle_pull), as a world vector."""
        ip = self.presets.get("idle_pull") or {}
        VR, VF, VU = (np.array(list(v)) for v in self.gk["view"])
        return (VR * float(ip.get("right_cm", 0.0)) - VF * float(ip.get("back_cm", 0.0)) - VU * float(ip.get("down_cm", 0.0))) / 100.0

    def slide_within_reach(self, side, mark, M, max_cm=20.0, step_cm=1.0):
        """A support hold (the market's: the hand wherever it reaches along the handguard) slid back along the bore
        until the arm reaches it at the rest hold with its elbow bent (at least ELBOW_MIN) and its wrist inside:
        the bar's support hand sits 32 cm ahead of the eye, an arm's reach, not the handguard's front. Only marks the
        preset flags slide_along_bore (the support by default)."""
        _key, p = self.preset(side, mark, None if mark != "support" else "palm")
        if not ((p or {}).get("slide_along_bore") or mark == "support"):
            return M, 0.0
        F_ = Vector(self.gun_axes()[0].tolist())
        shift = Vector(self.rest_shift().tolist())
        best = None
        for k in range(int(max_cm / step_cm) + 1):
            M2 = Matrix.Translation(-F_ * (k * step_cm / 100.0)) @ M
            Mr = Matrix.Translation(shift) @ M2
            _E, wrist, bend, under = self.best_elbow(side, Mr)
            ok = bend >= self.ELBOW_MIN + 10.0 and wrist <= self.WRIST_MAX + 10.0
            if best is None or (ok and not best[0]):
                best = (ok, k * step_cm, M2)
            if ok:
                break
        return best[2], best[1]

    def palm_normal_for(self, side, M):
        """The palm's normal (out of the palm) as M would set it."""
        L = self.L
        Hn = L._bw(L._n("hand", side))
        local = Hn.to_3x3().inverted() @ Vector(list(L._palm_facing(side)))
        return unit(np.array(list(M.to_3x3() @ local)))

    def turn_hand_within(self, side, M, max_deg=25.0, step_deg=2.5):
        """When the best elbow still leaves the wrist over its limit: the hand turned about its palm's normal through
        its wrist (the palm stays on the mark's face), by the least angle that brings the wrist inside, at most
        max_deg. Returns (the new M, degrees turned, the wrist after)."""
        _E, wrist, _b, _u = self.best_elbow(side, M)
        if wrist <= self.WRIST_MAX:
            return M, 0.0, wrist
        n = Vector(self.palm_normal_for(side, M).tolist())
        pivot = M.translation.copy()
        best = (wrist, M, 0.0)
        for sgn in (1.0, -1.0):
            for k in range(1, int(max_deg / step_deg) + 1):
                a = sgn * k * step_deg
                R = Matrix.Rotation(math.radians(a), 4, n)
                M2 = Matrix.Translation(pivot) @ R @ Matrix.Translation(-pivot) @ M
                _E2, w2, _b2, _u2 = self.best_elbow(side, M2)
                if w2 < best[0]:
                    best = (w2, M2, a)
                if w2 <= self.WRIST_MAX:
                    break
            if best[0] <= self.WRIST_MAX:
                break
        return best[1], best[2], best[0]

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
            D = self.gun_signed(X)
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
            D = self.gun_signed(P[idx])
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
        gun = self.gun_bvh()
        eye = L.eye
        t = math.tan(math.radians(H_FOV / 2.0))
        nx, ny = res
        lim = self.glove / 100.0
        clip, seen_gun, seen_skin, where = 0, 0, 0, []
        out_ = {}          # per side: the deepest clip's way out, a world vector as long as its depth
        parts_ = {}        # per side: the digits that clip, and "palm" when the palm or forearm does
        DG_ = ("thumb", "index", "middle", "ring", "pinky")

        def part_of(v):
            return DG_[int(_s[v]) // 3] if int(kind[v]) == 3 and int(_s[v]) >= 0 else "palm"
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
                        sd_ = {1: "r", 2: "l"}.get(int(sidev[tri[_i][0]]), "?") if _i is not None else "?"
                        where.append(("gun in skin", ix, iy, round(dist * 100.0, 2), sd_))
                        if _i is not None:
                            parts_.setdefault(sd_, set()).add(part_of(tri[_i][0]))
                        if dist > out_.get(sd_, (0.0, None))[0]:
                            out_[sd_] = (dist, -nrm.normalized() * dist)     # the skin moved past the gun's point
                else:
                    seen_skin += 1
                    q = hs[0]
                    D = float(self.gun_signed([list(q)])[0])
                    if D < -self.glove:
                        clip += 1
                        sd_ = {1: "r", 2: "l"}.get(int(sidev[tri[hs[2]][0]]), "?") if hs[2] is not None else "?"
                        where.append(("skin in gun", ix, iy, round(-D, 2), sd_))
                        if hs[2] is not None:
                            parts_.setdefault(sd_, set()).add(part_of(tri[hs[2]][0]))
                        gl, gn, _gi, _gd = gun.find_nearest(q)
                        if gl is not None and -D / 100.0 > out_.get(sd_, (0.0, None))[0]:
                            out_[sd_] = (-D / 100.0, (gl - q).normalized() * (-D / 100.0))   # the skin's point out to the gun's face
        return {"clip_pixels": clip, "pixels": nx * ny, "sides": sorted(set(w[4] for w in where if w[4] in ("r", "l"))), "gun_pixels": seen_gun, "skin_pixels": seen_skin,
                "deepest_seen_cm": max((w[3] for w in where), default=0.0), "where": where[:40],
                "way_out": {k: [float(c) for c in v[1]] for k, v in out_.items() if k in ("r", "l") and v[1] is not None},
                "parts": {k: sorted(v) for k, v in parts_.items() if k in ("r", "l")},
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

    def digit_depth(self, side, digit):
        """How deep a digit's skin sits in the gun (cm, 0 when it is out): its deepest skin point's signed distance."""
        L = self.L
        P = L._skin_arrays()[0]
        _b, _T, sidev, kind, segi = L._skin_static()
        k = {"thumb": 0, "index": 1, "middle": 2, "ring": 3, "pinky": 4}[digit]
        m = (sidev == (1 if side == "r" else 2)) & (kind == 3) & (segi // 3 == k)
        if not m.any():
            return 0.0
        return max(0.0, -float(np.min(self.gun_signed(P[m].tolist()))))

    def open_to_clear(self, side, digit, step_deg=5.0, max_deg=60.0):
        """A digit that clips opened the way games do: its three joints turned together against their curl (each
        joint's hinge and its curling sign read as curl_to_contact reads them), step_deg at a time, until its skin is
        out of the gun by the glove or it has opened max_deg. Returns how far it opened (degrees)."""
        L = self.L
        names = [L._n("finger", side, digit, j) for j in ("01", "02", "03")]
        base = [L._bw(n).copy() for n in names]
        if digit == "thumb":
            hinge = []
            for j in ("01", "02", "03"):
                ax_ = L._thumb_report(side, L._thumb_limits())[2].get(j)
                hinge.append(Vector(list(ax_)) if ax_ is not None else None)
        else:
            hinge = [Vector(list(L._finger_report(side, L._limits()[1])[2][digit]))] * 3
        f0 = Vector(list(L._palm_facing(side)))
        tip = (lambda: L._anchor(side, "thumb_tip")) if digit == "thumb" else (lambda: L._finger_tip(digit, side))
        sign = []
        for j, n in enumerate(names):
            if hinge[j] is None:
                sign.append(0.0)
                continue
            t0 = Vector(list(tip()))
            L._turn_about(n, hinge[j], 5.0, base[j].translation)
            sign.append(1.0 if (Vector(list(tip())) - t0).dot(f0) > 0.0 else -1.0)
            for n_, M_ in zip(names, base):
                L._set_world(n_, M_)

        def pose(a):
            for n_, M_ in zip(names, base):
                L._set_world(n_, M_)
            for j, n in enumerate(names):
                if hinge[j] is None:
                    continue
                h = hinge[j].copy()
                for i in range(j):
                    if hinge[i] is not None:
                        h = Matrix.Rotation(math.radians(-sign[i] * a), 3, hinge[i]) @ h
                L._turn_about(n, h, -sign[j] * a, L._bw(n).translation.copy())
            bpy.context.view_layer.update()
        a = 0.0
        while self.digit_depth(side, digit) > self.glove and a < max_deg:
            a += step_deg
            pose(a)
        return a

    def unclip_seen(self, ec, tries=6, res=(96, 54), max_cm=4.0, step_cm=0.2):
        """The market's fix for clipping the eye sees, in the order games use: the digits the check names opened
        until each is out of the gun (open_to_clear); then, while the palm still clips, the hand moved straight out
        of the gun along the deepest clip's way out by its depth plus the glove, up to max_cm in all (with no way out
        measured, set back against the palm's facing step_cm at a time). Checked again after each round. Returns the
        moves (cm, and the digits opened) and the last check."""
        L = self.L
        moved = {}
        for _ in range(tries):
            if not ec["clip_pixels"]:
                break
            for sd in ec.get("sides") or ("r", "l"):
                parts = ec.get("parts", {}).get(sd) or ["palm"]
                digits = [p for p in parts if p != "palm"]
                for dg in digits:
                    moved.setdefault("opened", {})["%s:%s" % (sd, dg)] = self.open_to_clear(sd, dg)
                if moved.get(sd, 0.0) >= max_cm:
                    continue
                if "palm" not in parts and all(self.digit_depth(sd, dg) <= self.glove for dg in digits):
                    continue                     # the opened digits cleared it: the hand stays
                hn = L._n("hand", sd)
                w = ec.get("way_out", {}).get(sd)
                if w:
                    v = Vector(w)
                    v = v.normalized() * min(v.length + self.glove / 100.0 + 0.002, (max_cm - moved.get(sd, 0.0)) / 100.0)
                else:
                    v = -Vector(list(L._palm_facing(sd))).normalized() * (step_cm / 100.0)
                L._put_hand(sd, Matrix.Translation(v) @ L._bw(hn).copy())
                moved[sd] = round(moved.get(sd, 0.0) + v.length * 100.0, 2)
            ec = self.eye_clip(res=res)
        return moved, ec

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
        turned, slid = 0.0, 0.0
        if getattr(L, "_put_hand_unlimited", None) is not None:
            H, slid = self.slide_within_reach(side, mark, H)
            H, turned, _w = self.turn_hand_within(side, H)
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
               "limits": dict(getattr(self, "last_limits", {}).get(side) or {}, hand_turned_deg=round(turned, 1), slid_back_cm=round(slid, 1)),
               "arm": {k: v for k, v in L._arm_report(side, L._limits()[0])[0].items()
                       if k in ("elbow_bend_deg", "wrist_bend_deg", "wrist_flexion_deg", "wrist_radial_deg")}}
        self.report["holds"]["%s:%s:%s" % (side, mark, kind)] = out
        fq = {n: L.arm.pose.bones[n].rotation_quaternion.copy() for n in self.gk["finger_bones"][side]}
        return Hn, fq, out
