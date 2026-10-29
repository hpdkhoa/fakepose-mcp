# State of the gun work: rules, decisions, asks, what is built, what is open

Read this after every context summary, before any step (the owner, 2026-10-26: "make sure every decision and rule
with working things is placed inside the file to recall after memory compress and summarize, then do a recall after
compress so the rules and what I asked still be up to date"). The owner's words are in
`K:/Projects/gitHub/poselab-mcp/docs/OWNER_FEEDBACK.md` (dated, verbatim); this file is the index of what stands.

## Rules that stand (the owner's; the global CLAUDE.md holds the full text)

| Rule | Where |
|---|---|
| Build the stated method; walls are never traded; touch points first; show 3D evidence as pictures; a question gets an answer | global CLAUDE.md |
| The M1911A1 is the quality bar for models | memory m1911-is-the-quality-bar |
| The game's AR-15 clips are the pose bar for fakepose: ten measured rules | `docs/POSE_RULES.md` |
| The hand gate: every hold measured (digits touch, none inside the mesh from any side, no twist, thumb on the gun, joints in limits) before it is used or shown; FAIL is reported, never shown as done | global CLAUDE.md "The hand gate"; fakepose `hold_gate`; Gun Kit rule 11 |
| Zero clipping seen from the eye, every frame (2026-10-23, choice b) | fakepose eye_clip; at the hold the mesh check from any side now adds to it (2026-10-26, flagged) |
| One heavy Blender job at a time; a run at most 10 minutes | memory, Gun Kit time budget |
| Log every piece of feedback in OWNER_FEEDBACK.md; read it after a summary; flag a decision that conflicts with a rule before building | global CLAUDE.md |

## Decisions, by date (the owner's)

| Date | Decision |
|---|---|
| 2026-10-23 | fakepose holds the market way: presets on marks, fingers curl to contact, two-bone IK; anatomy reported, not enforced; eye from the head bone for fakepose only |
| 2026-10-24 | "the idle position is just the aim position with a pull"; the reload view: the port in the lower third, rolled to the eye (the M24) |
| 2026-10-25 | The AR-15 clips are the bar for fakepose. Joint limits in the IK (wrist 30, elbow 5 to 150, under the shoulder): the market's method with a body's limits, nothing refused. Keep the cover band. Fix the rolled wrist and the clipping first |
| 2026-10-26 | Rifles use the game camera (choice 1). Fix the left arm and the open fingers; the support thumb must close on the gun. Continue optimising. The chamber check in two variants, with the bullet and without, in the labs. A finger twisted, clipping, not touching is false physics: fix. Set up the hand gate and write it into the rules. Keep this state file. Fix the mend order, then author the two holds |
| 2026-10-27 | The shoulder-back limit 4 cm; the upper arm lengthened to a man's (32.8 cm, ANSUR II), the owner's permission on the Gun Kit arms copy |
| 2026-10-27 | The gate keeps every finger fault (the owner's question on fingers bent backward); the bar's fingers carried as joint angles, set by Pose Lab's measured setters; curls and openings set measured angles inside the ranges |
| 2026-10-26 | Engine additions while authoring (mine, told): `way_out_cm` on an inside digit, the thumb swing stopping at any segment's touch, the thumb clearing by its deepest point, the gate's untwist, `start_curl` (a hold's starting hook), `fingers_fit` true on the AR15 grip capture |
| 2026-10-26 | fakepose stays decoupled from Pose Lab: the fast market path, no Hold Lab solver behind its gate (it shares Pose Lab's Blender library for the plumbing only). Build per-gun authored holds (presets/guns/<gun>.json, tuned by the gate's numbers) and a wrap curl (joints close one after another, each at its own touch; the thumb swings toward the index first) |
| 2026-10-25 | The M107 is on hold until the owner reviews the rest |

My own choices, told to the owner: the rifle family keeps the first-person template body (the bar's shoulders); pistols keep the anatomical body and the head-bone eye; the barrett_handle action (the right hand charges the M107); the AR check's forward-assist tap dropped; cover and joints not judged on equip, holster, run.

## The asks and their status (since 2026-10-24)

| Ask | Status |
|---|---|
| M107 built from public photos; report every gun; showcases like the M1911; showcases with hands | done; M107 on hold since 2026-10-25 (detail pass done, 1 clipping frame, not rerun on the new holds) |
| Photo detail layer from the source photos | done (blueprint_photomap), in the report |
| Retrospective report of the labs | done: `K:/Projects/Claude/cc/report/lab_mcp_retrospective_2026-10-25.md` |
| fakepose at the AR-15 bar | 8 of 10 on the AR15, 6 of 10 on the M16A2 (POSE_RULES runs 1 to 9); cover and rule 7 open |
| Left arm and open fingers; the thumb on the gun | done to the holds' numbers; the gate now says the holds still miss (below) |
| The round in the chamber, two variants | done: rounds.py, blueprint_round, showcase loaded/empty (`out/showcase/<gun>/`), rig Round mesh and FBX riding the running part, hands round option; the M24 round shows at the port; the M16A2's stays behind the port wall at the check's draw |
| The hand gate | built; first entries FAIL on both guns (POSE_RULES rule 11) |
| The mend order, then the handle pinch and the magazine cup authored | done: the mend order, the per-gun overlay (presets/guns/<gun>.json), the wrap curl (off by default: it twisted), the gate's palm-in. All holds but the bolt catch still FAIL the gate (POSE_RULES run 11). Eight of eight holds pass the full rule hold by hold (runs 14 and 15); the bolt catch (a fifth hold) authored and PASS on the AR15 (run 16); every hold now starts from the open hand. Full runs (run 17): rule 11 PASS on both guns, 0 clipping frames of 1,178 and 997. Open: rule 4 cover, rule 7 hand on screen (both guns), rule 6 port 53 % (M16A2), rule 8 left elbow 2.2 in one M16A2 clip (gone on the long arm, run 20). The video: first cut built (out/showcase/labs_evolution.mp4 and _720p; builder report/video/build_lab_video.py); reworked 2026-10-27 on the owner's review: scene 4a before and after on one screen in step (five clip pairs, the old run's own frames beside the current engine's: Saved/Gate/gunkit/<gun>/hands_after_a..d), scene 4b the M1911A1 blueprint against the model (six screens); the owner reviews again. Tool: tune_hold.py <gun> <side:mark> <clip> <fwd> <up> <left> (run from the game folder K:/epic/ToangTown/ToangTown; the gate's way_out_cm says which way to shift) |

## Queued asks

- 2026-10-28, the owner: "try stock hold and lower then show me the evidences" (done, five runs, both gates each,
  `report/tune/M24_options_compare.png`): stock hold 1 cm up wrist 28.4 / pinky 2.12 off; 2 cm up wrist 28.5 / pinky
  0.79 off; the gun lowered against the eye (job option `aim_drop_cm`, fakepose AIM_DROP_CM) 2 cm wrist 35.7, 4 cm
  wrist 29.7, 6.5 cm wrist 28.9, pinky 1.36 to 1.69 off. Every pulled gate passes the joints, the pinky fails on all.
  None passes the gate. Waiting for the owner's decision on the M24 grip.

- 2026-10-28, the owner: "gate must behind all changed. And gate the pulled hold too" (done): fakepose `gate_again`;
  Gun Kit's final gate before the hold snapshot (fix on, the clips take the hold as it leaves it, `report["gate_final"]`,
  the grasp's gate kept as `gate_at_solve`) and the pulled gate before the clips (the gun at the idle pull, hands
  re-placed as frame 0, measured only, `report["gate_pulled"]`, arm_pulled.png with arm_view). Rule 11 counts both
  (`<hold>:pulled` entries). M24 grip run gate2: final FAIL (pinky 1.36 off, wrist 40.5), pulled FAIL (pinky 1.36
  off; wrist 29.1 and elbow 111 PASS); support PASS on both. Open: the M24 grip decision (the pinky under the stock's
  short wrist, the wrist 40.5 at the aim). The owner's rule (2026-10-27): every fail or pass picture carries markers.

- 2026-10-27, the owner: "keep your 4cm limit for shoulder and start the work": the shoulder-back limit is 4 cm (the owner's decision). The upper arm lengthened to 32.8 cm (run 19; Tools/blender/long_arms.py; Arms.pre_long_upperarm.fbx kept; bone_edits "upperarm"): AR15 rule 11 PASS, 0 clipping, support reach 17 to 11 cm short. The M24 round (run 20): the support authored (3 cm left, PASS); the grip meets the wrist wall (48 as the preset sits; 28 only with the fingers along the stock's side): the owner decides (POSE_RULES run 20). Regressions on the long arm and the palm-seating change: AR15 unchanged from run 19; M16A2 rule 11 five of five, 0 clipping, rule 8 PASS (the elbow lock of run 17 gone). Open: rules 4 and 7 on both, rule 6 port 53 % on the M16A2.

- 2026-10-27 (done, run 18): the M24 rerun; the shoulder-back move built (SHOULDER_BACK_MAX_CM 4, job option shoulder_back_max_cm); it opens the elbow, not the wrist, on the M24 grip; the M24 holds still fail the gate (grip pinky 1.32 off, wrist 35; support thumb 1.46 inside): their authoring is next if the owner says so. The ask was: rerun the M24 on the current engine (gate, limits) and report; build the shoulder-back move (the owner's idea: "move the shoulder back so the arm is extend then the wrist can be flatten") with a limit; the AR15 and M16A2 are two guns (Model Lab test gun; Blueprint Lab gun).

- 2026-10-27, the owner: "when all done, I want to have a video showcase about the evolution of all my lab mcp, and the visual flow of the lab mcp collaboration". After the M16A2's four holds pass the full rule. Sources: `K:/Projects/Claude/cc/report/lab_mcp_retrospective_2026-10-25.md`, each lab's git log, the showcases in `cc/out/showcase/`.

## Open, by the gate's numbers (2026-10-26)

- AR15: all four holds PASS under the full finger rule (run 14). Runs 11 to 13 judged twist only (void). M16A2: all four holds PASS under the full rule (run 15; grip back 2.5 down 4.2 right 0.4, cup up 1.5 left 1.0). Old numbers: grip middle/ring 0.79 off, thumb 0.33 inside; handguard 0.75 to 3.5 off, index and thumb 0.78 inside; handle three fingers 1.45 inside; magazine thumb 0.97 inside.
- Cause for most: the eye mend sets the whole hand back up to 3 cm after the digits closed. Fix: open the digit that is inside; move the hand only when the palm is inside.
- The handle pinch and the magazine cup hold nothing: author them (presets), through the gate.
- Cover 6 % against the game's 11 to 19 % (arm and model bulk); rule 7 (pulling hand on screen 19 to 24 % against the game's 44 and 58).
- The M16A2 port 53 % visible under the carry handle at roll 60.

## Where things are

- Repos (pushed): fakepose-mcp (presets, captured holds, POSE_RULES.md, this file, docs/validate scripts), weaponlab-mcp (Gun Kit hands job with the rules and the gate judgement, Blueprint Lab rounds/showcase/photomap), poselab-mcp (OWNER_FEEDBACK.md).
- Game outputs: `K:/epic/ToangTown/ToangTown/Saved/Gate/gunkit/<gun>/` (gunfacts.json, rigs, hands/hands.json with `pose_rules` and each hold's `gate`).
- Blueprint Lab guns: `K:/Projects/digitize/<gun>/` (blueprint, model, showcase, round.json).
- Review copies: `K:/Projects/Claude/cc/out/showcase/<gun>/`; reports and pictures: `K:/Projects/Claude/cc/report/`.
- Scratch tools (session only): clips_only.py, drive_split.py, hands_showcase.py, rules_sheet.py in the session scratchpad; the durable ones are copied to fakepose-mcp/docs/validate/.

## How to validate after a summary

1. Read OWNER_FEEDBACK.md from the last entry you remember; list every ask without a "result" line after it.
2. Run the AR15 through Gun Kit (`clips_only.py AR15`, 9 minutes) and read `hands.json`: `pose_rules` (11 rules) and each hold's `gate`.
3. Compare with the last table in POSE_RULES.md; anything worse is a regression to report before going on.

## 2026-10-28, queued ask: the M24 grip by line B (the owner: thumb on, index on the ring's middle, gun to the shoulder, sight line on the eye)

Built: fakepose `measure_line_b` (side rays on a grid round the trigger mark, the trigger's polygons left out; the ring
= the closed opening; the face hit above it at both ends, moved down to the ring's centre height; parallel to the bore),
`place_index_on_b` (the straight index's pad line turned onto B, its middle on B's middle the glove out, the hand rolled
about B to face the palm into the side and out of the mesh), `index_b_reading` (the gate's index item: 5 deg, 0.5 cm
across, 0.1 in, 1 cm along; mine, told); a hold with tuning `place: index_on_line_b` skips the slide, the palm turn, the
reach and the push-out, and TURN_MAX becomes 0. Gun Kit: touch points first (line B checked before any hand; a miss
stops the run; arm_touch.png), line B and the index pads in arm_view's json. M24 overlay r:grip: place, shift 0.
Result: line B PASS its definition; the index on it (0.3 deg); joints PASS; the hand inside the stock (web 1.8 cm in,
thumb base 2.8, thumb tip 1.47 inside; stock wrist 1.8 cm proud of the guard's face): gate FAIL. Waiting for the owner's
choice (OWNER_FEEDBACK.md, 2026-10-28). Note: arm_touch.png renders black (no lights yet at that point): the picture
script uses the hold's render with the touch json's points; fix when the owner continues this line.

## HANDOFF 2026-10-29 (for the next model/session): the M24 grip work, where it stands

Read first: the global CLAUDE.md rules (walls, markers, least verbose), poselab-mcp/docs/OWNER_FEEDBACK.md from
"2026-10-28, the owner: I see that index finger is not on the B line" to the end (every ask and result), this file.

**The hold now (run plan16), M24SWS r:grip, overlay `src/fakepose_mcp/data/presets/guns/M24SWS.json`:**
place `web_a_thumb_arrow`, point_a {behind_ring_cm 6.2, right_of_centre_cm 1.0}, thumb_arrow {forward 2, up -1},
thumb_over_down 0.7, fingers.thumb curl_to_contact, shift 0. Pipeline (fakepose.py `place_web_a_thumb_arrow`): web
fold on A (the wrist's top behind the action, measured by down rays) → the hand slid right by the wrist's half width
(1.07 cm) so the palm sits on the right face → turned about the palm's normal so the index aims at line B's middle →
index knuckle set (17.5 deg) → thumb laid across the top toward the left and down, pad rolled onto the top, joints
bent until the tip meets the left face → the other fingers curl to contact. Line B measured by `measure_line_b`
(side rays round the trigger mark, the trigger's polygons left out). Gate items added: index vs B (mode "fingers":
angle only), web vs A (0.5 cm). Hand turn on the palm off (hand_turn_max_deg 0). Elbow wall ELBOW_OUT_CM 3 (on its
own side of the gun).

**Body and gun (Gun Kit options, gunkit_hands.py):** `body: anatomical` (both shoulders 19 cm under the eye),
`butt_lock_cm: 5` (body_blade: the torso turned 70 deg cap, the butt still 8 cm behind the joint), `gun_to_shoulder:
true` (the gun pushed 13 cm forward: butt 5 cm ahead of the joint, eye relief 19.3 cm instead of 6.35), `arm_view:
true`, `arm_view_extra: [{name, side left|right, centre_mark, fov_deg}]` (arm_<name>.png + json).

**Run command (from K:/epic/ToangTown/ToangTown; one Blender job at a time, ~2 min):**
TUNE_VIEWS=right TUNE_TAG=_x HANDS_OPTIONS='{"arm_view": true, "hand_turn_max_deg": 0, "body": "anatomical",
"butt_lock_cm": 5.0, "gun_to_shoulder": true, "arm_view_extra": [{"name": "arm_left", "side": "left"}, {"name":
"grip_left", "side": "left", "centre_mark": "grip", "fov_deg": 30}]}' python <scratchpad>/tune_hold.py M24SWS r:grip
fire 0.0 0.0 0.0   (tune_hold.py: fakepose-mcp/docs/validate/ has copies of the durable scratch tools; tune_hold.py
and lineb_pic.py live in the session scratchpad: copy them to docs/validate/ when starting fresh.)
Output: Saved/Gate/gunkit/M24SWS/hands_tune/ (hands.json, arm_hold/pulled/touch/arm_left/grip_*.png + .json).
Pictures go to K:/Projects/Claude/cc/report/tune/M24_<run>_*.png with markers (lineb_pic.py and the small PIL
labelers in the transcript).

**Numbers now (plan16):** five digits touch (thumb -0.36 left face, index -0.25, middle 0.11, ring 0.10, pinky 0.10);
web 1.13 from A (the planned slide); elbow 121.5 aim / 112.4 pulled PASS, 2.2 cm under the shoulder; wrist 94.0 aim /
74.2 pulled FAIL (wall 30); index 49 deg off line B's direction (the slant to the trigger).

**Straight-wrist geometry (asked 2026-10-29):** with the hand as it sits, the forearm on the hand's line needs the
elbow 28 cm ABOVE the shoulder (aim) / 24 (pulled), 29 cm from it (upper arm 32.8): the raised firing elbow, which
breaks the elbow-under-shoulder wall. With the elbow as it is, a straight wrist needs the hand along the forearm,
off the grip. Pictures report/tune/M24_plan16_straight_wrist_aim.png, _pulled.png.

**Open decisions (the owner's):** (1) the wrist: the elbow-under wall vs the raised elbow vs the hand's angle on the
grip; (2) the index slant rule for this stock; (3) the eye relief 19.3 after the gun push (the scope); (4) the web-vs-A
gate check measures from A's middle-line point (1.13 "fail" is the planned slide: adjust the check to A's height
and place along the bore); (5) the gate's thumb "opened_first" and a later step bending the index a few degrees.
**Rules learned this thread:** never move the hand to fix a finger (A is a wall); the palm faces the grip, no roll
search; the thumb reaches the left by its own joints; A moved only where the owner marks it; verify + report with
numbers before building; least verbose; markers on every picture; left and right close views on every round.

## 2026-10-29 later: the hold as one solve (the owner: "build that two points")
fakepose `solve_parts`, `contact_readings`, `solve_hold`; overlay r:grip place "solve", A 7.1/1.0, solve_turn_max_deg
180, solve_grid_deg 15; a solved hold is gated with fix off. Run solve3 (412 s): walls held (wrist 13.3), web, thumb
pass; index 2.18 and palm 0.72 miss; the hand wraps upside down. Open: the owner to define the wrap's way (fingers
under, thumb over the top) as a contact or a wall. The market preset is in git at 6cb1ac4.
