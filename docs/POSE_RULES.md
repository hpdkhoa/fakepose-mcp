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
| 11 | The hand gate (the owner, 2026-10-26): every hold's digits touch their part (tip within glove + 0.3 cm), none inside the mesh from any side, none twisted, the thumb on the gun, wrist within 30, elbow 5 to 150 and under the shoulder; the gate fixes what it can and reports FAIL otherwise | the hand-made holds touch and wrap | measured at every grasp (fakepose `hold_gate`), judged by Gun Kit rule 11 | 2026-10-26, first entry: AR15 grip FAIL (thumb 0.77 cm off, middle 0.44), handguard FAIL (index 1.09, middle 1.32, ring 1.87, pinky 1.63), bolt catch PASS, handle FAIL (thumb 4.36 off), magazine FAIL (fingers 1.2 to 1.6 off, thumb 0.95 inside); M16A2 grip FAIL (middle 0.79, ring 0.79, thumb 0.33 inside), handguard FAIL (0.75 to 3.53 off, index and thumb 0.78 inside), catch PASS, handle FAIL (thumb 1.87, index 0.50 off, three fingers 1.45 inside), magazine FAIL. The cause behind most: the eye mend sets the whole hand back up to 3 cm after the digits closed, so they end 0.4 to 1.9 cm off; the digits inside should be opened one by one instead. The handle pinch and the magazine cup need authored holds. | FAIL |

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

## Run 6, 2026-10-26: the handle pinch from the bar, the transit set-back

The owner (2026-10-26): "continue optimize". Built: the charging-handle pinch captured from the game's charge clip
at the pull (the left knuckle nearest the handle: 0.82 s, 5.4 cm; the hand 14.6 cm left of the gun's centre line,
pinching the handle's left wing beside the receiver), the bar's fingers kept (a pinch finds nothing to close on); a
hand in transit may be set back up to 8 cm when the eye sees it clip (the two empty-reload frames were a transit
capped at 4 cm, 2.5 cm deep); captured holds may carry a kind.

| # | Rule | Game AR-15 | fakepose AR15, run 6 | Result |
|---|---|---|---|---|
| 1 to 3, 5, 6, 10 | | | as run 5 | PASS |
| 4 | cover 10 to 20 % | 11 to 19 % | aim 8.3, idle 5.9, check 4.4 (least per clip) | FAIL |
| 7 | pulling hand on screen | on screen in the approach (charge 0.47 s), off screen at the pull's end (0.93 s: the hand 3.7 cm ahead of the eye, 19 cm under) | on screen 19 to 24 % of the frames; at the pull [-7.0, 0.4, -21.9], as the game's | FAIL as written; the bar itself has the hand off screen at the pull |
| 8 | joints | kept | every gun clip: left wrist 3 to 30, left elbow 17 to 121, right wrist 12 to 23, elbows 2 cm under the shoulder; handle hold wrist 2, elbow 121 | PASS |
| 9 | zero clipping | 0 | 0 on 1,178 frames | PASS |

8 of 10. The two left: the cover (the arms sit at the bar's stations; the pack's sleeves and model fill the game's
view), and rule 7, whose bar value came from the approach, not the pull: to re-measure on the game's clip before it
counts.

## Run 7, 2026-10-26: rule 7 re-measured, the support slips in a sway

Rule 7's bar re-measured on the game's own clips (Pose Lab, `docs/validate/measure_ar_hand_on.py`): the left hand is
on screen on 44 % of the check frames and 58 % of the charge frames, not throughout; the rule now asks for those
shares within 0.05. A sway that takes the support hold past the arm's reach (the walk's bob) slips the hand back
along the handguard for that frame by the shortfall, instead of locking the elbow straight (a margin from the
clips' sway over-slid the hold: elbow 78, the hand under the view). AR15: 8 of 10, 0 clipping on 1,178 frames,
left elbow at least 17 on every gun clip (walk 36, idle 39), left wrist at most 30, right wrist at most 23. Left:
cover (6 %) and rule 7 (19 to 24 % against the game's 44 and 58).

## Run 8, 2026-10-26: the hold mended once against the eye

Found: the eye's frame-by-frame fix was moving a resting hand off its hold on most frames (the M16A2 idle: 143 of
181; the AR15 magazine check: 93), and the arm straightened to follow; that was every locked elbow left. Built: a
hold is mended once against the eye's rule at the hold (set back up to 3 cm, the digits closed again); a hand the
fix still moves slips back along the bore until its elbow bends. M16A2 idle: 24 frames moved (was 143), walk 3
(was 20); left elbow at least 15 in the idle, walk, fire and run (was 2.2), left wrist at most 17 there.

| Gun | Rules | Left |
|---|---|---|
| AR15 | 8 of 10, 0 clipping on 1,178 frames | cover 6 %; rule 7 (19 to 24 % against 44 and 58) |
| M16A2 | 7 of 10 on the resting clips (walk, run, fire); 5 of 10 on the working clips | port 53 % visible under the carry handle; the first 0.2 s of the charge and the check (the hand leaving the support: elbow locked); left wrist 33 in the empty reload; 9 clipping frames (aim 7, check 1, magazine check 1); cover 5 to 11 % |

## Run 9, 2026-10-26: a hold touches its part, from any side

The owner (2026-10-26, a side view of the M16A2 check): "I see finger twisted and clipping, also hand not touch
charger, I don't think market work has this false physics works." Cause: the handle pinch captured from the game
copied the pack gun's finger turns and its hand-to-handle offset (the T wing 14.6 cm off centre), so on the M16A2
the fingers landed inside the carry handle and nothing touched the handle; the eye-only clipping rule did not see
the side. Built: a captured hold keeps the hand's place only (digits start open, close to contact in their planes:
no twist); a pinch or pull reaches until its index tip touches the part (the M16A2 handle: 1.25 cm, gap 0.09 cm);
any digit the gun's mesh says is inside at a hold is opened until clear and closed again (the M16A2 handle: the ring
finger 1.31 cm in, then 0.24). This extends rule 9 at the hold from "seen from the eye" to "measured on the mesh,
any side"; the frame-by-frame rule stays the eye's. Left: the pinch touches but does not wrap the T (thumb and
index closing on the wing from both sides), to author.

