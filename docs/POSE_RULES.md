# Pose rules: the AR-15 bar for fakepose

The owner (2026-10-25): "look again at my AR-15 in my previous work and gameplay, the pose the angle and the action
all better than what has been built in the showcase, I want fakepose at least will have that quality."

The bar is the game's AR-15 first-person clips (the pack's idle mended on 2026-10-10, the hand-made chamber check and
charge of 2026-10-07/08), measured with Pose Lab (`Tools/poselab/lab.py`, rig `ar`, 90 degree view, 16:9). Every
rule below carries the bar's measured number and fakepose's measured number on the same gun (Model Lab AR15 through
Gun Kit, `Saved/Gate/gunkit/AR15`, run 2026-10-24). This file is the record that survives context summaries: read it
before any fakepose change, revalidate after.

Screen coordinates: x right, y up, each -1 to 1. "Cover" is the share of the view the gun and arms fill.

## The rules, validated 2026-10-25

| # | Rule (from the bar) | Game AR-15 (the bar) | fakepose AR15 | Result |
|---|---|---|---|---|
| 1 | At rest the bore runs parallel to the view: yaw 0, pitch 0, roll 0 | 0.0 / 0.0 / 0.0 | pitch -10 (the idle pull) | FAIL |
| 2 | At rest the rear sight sits just under the eye line: 13 cm ahead, 4 cm right, 4 cm below | [3.8, 13.1, -4.4] cm | [6, 12, -14] cm (pull 14 down, 6 right) | FAIL |
| 3 | At rest the muzzle is near the view's centre | screen [0.09, -0.19] | screen [0.09, -0.63] (computed) | FAIL |
| 4 | The gun and arms fill 10 to 20 % of the view in every clip, every frame | idle 15 %, check 11 to 15 %, charge 11 to 19 % | aim 9 %, idle 0.8 %, check 0.7 %, charge 0.8 %, reload 1.7 % | FAIL |
| 5 | The support hand is on screen at rest | hand_l screen [0.04, -0.59] | not seen (0.8 % cover) | FAIL |
| 6 | Chamber check and charge: the gun rolls 60 degrees so the port turns to the eye, yaw and pitch stay 0 | roll -60, port 65 % visible, port at screen [0.30, -0.47] | port not seen | FAIL |
| 7 | Chamber check and charge: the hand on the handle is on screen while it pulls | hand_l screen [-0.28, -0.87] at 0.47 s | not seen | FAIL |
| 8 | Elbow below the shoulder, elbow bend 5 to 150, wrist within 30 of the forearm | idle: right ok, left wrist 33 (mended to ok on 2026-10-10); check and charge: both ok | right grip wrist 104, support wrist 48, handle 64, mag 55 (reported, not enforced) | FAIL |
| 9 | Zero clipping seen from the eye, every frame | the shipped clips were mended to 0 | 0 on 594 frames | PASS |
| 10 | Every hand has a target each action; the palm faces the held part | by construction in the hand-made clips | holds on marks by preset, fingers curl to contact | PASS (by design, not measured here) |

