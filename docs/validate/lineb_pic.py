"""The M24 grip placed by line B (the owner, 2026-10-28): the touch-point picture (line B and the ring's middle on the gun,
no hand yet), then the final gate and the pulled gate beside the hold before this round (run gate2), same camera,
markers on every verdict: the joints, the digits' gaps, the index against line B, the gate's box."""
import json, os, sys, textwrap
from PIL import Image, ImageDraw, ImageFont
GK = "K:/epic/ToangTown/ToangTown/Saved/Gate/gunkit/M24SWS"
NEW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(GK, "hands_tune")
OLD = os.path.join(GK, "hands_tune_gate2")
OUTD = "K:/Projects/Claude/cc/report/tune"
F = lambda s: ImageFont.truetype("arial.ttf", s)
RED, GRN, YEL, ORA, CYA, WHT, GRY, MAG = (235, 70, 60), (70, 210, 90), (250, 220, 60), (250, 150, 50), (80, 210, 240), (255, 255, 255), (170, 170, 175), (240, 90, 220)
WALL = 30.0


def dtxt(gate, f_):
    g = gate["after"]["digits"][f_]; gap = g["tip_gap_cm"]; used = gate["after"].get("used") or gate.get("used") or []
    if f_ not in used:
        ib = gate["after"].get("index_on_b")
        if f_ == "index" and ib and "fails" in ib:
            return ("index on line B: %s" % ("PASS" if ib["pass"] else "FAIL"), GRN if ib["pass"] else RED)
        return ("%s %.2f (trigger finger, not judged)" % (f_, gap), GRY)
    if g["inside"]:
        return ("%s INSIDE %.2f cm FAIL" % (f_, -gap), RED)
    if g["touch"]:
        return ("%s touch %.2f PASS" % (f_, gap), GRN)
    return ("%s %.2f cm off FAIL" % (f_, gap), RED)


def draw_line_b(d, P, col=MAG, w=3, label=True):
    if "line_b_B0" in P and "line_b_B1" in P:
        d.line((P["line_b_B0"], P["line_b_B1"]), fill=col, width=w)
        for k in ("line_b_B0", "line_b_B1"):
            x, y = P[k]; d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=col)
        if label:
            x, y = P["line_b_B1"]; d.text((x + 8, y - 30), "line B", font=F(22), fill=col)
    if "line_b_ring" in P:
        x, y = P["line_b_ring"]; d.ellipse((x - 7, y - 7, x + 7, y + 7), outline=CYA, width=3)
        if label:
            d.text((x + 10, y + 2), "ring middle", font=F(20), fill=CYA)
    if "point_a" in P:
        x, y = P["point_a"]; d.ellipse((x - 7, y - 7, x + 7, y + 7), outline=YEL, width=3)
        if label:
            d.text((x - 150, y - 8), "point A (back of the grip)", font=F(20), fill=YEL)
    if "web_fold_r" in P:
        x, y = P["web_fold_r"]; d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=WHT)
        if label:
            d.text((x - 60, y + 8), "web fold", font=F(18), fill=WHT)