## Run 10, 2026-10-26: the mend order and the two authored holds, through the gate

The owner: "fix the mend order first then author the two holds." Built: the hold mend opens the digit that is
inside and moves the hand only when the palm is; the gate moves a palm or cup hold in along the palm's facing until
the palm touches, then closes the digits; the charging-handle pinch authored as a preset (the hand over the
receiver's rear, palm down, the pinch's middle on the T's left wing, reaching the part); the magazine cup kept as
authored and pushed in by the gate.

| Hold | AR15 | M16A2 |
|---|---|---|
| Grip | FAIL: middle 0.75 cm off (was thumb 0.77 and middle 0.44) | FAIL: middle, ring 0.79 off; thumb 0.33 inside (unchanged) |
| Handguard | FAIL: thumb 0.61, ring 1.49, pinky 0.61 off; index 0.27 inside (the palm moved in 3.0 cm) | FAIL: 0.75 to 3.53 off; index and thumb 0.78 inside (unchanged: its eye mend still moved the hand, the palm was in the seen parts) |
| Bolt catch | PASS | PASS |
| Handle pinch (authored) | FAIL: the index reached (0.6 cm), the thumb 4.11 off after a full swing | FAIL: index 1.26 off; index, middle, thumb 1.12 inside |
| Magazine cup | FAIL: fingers 1.2 to 2.0 off, thumb 0.95 inside | FAIL: fingers 1.0 to 2.5 off, thumb 0.96 inside (the palm moved in 2.75 cm) |

Rule 11 FAIL on both; the other rules as run 9 (AR15 8 of 10, M16A2 6 of 10), 0 clipping seen. What the numbers
say: a palm pushed to the surface still leaves the fingers 1 to 2 cm off where the part is thin (the rail, the
magazine): the fingers need to wrap round, which the curl to a fist target on a hinge does not reach; the thumb on
the grip and the magazine sits inside and only opens. The pinch's thumb cannot reach under the T from a palm-down
hand on these models. These holds need authoring on each gun's own surfaces, hold by hold, with the gate as judge.

## Run 11, 2026-10-26: per-gun authored holds and the wrap curl, decoupled from Pose Lab

The owner: "build both, keep fakepose decoupled from poselab." Built: `presets/guns/<gun>.json`, a per-gun overlay
on any hold (a shift in cm along the gun's axes, finger rules, the curl mode); a wrap curl (joints one after
another, each at its own touch, the thumb swung toward the gun first); the gate's palm-in (the hand moved in a
quarter cm at a time while any used finger closes to its target without touching and nothing is inside). Measured:
the wrap curl twisted the index end joint 32 degrees and reached no better, so it is off by default; the first
shifts (guessed directions) made the pinch and the cup worse and were removed; the palm-in moved the AR15 handguard
hand 1.75 cm and little else, since a thumb already inside stops it.