8 of 10 fail. The one cause behind 1 to 7: fakepose's idle is "the aim with a pull" of 14 cm down, 6 cm right and
10 degrees of pitch (the preset `idle_pull`), which puts the gun out of the view. The game's rest hold keeps the bore
parallel to the view with the rear sight 4 cm under the eye line, and the check and charge roll the gun 60 degrees in
place. Rule 8 fails because fakepose reports anatomy and does not enforce it (the owner, 2026-10-23: "just the way
the market does it"); the bar was built under the anatomy walls, so meeting it needs the walls back in fakepose.
That is a conflict between two decisions and is flagged to the owner before any change.

## Run 2, 2026-10-26: joint limits in the IK, the rest hold from the bar, the roll about the bore

The owner (2026-10-25): "go with the joint limits, then measure the AR15 again, then apply the fix list." Built:
the elbow chosen on its IK circle where the wrist bends least (under the shoulder, inside its hinge); the hand turned
on its palm's normal when no elbow keeps the wrist inside (at most 25 degrees, the hand stays on the mark); the
support hold slid back along the bore to the arm's reach at rest; `idle_pull` set to the bar's rest hold; the check
and charge roll 60 degrees about the bore line over the grip (the first try rolled about the grip and threw the
rear sight 13 cm left: the game's handle moves 1 cm); a loading view that only rolls for magazine rifles; the ten
rules measured on every eye-checked frame and judged in `hands.json` `pose_rules`.

| # | Rule | Game AR-15 | fakepose AR15, run 2 | Result |
|---|---|---|---|---|
| 1 | bore parallel at rest | 0 / 0 / 0 | 0 / 0 / 0 | PASS |
| 2 | rear sight at rest | [3.8, 13.1, -4.4] | [3.8, 13.1, -4.4] | PASS |
| 3 | muzzle near the centre | [0.09, -0.19] | [0.05, -0.26] | PASS |
| 4 | cover 10 to 20 % | 11 to 19 % | rest 7.2 %, aim 10.7 %, check 5 %, equip and run 0 | FAIL |
| 5 | support hand on screen at rest | yes | [-0.03, -0.73] | PASS |
| 6 | check and charge: roll 60, port to the eye | port 65 % visible | roll 60 about the bore, port 94 to 100 % visible, rear sight moves 5.5 cm left, 3 cm down (game: 1 cm, 3 cm) | PASS |
| 7 | the pulling hand on screen | yes | 23 to 34 % of the frames | FAIL |
| 8 | wrist 30, elbow 5 to 150, under the shoulder | kept | holds: grip 29.5, support 25.1 (slid 5 cm), handle 6.4, assist 28.5; rest and aim, walk, fire, reload_empty: at most 30.7; check and charge: right wrist 48 while rolled, reload: left 41.6, run 42, check_mag 35 | FAIL (rest passes; the rolled poses fail) |
| 9 | zero clipping seen | 0 | 7 frames left after the fix (check 6: the left ring finger at 1.5 s, reload_empty 1) | FAIL |
| 10 | targets and palms | yes | yes | PASS |

6 of 10 pass (was 2). What the numbers say about the rest: the right wrist at 48 in the rolled check is the gun's
roll turning the grip hand 60 degrees with it; a real shooter lets the gun roll in the hand or turns the forearm,
and the hold does neither yet. The cover stays at 7 % with the pose matched to the bar's numbers: the difference is
the arms' bulk and the model, not the gun's place; the bar's cover number carries the pack's thick sleeves.

## What fakepose must change to meet the bar

1. `idle_pull`: replace 14 down / 6 right / -4 back / pitch -10 with the bar's rest hold: the rear sight at [4, 13, -4]
   cm in the view, bore parallel (pitch 0). Measured, not guessed: solve the gun's move so the rear sight lands there.
2. Check and charge: roll the gun 60 degrees in place (the port toward the eye), no raise, no pitch; verify the port
   disc at least 60 % visible and the pulling hand on screen.
3. Reload: keep rule 4 (cover 10 to 20 %) as the check instead of the "lower third" load view; the gun may roll, it
   does not leave the view.
4. Rule 8: enforce the wrist 30 and the elbow rules in the hold solver (the arms reach the mark by moving the elbow
   and the gun, not the wrist), once the owner settles the conflict above.
5. Every run reports the ten rules' numbers for the gun, and the Gun Kit result sheet shows them.

## How to validate

- The game bar: `blender -b --factory-startup -P measure_ar_game.py -- <project> out.json` (the script is kept in
  `docs/validate/measure_ar_game.py`); it prints the gun's angles, the marks' screen places, the port's facing and
  visibility, the anatomy and the cover for the idle and five times through the check and the charge.
- fakepose: the eye pictures' cover and centre (`docs/validate/cover.py` over `hands/fakepose_eye/*.png`), the
  `hold_report` arm angles, `clip_report` clipping.
- Pictures: `K:\Projects\Claude\cc\report\ar15_bar_vs_fakepose.png` (the game's idle, check and charge beside
  fakepose's, same views).
