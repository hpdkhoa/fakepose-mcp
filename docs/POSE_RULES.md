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

## Run 3, 2026-10-26: the bar's body and holds

The owner (2026-10-26): "keep the cover band, fix the rolled wrist and the clipping first." Measured on the way: the
game's right shoulder sits 11 cm over the eye (the first-person template's body; view cm: right shoulder
[4.1, -16.8, 10.8], left [-28.9, -12.4, -11.8]); fakepose's anatomical body (my choice of 2026-10-24) put it 16 cm
under. With the shoulder 27 cm lower no elbow kept the wrist inside, and the hand turns that run 2 used had pushed
fingers into the grip (a contact test on the turn now stops that). Built: the rifle family keeps the template body
(pistols keep the anatomical one, the approved M1911A1); the bar's own right grip and left support captured from the
game's idle as fakepose holds for the AR15 (`presets/captured/AR15_*.json`); the AR check's forward-assist tap dropped
(not in the bar; it bent the left wrist 114); the support slide checks the aim too and takes the least violation;
captured fingers close to contact by the authored rules; cover is not judged on equip, holster and run (the gun
leaves the view by design); Gun Kit's `hands()` reads its report from the folder it wrote (a stale-report bug).

| # | Rule | Game AR-15 | fakepose AR15, run 3 | Result |
|---|---|---|---|---|
| 1 | bore parallel at rest | 0 / 0 / 0 | 0 / 0 / 0 | PASS |
| 2 | rear sight at rest | [3.8, 13.1, -4.4] | [3.8, 13.1, -4.4] | PASS |
| 3 | muzzle near the centre | [0.09, -0.19] | [0.05, -0.26] | PASS |
| 4 | cover 10 to 20 % | 11 to 19 % | aim 15.7, idle 9.7, fire 9.6, reload_empty 9.7, walk 8.4, reload 7.8, check_mag 7.1, charge 6.8, check 6.5 (least per clip) | FAIL (idle and fire 0.3 under) |
| 5 | support hand on screen at rest | yes | [-0.21, -0.84] | PASS |
| 6 | check and charge: roll 60, port to the eye | port 65 % | port 94 to 100 % | PASS |
| 7 | the pulling hand on screen | yes | 19 to 24 % of the frames | FAIL |
| 8 | wrist 30, elbow 5 to 150, under the shoulder | kept | right: 10 at the hold, 8 rolled 60, 25 at most (was 48); left: support 14 (slid 8 cm) but its elbow 2.2 (locked straight, the game's is 27), 62 in the transit to the handle, catch 48 | FAIL (right passes; left elbow and transits fail) |
| 9 | zero clipping seen | 0 | 1 frame (reload_empty) | FAIL |
| 10 | targets and palms | yes | yes | PASS |

6 of 10 pass; the right arm meets the bar on every clip. What remains is the left arm: the template body's left
shoulder sits 29 cm left of the eye, so the support hand is at the arm's full reach (the bar itself has that elbow
at 27 degrees), and the moves to the handle and the catch bend the wrist in transit. The cover in idle and fire sits
0.3 % under the band. The captured support's fingers stay open beside the AR15's slimmer rail (the closure from the
pack's finger turns reads "already touching"): to mend.

## Run 4, 2026-10-26: the game camera, the support within reach, the fingers closed

The owner (2026-10-26): "fix the left arm and the open fingers next"; then "use 1, rifles use the game camera".
Found: fakepose's eye (the head bone with the template's camera offset) stood 8.9 cm ahead and 2.8 cm under the
game camera the bar was measured with, so the gun placed 13.1 cm from it stood 9 cm further forward than the bar and
the support arm ran out of reach (55.0 cm from the shoulder, the arm's length). Built: rifles take the game camera
(Gun Kit's eye; pistols keep the head-bone eye); the support hold slides back until the arm reaches it with a bent
elbow at the aim and at rest (14 cm on the AR15); a hold captured from another gun keeps its placement only, so the
digits start open and close to contact by the authored rules.

| # | Rule | Game AR-15 | fakepose AR15, run 4 | Result |
|---|---|---|---|---|
| 1 to 3 | rest: bore, rear sight, muzzle | | as the bar | PASS |
| 4 | cover 10 to 20 % | 11 to 19 % | aim 8.5, idle 7.5, fire 7.4, check 6.1 | FAIL |
| 5 | support hand on screen | yes | [-0.02, -0.73] | PASS |
| 6 | check and charge roll, port | port 65 % | port 94 to 100 % | PASS |
| 7 | pulling hand on screen | yes | 21 to 33 % of frames | FAIL |
| 8 | joints | kept | holds: grip wrist 15, elbow 110; support wrist 16, elbow 58 (the game: 30 and 27), hand at [-4.6, 28.9, -9.6] (the game [1.2, 31.8, -10.5]); clips: right wrist 24 at most; left 15 to 23 in idle, walk, fire, run; 44 in the move to the handle (charge 0.25 s), 32 to 34 in the check and the empty reload; left elbow straight for one moment of the idle sway (2.1 s) and in the handle moves | FAIL (the holds pass; the transits fail) |
| 9 | zero clipping | 0 | 5 frames (charge 2, check 2 at the pull, aim 1) | FAIL |
| 10 | targets and palms | yes | yes | PASS |

6 of 10. Both holds now sit within the bar's numbers. What remains is in the moves between holds (the support hand
to the handle and back: wrist 44, elbow straight, the 4 clipping frames at the pull) and the cover, which fell to
7.5 % as the support arm sits further from the eye than before.

## Run 5, 2026-10-26: the thumb on the gun, the handle move, the capture against the bore

The owner (2026-10-26): "continue, and one more thing to change is the thumb of support hand open too big, thumb
need to hold/close to the gun." Built: the thumb closes by its base (swung toward the gun until its pad touches,
then the joints curl: 15 degrees, pad at the surface); a hand in transit relaxes its wrist to 30 off the forearm and
the arc's lift is cut where it takes the hand past the arm's reach; the support slide keeps 2 cm for the idle's
sway; the capture measures both guns' points against their bore lines (the pack gun's frame origin lies 3 cm under
its bore, which had put the hand 3 cm low). The clips that take the hands off the gun (equip, holster, run) are not
judged on cover or joints: the bar has no such clips.

