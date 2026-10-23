# fakepose-mcp plan (2026-10-23)

## The owner's words

- "now create a fakepose-mcp, this one will do the hand hold like the current game market is doing, and my flow will
  have the toggle to switch between poselab and fakepose, default until poselab is ready will be fakepose."
- "the result must be automatic done without clipping and for first person view with every actions I needed, also
  interact or attach on the gun part to complete the animation like my previous AR-15 work"
- "use b) Zero clipping seen from the first-person camera, start on M1911A1 as my lab model outpu"
- Earlier, for the aim: "we start with the aim position first, then the idle position is just the aim position with a
  pull so can work on it later."

## The design, next to the words

| The owner's words | The design |
|---|---|
| "the hand hold like the current game market is doing" | A hold is an authored preset placed on a socket of the gun (a mark), not solved from anatomy. The fingers close until they touch the gun (curl to contact). The arm reaches the hand by two-bone IK with a pole. |
| "my flow will have the toggle ... default ... fakepose" | Gun Kit job option `pose_engine`: `"fakepose"` (default) or `"poselab"`. Both read the same gun facts, marks and actions. |
| "automatic" | No hand tuning: presets are data, the fingers' stops and the aim place are computed. |
| "Zero clipping seen from the first-person camera" | The check: rays from the eye through every pixel of the 90 degree, 16:9 view; a pixel clips when the surface it sees is the gun inside the hand's skin, or the skin inside the gun past its give. The target is 0 pixels in every frame. Clipping the eye cannot see is measured and listed, not fixed. |
| "first person view" | The aim place: the gun's sight line through the eye, the bore along the view; its distance from the eye set so the firing arm is extended to its elbow limit (5 degrees, the arm rules: "arms fully extended", FM 3-23.35 isosceles). |
| "with every actions I needed" | Gun Kit's actions for the gun (M1911A1: idle, walk, run, fire, equip, holster, reload, reload_empty, charge, check_chamber, check_mag), each frame posed from the presets. |
| "interact or attach on the gun part ... like my previous AR-15 work" | Gun Kit's part tracks: a hand rides a part (slide, release) or a part rides a hand (the magazine); the presets give each hold on those parts. |
| "start on M1911A1" | Pistol presets first. |

## The owner's answer on anatomy (2026-10-23)

"just the way the market does it": fakepose enforces no anatomy walls. Its one rule is zero clipping seen from the
first-person camera. Wrist, elbow and finger angles are reported, not enforced. Pose Lab keeps its walls.

## Presets (data, src/fakepose_mcp/data/presets/pistol.json)

Each preset: the mark, the grasp kind (palm, cup, pinch), how the hand sits on the mark, each finger's rule
(straight, curl to contact, or a set curl), and its source. The firing grip is the hand-to-gun pose of the owner's
approved experiment (2026-10-23: "hand position is a hold"), stored as an authored grip.

## Phases

1. The aim place, the firing grip, curl to contact, the eye clip check; pictures (eye view + three views).
2. The support hand and every hold the clips need; the clips with the eye clip check per frame.
3. The MCP server (presets, run, check) and the Gun Kit toggle default.