| Hold | AR15 | M16A2 |
|---|---|---|
| Grip | FAIL: thumb 0.45, middle 0.85, ring 0.81 off | FAIL: middle, ring 0.79 off; thumb 0.33 inside |
| Handguard | FAIL: middle 0.58, ring 1.38, pinky 1.04 off; index 0.29 inside | FAIL: 0.75 to 3.53 off; index, thumb 0.78 inside |
| Bolt catch | PASS | PASS |
| Handle pinch | FAIL: thumb 4.11 off | FAIL: index 1.26 off; index, middle, thumb 1.12 inside |
| Magazine cup | FAIL: fingers 1.2 to 1.4 off; thumb 0.95 inside | FAIL: fingers 1.2 to 2.8 off; thumb 0.97 inside |

Rule 11 FAIL on both. The gate holds: it refuses every one of these as a hold and says by how much. The market
way's levers inside fakepose (a preset's place, a curl, a push in) do not close these gaps on their own; the holds
need authoring per gun, one at a time, each attempt judged by the gate with its picture: the overlay file is the
place for that authoring.

## The M16A2 on the AR-15 bar, 2026-10-26

The captures now carry the hand against the mark point and a family (`ar_gas`): any gun of the family with the same
marks takes them on its own grip, support and handle. The M16A2 (the TM-built model with the carry handle), two runs
(the clips split under the 10 minute rule), the per-part judgements joined:

| # | Rule | fakepose M16A2 | Result |
|---|---|---|---|
| 1 to 3, 5, 10 | rest pose, support hand, targets | as the bar: rear sight [3.8, 13.1, -4.4], support hand at rest [-0.8, 31.9, -17.2] | PASS |
| 4 | cover | 5 to 11 % | FAIL |
| 6 | port to the eye at roll 60 | port 53 % visible (the carry handle and the deflector over the M16A2's port; the AR15's flat top gave 94 %) | FAIL, 7 % under |
| 7 | pulling hand on screen | 17 to 19 % | FAIL as written |
| 8 | joints | holds: grip wrist 19, support wrist 15 elbow 66 (slid 14 cm), handle from the capture; clips: left wrist 5 to 33 (33 in the empty reload at 1.95 s), left elbow straight for a moment in the walk (0.58 s) and the charge (1.1 s), right wrist 11 to 23 | FAIL on three moments |
| 9 | clipping | 1 frame (check, 0.22 s) on 1,178 | FAIL by one frame |

5 to 6 of 10. The same shape as the AR15 before its last two runs: the holds sit at the bar; a few transit moments
and the port's cover under the carry handle remain.

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

### Run 12 (2026-10-26): the AR15 grip through the gate

| Hold | Gate | Digits (min skin gap, cm; + off, - inside) | Joints |
|---|---|---|---|
| AR15 r:grip (idle) | PASS | thumb -0.09, index -0.02, middle 0.26, ring 0.00, pinky 0.01 | wrist 12.1, elbow 114.6, 26.3 cm under |