| # | Rule | Game AR-15 | fakepose AR15, run 5 | Result |
|---|---|---|---|---|
| 1 to 3 | rest: bore, rear sight, muzzle | | as the bar | PASS |
| 4 | cover 10 to 20 % | 11 to 19 % | aim 8.3, idle 5.9, check 5.7 | FAIL |
| 5 | support hand on screen | yes | [-0.02, -0.92] | PASS |
| 6 | check and charge roll, port | port 65 % | 94 to 100 % | PASS |
| 7 | pulling hand on screen | charge yes; the game's own check has it off screen at the pull | 19 to 24 % of frames | FAIL |
| 8 | joints | kept | support hand at rest [-0.8, 31.0, -16.1] (the game [1.2, 31.8, -10.5]), shoulder as the game's; support hold wrist 16, elbow 69; grip wrist 15; every gun clip: left wrist 3 to 30, left elbow 17 to 39 at least, right wrist 12 to 23, elbows 2 cm under the shoulder | PASS on the gun clips (equip and holster excluded) |
| 9 | zero clipping | 0 | 2 frames (reload_empty) | FAIL |
| 10 | targets and palms | yes | yes | PASS |

7 of 10 on the gun clips. Both arms now stay inside the joint rules through every hold and every move on the gun.
Left: the cover (the arms sit at the bar's stations, and still fill 6 % against the game's 15 %: the pack's sleeves
and model bulk), the pulling hand's station at the charging handle (the authored pinch sits lower than the game's),
and 2 clipping frames in the empty reload.

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