def mark(png, gate, label):
    lim = gate["after"]["limits"]
    wr, eb = lim["wrist_bones_deg"], lim["elbow_bones_deg"]
    wcol = RED if wr > WALL + 0.5 else GRN
    ecol = GRN if 5.0 <= eb <= 150.0 else RED
    digits = {f_: dtxt(gate, f_) for f_ in ("thumb", "index", "middle", "ring", "pinky")}
    im = Image.open(png).convert("RGB"); J = json.load(open(png + ".json")); P = {k: tuple(v) for k, v in J["points"].items()}
    ks = [k for k in P if k in ("wrist_r", "knuckle_r") or k.endswith("_tip_r")]
    xs, ys = [P[k][0] for k in ks], [P[k][1] for k in ks]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    bw = max(max(xs) - min(xs) + 120, (max(ys) - min(ys) + 120) * 4 / 3)
    box = (int(cx - bw / 2), int(cy - bw * 3 / 8), int(cx + bw / 2), int(cy + bw * 3 / 8))
    inset = im.crop(box).resize((640, 420), Image.LANCZOS); di = ImageDraw.Draw(inset)
    sx, sy = 640 / (box[2] - box[0]), 420 / (box[3] - box[1])
    tp = lambda k: ((P[k][0] - box[0]) * sx, (P[k][1] - box[1]) * sy)
    Pi = {k: tp(k) for k in P}
    draw_line_b(di, Pi, w=2, label=False)
    row = 0
    for f_, (txt, col) in digits.items():
        k = f_ + "_tip_r"
        if k in P:
            x, y = tp(k); di.ellipse((x - 8, y - 8, x + 8, y + 8), outline=col, width=3)
            ly = 36 + row * 30; lx = 400 if x < 400 else 20
            di.line((x, y, lx + (0 if lx == 400 else 8), ly + 10), fill=col, width=1)
            di.text((lx, ly), txt, font=F(19), fill=col); row += 1
    ib = gate["after"].get("index_on_b")
    if ib and "pads_across_face_cm" in ib:
        for k_ in ("1", "2", "3"):
            kk = "index_pad_%s_r" % k_
            if kk in Pi:
                x, y = Pi[kk]; di.ellipse((x - 5, y - 5, x + 5, y + 5), fill=MAG)
        ly = 36 + row * 30
        di.text((20, ly), "index pads across B %s cm, out %s cm" % (list(ib["pads_across_face_cm"].values()), list(ib["pads_out_past_face_cm"].values())), font=F(17), fill=MAG)
        di.text((20, ly + 24), "index line %.1f deg to B, middle %.2f cm from the ring middle" % (ib["angle_to_B_deg"], ib["middle_along_bore_cm"]), font=F(17), fill=MAG)
        if ib.get("web"):
            wc = GRN if ib["web"]["web_to_A_cm"] <= 0.5 else RED
            di.text((20, ly + 48), "web fold %.2f cm from point A %s" % (ib["web"]["web_to_A_cm"], "PASS" if wc == GRN else "FAIL"), font=F(17), fill=wc)
    di.rectangle((0, 0, 639, 419), outline=WHT, width=2); di.text((8, 6), "hand 2.5x, the gate's digits; magenta: line B and the index pads", font=F(18), fill=WHT)
    d = ImageDraw.Draw(im)
    draw_line_b(d, P)
    d.line((P["shoulder_r"], P["elbow_r"]), fill=YEL, width=5); d.line((P["elbow_r"], P["wrist_r"]), fill=ORA, width=5); d.line((P["wrist_r"], P["knuckle_r"]), fill=wcol, width=6)
    d.line(((0, P["eye"][1]), (im.width, P["eye"][1])), fill=CYA, width=1)

    def dot(k, col, lab, r=11):
        x, y = P[k]; d.ellipse((x - r, y - r, x + r, y + r), outline=col, width=4); d.text((x + r + 5, y - 14), lab, font=F(26), fill=col)
    dot("eye", CYA, "eye"); dot("shoulder_r", YEL, "shoulder, back %.2f cm" % lim.get("shoulder_back_cm", 0.0))
    dot("elbow_r", ecol, "elbow bend %.1f %s" % (eb, "PASS" if ecol == GRN else "FAIL"))
    dot("wrist_r", wcol, "wrist %.1f %s (wall %.0f)" % (wr, "PASS" if wcol == GRN else "FAIL", WALL)); dot("bore", GRN, "gun bone", 8)
    d.rectangle(box, outline=WHT, width=2)
    im.paste(inset, (im.width - 660, im.height - 440))
    verdict = "%s: GATE %s" % (label, "PASS" if gate["pass"] else "FAIL: " + "; ".join(gate["fails"]))
    vc = GRN if gate["pass"] else RED
    lines = textwrap.wrap(verdict, 95)
    tw = max(d.textlength(ln, font=F(26)) for ln in lines)
    d.rounded_rectangle((16, 16, 16 + tw + 30, 26 + 32 * len(lines) + 14), radius=8, fill=(30, 30, 34), outline=vc, width=3)
    for i, ln in enumerate(lines):
        d.text((30, 26 + 32 * i), ln, font=F(26), fill=vc)
    return im


def header(w, title, sub):
    hdr = Image.new("RGB", (w, 160), (18, 18, 20)); hd = ImageDraw.Draw(hdr); y = 8
    for ln in textwrap.wrap(title, 95): hd.text((16, y), ln, font=F(28), fill=WHT); y += 34
    for ln in textwrap.wrap(sub, 140): hd.text((16, y), ln, font=F(20), fill=GRY); y += 26
    return hdr.crop((0, 0, w, y + 6))


h = json.load(open(os.path.join(NEW, "hands.json"), encoding="utf-8"))
v = h["fakepose"]["holds"]["r:grip:palm"]
gf, gp = v["gate"], v.get("gate_pulled")
lb = h.get("line_b") or {}
aim = h["fakepose"].get("aim") or {}

