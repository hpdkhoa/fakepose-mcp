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