Authored in `presets/guns/AR15.json`: the capture's finger turns kept (`fingers_fit` true: the pack gun's grip is the
AR15's), the hand 3.5 cm back and 3.5 cm down. Found by the gate's new `way_out_cm` (the deepest skin point of an
inside digit and its way to the surface, in the gun's axes): the thumb's root sat in the lower receiver's rear bottom
at gun [0.0, -14.7, -3.3], way out back 0.9 and down 0.9. Attempts that failed: up 1.0 (thumb 1.45 inside), down 1.0
(0.66), right 1.2 (2.09: the thumb crosses the backstrap from behind). The thumb swing now stops when any segment's
skin touches; the thumb clear swings its deepest point out. Picture: `K:/Projects/Claude/cc/report/tune/AR15_grip_gate_before_after.png`.

### Run 13 (2026-10-26): the AR15's four holds through the gate

| Hold (clip) | Gate | Digits (min skin gap, cm) | Joints | What it took |
|---|---|---|---|---|
| r:grip (idle) | PASS | thumb -0.09, index -0.02, middle 0.26, ring 0.00, pinky 0.01 | wrist 12, elbow 115 | run 12 |
| l:support (idle) | PASS | thumb -0.02, index 0.01, middle 0.10, ring 0.11, pinky 0.10 | wrist 16, elbow 69 | overlay up 0.5; the gate untwists a joint bent out of its plane (index end joint 26 to 0) |
| l:handle (charge) | PASS | thumb -0.13, index 0.38 (middle 1.41, ring 3.57, pinky 6.1 not used) | wrist 9, elbow 131 | preset reshaped: fingers forward, palm down, the fingers start hooked (`start_curl`), the index hooks the latch; the thumb lies on the stock's top at gun y -27, 11 cm behind the latch (any gun surface counts for the gate; a thumb on the receiver would be closer to a real charge) |
| l:mag_grab (reload) | PASS | thumb -0.12, index 0.12, middle 0.11, ring 0.11, pinky -0.01 | wrist 2, elbow 83, 2.3 cm under | the gate's own fixes (thumb cleared 60, pinky opened 80) |

The idle: 0 clipping frames of 181 from the eye. The M16A2 at the AR15's grip shift (back 3.5, down 3.5) fails
badly (ring and pinky 2.7 to 3.0 inside on the grip's right face, thumb 2.3): its own authoring starts from zero.
Pictures: `K:/Projects/Claude/cc/report/tune/AR15_{grip,support,handle}_gate_before_after.png`.

### Run 14 (2026-10-27): the full finger rule; the AR15's four holds again

The owner (2026-10-26, a picture of the M16A2 grip from the left): "why finger always bend backward? I remember I
have a rule that not bend like that". The rule stood (no hyperextended or twisted finger); the gate's code kept only
the "twisted" lines of Pose Lab's finger report and dropped "bent backward" and "curled past its range". Runs 11 to
13 were judged under that filter: their PASS lines are void. Under the full rule the captured grip read knuckles
curled 125 to 140 and end joints 143 to 153: the game rig's finger turns copied onto Gun Kit's arms (ar_slim) do not
carry. Fixed: the bar's fingers captured as joint angles (`curls_deg`, the thumb base's spread and palm angle) and
set with Pose Lab's measured setters; every curl and opening sets measured angles inside their ranges; a joint bent
backward is straightened by the gate; a segment pushed deeper by the joints before it stops the close.

| Hold (clip) | Gate | Digits (min skin gap, cm) | Finger faults | Joints |
|---|---|---|---|---|
| AR15 r:grip (idle), back 3.5 down 5.0 | PASS | thumb -0.08, index -0.17, middle 0.03, ring 0.10, pinky -0.02 | none | wrist 9, elbow 112, 26 cm under |
| AR15 l:support (idle), up 0.5 | PASS | thumb -0.15, index 0.24, middle -0.11, ring 0.06, pinky 0.14 | none | wrist 16, elbow 69 |
| AR15 l:handle (charge) | PASS | thumb -0.15, index -0.18 | none | wrist 11, elbow 128 |
| AR15 l:mag_grab (reload), thumb_base 25/5 | PASS | thumb -0.20, index 0.12, middle 0.15, ring -0.30, pinky 0.09 | none | wrist 2, elbow 83 |

The idle: 0 clipping frames of 181 from the eye. The bar's grip angles as captured: index -15/89/-5, middle 83/74/88,
ring 81/71/88, pinky 65/64/88, thumb knuckle 58, end 88, base spread 46, palm 50; read back on Gun Kit's arms to the
degree. The M16A2's four holds: see run 15.

### Run 15 (2026-10-27): the M16A2's four holds under the full finger rule

| Hold (clip) | Gate | Digits (min skin gap, cm) | Finger faults | Joints |
|---|---|---|---|---|
| M16A2 r:grip (idle), back 2.5 down 4.2 right 0.4 | PASS | thumb -0.10, index 0.50, middle 0.13, ring 0.12, pinky 0.10 | none | wrist 8, elbow 114, 26 cm under |
| M16A2 l:support (idle) | PASS | thumb -0.17, index 0.06, middle 0.12, ring 0.02, pinky 0.09 | none | wrist 15, elbow 66 |
| M16A2 l:handle (charge) | PASS | thumb -0.09, index 0.01 | none | wrist 18, elbow 126 |
| M16A2 l:mag_grab (reload), up 1.5 left 1.0 | PASS | thumb -0.38, index 0.08, middle 0.12, ring 0.11, pinky 0.06 | none | wrist 3, elbow 85 |

The cup's thumb base setter now lowers each reading on its own axis (it had stalled at palm 29 asked 5); the AR15 cup
re-judged with it: PASS (thumb -0.07, palm 5). Eight of eight holds pass on the two guns. Pictures:
`K:/Projects/Claude/cc/report/tune/{AR15,M16A2}_grip_full_rule.png`, `M16A2_cup_full_rule.png`.

### Run 16 (2026-10-27): the full AR15 clip run against the hold-only runs

The full run (every clip) judged the handle pinch FAIL (thumb 0.83 cm inside) where the hold-only run passed: the
pinch started from the bolt catch's hand (the clip before it), not the open hand. Fixed: every fakepose hold starts
from the open hand (the market way: a hold does not depend on the hold before it). The fifth hold, the bolt catch
(reload_empty), authored through the gate: the thumb beside the index in the palm's plane, the fingers forward and
up (straight up bent the wrist 34 to 37): PASS, thumb 0.14, index -0.08, middle -0.27, ring 0.03, pinky 0.19; wrist
10, elbow 91. The full run is being repeated; its rule 11 line is the number that counts.

### Run 17 (2026-10-27): the full clip runs, both guns

| Gun | Rule 11 (every hold's gate) | Clipping seen from the eye | Rules passed | Open |
|---|---|---|---|---|
| AR15 | PASS: grip, handguard, bolt catch, charging handle, magazine cup | 0 frames of 1,178 (12 clips) | 9 of 11 | 4 cover 3 to 9 % (bar 10 to 20); 7 pulling hand on screen 19 / 30 % (bar 44 / 58) |
| M16A2 | PASS: the same five holds | 0 frames of 997 | 7 of 11 | 4 cover 4 to 8 %; 6 port 53 % under the carry handle (bar 60); 7 hand on screen 16 / 18 %; 8 the left elbow locks to 2.2 degrees in one clip (wall: 5 to 150); the clip is not named by the report yet |

Fixes on the way: the M16A2 handle pinch failed in the full run (the thumb's tip 2 cm inside the stock, the base
swing could not lift it): the gate now opens such a thumb to straight and lays it back; the handle preset's thumb
starts straight beside the index (thumb_base 30/10). The owner's rule holds: a hold is not shown without its gate
numbers; rule 8's elbow lock on the M16A2 is a wall break reported, not tuned through.

### Run 18 (2026-10-27): the M24 on the current engine; the owner's shoulder-back move

The M24 (two runs under the 10 minute rule, 11 clips, 1,045 frames): 0 clipping frames seen from the eye; rules 8 of
11 (open: 6 port, 7 hand on screen, 11). Rule 11 FAIL: the grip's pinky 1.32 cm off and its wrist 34.5 to 36.3; the
support's thumb 1.46 cm inside. The video's M24 clip (2026-10-25) was made before any of this and showed the
support hand through the gun; this run shows 0 seen clipping but the holds still fail the gate.

The owner's idea ("move the shoulder back so the arm is extend then the wrist can be flatten"), built as
`shoulder_back` in the IK (the collarbone turned so the shoulder moves back along the view, at most
SHOULDER_BACK_MAX_CM from the template's shoulder, counted from the template each frame; the limit 4 cm is mine
until the owner sets it; job option `shoulder_back_max_cm`), measured on the M24 grip at the idle:

| Shoulder back, cm | Wrist bend | Elbow bend | Gate |
|---|---|---|---|
| 0 | 34.5 | 120.6 | FAIL: pinky 1.32 off, wrist |
| 4.2 (limit 4) | 36.3 | 113.1 | FAIL: same |
| 8.2 (limit 8) | 35.9 | 105.0 | FAIL: same |

The arm extends as the owner said (the elbow opens 16 degrees over 8 cm) but the wrist does not flatten: the wrist
bend here is set by the hand's authored facing on the M24's raked grip against the forearm's line, not by the reach.
The move is kept (it does what it says for the elbow) and reported. Picture:
`K:/Projects/Claude/cc/report/tune/M24_grip_shoulder_scan.png`.

The arms rig against a real arm (`docs/validate/arms_rig_vs_human.md`, ANSUR II men): the upper arm bone 27.8 cm
against about 32.8 (5 cm, 15 % short); the forearm 27.2 against 26.7; the hand 19.1 against 19.3; the breadth 8.6
against 8.8; the upper arm girth 34.8 against about 33 relaxed; the forearm girth 26.4 against about 29 (slim). The
owner's reading holds: the arm reaches 5 cm less than a man's, which is why the support hand slides back 14 to 17
cm on every rifle.

### Run 19 (2026-10-27): the upper arm lengthened to a man's; the AR15 regression

The owner: "upper arm will need to lengthen" and "keep your 4cm limit for shoulder and start the work". Each upper
arm bone of the Gun Kit arms copy (Saved/PoseLab/ar_slim/Arms.fbx) lengthened 27.8 to 32.8 cm (ANSUR II men, 50th:
36.3 from the acromion minus about 3.5 to the joint) by `Tools/blender/long_arms.py` (a copy in
`docs/validate/long_arms.py`): the elbow joint and all below it carried out along the upper arm's line, the upper
arm's skin stretched along that line; the old file kept as `Arms.pre_long_upperarm.fbx`. The skeleton edit lives in
`bone_edits.json` ("upperarm": 1.1811) and Pose Lab's loader applies it to the idle clip's skeleton (lab.py
`_edit_skeleton`), the same way as the finger and palm edits. Check through the loader: both upper arms 32.8, the
forearms 27.25 unchanged, the elbow skin's centre against the joint 1.85 to 1.98 cm (right) and 1.26 to 1.40
(left): the skin follows the bones. Pictures: `K:/Projects/Claude/cc/report/arms/arms_upperarm_before_after.png`
(the file at rest) and `arms_upperarm_loader_before_after.png` (the idle pose through the loader).

A fresh rig measures its hands anew (the measure cache keys on the arms files); that path reached the object's
samples before any region call and crashed the first run (fixed in poselab contactlab `_object_now`). The full run
then ran out of the 10 minute budget at 5 clips (the fresh measure's cost), so the AR15 ran as two hand parts
(drive_split, now merging the rule tables).

AR15, 12 clips, 1,178 frames, run 17 (short arm) against run 19 (long arm):

| Rule | Run 17 | Run 19 |
|---|---|---|
| 4 cover | 3.4 to 8.6 % | 3.4 to 8.4 % (idle 5.4 to 6.4): FAIL as before |
| 7 pulling hand on screen | check 0.19, charge 0.30 | check 0.21, charge 0.34: FAIL as before |
| 8 joints, every frame | r wrist 13.6, l wrist 30.0 | r wrist 25.0, l wrist 29.9 (elbows 102 to 119 r, 24 to 137 l): PASS |
| 9 clipping seen | 0 of 1,178 | 0 of 1,178 |
| 11 gate | 5 of 5 PASS | 5 of 5 PASS |
| support slid back along the handguard | 17.0 cm | 11.0 cm |
| grip wrist / elbow | 9.0 / 111.6 | 20.6 / 118.8 |
| support wrist / elbow | 16.2 / 68.8 | 22.2 / 65.5 |
| catch, handle, mag wrist | 10.0, 3.2, 2.6 | 0.7, 14.9, 8.0 |

The owner's reading holds: with the arm at a man's length the support hand reaches 6 cm further along the
handguard (17 to 11 cm short of the mark). The grip wrist grew 9 to 20.6 (inside the 30 wall): the longer bone puts
the elbow further under (26 to 32 cm) and the forearm's line meets the authored hand facing at a bigger angle; the
hold is authored for the short arm and can be re-tuned. The shoulder-back move did not fire on any AR15 hold
(shoulder_back_cm 0). Open as before: rules 4 and 7. The shoulder limit stays 4 cm (the owner, 2026-10-27).

### Run 20 (2026-10-27): the M24 on the long arm; its support authored; its grip meets the wrist wall

The M24 on the long arm (two parts, 10 clips, 864 frames): 0 clipping seen; the preset holds fail the gate as
before (grip pinky 1.32 off, wrist 48.1 in the fire clip with the shoulder back 4.2; support thumb 1.41 inside);
rule 8 breaks in the clips (right wrist 32.5, left wrist 59.0, elbows at 2.1 degrees: the bolt-work clips with the
unauthored holds); rule 6 port 0 % (roll 5 and 30, not 60).

The support authored: the forend is 5.4 cm wide with a flat bottom 4.1 cm under the bore (measured); the preset's
thumb folded under the flat bottom 1 cm right of centre. The hand 3.0 cm left (presets/guns/M24SWS.json): PASS,
thumb -0.15 index 0.08 middle 0.20 ring 0.11 pinky 0.09, wrist 10.7, elbow 63.9, slid back 9.0 cm (the long arm:
11 cm as the preset sat). Picture: `K:/Projects/Claude/cc/report/tune/M24_support_before_after.png`.

The grip (picture `M24_grip_scan.png`, the fire clip):

| Placement | Wrist | Elbow | Digits | Gate |
|---|---|---|---|---|
| A preset as is, shoulder back 4.2 | 48.1 | 120 | pinky 1.32 off | FAIL |
| B fingers square across the wrist line (the stock's wrist runs ~35 deg from vertical, measured) | 64.6 | 121 | ring 1.32, pinky 0.76 off | FAIL |
| C as A, shoulder allowed 16 (went 14.8) | 36.3 | 96.5 | pinky 1.32 off | FAIL |
| D hand 1.0 up, palm seated on first contact, hand turned 2.5 | 28.4 | 128 | four touch, pinky 2.12 off; the fingers lie along the stock's side | FAIL |

Why: the shoulder-to-hand distance at the M24 grip is 30 cm (the AR15's 30.9), so the elbow sits 25.6 cm off the
shoulder-hand line and the forearm comes in 70 degrees off that line whatever the elbow's swing; the AR15's grip
hangs 14.3 cm under the eye (its hand points 34 degrees off the line, wrist 20.6), the M24's only 7.8 (18 degrees
off, wrist 48). A forearm within 30 of a hand that wraps the wrist needs the shoulder-to-hand distance near 45 cm
(d 30: 70 deg off; 35: 62; 40: 54; 45: 46; 50: 37), 15 cm more than the body has; the collarbone gave 14.8 cm and
the wrist still 36. The hand turned on its palm reaches 28 only with the fingers along the stock's side (D), which
is not a grip. Engine changes in this run (mine, told): a gun's tuning may set a hold's facing and seat
(palm_into, fingers_toward, offset_cm, standoff_cm, contact); the gate's palm-in seats the hand on its first finger
contact instead of chasing a finger that cannot reach (the pinky under the short wrist drove the palm 2 cm into the
stock). Open for the owner: the M24 grip against the wrist wall.

Regression of the palm-seating change, AR15 (two parts, 12 clips, 1,178 frames): the same numbers as run 19 to the
decimal (rule 11 five of five, 0 clipping, grip wrist 20.6, support slid back 11.0, rules 4 and 7 open): the AR15's
holds never used the palm-in. The M16A2 regression follows.

M16A2 on the long arm with the palm-seating change (two parts, 12 clips, 1,178 frames): rule 11 five of five PASS,
0 clipping, and rule 8 now PASS (the left elbow's least bend 11.4 degrees; run 17's lock at 2.2 is gone with the
longer upper arm); rule 6 port 53 % as before; rules 4 (4 to 11 %) and 7 (0.21 / 0.32) open as before. Holds: grip
wrist 19.4, support 19.9 (slid back 9.0), catch 2.0, handle 3.4, cup 8.2.