# 1. the touch points on the gun, no hand yet
tp_png = os.path.join(NEW, "arm_touch.png")
if os.path.exists(tp_png) and lb:
    # the touch view itself rendered before the scene's lights exist (black): the points come from it, the render from the
    # hold's view (the same fixed camera, the gun at the same aim place)
    base_png = tp_png
    im = Image.open(base_png).convert("RGB"); J = json.load(open(tp_png + ".json")); P = {k: tuple(v_) for k, v_ in J["points"].items()}
    d = ImageDraw.Draw(im)
    draw_line_b(d, P)
    d.line(((0, P["eye"][1]), (im.width, P["eye"][1])), fill=CYA, width=1)
    x, y = P["eye"]; d.ellipse((x - 11, y - 11, x + 11, y + 11), outline=CYA, width=4); d.text((x + 16, y - 14), "eye, the sight line on it (0.00 cm under)", font=F(24), fill=CYA)
    if "line_b_bottom" in P:
        x, y = P["line_b_bottom"]; d.ellipse((x - 6, y - 6, x + 6, y + 6), outline=ORA, width=3); d.text((x + 10, y), "guard bottom", font=F(20), fill=ORA)
    # a zoom on the ring
    cx, cy = P["line_b_ring"]; bw = 360
    box = (int(cx - bw / 2), int(cy - bw * 3 / 8), int(cx + bw / 2), int(cy + bw * 3 / 8))
    base = Image.open(base_png).convert("RGB")
    inset = base.crop(box).resize((640, 420), Image.LANCZOS); di = ImageDraw.Draw(inset)
    sx, sy = 640 / (box[2] - box[0]), 420 / (box[3] - box[1])
    Pi = {k: ((P[k][0] - box[0]) * sx, (P[k][1] - box[1]) * sy) for k in P}
    draw_line_b(di, Pi)
    di.rectangle((0, 0, 639, 419), outline=WHT, width=2); di.text((8, 6), "the trigger ring 4.4x", font=F(18), fill=WHT)
    d.rectangle(box, outline=WHT, width=2)
    im.paste(inset, (im.width - 660, im.height - 440))
    chk = lb["check"]
    vc = GRN if chk["ok"] else RED
    verdict = "TOUCH POINT line B: %s. middle %.3f cm off the ring's centre height; ends %.2f / %.2f cm on the firing side; ring centre %.2f, %.2f cm from the trigger mark" % (
        "PASS its definition" if chk["ok"] else "FAIL its definition", chk["middle_height_off_ring_centre_cm"], *chk["ends_on_firing_side_cm"], *chk["ring_centre_from_trigger_mark_cm"])
    lines = textwrap.wrap(verdict, 95)
    tw = max(d.textlength(ln, font=F(26)) for ln in lines)
    d.rounded_rectangle((16, 16, 16 + tw + 30, 26 + 32 * len(lines) + 14), radius=8, fill=(30, 30, 34), outline=vc, width=3)
    for i, ln in enumerate(lines):
        d.text((30, 26 + 32 * i), ln, font=F(26), fill=vc)
    sub = "measured on the mesh: the ring's opening %.2f cm long, %.2f cm high, its centre %s cm in the gun's frame; the frame's face %.2f cm from the middle plane; %s. Definition (the owner, 2026-10-21/22): parallel to the bore, on the frame's firing-side face, its middle at the trigger ring's middle height. Dev view, fixed side camera, not the game; the points were measured before any hand was placed, no hand on the gun yet (the body at rest)." % (
        lb["ring_length_cm"], lb["ring_height_cm"], lb["ring_centre_gun_cm"], lb["face_from_middle_plane_cm"], lb["how"])
    hdr = header(im.width, "TOUCH POINTS FIRST: line B on the M24, checked against its definition before any hand is placed", sub)
    S = Image.new("RGB", (im.width, hdr.height + im.height), (18, 18, 20)); S.paste(hdr, (0, 0)); S.paste(im, (0, hdr.height))
    out = os.path.join(OUTD, "M24_plan16_touch.png"); S.save(out); print("saved", out)

