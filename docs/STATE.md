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
| The mend order, then the handle pinch and the magazine cup authored | done: the mend order, the per-gun overlay (presets/guns/<gun>.json), the wrap curl (off by default: it twisted), the gate's palm-in. All holds but the bolt catch still FAIL the gate (POSE_RULES run 11). Eight of eight holds pass the full rule hold by hold (runs 14 and 15); the bolt catch (a fifth hold) authored and PASS on the AR15 (run 16); every hold now starts from the open hand. Full runs (run 17): rule 11 PASS on both guns, 0 clipping frames of 1,178 and 997. Open: rule 4 cover, rule 7 hand on screen (both guns), rule 6 port 53 % (M16A2), rule 8 left elbow 2.2 in one M16A2 clip (a wall: find the clip, ask). The video: first cut built (out/showcase/labs_evolution.mp4 and _720p; builder report/video/build_lab_video.py); the owner reviews. Tool: tune_hold.py <gun> <side:mark> <clip> <fwd> <up> <left> (run from the game folder K:/epic/ToangTown/ToangTown; the gate's way_out_cm says which way to shift) |

## Queued asks

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
