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
        import glob as _glob
        # a gun's own captures first; then its action family's (a hold against a mark point carries to any gun of the
        # family with the same marks: the AR-15 bar's holds on every AR)
        fam_ = self.facts.get("action")
        for cap in sorted(_glob.glob(os.path.join(DATA, "presets", "captured", "*.json"))):
            d_ = json.load(open(cap, encoding="utf-8"))
            if not (d_.get("side") and d_.get("mark")):
                continue
            key_ = "%s:%s" % (d_["side"], d_["mark"])
            own_ = d_.get("gun") == self.facts["name"]
            fam_ok = fam_ and d_.get("family") == fam_ and d_.get("rel_to_mark") and d_["mark"] in self.facts.get("marks", {})
            if own_ or (fam_ok and key_ not in out.get("captured", {})):
                out.setdefault("captured", {})[key_] = dict(d_, _own=own_)
        # the gun's own tuning of its holds (the owner, 2026-10-26: per-gun authored holds, tuned by the gate's numbers):
        # presets/guns/<gun>.json {"holds": {"side:mark": {"shift_cm": {forward, up, left}, "standoff_cm", "offset_cm",
        # "palm_into", "fingers_toward", "contact", "fingers": {...}, "curl": "wrap"|"together"}}}; applied over the
        # family's preset or the captured hold
        gp = os.path.join(DATA, "presets", "guns", "%s.json" % self.facts["name"])
        out["gun_tuning"] = json.load(open(gp, encoding="utf-8")).get("holds", {}) if os.path.exists(gp) else {}
        out["file"] = p
        return out

    def tuning(self, side, mark):
        return (self.presets.get("gun_tuning") or {}).get("%s:%s" % (side, mark)) or {}

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
            inside = d < 0.03 and self._inside(bvh, v)
            out[i] = (-d if inside else d) * 100.0
        return out

    def _inside(self, bvh, v, max_hits=64):
        """Is v inside the gun: by signed ray crossings (an exit counts +1, an entry -1) along three fixed rays, a
        vote of the three. The nearest face's side is not used: beside fine detail (a checkered grip's grooves, a
        vent's wall) the nearest face's normal is not the surface's way out, and read a finger 3 cm off the M16A2's
        grip as 3 cm inside (2026-10-26). Overlapping closed parts count as inside; a flipped part reads negative."""
        votes = 0
        for d_ in self._ray_dirs():
            net, o, n_ = 0, Vector(v), 0
            while n_ < max_hits:
                loc, nrm, _i, dist = bvh.ray_cast(o, d_)
                if loc is None:
                    break
                net += 1 if nrm.dot(d_) > 0.0 else -1
                o = loc + d_ * 1e-5
                n_ += 1
            if net > 0:
                votes += 1
        return votes >= 2

    def _ray_dirs(self):
        c = getattr(self, "_rdirs", None)
        if c is None:
            F, U, Lf = self.gun_axes()
            c = [Vector(list(Lf)).normalized(), Vector(list(-Lf)).normalized(), Vector(list(U)).normalized()]
            self._rdirs = c
        return c

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
        if self.family == "rifle" and self.presets.get("body", "template") == "template":
            # the bar (the owner, 2026-10-25: the game's AR-15 clips): the first-person template's own body, its right
            # shoulder over the eye (measured 2026-10-26 at the game's idle, view cm: right shoulder [4.1, -16.8, 10.8],
            # left [-28.9, -12.4, -11.8]); an anatomical body put the right shoulder 16 cm under the eye and the
            # firing wrist at 40 to 55 degrees on a rifle's grip. The pistol family keeps the anatomical body (the
            # owner's approved M1911A1).
            self.report["body_rest"] = {"kept": "the rig's own idle body (the first-person template's)", "reset": []}
        else:
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
        if self.family == "rifle" and self.presets.get("eye", "game") == "game":
            # the owner, 2026-10-26: rifles use the game camera (Gun Kit's eye, the one the bar was measured from); the
            # head-bone eye stood 8.9 cm ahead and 2.8 cm under it, so the gun placed from it stood 9 cm further
            # forward than the bar and the support arm ran out of reach. Pistols keep the head-bone eye (2026-10-23).
            self.report["eye"] = {"kept": "the game camera (Gun Kit's eye)", "eye": [round(x, 4) for x in L.eye],
                                  "source": "the owner, 2026-10-26: rifles use the game camera"}
            return L.eye
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

        # the gun lowered against the eye (the owner, 2026-10-28: "try ... lower": the eye higher over the stock, as a
        # scope mounted higher in its rings would set it): the sight line AIM_DROP_CM under the eye, reported as such
        drop = float(getattr(self, "AIM_DROP_CM", 0.0) or 0.0) / 100.0

        def place(d):
            t = eye + VF * d - VU * drop - Rd @ s["rear"]
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
            out = {"aim_drop_cm": round(drop * 100.0, 2), "eye_to_rear_sight_cm": round(float(np.linalg.norm(s2["rear"] - eye)) * 100.0, 2),
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
    TURN_MAX = 40.0            # the hand's turn on its palm's normal, at most (a cant of the hand on a grip)
    # the owner (2026-10-27): "move the shoulder back so the arm is extend then the wrist can be flatten": when no
    # elbow and no hand turn keeps the wrist inside, or the arm is short, the collarbone turns so the shoulder moves
    # back (toward the body, against the view's forward), at most SHOULDER_BACK_MAX_CM from the template's place. The
    # limit is mine until the owner sets it: 4 cm, about a collarbone's retraction (the scapula slides 2 to 5 cm).
    SHOULDER_BACK_MAX_CM = 4.0

    def hand_points_for(self, side, M):
        """The hand's knuckles and fingertips as M would place them (world), to test a turn against the gun."""
        L = self.L
        Hn = L._bw(L._n("hand", side))
        inv = Hn.inverted()
        pts = []
        for fi in ("index", "middle", "ring", "pinky", "thumb"):
            for j in ("01", "02", "03"):
                try:
                    pts.append(inv @ L._bw(L._n("finger", side, fi, j)).translation)
                except Exception:
                    pass
            try:
                pts.append(inv @ L._finger_tip(fi, side))
            except Exception:
                pass
        return [list(M @ q) for q in pts]

    def turn_keeps_out(self, side, M):
        """True when no knuckle or tip of the hand at M sits inside the gun past the glove (the turn must not push
        the fingers into the receiver)."""
        pts = self.hand_points_for(side, M)
        if not pts:
            return True
        D = self.gun_signed(pts)
        return float(np.min(D)) >= -self.glove

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
        if self.SHOULDER_BACK_MAX_CM > 0.0:
            self._clavicle_rest(side)
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
        back = 0.0
        if (wrist > self.WRIST_MAX or short > 0.0) and self.SHOULDER_BACK_MAX_CM > 0.0:
            back, E, wrist, bend, under, short = self.shoulder_back(side, M)
            S, E0, W0 = L._bw(up).translation, L._bw(lo).translation, L._bw(hn).translation
        L._two_bone(side, M.translation, pole_world=Vector(E.tolist()))
        L._set_world(hn, Matrix.LocRotScale(L._bw(hn).translation, M.to_quaternion(), L._unit()))
        L._roll_forearm(side)
        if not hasattr(self, "last_limits"):
            self.last_limits = {}
        self.last_limits[side] = {"wrist_bend_deg": round(wrist, 1), "elbow_bend_deg": round(bend, 1), "elbow_under_cm": round(under, 1),
                                  "hand_turned_deg": round(turned, 1), "shoulder_back_cm": round(back, 2)}
        return short

    def _clavicle_name(self, side):
        L = self.L
        for cn in ((L.names.get("clavicle") or "clavicle_{s}").format(s=side), "clavicle_" + side):
            if cn in L.arm.pose.bones:
                return cn
        return None

    def _clavicle_rest(self, side):
        """Each frame's shoulder move starts from the template body's collarbone (saved at first use), so the moves
        never add up frame over frame; the limit counts from the template's shoulder place."""
        L = self.L
        if not hasattr(self, "_clav_rest"):
            self._clav_rest = {}
        cn = self._clavicle_name(side)
        if cn is None:
            return
        if side not in self._clav_rest:
            self._clav_rest[side] = (L._bw(cn).copy(), L._bw(L._n("upperarm", side)).translation.copy())
        else:
            L._set_world(cn, self._clav_rest[side][0])
            bpy.context.view_layer.update()

    def shoulder_back(self, side, M, step_deg=1.0):
        """The owner's move (2026-10-27): the collarbone turned so the shoulder joint moves back along the view until
        the wrist bends inside WRIST_MAX and the arm reaches, at most SHOULDER_BACK_MAX_CM from where it started.
        Each step turns the clavicle about the world's up axis through its head, the sign that moves the shoulder
        back; stops when a step moves it back no more. Returns (cm moved back, elbow, wrist, bend, under, short)."""
        L = self.L
        cn = self._clavicle_name(side)
        if cn is None:
            E, wrist, bend, under = self.best_elbow(side, M)
            return 0.0, E, wrist, bend, under, 0.0
        VF = Vector(list(self.gk["view"][1]))
        up, lo, hn = L._n("upperarm", side), L._n("lowerarm", side), L._n("hand", side)
        S0 = Vector(self._clav_rest[side][1])            # the template body's shoulder: the limit counts from here
        head = L._bw(cn).translation.copy()

        def state():
            E, wrist, bend, under = self.best_elbow(side, M)
            S, E0, W0 = L._bw(up).translation, L._bw(lo).translation, L._bw(hn).translation
            short = max(0.0, (M.translation - S).length - (E0 - S).length - (W0 - E0).length) * 100.0
            return E, wrist, bend, under, short
        E, wrist, bend, under, short = state()
        moved = 0.0
        for _ in range(int(60 / step_deg)):
            if wrist <= self.WRIST_MAX and short <= 0.0:
                break
            if moved >= self.SHOULDER_BACK_MAX_CM:
                break
            M0 = L._bw(cn).copy()
            best = None
            for sg in (1.0, -1.0):
                L._set_world(cn, M0)
                L._turn_about(cn, Vector((0.0, 0.0, 1.0)), sg * step_deg, head)
                bpy.context.view_layer.update()
                b_ = float((S0 - L._bw(up).translation).dot(VF)) * 100.0        # cm the shoulder sits behind its start
                if best is None or b_ > best[0]:
                    best = (b_, L._bw(cn).copy())
            if best is None or best[0] <= moved + 0.02:
                L._set_world(cn, M0)
                bpy.context.view_layer.update()
                break
            L._set_world(cn, best[1])
            bpy.context.view_layer.update()
            moved = best[0]
            E, wrist, bend, under, short = state()
        return moved, E, wrist, bend, under, short

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
        L = self.L
        S = L._bw(L._n("upperarm", side)).translation
        E0, W0 = L._bw(L._n("lowerarm", side)).translation, L._bw(L._n("hand", side)).translation
        l1, l2 = (E0 - S).length, (W0 - E0).length
        reach = math.sqrt(l1 * l1 + l2 * l2 + 2.0 * l1 * l2 * math.cos(math.radians(self.ELBOW_MIN + 10.0)))   # the elbow bent 15
        best = None
        for k in range(int(max_cm / step_cm) + 1):
            M2 = Matrix.Translation(-F_ * (k * step_cm / 100.0)) @ M
            d_aim = (M2.translation - S).length
            d_rest = (M2.translation + shift - S).length
            margin = 0.02      # 2 cm; a clip's own sway past it is taken frame by frame (the hand slips along the handguard)
            over = max(0.0, d_aim - reach, d_rest - reach + margin) * 100.0   # cm past the arm's reach, at the aim or at rest
            if best is None or over < best[1]:
                best = (k * step_cm, over, M2)
            if over <= 0.0:
                break
        return best[2], best[0]

    def thumb_toward_gun(self, side, step_deg=3.0, max_deg=70.0):
        """The thumb swung as one about its base (the axis square to the thumb and to the way to the gun's nearest
        surface) until its pad touches (the glove counted), at most max_deg. Returns the swing and the gap left."""
        L = self.L
        bvh = self.gun_bvh()
        n = L._n("finger", side, "thumb", "01")
        base = L._bw(n).translation.copy()
        turned = 0.0
        gap = None
        for _ in range(int(max_deg / step_deg)):
            tip = Vector(list(L._anchor(side, "thumb_tip")))
            # the swing stops when any segment's skin touches (the thumb lies on the gun by its pad or its side): a
            # tip that reaches the surface after the middle segment went through it is not a hold (the gate,
            # 2026-10-26)
            gap = float(min(self._gaps(side, "thumb", None)))
            if gap <= self.glove:
                break
            near = bvh.find_nearest(tip)[0]
            if near is None:
                break
            d = (near - tip)
            axis = (tip - base).cross(d)
            if axis.length < 1e-6:
                break
            L._turn_about(n, axis.normalized(), step_deg, base)
            turned += step_deg
        return {"swing_deg": round(turned, 1), "pad_gap_cm": round(gap, 2) if gap is not None else None}

    def relax_wrist(self, side):
        """A hand in transit (holding nothing) relaxes: when its line bends past WRIST_MAX off the forearm, the hand is
        turned about the wrist by the least angle that brings the bend to WRIST_MAX (its roll kept), then the roll
        goes into the forearm. Returns the bend before and after."""
        L = self.L
        hn = L._n("hand", side)
        W = L._bw(hn).translation.copy()
        E = L._bw(L._n("lowerarm", side)).translation
        K = L._bw(L._n("finger", side, "middle", "01")).translation
        fore = (W - E).normalized()
        hand = (K - W).normalized()
        bend = math.degrees(fore.angle(hand))
        if bend <= self.WRIST_MAX:
            return {"before": round(bend, 1), "after": round(bend, 1)}
        axis = hand.cross(fore)
        if axis.length < 1e-6:
            return {"before": round(bend, 1), "after": round(bend, 1)}
        R = Matrix.Rotation(math.radians(bend - self.WRIST_MAX), 4, axis.normalized())
        H = L._bw(hn).copy()
        M = Matrix.Translation(W) @ R @ Matrix.Translation(-W) @ H
        L._set_world(hn, Matrix.LocRotScale(W, M.to_quaternion(), L._unit()))
        L._roll_forearm(side)
        K2 = L._bw(L._n("finger", side, "middle", "01")).translation
        after = round(math.degrees(fore.angle((K2 - W).normalized())), 1)
        if hasattr(self, "last_limits") and side in self.last_limits:
            self.last_limits[side]["wrist_bend_deg"] = after
            self.last_limits[side]["relaxed_from_deg"] = round(bend, 1)
        return {"before": round(bend, 1), "after": after}

    def reach_mark(self, side, mark, M, max_cm=8.0, step_cm=0.25):
        """A pinch or a pull must touch its part: the hand (at M) moved along the line from its index pad to the
        mark point until the pad is at the gun's surface (the glove counted), at most max_cm. Returns (M, cm moved,
        the pad's gap left)."""
        L, gk = self.L, self.gk
        self.gun_bvh()
        target = Vector(list(gk["mark_world"](mark)))
        Hn = L._bw(L._n("hand", side))
        pad_local = Hn.inverted() @ Vector(list(L._finger_tip("index", side)))      # the index tip (the pad's place on a pinch)
        moved = 0.0
        gap = None
        for _ in range(int(max_cm / step_cm)):
            pad = M @ pad_local
            gap = float(self.gun_signed([list(pad)])[0])
            if gap <= self.glove + 0.05:
                break
            d = (target - pad)
            if d.length < 1e-4:
                break
            M = Matrix.Translation(d.normalized() * (step_cm / 100.0)) @ M
            moved += step_cm
        return M, round(moved, 2), (round(gap, 2) if gap is not None else None)

    def hand_in_gun(self, side):
        """The hand's knuckles and tips inside the gun past the glove, measured on the mesh (not through a camera):
        the deepest, cm, and which digits. A hold is not a hold with a finger through the gun."""
        pts = self.hand_points_for(side, Matrix(self.L._bw(self.L._n("hand", side))))
        if not pts:
            return {"deepest_cm": 0.0, "digits": []}
        D = self.gun_signed(pts)
        names = []
        for fi in ("index", "middle", "ring", "pinky", "thumb"):
            names += [fi] * 4
        inside = [(float(-D[i]), names[i] if i < len(names) else "?") for i in range(len(pts)) if float(D[i]) < -self.glove]
        return {"deepest_cm": round(max((d for d, _ in inside), default=0.0), 2), "digits": sorted(set(n for _, n in inside))}

    # --- the hand gate (the owner, 2026-10-26: "setup a gate to auto check and calculate for the finger, touch point and
    # everything related to this issue because the error happened a lot") ----------------------------------------------
    GATE_TOUCH_CM = 0.3          # a digit the hold uses touches when its tip is within glove + this of the surface
    GATE_TWIST_DEG = 15.0

    def digit_tip_gap(self, side, digit):
        """The digit's nearest skin to the gun: the least signed distance over its middle joint, end joint and tip
        (a finger wrapped round a handguard touches with a segment, not always with its tip)."""
        # the skin's own least gap per segment (the same measure the curl stops on), the least of the three
        try:
            return float(min(self._gaps(side, digit, None)))      # None: the gun alone (False raised and fell back to bone points)
        except Exception:
            L = self.L
            pts = [list(self._tip_of(side, digit))]
            for j in ("02", "03"):
                try:
                    pts.append(list(L._bw(L._n("finger", side, digit, j)).translation))
                except Exception:
                    pass
            return float(min(self.gun_signed(pts)))

    def _tip_of(self, side, digit):
        L = self.L
        return L._anchor(side, "thumb_tip") if digit == "thumb" else L._finger_tip(digit, side)

    def gate_again(self, side, mark, kind=None, fix=True, tag="final"):
        """The gate run once more on the hold as it stands now (the owner, 2026-10-28: "gate must behind all changed",
        "gate the pulled hold too"): after the caller's last placement of the hand, or at the pulled gun place the
        clips play. The hold's own rules (as its grasp used them). With fix the digits are mended as hold_gate does;
        without, the hold is measured as it is. The result is kept on the hold's report entry as gate_<tag>."""
        hr = (getattr(self, "_hold_rules", {}) or {}).get("%s:%s" % (side, mark)) or {}
        kind = kind or hr.get("kind", "palm")
        rules = hr.get("rules") or (self.preset(side, mark, kind)[1] or {}).get("fingers") or {}
        self._gate_mark = mark
        gate = self.hold_gate(side, kind, rules, fix=fix)
        self.report.setdefault("holds", {}).setdefault("%s:%s:%s" % (side, mark, kind), {})["gate_" + tag] = gate
        return gate

    # --- line B (the owner, 2026-10-28: "index finger stay on middle of trigger ring"; the definition the owner set in
    # Pose Lab, 2026-10-22: parallel to the bore, on the frame's firing-side face, its middle at the trigger ring's
    # middle height) -------------------------------------------------------------------------------------------------
    LINE_B_ANGLE_DEG = 5.0       # the index's pad line within this of line B (mine, 2026-10-28, told)
    LINE_B_OFF_CM = 0.5          # each pad within this of line B across the face
    LINE_B_INSIDE_CM = 0.1       # no pad past the face by more than this
    LINE_B_ALONG_CM = 1.0        # the pad line's middle within this of the ring's middle along the bore

    def gun_bvh_without(self, bones):
        """The gun's surface without the parts the named bones move (the trigger sits in the ring's opening: a side
        ray through the hole hits it, and the trigger is not the frame's face), world, as posed now."""
        L = self.L
        obs = [o for o in bpy.context.scene.objects if o.type == "MESH" and o not in L.meshes and not o.hide_viewport
               and o.vertex_groups.get("hand_r") is None]
        dg = bpy.context.evaluated_depsgraph_get()
        verts, tris, cut = [], [], 0
        for o in obs:
            gi = {g_.index for g_ in o.vertex_groups if g_.name in bones}
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            M = ev.matrix_world
            base = len(verts)
            verts.extend([tuple(M @ v.co) for v in me.vertices])
            skip = set()
            if gi and len(o.data.vertices) == len(me.vertices):
                skip = {v.index for v in o.data.vertices if any(g_.group in gi and g_.weight > 0.5 for g_ in v.groups)}
            me.calc_loop_triangles()
            for t in me.loop_triangles:
                if any(i in skip for i in t.vertices):
                    cut += 1
                    continue
                tris.append(tuple(base + i for i in t.vertices))
            ev.to_mesh_clear()
        self._bvh_cut_tris = cut
        return BVHTree.FromPolygons(verts, tris)

    def measure_line_b(self, side="r", half_cm=6.0, up_cm=5.0, step_cm=0.2):
        """Line B measured on the gun's mesh, from the trigger mark: side rays from the firing side on a grid round the
        mark (the trigger's own polygons left out) find the ring's opening (the closed run of rays that pass through);
        its centre is the ring's middle; the frame's face is hit just above the opening at both ends of its length;
        those two hits move straight down to the ring's centre height, and the line runs through their middle parallel
        to the bore, the opening's length long (Pose Lab's definition, the owner's decisions 2026-10-21/22). Kept in
        the gun's frame so it rides the gun; checked against its definition before any hand is placed."""
        L = self.L
        m = self.facts["marks"]
        if "trigger" not in m:
            raise ValueError("fakepose: line B needs the trigger mark")
        F, U, Lf = self.gun_axes()
        S = -Lf if side == "r" else Lf                      # the firing side
        T = self.to_world(m["trigger"])
        tb = [p_.get("bone") for n_, p_ in (self.facts.get("parts") or {}).items() if n_ == "trigger" and p_.get("bone")]
        bvh = self.gun_bvh_without(tb + ["Trigger", "trigger"])
        A = np.arange(-half_cm, half_cm + 1e-9, step_cm)
        Bv = np.arange(-up_cm, up_cm + 1e-9, step_cm)
        na, nb = len(A), len(Bv)
        hit = np.full((na, nb), np.nan)                     # the face's distance from the middle plane toward the firing side, cm; nan: the ray passed
        for i, a in enumerate(A):
            for j, b in enumerate(Bv):
                o = Vector(list(T + F * (a / 100.0) + U * (b / 100.0) + S * 0.12))
                h = bvh.ray_cast(o, Vector(list(-S)), 0.24)
                if h[0] is not None:
                    hit[i, j] = float((np.array(list(h[0])) - T) @ S) * 100.0
        open_ = np.isnan(hit)
        i0, j0 = int(np.argmin(np.abs(A))), int(np.argmin(np.abs(Bv)))
        if not open_[i0, j0]:
            cand = np.argwhere(open_)
            if not len(cand):
                raise ValueError("fakepose: no opening beside the trigger mark")
            k = int(np.argmin(((cand - np.array([i0, j0])) ** 2).sum(1)))
            i0, j0 = (int(x) for x in cand[k])
        comp = np.zeros_like(open_)
        comp[i0, j0] = True
        stack = [(i0, j0)]
        while stack:
            i, j = stack.pop()
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ii, jj = i + di, j + dj
                if 0 <= ii < na and 0 <= jj < nb and open_[ii, jj] and not comp[ii, jj]:
                    comp[ii, jj] = True
                    stack.append((ii, jj))
        cells = np.argwhere(comp)
        if cells[:, 0].min() == 0 or cells[:, 0].max() == na - 1 or cells[:, 1].min() == 0 or cells[:, 1].max() == nb - 1:
            raise ValueError("fakepose: the opening by the trigger runs off the %.0f x %.0f cm grid (not a closed ring)" % (2 * half_cm, 2 * up_cm))
        ac, bc = float(A[cells[:, 0]].mean()), float(Bv[cells[:, 1]].mean())
        jc = int(np.argmin(np.abs(Bv - bc)))
        row = [i for i in range(na) if comp[i, jc]]
        a0, a1 = float(A[min(row)]), float(A[max(row)])

        def top_hit(i):
            jt = max(j for j in range(nb) if comp[i, j]) + 1
            while jt < nb and np.isnan(hit[i, jt]):
                jt += 1
            return None if jt >= nb else (float(A[i]), float(Bv[jt]), float(hit[i, jt]))
        e0, e1 = top_hit(min(row)), top_hit(max(row))
        if e0 is None or e1 is None:
            raise ValueError("fakepose: the frame's face above the ring's opening was not hit")
        x_face = 0.5 * (e0[2] + e1[2])
        hl = (a1 - a0) / 2.0
        ring = T + F * (ac / 100.0) + U * (bc / 100.0)
        mid = ring + S * (x_face / 100.0)
        B0, B1 = mid - F * (hl / 100.0), mid + F * (hl / 100.0)
        gb = bvh.ray_cast(Vector(list(ring - U * 0.08)), Vector(list(U)), 0.08)
        bottom = np.array(list(gb[0])) if gb[0] is not None else None
        Rw = self.gk["bone_world"]("Root")
        Ri = Rw.inverted()
        loc = lambda v: list(Ri @ Vector(list(v)))                           # noqa: E731
        dirl = lambda v: list((Ri.to_3x3() @ Vector(list(v))).normalized())  # noqa: E731
        chk = {"middle_height_off_ring_centre_cm": round(float((mid - ring) @ U) * 100.0, 3),
               "ends_height_off_ring_centre_cm": [round(float((e_ - ring) @ U) * 100.0, 3) for e_ in (B0, B1)],
               "ends_on_firing_side_cm": [round(float((e_ - ring) @ S) * 100.0, 3) for e_ in (B0, B1)],
               "top_edge_faces_cm": [round(e0[2], 3), round(e1[2], 3)],
               "ring_centre_from_trigger_mark_cm": [round(ac, 2), round(bc, 2)],
               "ring_centre_in_the_opening": bool(comp[int(np.argmin(np.abs(A - ac))), jc]),
               "line_to_bore_deg": 0.0}
        chk["ok"] = (abs(chk["middle_height_off_ring_centre_cm"]) <= 0.05 and all(v_ >= 0.2 for v_ in chk["ends_on_firing_side_cm"])
                     and chk["ring_centre_in_the_opening"] and math.hypot(ac, bc) <= 3.0 and abs(e0[2] - e1[2]) <= 0.5)
        if not hasattr(self, "line_b"):
            self.line_b = {}
        self.line_b[side] = {"B0": loc(B0), "B1": loc(B1), "mid": loc(mid), "ring": loc(ring), "dir": dirl(F), "normal": dirl(S),
                             "bottom": loc(bottom) if bottom is not None else None}
        out = {"side": side, "how": "side rays from the firing side on a %.1f cm grid round the trigger mark, the trigger's polygons left out; "
                                    "the ring = the closed opening they pass through; the frame's face hit just above the opening at both ends, "
                                    "moved straight down to the ring's centre height; the line parallel to the bore through their middle" % step_cm,
               "definition": "parallel to the bore, on the frame's firing-side face, its middle at the trigger ring's middle height (the owner, 2026-10-21/22)",
               "ring_centre_gun_cm": [round(x * 100.0, 2) for x in loc(ring)], "ring_length_cm": round(a1 - a0, 2),
               "ring_height_cm": round(float(Bv[cells[:, 1]].max() - Bv[cells[:, 1]].min()), 2), "opening_cells": int(comp.sum()),
               "face_from_middle_plane_cm": round(x_face, 3), "ends_gun_cm": [[round(x * 100.0, 2) for x in loc(e_)] for e_ in (B0, B1)],
               "guard_bottom_under_centre_cm": round(float((ring - bottom) @ U) * 100.0, 2) if bottom is not None else None,
               "trigger_tris_left_out": getattr(self, "_bvh_cut_tris", 0), "check": chk}
        self.report.setdefault("line_b", {})[side] = out
        return out

    WEB_A_CM = 0.5               # the web fold within this of point A (mine, 2026-10-28, told)

    def measure_point_a(self, side="r"):
        """Point A on the back of the grip (the owner, 2026-10-28: "the web need to goes in the back of the grip"): rays
        along the bore on the gun's middle line, from far behind, at heights from 4 cm above the ring's top to 10 cm
        under its centre; on each the surfaces that face backward (the grip's back) between 15 and 1.5 cm behind the
        ring's middle; A = the most forward of them, the deepest point of the grip's back curve where the web sits
        (my reading of "the back of the grip", a point). Kept in the gun's frame; the profile reported."""
        if not getattr(self, "line_b", {}).get(side):
            self.measure_line_b(side)
        F, U, _Lf = self.gun_axes()
        lb = self.line_b_world(side)
        ring = lb["ring"]
        rh = float((self.report.get("line_b", {}).get(side) or {}).get("ring_height_cm") or 1.8)
        bvh = self.gun_bvh()
        prof, best = [], None
        for zc in np.arange(rh / 2.0 + 4.0, -10.0 - 1e-9, -0.2):
            o = Vector(list(ring - F * 0.45 + U * (zc / 100.0)))
            d = Vector(list(F))
            got = None
            for _ in range(48):
                h = bvh.ray_cast(o, d, 0.6)
                if h[0] is None:
                    break
                dd = float((np.array(list(h[0])) - ring) @ F) * 100.0
                if dd > -1.5:
                    break
                if dd > -15.0 and h[1].dot(d) < 0.0:
                    got = (dd, np.array(list(h[0])), np.array(list(h[1].normalized())))
                o = h[0] + d * 1e-5
            if got is not None:
                prof.append([round(zc, 1), round(got[0], 2)])
                if best is None or got[0] > best[0]:
                    best = (got[0], got[1], got[2], zc)
        if best is None:
            raise ValueError("fakepose: no back face of the grip found behind the ring")
        back_face = {"A_gun_cm": [round(x * 100.0, 2) for x in (self.gk["bone_world"]("Root").inverted() @ Vector(list(best[1])))],
                     "behind_ring_cm": round(best[0], 2), "above_ring_centre_cm": round(best[3], 2), "profile_z_cm_depth_cm": prof[::3],
                     "note": "the backward-facing surface nearest the ring: on the M24 this is the trigger guard's rear bow, not the grip (run weba, 2026-10-28)"}
        # the wrist's top behind the tang (the owner, 2026-10-28: the web "in the back of the grip" with the thumb crossing to
        # the left side: the hand wraps the wrist from the right, the web over its top): rays straight down on the middle
        # line from 1.5 to 20 cm behind the ring; the top profile; A = its lowest point behind the receiver (the saddle
        # between the tang and the comb), the web's seat
        topp, best = [], None
        U_ = Vector(list(U))
        for yc in np.arange(-1.5, -20.0 - 1e-9, -0.2):
            o = Vector(list(ring + F * (yc / 100.0) + U * 0.25))
            h = bvh.ray_cast(o, -U_, 0.5)
            if h[0] is None:
                continue
            zc = float((np.array(list(h[0])) - ring) @ U) * 100.0
            topp.append([round(yc, 1), round(zc, 2)])
            if best is None or zc < best[0]:
                best = (zc, np.array(list(h[0])), np.array(list(h[1].normalized())), yc)
        if best is None:
            raise ValueError("fakepose: no top of the wrist found behind the ring")
        prof = topp
        Rw = self.gk["bone_world"]("Root")
        Ri = Rw.inverted()
        A, nA = best[1], best[2]
        if float(nA @ U) < 0.0:
            nA = -nA
        if not hasattr(self, "point_a"):
            self.point_a = {}
        self.point_a[side] = {"A": list(Ri @ Vector(list(A))), "normal": list((Ri.to_3x3() @ Vector(list(nA))).normalized())}
        out = {"side": side, "A_gun_cm": [round(x * 100.0, 2) for x in self.point_a[side]["A"]],
               "A_behind_ring_cm": round(best[3], 2), "A_above_ring_centre_cm": round(best[0], 2),
               "how": "rays straight down on the middle line 1.5 to 20 cm behind the ring; the wrist's top profile; A = its lowest point (the saddle between the tang and the comb)",
               "definition": "the web fold in the back of the grip (the owner, 2026-10-28), read as the seat on top of the wrist behind the tang, where the web rests when the thumb crosses to the left (a point; my reading, told)",
               "top_profile_y_cm_z_cm": prof[::3], "back_face_reading_rejected": back_face,
               "check": {"on_middle_line": True, "faces_up": bool(float(nA @ U) > 0.0), "ok": bool(float(nA @ U) > 0.0 and -20.0 < best[3] < -1.5)}}
        self.report.setdefault("point_a", {})[side] = out
        return out

    def point_a_world(self, side):
        pa = self.point_a[side]
        Rw = self.gk["bone_world"]("Root")
        return np.array(list(Rw @ Vector(pa["A"]))), unit(np.array(list(Rw.to_3x3() @ Vector(pa["normal"]))))

    def web_a_reading(self, side):
        A, nA = self.point_a_world(side)
        W = np.array(list(self.L._anchor(side, "web_fold")))
        F, U, _Lf = self.gun_axes()
        return {"web_to_A_cm": round(float(np.linalg.norm(W - A)) * 100.0, 2),
                "web_from_A_along_bore_up_out_cm": [round(float((W - A) @ F) * 100.0, 2), round(float((W - A) @ U) * 100.0, 2), round(float((W - A) @ nA) * 100.0, 2)]}

    def place_web_a_index_b(self, side, H, into):
        """The pistol grip's rule on this gun (the owner, 2026-10-28): the web fold on point A (the back of the grip),
        the straight index turned parallel to the bore (tip forward) about A, then the hand rolled about the bore's
        line through A to bring the index pads as near line B as the hand allows, outside and not pressing (the owner,
        2026-10-22: "just keep it close"). The thumb's rule then closes it on the far (left) side."""
        L = self.L
        PH = getattr(L, "_put_hand_unlimited", None) or L._put_hand
        L.natural_open(side, index_extended=True)
        bpy.context.view_layer.update()
        PH(side, H)
        bpy.context.view_layer.update()
        F, U, _Lf = self.gun_axes()
        A, nA = self.point_a_world(side)
        At = A + nA * (self.glove / 100.0)
        lb = self.line_b_world(side)
        dB, nF, mid = lb["dir"], lb["normal"], lb["mid"]
        W = np.array(list(L._anchor(side, "web_fold")))
        H1 = Matrix.Translation(Vector(list(At - W))) @ Matrix(H)
        PH(side, H1)
        bpy.context.view_layer.update()
        Li = L.index_pad_line(side)
        d = unit(np.array(Li["dir"]))
        q = Vector(list(d)).rotation_difference(Vector(list(F)))
        pv = Vector(list(At))
        H2 = Matrix.Translation(pv) @ q.to_matrix().to_4x4() @ Matrix.Translation(-pv) @ H1
        PH(side, H2)
        bpy.context.view_layer.update()
        _b, _T, sidev, kind, segi = L._skin_static()
        sc = 1 if side == "r" else 2
        sel = np.nonzero((sidev == sc) & ((kind == 2) | ((kind == 3) & (segi >= 3) & (segi <= 5))))[0][::3]

        def at(theta):
            return Matrix.Translation(pv) @ Matrix.Rotation(math.radians(theta), 4, Vector(list(F))) @ Matrix.Translation(-pv) @ H2

        def state(theta):
            PH(side, at(theta))
            bpy.context.view_layer.update()
            P = L._skin_arrays()[0]
            dp = float(np.min(self.gun_signed(P[sel])))
            Li_ = L.index_pad_line(side)
            c_ = np.array(Li_["centre"]) - mid
            c_ = c_ - F * float(c_ @ F)
            dist = float(np.linalg.norm(c_)) * 100.0
            outp = min(float((Li_["pads"][k] - mid) @ nF) * 100.0 for k in Li_["pads"])
            return dp, dist, outp
        # the palm's facing as the preset says gives the starting roll; the scan covers 90 degrees either way
        f = unit(np.array(list(L._palm_facing(side))))
        into = unit(np.asarray(into, dtype=float))
        fp, ip = f - F * float(f @ F), into - F * float(into @ F)
        th0 = math.degrees(math.atan2(float(np.cross(fp, ip) @ F), float(fp @ ip)))
        # the owner, 2026-10-28: "the palm need to hold the grip or the place hand need to stay": no roll search (it
        # turned the palm flat to the ground); the palm keeps its facing into the grip's side, and what is then inside
        # or off is reported by the gate
        dp, dist, outp = state(th0)
        chosen, tried, note = (th0, dp, dist, outp), [[round(th0, 1), round(dp, 2), round(dist, 2), round(outp, 2)]], "palm facing kept (no roll)"
        H3 = at(chosen[0])
        PH(side, H3)
        bpy.context.view_layer.update()
        return H3, {"web_moved_to_A_cm": round(float(np.linalg.norm(At - W)) * 100.0, 2), "index_turned_to_bore_deg": round(math.degrees(q.angle), 2),
                    "roll_to_palm_facing_deg": round(th0, 1), "roll_chosen_deg": round(chosen[0], 1), "least_depth_cm": round(chosen[1], 2),
                    "index_middle_to_line_B_cm": round(chosen[2], 2), "pads_out_past_face_cm": round(chosen[3], 2),
                    "roll_tried_deg_depth_dist_out": tried[::4], "note": note,
                    "reading": self.index_b_reading(side), "web": self.web_a_reading(side)}

    def index_along_bore(self, side, mark):
        """The index straightened (middle and end joints at 0) and its knuckle bent, within its range, to the angle
        that lays its pad line most nearly parallel to the bore with the tip forward. The hand is not moved. Returns
        the knuckle angle, the angle left to the bore and the reading against line B (measured if not yet)."""
        L = self.L
        if not getattr(self, "line_b", {}).get(side):
            self.measure_line_b(side)
        if not hasattr(self, "_b_holds"):
            self._b_holds = set()
        self._b_holds.add((side, mark))
        if not hasattr(self, "_b_mode"):
            self._b_mode = {}
        self._b_mode[side] = "fingers"
        F = self.gun_axes()[0]
        best = None
        for a in np.arange(-15.0, 90.0 + 1e-9, 2.5):
            self._pose_abs(side, "index", [float(a), 0.0, 0.0])
            bpy.context.view_layer.update()
            d = unit(np.array(L.index_pad_line(side)["dir"]))
            c = float(d @ F)
            if best is None or c > best[0]:
                best = (c, float(a))
        self._pose_abs(side, "index", [best[1], 0.0, 0.0])
        bpy.context.view_layer.update()
        return {"knuckle_deg": best[1], "angle_to_bore_deg": round(math.degrees(math.acos(min(1.0, max(-1.0, best[0])))), 2),
                "reading": self.index_b_reading(side)}

    def thumb_over(self, side, to="left", step_deg=3.0, max_deg=120.0):
        """The thumb swung as one about its base, about the hand's own forward line (wrist to the middle knuckle),
        toward the gun's far side (to: left or right), until its tip passes the gun's middle plane or any of its skin
        meets the gun; the closing to contact follows. Returns the swing, the tip's side and the gap."""
        L = self.L
        F, U, Lf = self.gun_axes()
        side_v = Lf if to == "left" else -Lf
        o = self.to_world((0.0, 0.0, 0.0))
        n = L._n("finger", side, "thumb", "01")
        base = L._bw(n).translation.copy()
        w = L._bw(L._n("hand", side)).translation
        k = L._bw(L._n("finger", side, "middle", "01")).translation
        axis = (k - w).normalized()
        tip = np.array(list(L._anchor(side, "thumb_tip")))
        # the sign that moves the tip toward the far side
        sgn = 1.0
        L._turn_about(n, axis, step_deg, base)
        bpy.context.view_layer.update()
        t2 = np.array(list(L._anchor(side, "thumb_tip")))
        if float((t2 - tip) @ side_v) < 0.0:
            L._turn_about(n, axis, -2.0 * step_deg, base)
            sgn = -1.0
        bpy.context.view_layer.update()
        turned, gap, across = step_deg, None, None
        for _ in range(int(max_deg / step_deg)):
            tip = np.array(list(L._anchor(side, "thumb_tip")))
            across = float((tip - o) @ side_v) * 100.0
            gap = float(min(self._gaps(side, "thumb", None)))
            if across > 0.0 or gap <= self.glove:
                break
            L._turn_about(n, axis, sgn * step_deg, base)
            bpy.context.view_layer.update()
            turned += step_deg
        return {"swing_deg": round(turned, 1), "tip_past_middle_plane_cm": round(across, 2) if across is not None else None,
                "gap_cm": round(gap, 2) if gap is not None else None}

    def place_web_a_thumb_arrow(self, side, H, into, arrow):
        """The owner's hold (2026-10-28, drawn on the left view): the web fold on A, the palm facing into the grip's
        right side as the preset says (no roll), the hand turned about its palm's normal so the straight index aims at
        the middle of line B (the trigger), the thumb laid down the left face along the arrow (forward and down)."""
        L = self.L
        PH = getattr(L, "_put_hand_unlimited", None) or L._put_hand
        L.natural_open(side, index_extended=False)
        self._pose_abs(side, "index", [0.0, 0.0, 0.0])
        bpy.context.view_layer.update()
        PH(side, H)
        bpy.context.view_layer.update()
        A, nA = self.point_a_world(side)
        At = A + nA * (self.glove / 100.0)
        lb = self.line_b_world(side)
        W = np.array(list(L._anchor(side, "web_fold")))
        H1 = Matrix.Translation(Vector(list(At - W))) @ Matrix(H)
        PH(side, H1)
        bpy.context.view_layer.update()
        # the palm onto the grip's right face: rolled about the bore's line through the web (the web stays on A) by the
        # least angle that brings the palm's skin out of the stock toward the gun's right (a hand wraps over the top
        # of the wrist; without this the palm hangs through the stock's middle, run arrow 2026-10-28)
        F_, U_, Lf_ = self.gun_axes()
        _b, _T, sidev, kind, segi = L._skin_static()
        sc = 1 if side == "r" else 2
        psel = np.nonzero((sidev == sc) & (kind == 2))[0][::2]
        pv = Vector(list(At))
        roll_out, roll_depth = 0.0, None
        pc0 = np.array(list(L._bw(L._n("finger", side, "middle", "01")).translation))
        for sg in (1.0, -1.0):
            Hs = Matrix.Translation(pv) @ Matrix.Rotation(math.radians(sg * 5.0), 4, Vector(list(F_))) @ Matrix.Translation(-pv) @ H1
            PH(side, Hs)
            bpy.context.view_layer.update()
            pc = np.array(list(L._bw(L._n("finger", side, "middle", "01")).translation))
            if float((pc - pc0) @ -Lf_) > 0.0:
                sgn_ = sg
                break
        PH(side, H1)
        bpy.context.view_layer.update()
        for k in range(0, 37):
            th_ = sgn_ * k * 2.5
            Hs = Matrix.Translation(pv) @ Matrix.Rotation(math.radians(th_), 4, Vector(list(F_))) @ Matrix.Translation(-pv) @ H1
            PH(side, Hs)
            bpy.context.view_layer.update()
            dp = float(np.min(self.gun_signed(L._skin_arrays()[0][psel])))
            roll_out, roll_depth = th_, dp
            if dp >= 0.0:
                break
        H1 = Hs
        # about the palm's normal through the web: the index's line aimed at line B's middle
        n = unit(np.array(list(L._palm_facing(side))))
        d = unit(np.array(L.index_pad_line(side)["dir"]))
        want = unit(lb["mid"] - At)
        dp, wp = unit(d - n * float(d @ n)), unit(want - n * float(want @ n))
        th = math.degrees(math.atan2(float(np.cross(dp, wp) @ n), float(dp @ wp)))
        pv = Vector(list(At))
        H2 = Matrix.Translation(pv) @ Matrix.Rotation(math.radians(th), 4, Vector(list(n))) @ Matrix.Translation(-pv) @ H1
        PH(side, H2)
        bpy.context.view_layer.update()
        # the index knuckle: the straight finger aimed at B's middle
        best = None
        for a in np.arange(-15.0, 90.0 + 1e-9, 2.5):
            self._pose_abs(side, "index", [float(a), 0.0, 0.0])
            bpy.context.view_layer.update()
            Li = L.index_pad_line(side)
            c = float(unit(np.array(Li["dir"])) @ unit(lb["mid"] - np.array(Li["pads"][min(Li["pads"])])))
            if best is None or c > best[0]:
                best = (c, float(a))
        self._pose_abs(side, "index", [best[1], 0.0, 0.0])
        bpy.context.view_layer.update()
        # the thumb along the arrow: straight, its base turned so it points the arrow's way (gun axes); the hold's rule
        # then swings it onto the gun and closes it
        F, U, Lf = self.gun_axes()
        dt = unit(F * float(arrow.get("forward", 0.0)) + U * float(arrow.get("up", 0.0)) + Lf * float(arrow.get("left", 0.0)))
        tn = L._n("finger", side, "thumb", "01")
        self._pose_abs(side, "thumb", [0.0, 0.0, 0.0])
        bpy.context.view_layer.update()
        base = L._bw(tn).translation.copy()
        tip = Vector(list(L._anchor(side, "thumb_tip")))
        q = (tip - base).normalized().rotation_difference(Vector(list(dt)))
        ax, ang = q.axis, math.degrees(q.angle)
        if ax.length > 1e-6:
            L._turn_about(tn, ax.normalized(), ang, base)
        bpy.context.view_layer.update()
        tip2 = np.array(list(L._anchor(side, "thumb_tip")))
        rd = self.index_b_reading(side)
        return H2, {"web_moved_to_A_cm": round(float(np.linalg.norm(At - W)) * 100.0, 2), "palm_rolled_onto_right_face_deg": round(roll_out, 1),
                    "palm_least_depth_after_roll_cm": round(roll_depth, 2) if roll_depth is not None else None, "turned_about_palm_deg": round(th, 1),
                    "index_knuckle_deg": best[1], "index_aim_cos": round(best[0], 4), "thumb_turned_deg": round(ang, 1),
                    "thumb_dir_to_arrow_deg": round(math.degrees(math.acos(min(1.0, max(-1.0, float(unit(tip2 - np.array(list(base))) @ dt))))), 1),
                    "thumb_tip_left_of_middle_cm": round(float((tip2 - self.to_world((0.0, 0.0, 0.0))) @ Lf) * 100.0, 2),
                    "reading": rd, "web": self.web_a_reading(side)}

    def line_b_world(self, side):
        lb = self.line_b[side]
        Rw = self.gk["bone_world"]("Root")
        w = lambda v: np.array(list(Rw @ Vector(v)))                           # noqa: E731
        d = lambda v: unit(np.array(list(Rw.to_3x3() @ Vector(v))))           # noqa: E731
        return {"B0": w(lb["B0"]), "B1": w(lb["B1"]), "mid": w(lb["mid"]), "ring": w(lb["ring"]), "dir": d(lb["dir"]), "normal": d(lb["normal"]),
                "bottom": w(lb["bottom"]) if lb.get("bottom") else None}

    def index_b_reading(self, side):
        """Where the straight index lies against line B, as posed now: its pad line's angle to B, each pad across the
        face from B (cm), each pad out past the face (cm, + outside), the pad line's middle from the ring's middle along
        the bore; the faults by the thresholds above."""
        L = self.L
        lb = self.line_b_world(side)
        dB, nF = lb["dir"], lb["normal"]
        uB = unit(np.cross(nF, dB))
        Li = L.index_pad_line(side)
        d = unit(np.array(Li["dir"]))
        ks = sorted(Li["pads"])
        ang = math.degrees(math.acos(min(1.0, abs(float(d @ dB)))))
        off = {str(k): round(float((Li["pads"][k] - lb["mid"]) @ uB) * 100.0, 2) for k in ks}
        out = {str(k): round(float((Li["pads"][k] - lb["mid"]) @ nF) * 100.0, 2) for k in ks}
        along = round(float((np.array(Li["centre"]) - lb["mid"]) @ dB) * 100.0, 2)
        tipfwd = bool(float(d @ dB) > 0.0)
        fails = []
        mode = (getattr(self, "_b_mode", {}) or {}).get(side, "index_on_line_b")
        if ang > self.LINE_B_ANGLE_DEG or not tipfwd:
            fails.append("index line %.1f deg off line B%s" % (ang, "" if tipfwd else ", tip backward"))
        if mode == "index_on_line_b" and max(abs(v) for v in off.values()) > self.LINE_B_OFF_CM:
            fails.append("index pad %.2f cm off line B across the face" % max(off.values(), key=abs))
        if mode != "fingers" and min(out.values()) < -self.LINE_B_INSIDE_CM:
            fails.append("index pad %.2f cm inside the face" % -min(out.values()))
        if mode == "index_on_line_b" and abs(along) > self.LINE_B_ALONG_CM:
            fails.append("index middle %.2f cm from the ring's middle along the bore" % along)
        web = None
        if mode in ("web_a_index_b", "fingers") and getattr(self, "point_a", {}).get(side):
            web = self.web_a_reading(side)
            if web["web_to_A_cm"] > self.WEB_A_CM:
                fails.append("web fold %.2f cm off point A" % web["web_to_A_cm"])
        return {"mode": mode, "angle_to_B_deg": round(ang, 2), "tip_forward": tipfwd, "pads_across_face_cm": off, "pads_out_past_face_cm": out,
                "middle_along_bore_cm": along, "web": web, "fails": fails, "pass": not fails,
                "pads_world": {str(k): [round(float(x), 4) for x in Li["pads"][k]] for k in ks}}

    def place_index_on_b(self, side, H, into):
        """The hand placed by line B (the owner, 2026-10-28: "index finger stay on middle of trigger ring"): from the
        preset's facing H, the straight index's pad line turned parallel to line B (tip forward) about its middle,
        moved so that middle sits on line B's middle the glove's thickness outside the face, then rolled about line B
        (the one freedom left; mine, told): first to face the palm into the gun's side as the preset says, then out
        only until the palm and the index are outside the mesh. Returns (the hand's matrix, the readings)."""
        L = self.L
        PH = getattr(L, "_put_hand_unlimited", None) or L._put_hand
        L.natural_open(side, index_extended=True)
        bpy.context.view_layer.update()
        PH(side, H)
        bpy.context.view_layer.update()
        lb = self.line_b_world(side)
        dB, nF, mid = lb["dir"], lb["normal"], lb["mid"]
        Li = L.index_pad_line(side)
        d, c = unit(np.array(Li["dir"])), np.array(Li["centre"])
        q = Vector(list(d)).rotation_difference(Vector(list(dB)))
        R1 = Matrix.Translation(Vector(list(c))) @ q.to_matrix().to_4x4() @ Matrix.Translation(Vector(list(-c)))
        H1 = R1 @ Matrix(H)
        PH(side, H1)
        bpy.context.view_layer.update()
        c1 = np.array(L.index_pad_line(side)["centre"])
        piv = mid + nF * (self.glove / 100.0)
        t = piv - c1
        H2 = Matrix.Translation(Vector(list(t))) @ H1
        PH(side, H2)
        bpy.context.view_layer.update()
        f = unit(np.array(list(L._palm_facing(side))))
        into = unit(np.asarray(into, dtype=float))
        fp, ip = f - dB * float(f @ dB), into - dB * float(into @ dB)
        th0 = math.degrees(math.atan2(float(np.cross(fp, ip) @ dB), float(fp @ ip)))
        pv = Vector(list(piv))

        def at(theta):
            return Matrix.Translation(pv) @ Matrix.Rotation(math.radians(theta), 4, Vector(list(dB))) @ Matrix.Translation(-pv) @ H2
        _b, _T, sidev, kind, segi = L._skin_static()
        sc = 1 if side == "r" else 2
        sel = np.nonzero((sidev == sc) & ((kind == 2) | ((kind == 3) & (segi >= 3) & (segi <= 5))))[0][::3]

        def depth(theta):
            PH(side, at(theta))
            bpy.context.view_layer.update()
            P = L._skin_arrays()[0]
            return float(np.min(self.gun_signed(P[sel])))
        chosen, best, tried = None, None, []
        for k in range(0, 25):
            for sg in ((1.0,) if k == 0 else (1.0, -1.0)):
                th = th0 + sg * k * 2.5
                dp = depth(th)
                tried.append([round(th, 1), round(dp, 2)])
                if best is None or dp > best[1]:
                    best = (th, dp)
                if dp >= 0.0:
                    chosen = (th, dp)
                    break
            if chosen is not None:
                break
        note = None
        if chosen is None:
            chosen, note = best, "no roll within 60 degrees puts the palm and the index outside: the least inside kept"
        H3 = at(chosen[0])
        PH(side, H3)
        bpy.context.view_layer.update()
        rd = self.index_b_reading(side)
        return H3, {"turned_to_B_deg": round(math.degrees(q.angle), 2), "moved_to_B_cm": round(float(np.linalg.norm(t)) * 100.0, 2),
                    "roll_to_palm_facing_deg": round(th0, 1), "roll_out_deg": round(chosen[0] - th0, 1), "least_depth_cm": round(chosen[1], 2),
                    "roll_tried": tried, "note": note, "reading": rd}

    def hold_gate(self, side, kind, rules, fix=True):
        """Every hold measured before it is used: each digit the hold uses touches its part (tip gap), no digit inside
        the mesh from any side, no finger twisted out of its plane, the thumb on the gun, the wrist and elbow inside
        their limits. With fix, what can be mended is (a digit closed to contact, one inside opened, the thumb swung
        on), then measured again. Returns the numbers and pass/fail; a failing hold is reported, never shown as done."""
        L = self.L
        used = [d for d in DIGITS if (rules.get(d) or {}).get("rule") == "curl_to_contact"]
        if kind == "pinch":
            used = [d for d in ("thumb", "index") if d in used] or ["thumb", "index"]

        def measure():
            g = {}
            for d in DIGITS:
                gap = self.digit_tip_gap(side, d)
                g[d] = {"tip_gap_cm": round(gap, 2), "touch": gap <= self.glove + self.GATE_TOUCH_CM, "inside": gap < -self.glove - 0.3}
                if g[d]["inside"]:
                    # which way out, in the gun's axes (cm): what an authored shift must undo
                    g[d]["way_out_cm"] = self.digit_way_out(side, d)
            # one measure throughout: the skin's segment gaps (a bone point sits a finger's thickness behind the skin)
            ins = [d for d in DIGITS if g[d]["inside"]]
            ing = {"deepest_cm": round(max((-g[d]["tip_gap_cm"] for d in ins), default=0.0), 2), "digits": ins}
            tw = {}
            try:
                FL = L._limits()[1]
                rep_ = L._finger_report(side, FL)
                bad_ = rep_[1] if isinstance(rep_, (list, tuple)) and len(rep_) > 1 else []
                # every fault the report names: twisted, bent backward (hyperextended), curled past its range. The
                # owner's rule (no hyperextended or twisted finger); until 2026-10-26 this kept the twisted lines only
                # and let a joint bent backward pass (the owner saw it on the M16A2 grip)
                tw = {"bad": [str(b) for b in bad_]}
                try:
                    tb_ = L._thumb_report(side, L._thumb_limits())[1]
                    tw["bad"] += [str(b) for b in (tb_ or [])]
                except Exception:
                    pass
            except Exception as e_:
                tw = {"error": repr(e_)[:80]}
            lim = dict((getattr(self, "last_limits", {}) or {}).get(side) or {})
            try:
                # the same joints read off the bones as they stand now (the limits above are the last placement's
                # prediction; 2026-10-27 the two disagreed on the M24 grip: hold 47.9, clip 29.2)
                S_, E_, W_ = (L._bw(L._n(b_, side)).translation for b_ in ("upperarm", "lowerarm", "hand"))
                K_ = L._bw(L._n("finger", side, "middle", "01")).translation
                lim["wrist_bones_deg"] = round(math.degrees((W_ - E_).angle(K_ - W_)), 1)
                lim["elbow_bones_deg"] = round(180.0 - math.degrees((S_ - E_).angle(W_ - E_)), 1)
                lim["hand_cm"] = [round(x * 100.0, 2) for x in W_]
                lim["shoulder_cm"] = [round(x * 100.0, 2) for x in S_]
            except Exception as e_:
                lim["wrist_bones_deg"] = repr(e_)[:60]
            fails = []
            ib = None
            if (side, getattr(self, "_gate_mark", None)) in getattr(self, "_b_holds", set()):
                # the index on line B is judged with the hold (the owner, 2026-10-23: a hard rule, never traded)
                try:
                    ib = self.index_b_reading(side)
                    fails += ib["fails"]
                except Exception as e_:
                    ib = {"error": repr(e_)[:120]}
            for d in used:
                if not g[d]["touch"]:
                    fails.append("%s not touching (tip %.2f cm off)" % (d, g[d]["tip_gap_cm"]))
            if ing["digits"]:
                fails.append("inside the gun: %s (%.2f cm)" % (", ".join(ing["digits"]), ing["deepest_cm"]))
            if tw.get("bad"):
                fails.append("finger fault: %s" % "; ".join(str(b) for b in tw["bad"][:3]))
            if lim.get("wrist_bend_deg", 0.0) > self.WRIST_MAX + 0.5:
                fails.append("wrist %.1f" % lim["wrist_bend_deg"])
            if lim.get("elbow_bend_deg", 90.0) < self.ELBOW_MIN or lim.get("elbow_bend_deg", 90.0) > self.ELBOW_MAX:
                fails.append("elbow %.1f" % lim["elbow_bend_deg"])
            if lim.get("elbow_under_cm", 99.0) < self.ELBOW_UNDER_CM - 0.05:
                fails.append("elbow %.1f cm under the shoulder" % lim["elbow_under_cm"])
            return {"digits": g, "used": used, "in_gun": ing, "twist": tw, "limits": lim, "fails": fails, "pass": not fails, "index_on_b": ib}
        before = measure()
        fixed = []
        if fix and not before["pass"]:
            if kind == "pinch" and any(not before["digits"][d]["touch"] for d in used):
                # a pinch reaches its part before its digits close (the index tip to the surface)
                H0 = Matrix(L._bw(L._n("hand", side)))
                H1, mv_, gap_ = self.reach_mark(side, getattr(self, "_gate_mark", "handle"), H0)
                if mv_ > 0.0:
                    L._put_hand(side, Matrix.LocRotScale(H1.translation, H1.to_quaternion(), L._unit()))
                    fixed.append({"reached_cm": mv_, "index_gap_cm": gap_})
            on_b = (side, getattr(self, "_gate_mark", None)) in getattr(self, "_b_holds", set())
            if kind != "pinch" and not on_b and any(not before["digits"][d]["touch"] for d in used if d != "thumb"):
                # the whole hand sits off the part: moved in along the palm's facing until the palm's skin touches
                # (not a hand placed by line B: its place is the index's, only its digits are mended, 2026-10-28)
                H0 = Matrix(L._bw(L._n("hand", side)))
                n_ = Vector(self.palm_normal_for(side, H0).tolist())
                mv_ = 0.0
                for _ in range(8):
                    # in by a quarter cm while every used finger still misses and nothing of the hand is inside: the
                    # hand seats on its first contact (2026-10-27: chasing a finger that cannot reach, the M24's
                    # pinky under the stock's short wrist, drove the palm 2 cm into the stock)
                    g_now = {d: self.digit_tip_gap(side, d) for d in used if d != "thumb"}
                    if any(v <= self.glove + self.GATE_TOUCH_CM for v in g_now.values()) or self.hand_in_gun(side)["digits"]:
                        break
                    H0 = Matrix.Translation(n_ * 0.0025) @ H0
                    L._put_hand(side, Matrix.LocRotScale(H0.translation, H0.to_quaternion(), L._unit()))
                    mv_ += 0.25
                fixed.append({"palm_in_cm": round(mv_, 2), "gaps_before": {d: before["digits"][d]["tip_gap_cm"] for d in used},
                              "gaps_after_move": {d: round(self.digit_tip_gap(side, d), 2) for d in used},
                              "palm_facing_toward_gun": round(float(np.array(n_) @ (np.array(list(self.gk["mark_world"](getattr(self, "_gate_mark", "grip")))) - np.array(list(L._bw(L._n("hand", side)).translation)))), 3)})
            for d in used:
                if not before["digits"][d]["touch"]:
                    if d == "thumb":
                        sw = self.thumb_toward_gun(side, max_deg=90.0)
                        fixed.append({"thumb_swing": sw})
                    r = rules.get(d) or {"target_deg": "fist"}
                    fixed.append({d: self.curl_to_contact(side, d, r.get("target_deg", "fist"), other=bool(r.get("other_hand")))["stopped_by"][:1]})
            for d in before["in_gun"]["digits"]:
                if d == "thumb":
                    fixed.append({"thumb_cleared": self.thumb_clear(side)})
                    if min(self._gaps(side, "thumb", None)) < -self.glove - 0.3:
                        # the base swing could not lift it (a tip through the stock behind a charging handle): the
                        # thumb's joints open to straight, then it lays back on the gun
                        fixed.append({"thumb_opened": self.open_to_clear(side, "thumb", max_deg=90.0)})
                        fixed.append({"thumb_laid": self.thumb_toward_gun(side, max_deg=60.0)})
                    continue
                fixed.append({d + "_opened": self.open_to_clear(side, d, max_deg=90.0)})
                r = rules.get(d)
                if r and r.get("rule") == "curl_to_contact":
                    fixed.append({d + "_closed": self.curl_to_contact(side, d, r.get("target_deg", "fist"), other=bool(r.get("other_hand")))["stopped_by"][:1]})
            # a twisted joint (bent out of its finger's plane, after the opening and closing above) is turned back into
            # the plane about the segment before it, then the finger closes to contact again
            mid = measure()
            for fi, j, curl in self._hyperextended(side, mid):
                fixed.append({"%s_%s_straightened" % (fi, j): self.straighten(side, fi, j, curl)})
                r = rules.get(fi)
                if r and r.get("rule") == "curl_to_contact":
                    fixed.append({fi + "_closed": self.curl_to_contact(side, fi, r.get("target_deg", "fist"), other=bool(r.get("other_hand")))["stopped_by"][:1]})
            mid = measure()
            for fi, j, deg in self._twisted(side, mid):
                fixed.append({"%s_%s_untwisted" % (fi, j): self.untwist(side, fi, j, deg)})
                r = rules.get(fi)
                if r and r.get("rule") == "curl_to_contact":
                    fixed.append({fi + "_closed": self.curl_to_contact(side, fi, r.get("target_deg", "fist"), other=bool(r.get("other_hand")))["stopped_by"][:1]})
            after = measure()
            return {"before": before, "fixed": fixed, "after": after, "pass": after["pass"], "fails": after["fails"]}
        return {"before": before, "fixed": fixed, "after": before, "pass": before["pass"], "fails": before["fails"]}

    def _twisted(self, side, m):
        """(finger, joint, side_deg) for each finger joint the measure found twisted past its limit."""
        L = self.L
        out = []
        try:
            FL = L._limits()[1]
            rep_ = L._finger_report(side, FL)[0]
        except Exception:
            return out
        names = {"knuckle": "01", "middle joint": "02", "end joint": "03"}
        for b_ in (m.get("twist") or {}).get("bad") or []:
            b_ = str(b_)
            if "twisted" not in b_:
                continue
            fi = b_.split(" ")[0]
            j = next((v for k, v in names.items() if " %s twisted" % k in b_), None)
            if j and ("%s_%s" % (fi, j)) in rep_:
                out.append((fi, j, float(rep_["%s_%s" % (fi, j)][1])))
        return out

    def _hyperextended(self, side, m):
        """(finger, joint, curl) for each finger joint the measure found bent backward past its range."""
        L = self.L
        out = []
        try:
            FL = L._limits()[1]
            rep_ = L._finger_report(side, FL)[0]
        except Exception:
            return out
        names = {"knuckle": "01", "middle joint": "02", "end joint": "03"}
        for b_ in (m.get("twist") or {}).get("bad") or []:
            if "backward" not in b_:
                continue
            fi = b_.split(" ")[0]
            j = next((v for k, v in names.items() if " %s bent" % k in b_), None)
            if j and ("%s_%s" % (fi, j)) in rep_:
                out.append((fi, j, float(rep_["%s_%s" % (fi, j)][0])))
        return out

    def straighten(self, side, fi, j, curl):
        """A finger joint bent backward (its curl under its range's floor): bent toward the palm to the floor, the
        other joints kept. Returns the curl before and after."""
        L = self.L
        FL = L._limits()[1]
        lo = float(FL[j][0])
        degs = [0.0, 0.0, 0.0]
        degs[("01", "02", "03").index(j)] = lo - curl
        self.set_curl(side, fi, degs)
        after = float(L._finger_report(side, FL)[0]["%s_%s" % (fi, j)][0])
        return {"before": round(curl, 1), "after": round(after, 1)}

    def untwist(self, side, fi, j, side_deg, max_deg=40.0):
        """A finger joint bent out of its plane: its bone turned about the segment before it (through the joint)
        by the twist read, the way that lowers it; the finger's curl is kept. Returns the twist before and after."""
        L = self.L
        n = L._n("finger", side, fi, j)
        prev = {"01": None, "02": "01", "03": "02"}[j]
        pivot = L._bw(n).translation.copy()
        if prev is None:
            mc = L._n("finger", side, fi, "metacarpal")
            start = L._bw(mc).translation if mc in L.arm.pose.bones else L._bw(L._n("hand", side)).translation
        else:
            start = L._bw(L._n("finger", side, fi, prev)).translation
        axis = (pivot - start)
        if axis.length < 1e-6:
            return {"before": round(side_deg, 1), "after": round(side_deg, 1)}
        axis.normalize()
        deg = max(-max_deg, min(max_deg, abs(side_deg)))
        M0 = L._bw(n).copy()
        FL = L._limits()[1]
        best, best_M = abs(side_deg), M0
        for sgn in (1.0, -1.0):
            L._set_world(n, M0)
            L._turn_about(n, axis, sgn * deg, pivot)
            now = abs(float(L._finger_report(side, FL)[0]["%s_%s" % (fi, j)][1]))
            if now < best:
                best, best_M = now, L._bw(n).copy()
        L._set_world(n, best_M)
        bpy.context.view_layer.update()
        return {"before": round(side_deg, 1), "after": round(best, 1)}

    def thumb_clear(self, side, step_deg=3.0, max_deg=60.0):
        """A thumb whose base segment sits inside the part: swung as one about its base away from the gun (the
        reverse of thumb_toward_gun) until its skin is out by the glove, at most max_deg; then thumb_toward_gun lays
        the pad back on. Opening the joints cannot move the base segment."""
        L = self.L
        bvh = self.gun_bvh()
        n = L._n("finger", side, "thumb", "01")
        base = L._bw(n).translation.copy()
        turned = 0.0
        for _ in range(int(max_deg / step_deg)):
            gaps = self._gaps(side, "thumb", None)
            if min(gaps) >= -self.glove:
                break
            # the deepest skin point of the thumb is what must come out: the swing carries it toward its nearest
            # surface point (a swing read from the tip, when the tip is already outside, can leave the base inside)
            deep, near = self._thumb_deepest(side, bvh)
            if deep is None or near is None:
                break
            axis = (deep - base).cross(near - deep)
            if axis.length < 1e-6:
                break
            L._turn_about(n, axis.normalized(), step_deg, base)
            turned += step_deg
        back = self.thumb_toward_gun(side, max_deg=max_deg)
        return {"cleared_deg": round(turned, 1), "laid_back": back, "gaps_cm": [round(v, 2) for v in self._gaps(side, "thumb", None)]}

    def digit_way_out(self, side, digit):
        """The deepest skin point of a digit: its depth and the way out to the gun's nearest surface, in the gun's
        axes (forward, up, left; cm), and the point itself in gun cm."""
        bvh = self.gun_bvh()
        deep, near = self._digit_deepest(side, digit, bvh)
        if deep is None or near is None:
            return None
        F, U, Lf = self.gun_axes()
        v = np.array(list(near - deep)) * 100.0
        R = np.array(self.gk["bone_world"]("Root"))
        pg = np.linalg.inv(R) @ np.array([deep.x, deep.y, deep.z, 1.0])
        return {"forward": round(float(v @ F), 2), "up": round(float(v @ U), 2), "left": round(float(v @ Lf), 2),
                "point_gun_cm": [round(float(pg[0]) * 100.0, 1), round(-float(pg[1]) * 100.0, 1), round(float(pg[2]) * 100.0, 1)]}

    def _digit_deepest(self, side, digit, bvh):
        """A digit's deepest skin point (world) and the gun's nearest surface point to it."""
        L = self.L
        P = L._skin_arrays()[0]
        _b, _T, sidev, kind, segi = L._skin_static()
        k = DIGITS.index(digit)
        sc = 1 if side == "r" else 2
        idx = np.nonzero((sidev == sc) & (kind == 3) & (segi >= k * 3) & (segi < k * 3 + 3))[0]
        if not len(idx):
            return None, None
        D = self.gun_signed(P[idx])
        i = int(np.argmin(D))
        deep = Vector([float(v) for v in P[idx][i]])
        return deep, bvh.find_nearest(deep)[0]

    def _thumb_deepest(self, side, bvh):
        return self._digit_deepest(side, "thumb", bvh)

    def _thumb_deepest_old(self, side, bvh):
        """The thumb's deepest skin point (world) and the gun's nearest surface point to it."""
        L = self.L
        P = L._skin_arrays()[0]
        _b, _T, sidev, kind, segi = L._skin_static()
        k = DIGITS.index("thumb")
        sc = 1 if side == "r" else 2
        idx = np.nonzero((sidev == sc) & (kind == 3) & (segi >= k * 3) & (segi < k * 3 + 3))[0]
        if not len(idx):
            return None, None
        D = self.gun_signed(P[idx])
        i = int(np.argmin(D))
        deep = Vector([float(v) for v in P[idx][i]])
        return deep, bvh.find_nearest(deep)[0]

    def palm_normal_for(self, side, M):
        """The palm's normal (out of the palm) as M would set it."""
        L = self.L
        Hn = L._bw(L._n("hand", side))
        local = Hn.to_3x3().inverted() @ Vector(list(L._palm_facing(side)))
        return unit(np.array(list(M.to_3x3() @ local)))

    def turn_hand_within(self, side, M, max_deg=None, step_deg=2.5):
        """When the best elbow still leaves the wrist over its limit: the hand turned about its palm's normal through
        its wrist (the palm stays on the mark's face), by the least angle that brings the wrist inside, at most
        max_deg. Returns (the new M, degrees turned, the wrist after)."""
        max_deg = self.TURN_MAX if max_deg is None else max_deg
        _E, wrist, _b, _u = self.best_elbow(side, M)
        if wrist <= self.WRIST_MAX:
            return M, 0.0, wrist
        self.gun_bvh()
        n = Vector(self.palm_normal_for(side, M).tolist())
        pivot = M.translation.copy()
        best = (wrist, M, 0.0)
        for sgn in (1.0, -1.0):
            for k in range(1, int(max_deg / step_deg) + 1):
                a = sgn * k * step_deg
                R = Matrix.Rotation(math.radians(a), 4, n)
                M2 = Matrix.Translation(pivot) @ R @ Matrix.Translation(-pivot) @ M
                if not self.turn_keeps_out(side, M2):
                    break                        # this way turns the fingers into the gun: no further
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
        if cap is not None and kind in ("palm", None, cap.get("kind")):
            if cap.get("rel_to_mark") and not cap.get("_own"):
                # the family's capture: the hand against this gun's own mark point
                rel = Matrix.Translation(Vector(list(gk["g"](self.facts["marks"][mark])))) @ Matrix(cap["rel_to_mark"])
            else:
                rel = Matrix(cap["rel_to_mark_bone"])
            H = gk["bone_world"](gk["mark_bone"](mark)) @ rel
            return H, {n: tuple(q) for n, q in cap["fingers"].items()}, "captured: " + cap["source"]
        key, p = self.preset(side, mark, kind)
        if p is None:
            raise KeyError("fakepose: no preset for %s %s %s" % (side, mark, kind))
        # the gun's own tuning may set the hand's facing and seat on this gun (a stock's sloped wrist against a
        # vertical pistol grip, 2026-10-27): these keys read over the family's preset
        tune_ = self.tuning(side, mark)
        p = dict(p, **{k: tune_[k] for k in ("palm_into", "fingers_toward", "offset_cm", "standoff_cm", "contact") if k in tune_})
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

    JOINTS = ("01", "02", "03")

    def _read_curls(self, side, digit):
        """A digit's joint readings now (degrees, the finger report's curl; the thumb's knuckle and end joint)."""
        L = self.L
        if digit == "thumb":
            tr = L._thumb_report(side, L._thumb_limits())[0]
            return [0.0] + [float((tr.get("thumb_" + j) or [0.0])[0]) for j in ("02", "03")]
        rep_ = L._finger_report(side, L._limits()[1])[0]
        return [float(rep_["%s_%s" % (digit, j)][0]) for j in self.JOINTS]

    def _ranges(self, digit):
        L = self.L
        if digit == "thumb":
            TL = L._thumb_limits()
            return [(-180.0, 180.0)] + [(float(TL[j][0]), float(TL[j][1])) for j in ("02", "03")]
        FL = L._limits()[1]
        return [(float(FL[j][0]), float(FL[j][1])) for j in self.JOINTS]

    def _pose_abs(self, side, digit, readings):
        """A digit's joints set to the given readings (degrees), each clamped to its range, with Pose Lab's measured
        setters (_set_curl, _set_thumb_bend): what is set is what the gate reads. A turn about a world hinge, added
        up over joints, read 138 degrees at a knuckle set to 100 (2026-10-26)."""
        L = self.L
        rg = self._ranges(digit)
        r = [min(hi, max(lo, float(v))) for v, (lo, hi) in zip(readings, rg)]
        if digit == "thumb":
            L._set_thumb_bend(side, r[1], r[2], L._thumb_limits())
        else:
            FL = L._limits()[1]
            for _ in range(2):
                for j, t_ in zip(self.JOINTS, r):
                    L._set_curl(side, digit, j, t_, FL)
        bpy.context.view_layer.update()
        return r

    def set_thumb_base(self, side, spread, palmar, tol=1.5, step=3.0, rounds=40):
        """The thumb's base joint (the metacarpal) turned until its measured spread from the index metacarpal and its
        angle in front of the palm read spread and palmar (degrees): two turns about the hand's axes, each step the
        sign that lowers the error (Pose Lab measures, it has no setter for this joint)."""
        L = self.L
        n = L._n("finger", side, "thumb", "01")
        TL = L._thumb_limits()
        across, _k = L._hand_frame(side)
        wrist = L._bw(L._n("hand", side)).translation
        mid = L._bw(L._n("finger", side, "middle", "01")).translation
        palm_n = across.cross((mid - wrist).normalized())
        palm_n = palm_n.normalized() if palm_n.length > 1e-9 else Vector((0, 0, 1))
        axes = (palm_n, across.normalized())

        def err():
            r = L._thumb_report(side, TL)[0]
            return (r["cmc_spread_deg"] - spread, r["cmc_palmar_deg"] - palmar)
        e = err()
        for _ in range(rounds):
            if abs(e[0]) <= tol and abs(e[1]) <= tol:
                break
            moved = False
            for ax, k_ in zip(axes, (0, 1)):
                # each axis lowers its own reading (the palm's normal: the spread; across the hand: the palm angle);
                # a sum of both stalled at palm 29 asked 5 (the M16A2 cup, 2026-10-27)
                base = L._bw(n).translation.copy()
                M0 = L._bw(n).copy()
                best = (abs(e[k_]), None, e)
                for sg in (1.0, -1.0):
                    L._set_world(n, M0)
                    L._turn_about(n, ax, sg * step, base)
                    e2 = err()
                    if abs(e2[k_]) < best[0] - 0.1:
                        best = (abs(e2[k_]), L._bw(n).copy(), e2)
                L._set_world(n, best[1] if best[1] is not None else M0)
                if best[1] is not None:
                    e, moved = best[2], True
            if not moved:
                break
        bpy.context.view_layer.update()
        r = L._thumb_report(side, TL)[0]
        return {"spread_deg": r["cmc_spread_deg"], "palmar_deg": r["cmc_palmar_deg"], "asked": [spread, palmar]}

    def set_curl(self, side, digit, degs):
        """A digit's joints bent by degs (toward the palm, degrees, from where they are), each inside its range."""
        now = self._read_curls(side, digit)
        return [round(v, 1) for v in self._pose_abs(side, digit, [n + float(d) for n, d in zip(now, degs)])]

    def set_curl_old(self, side, digit, degs):
        """A finger's three joints bent by degs (toward the palm, degrees, from where they are): the shape a hold
        starts from (a hook before a pull reaches its latch), with curl_to_contact's hinges and signs."""
        L = self.L
        names = [L._n("finger", side, digit, j) for j in ("01", "02", "03")]
        base = [L._bw(n).copy() for n in names]
        FL = L._limits()[1]
        if digit == "thumb":
            hinge = [L._thumb_report(side, L._thumb_limits())[2].get(j) for j in ("01", "02", "03")]
            hinge = [np.array(list(h)) if h is not None else None for h in hinge]
        else:
            hinge = [np.array(list(L._finger_report(side, FL)[2][digit]))] * 3
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
        for j, n in enumerate(names):
            if hinge[j] is None or abs(float(degs[j])) < 1e-9:
                continue
            h = Vector(list(hinge[j]))
            for i in range(j):
                if hinge[i] is not None:
                    h = Matrix.Rotation(math.radians(sign[i] * float(degs[i])), 3, Vector(list(hinge[i]))) @ h
            L._turn_about(n, h, sign[j] * float(degs[j]), L._bw(n).translation.copy())
        bpy.context.view_layer.update()
        return [round(float(d), 1) for d in degs]

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

        start = self._read_curls(side, digit)
        rg_ = self._ranges(digit)
        tgt = np.array([min(float(t_), hi - st) for t_, st, (lo, hi) in zip(tgt, start, rg_)])     # nothing past its range

        def pose(a):
            # absolute: each joint at its start reading plus a, set and read with the gate's own measure
            self._pose_abs(side, digit, [st + float(aj) for st, aj in zip(start, a)])
        wrap = getattr(self, "_curl_mode", "wrap") == "wrap"
        if wrap and digit == "thumb":
            # the market's wrap: the thumb's base swings toward the index first (opposition), then its joints close
            try:
                self.thumb_toward_gun(side, max_deg=60.0)
                start = self._read_curls(side, digit)
            except Exception:
                pass
        # wrap mode: the joints close one after another, the base first, each stopping at its own touch (a finger
        # round a handguard or a grip closes from the knuckle); together mode: every joint at once (a pinch, a trigger)
        order = [0, 1, 2]
        cur = 0
        for s in range(1, steps * (3 if wrap else 1) + 1):
            trial = ang.copy()
            if wrap:
                while cur < 3 and frozen[cur]:
                    cur += 1
                if cur >= 3:
                    break
                j_ = order[cur]
                trial[j_] = min(tgt[j_], ang[j_] + tgt[j_] / steps)
                if abs(trial[j_] - tgt[j_]) < 1e-9 and abs(ang[j_] - tgt[j_]) < 1e-9:
                    frozen[j_] = True
                    why[j_] = "target"
                    continue
            else:
                for j in range(3):
                    if not frozen[j]:
                        trial[j] = tgt[j] * s / steps
            pose(trial)
            gaps = self._gaps(side, digit, oth)
            # a segment touches when it reaches the glove, or, already touching at the start, when the joints before
            # it push it deeper (a pinky's end segment went 1.2 cm through the grip while its own joint stood still)
            hit = [g <= self.glove and (g0[j] > self.glove or g < g0[j] - 0.05) for j, g in enumerate(gaps)]
            if wrap and hit[cur] if cur < 3 else False:
                # this segment touches: its joint stops here (to a tenth of a step), the next joint goes on
                lo_, hi_ = ang.copy(), trial.copy()
                for _ in range(4):
                    mid = 0.5 * (lo_ + hi_)
                    pose(mid)
                    if self._gaps(side, digit, oth)[cur] <= self.glove:
                        hi_ = mid
                    else:
                        lo_ = mid
                ang = lo_
                frozen[cur] = True
                why[cur] = "touch at segment %d" % (cur + 1)
                continue
            if wrap:
                if any(hit):
                    # a later segment touched first (the finger's tip met the part): stop every joint here
                    ang = trial
                    for j in range(3):
                        if not frozen[j]:
                            frozen[j] = True
                            why[j] = "touch at segment %d" % (hit.index(True) + 1)
                    break
                ang = trial
                continue
            if any(hit):
                # the touch found to a tenth of the step by halving between the last clear bend and this one
                lo_, hi_ = ang.copy(), trial.copy()
                for _ in range(4):
                    mid = 0.5 * (lo_ + hi_)
                    pose(mid)
                    gm = self._gaps(side, digit, oth)
                    if any(g <= self.glove and (g0[j] > self.glove or g < g0[j] - 0.05) for j, g in enumerate(gm)):
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
        # each joint opens at most to its range's floor (straight): the market's clamp; a joint past straight is a
        # finger bent backward (the owner's rule), and the gate would fail it anyway
        cap = [max_deg] * 3
        try:
            if digit == "thumb":
                TL = L._thumb_limits()
                now = L._thumb_report(side, TL)[0]
                for i, j in enumerate(("01", "02", "03")):
                    c_ = now.get("thumb_" + j)
                    if c_ is not None and isinstance(TL.get(j), (list, tuple)):
                        cap[i] = max(0.0, float(c_[0]) - float(TL[j][0]))
            else:
                FL = L._limits()[1]
                now = L._finger_report(side, FL)[0]
                for i, j in enumerate(("01", "02", "03")):
                    cap[i] = max(0.0, float(now["%s_%s" % (digit, j)][0]) - float(FL[j][0]))
        except Exception:
            pass
        start_ = self._read_curls(side, digit)
        rg_ = self._ranges(digit)
        cap = [max(0.0, st - lo) for st, (lo, hi) in zip(start_, rg_)]
        if digit == "thumb":
            cap[0] = 0.0

        def pose(a):      # noqa: F811
            # absolute: each joint at its start reading minus a, never under its floor (straight)
            self._pose_abs(side, digit, [st - min(float(a), c_) for st, c_ in zip(start_, cap)])
        a = 0.0
        while self.digit_depth(side, digit) > self.glove and a < max_deg and a < max(cap):
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
                    continue                     # the hand's set-back is spent (or not allowed: digits only)
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
        # every hold starts from the open hand (the market way: a hold does not depend on the hold before it; in the
        # full run the handle pinch started from the bolt catch's hand and its thumb ended 0.83 cm inside, where the
        # hold-only run passed, 2026-10-27)
        try:
            L.natural_open(side, index_extended=False)
            bpy.context.view_layer.update()
        except Exception as e_:
            self.report.setdefault("notes", []).append("natural_open %s: %r" % (side, e_))
        H, fingers, src = self.hand_on(side, mark, kind)
        tune = self.tuning(side, mark)
        if tune.get("shift_cm"):
            F, U, Lf = self.gun_axes()
            sh = tune["shift_cm"]
            dv = (F * float(sh.get("forward", 0.0)) + U * float(sh.get("up", 0.0)) + Lf * float(sh.get("left", 0.0))) / 100.0
            H = Matrix.Translation(Vector(dv.tolist())) @ H
            src += "; tuned for %s: shifted %s cm" % (self.facts["name"], sh)
        on_b = tune.get("place") in ("index_on_line_b", "web_a_index_b", "web_a_thumb_arrow")
        placed_b = None
        if on_b:
            if not hasattr(self, "_b_mode"):
                self._b_mode = {}
            self._b_mode[side] = tune.get("place")
            # the owner, 2026-10-28: "thumb grab stay on, index finger stay on middle of trigger ring": the hand placed
            # by line B (measured first, measure_line_b); the slide, the turn on the palm and the push-out below would
            # move the index off B, so they are not run for this hold, and the hand is never turned on its palm again
            if not getattr(self, "line_b", {}).get(side):
                self.measure_line_b(side)
            if not hasattr(self, "_b_holds"):
                self._b_holds = set()
            self._b_holds.add((side, mark))
            self.TURN_MAX = 0.0
            _key0, _p0 = self.preset(side, mark, kind)
            _into = self.hand_axes(dict(_p0 or {}, **{k: tune[k] for k in ("palm_into", "fingers_toward") if k in tune}))[0]
            if tune.get("place") == "web_a_thumb_arrow":
                if not getattr(self, "point_a", {}).get(side):
                    self.measure_point_a(side)
                self._b_mode[side] = "fingers"
                H, placed_b = self.place_web_a_thumb_arrow(side, H, _into, tune.get("thumb_arrow") or {"forward": 2.0, "up": -1.0})
                src += "; placed by point A (the web fold on it), the index aimed at line B's middle, the thumb down the left face along the arrow"
            elif tune.get("place") == "web_a_index_b":
                if not getattr(self, "point_a", {}).get(side):
                    self.measure_point_a(side)
                H, placed_b = self.place_web_a_index_b(side, H, _into)
                src += "; placed by point A and line B (the web fold on the back of the grip, the straight index parallel to the bore near line B)"
            else:
                H, placed_b = self.place_index_on_b(side, H, _into)
                src += "; placed by line B (the index's pad line on it, its middle at the ring's middle)"
        cap_ = self.presets.get("captured", {}).get("%s:%s" % (side, mark))
        if fingers and cap_ is not None and cap_.get("fingers_fit") is False:
            # the capture came from another gun: its hand placement is kept, its finger turns are not (they fit that
            # gun's handguard); the digits start open and close to contact by the authored rules
            fingers = None
        if fingers:
            for n, q in fingers.items():
                L.arm.pose.bones[n].rotation_quaternion = q
            bpy.context.view_layer.update()
        turned, slid, reached = 0.0, 0.0, None
        curls = {}
        if getattr(L, "_put_hand_unlimited", None) is not None and not on_b:
            H, slid = self.slide_within_reach(side, mark, H)
            H, turned, _w = self.turn_hand_within(side, H)
        _cap = self.presets.get("captured", {}).get("%s:%s" % (side, mark)) or {}
        _pre = self.preset(side, mark, kind)[1] or {}
        start_curl = dict(_pre.get("start_curl") or {}, **(tune.get("start_curl") or {}))
        if _cap.get("curls_deg") and not fingers:
            # the bar's finger shape carried as joint angles: each joint bent from the open hand's reading to the
            # captured reading (the gate reads the same angles it checks)
            try:
                L._put_hand(side, H)
                FL_ = L._limits()[1]
                TL_ = L._thumb_limits()
                tr_ = _cap.get("thumb_report") or {}
                if tr_.get("cmc_spread_deg") is not None:
                    curls["captured_thumb_base"] = self.set_thumb_base(side, float(tr_["cmc_spread_deg"]), float(tr_["cmc_palmar_deg"]))
                for _pass in range(2):            # a later joint moves the planes the earlier ones are read in
                    for dg, cd in _cap["curls_deg"].items():
                        if dg == "thumb":
                            L._set_thumb_bend(side, float(cd[1]), float(cd[2]), TL_)
                        else:
                            for j, t_ in zip(("01", "02", "03"), cd):
                                L._set_curl(side, dg, j, float(t_), FL_)
                bpy.context.view_layer.update()
                got_ = L._finger_report(side, FL_)[0]
                gt_ = L._thumb_report(side, TL_)[0]
                curls["captured_curls_deg"] = {k: [round(float(v), 1) for v in vv] for k, vv in _cap["curls_deg"].items()}
                curls["captured_curls_read_deg"] = dict({fi: [round(float(got_["%s_%s" % (fi, j)][0])) for j in ("01", "02", "03")] for fi in ("index", "middle", "ring", "pinky") if "%s_01" % fi in got_},
                                                        thumb=[0, round(float((gt_.get("thumb_02") or [0])[0])), round(float((gt_.get("thumb_03") or [0])[0]))])
            except Exception as e_:
                curls["captured_curls_error"] = repr(e_)[:160]
        thumb_base = tune.get("thumb_base") or _pre.get("thumb_base")
        if start_curl or thumb_base:
            # the hold's starting shape (a hook before the reach: the pad close under the palm, so the palm lands by
            # the part, not a straight finger's length behind it; the thumb's base where the hold wants it)
            L._put_hand(side, H)
            if thumb_base:
                curls["thumb_base"] = self.set_thumb_base(side, float(thumb_base.get("spread_deg", 30.0)), float(thumb_base.get("palmar_deg", 20.0)))
            for dg, degs in start_curl.items():
                self.set_curl(side, dg, degs)
        if (_cap.get("reach_mark") or _pre.get("reach_mark")) and not on_b:
            H, _mv, _gap = self.reach_mark(side, mark, H)
            reached = {"moved_cm": _mv, "pad_gap_cm": _gap}
        short = L._put_hand(side, H)
        key, p = self.preset(side, mark, kind)
        pushed = None
        if p and p.get("push_out") and not on_b:
            into_ = np.asarray(self.hand_axes(p)[0]) if "palm_into" in p else -np.asarray(self.gun_axes()[2]) * (1.0 if side == "l" else -1.0)
            pushed = self.push_out(side, into_)
        if on_b:
            curls["index_on_b_placed"] = placed_b
            curls["index_on_b_after_put"] = self.index_b_reading(side)
        rules = (p or {}).get("fingers") or self.presets.get("captured_fingers", {}).get("%s:%s" % (side, mark), {})
        if tune.get("fingers"):
            rules = dict(rules, **tune["fingers"])
        self._curl_mode = tune.get("curl", (p or {}).get("curl", "together"))
        if fingers and not self.presets.get("captured_fingers", {}).get("%s:%s" % (side, mark)):
            # a captured hold brings the bar's finger turns for the bar's gun; on another gun each digit still closes
            # to contact by the authored preset's rules, from those turns (an open hand beside a slimmer handguard is
            # not a hold)
            rules = (p or {}).get("fingers") or {}
        if not hasattr(self, "_hold_rules"):
            self._hold_rules = {}
        self._hold_rules["%s:%s" % (side, mark)] = {"kind": kind, "rules": rules}     # for gate_again
        # a digit that starts inside the part (the open hand's own curl already past the surface) opens first, then
        # closes to contact from outside: a finger through the gun is not a hold, from any side (the owner, 2026-10-26)
        in_gun0 = self.hand_in_gun(side)
        for dg in in_gun0["digits"]:
            if on_b and dg == "index":
                curls["index_inside_kept_on_B_cm"] = in_gun0["deepest_cm"]      # B is a wall: not curled away, the gate reports it
                continue
            curls[dg + "_opened_first_deg"] = self.open_to_clear(side, dg, max_deg=90.0)
        for digit in DIGITS:
            r = rules.get(digit)
            if not r or r.get("rule") == "keep":
                continue
            if r["rule"] == "along_bore" and digit == "index":
                # the owner, 2026-10-28: the hand stays as it sat; only the index changes: straightened and turned at its
                # knuckle to lie parallel to the bore, tip forward, as near line B as the knuckle's range allows
                curls["index_along_bore"] = self.index_along_bore(side, mark)
                continue
            if r["rule"] == "curl_to_contact":
                if digit == "thumb":
                    if r.get("over_to"):
                        # the owner, 2026-10-28: "thumb is on another side (left side) of index finger": the thumb's base
                        # swung over the grip toward the gun's far side until its tip passes the middle plane or it meets
                        # the gun, then it closes to contact there
                        curls["thumb_over"] = self.thumb_over(side, r["over_to"])
                    # the owner, 2026-10-26: "thumb need to hold/close to the gun": the thumb's base swung toward the
                    # gun until its pad is at the surface (a thumb closes by its base, not by folding its tip), then
                    # the joints curl to contact
                    curls["thumb_close"] = self.thumb_toward_gun(side)
                curls[digit] = self.curl_to_contact(side, digit, r["target_deg"], other=bool(r.get("other_hand")))
        in_gun = dict(in_gun0, after=self.hand_in_gun(side))
        # the hold mended once against the eye's rule (zero clipping seen): what the eye sees inside the gun at the
        # hold is opened or set back here, then the digits close again; a frame-by-frame fix moved the whole hand off
        # the gun on many frames (the M16A2's idle: 143 of 181, the arm straightened to reach)
        hold_mend = None
        try:
            ec0 = self.eye_clip(res=(96, 54), sides=(side,))
            if ec0["clip_pixels"]:
                # the mend order (the owner, 2026-10-26): the digit that is inside opens; the hand moves only when the
                # palm itself is inside (a hand set back after the digits closed left them 0.4 to 1.9 cm off)
                palm_in = "palm" in (ec0.get("parts", {}).get(side) or [])
                if not palm_in:
                    # digits only: the gate judges them on the mesh (the eye's depth read opened a finger the mesh
                    # calls touching, 0.75 cm off after); the hold mend acts on the palm alone
                    moved, ec1 = {}, ec0
                else:
                    moved, ec1 = self.unclip_seen(ec0, res=(96, 54), max_cm=3.0)
                for digit in DIGITS:
                    r = rules.get(digit)
                    if r and r.get("rule") == "curl_to_contact" and ("%s:%s" % (side, digit)) in (moved.get("opened") or {}):
                        curls[digit + "_after_mend"] = self.curl_to_contact(side, digit, r["target_deg"], other=bool(r.get("other_hand")))
                hold_mend = {"seen_before": ec0["clip_pixels"], "seen_after": ec1["clip_pixels"], "moved": moved}
        except Exception as e_:
            hold_mend = {"error": repr(e_)[:200]}
        Hn = L._bw(L._n("hand", side)).copy()
        _VR, _VF, _VU = (np.array(list(v)) for v in self.gk["view"])
        _d = (np.array(list(L._bw(L._n("hand", side)).translation)) - np.array(list(L.eye))) * 100.0
        _sh = (np.array(list(L._bw(L._n("upperarm", side)).translation)) - np.array(list(L.eye))) * 100.0
        self._gate_mark = mark
        gate = self.hold_gate(side, kind, rules)
        if on_b:
            curls["index_on_b_after_gate"] = self.index_b_reading(side)
        out = {"preset": src, "arm_short_cm": round(short, 2), "curls": curls, "pushed_out_cm": pushed, "hold_mend": hold_mend,
               "reached": reached, "in_gun": in_gun, "gate": gate,
               "hand_view_cm": [round(float(_d @ _VR), 1), round(float(_d @ _VF), 1), round(float(_d @ _VU), 1)],
               "shoulder_view_cm": [round(float(_sh @ _VR), 1), round(float(_sh @ _VF), 1), round(float(_sh @ _VU), 1)],
               "limits": dict(getattr(self, "last_limits", {}).get(side) or {}, hand_turned_deg=round(turned, 1), slid_back_cm=round(slid, 1)),
               "arm": {k: v for k, v in L._arm_report(side, L._limits()[0])[0].items()
                       if k in ("elbow_bend_deg", "wrist_bend_deg", "wrist_flexion_deg", "wrist_radial_deg")}}
        self.report["holds"]["%s:%s:%s" % (side, mark, kind)] = out
        fq = {n: L.arm.pose.bones[n].rotation_quaternion.copy() for n in self.gk["finger_bones"][side]}
        return Hn, fq, out