# 2. the round's gates, full size, with the hold before this round beside them
A = mark(os.path.join(NEW, "arm_hold.png"), gf, "FINAL GATE (aim place), index on line B")
B = mark(os.path.join(NEW, "arm_pulled.png"), gp, "PULLED GATE (the clips' place)") if gp else None
pl = (v.get("curls") or {}).get("index_on_b_placed") or {}
rd = gf["after"].get("index_on_b") or {}
sub = ("placement: the index line turned %.1f deg onto B, the hand moved %.2f cm, rolled %.1f deg out from the palm's facing (least depth %.2f cm); after the final gate: index %.1f deg to B, pads across %s, out %s cm, middle %.2f cm along the bore from the ring's middle. "
       "aim: sight line %.2f cm under the eye, rear sight %.2f cm from the eye. hold: wrist %.1f, elbow %.1f, shoulder back %.2f; pulled: wrist %.1f, elbow %.1f. hand turn on the palm: off. Dev views, fixed side camera, not the game.") % (
    pl.get("index_turned_to_bore_deg", pl.get("turned_to_B_deg", 0)), pl.get("web_moved_to_A_cm", pl.get("moved_to_B_cm", 0)), pl.get("roll_chosen_deg", pl.get("roll_out_deg", 0)), pl.get("least_depth_cm", 0),
    rd.get("angle_to_B_deg", -1), list((rd.get("pads_across_face_cm") or {}).values()), list((rd.get("pads_out_past_face_cm") or {}).values()), rd.get("middle_along_bore_cm", 0),
    aim.get("aim_drop_cm", 0.0), aim.get("eye_to_rear_sight_cm", 0.0), gf["after"]["limits"]["wrist_bones_deg"], gf["after"]["limits"]["elbow_bones_deg"], gf["after"]["limits"].get("shoulder_back_cm", 0.0),
    (gp["after"]["limits"]["wrist_bones_deg"] if gp else -1), (gp["after"]["limits"]["elbow_bones_deg"] if gp else -1))
hdr = header(A.width, "M24 grip, run plan16: the body bladed, then the gun pushed forward until the butt locks 5 cm ahead of the shoulder joint: the web on A (1 cm right of centre), the palm on the right face, the thumb over the top onto the left, the index at the ring; the gun at the shoulder with the sight line on the eye. Full view with the shoulder.", sub)
S = Image.new("RGB", (A.width, hdr.height + A.height + (B.height if B else 0) + 40), (18, 18, 20))
S.paste(hdr, (0, 0)); S.paste(A, (0, hdr.height))
if B: S.paste(B, (0, hdr.height + A.height))
ImageDraw.Draw(S).text((16, S.height - 30), "M24SWS right grip. yellow: upper arm; orange: forearm; red/green: hand, red = past the wall; cyan: eye height; magenta: line B, the index pads; inset: fingertips with the gate's gap (cm, + off, - inside).", font=F(20), fill=GRY)
out = os.path.join(OUTD, "M24_plan16_round.png"); S.save(out); print("saved", out)

# 3. before and after, same camera: left the hold before this round (gate2), right this round; the final gate above, the pulled gate below
if os.path.exists(os.path.join(OLD, "hands.json")):
    h0 = json.load(open(os.path.join(OLD, "hands.json"), encoding="utf-8")); v0 = h0["fakepose"]["holds"]["r:grip:palm"]
    A0 = mark(os.path.join(OLD, "arm_hold.png"), v0["gate"], "BEFORE, final gate")
    B0 = mark(os.path.join(OLD, "arm_pulled.png"), v0["gate_pulled"], "BEFORE, pulled gate")
    sc = 0.5; cw, ch = int(A.width * sc), int(A.height * sc)
    S = Image.new("RGB", (2 * cw + 30, 110 + 2 * (ch + 50)), (18, 18, 20)); d = ImageDraw.Draw(S)
    d.text((16, 12), "M24 grip: BEFORE (the grip preset as it sat, run gate2) and AFTER (this round: index on line B, thumb on, sight line on the eye). Same camera. Markers: red FAIL, green PASS, magenta line B.", font=F(22), fill=WHT)
    d.text((16, 42), "The owner, 2026-10-28: 'thumb grab stay on, index finger stay on middle of trigger ring, then move the gun to shoulder and eye view is the same with human eye line'. Dev views, not the game.", font=F(18), fill=GRY)
    d.text((16, 70), "before final: %s | after final: %s" % (("PASS" if v0["gate"]["pass"] else "FAIL " + "; ".join(v0["gate"]["fails"])), ("PASS" if gf["pass"] else "FAIL " + "; ".join(gf["fails"])))[:230], font=F(18), fill=GRY)
    y = 110
    S.paste(A0.resize((cw, ch), Image.LANCZOS), (10, y)); S.paste(A.resize((cw, ch), Image.LANCZOS), (20 + cw, y))
    y += ch + 50
    S.paste(B0.resize((cw, ch), Image.LANCZOS), (10, y)); S.paste(B.resize((cw, ch), Image.LANCZOS), (20 + cw, y))
    d.text((16, y - 40), "before pulled: %s | after pulled: %s" % (("PASS" if v0["gate_pulled"]["pass"] else "FAIL " + "; ".join(v0["gate_pulled"]["fails"])), ("PASS" if gp["pass"] else "FAIL " + "; ".join(gp["fails"])))[:230], font=F(18), fill=GRY)
    out = os.path.join(OUTD, "M24_plan16_compare.png"); S.save(out); print("saved", out, S.size)
