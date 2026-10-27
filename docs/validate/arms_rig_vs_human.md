# The arms rig against a real arm (2026-10-27)

The owner: "check for me if the current arm model has the real human perimeter". Rig: the Gun Kit arms (Saved/PoseLab/ar_slim/Arms.fbx), measured in Blender (docs/validate/measure_arms.py). Human: ANSUR II men, 50th percentile (docs/validate/human_arm_ansur2.json).

| Measure | Rig, cm | Human, cm (source) | Rig against human |
|---|---|---|---|
| upper arm (shoulder joint to elbow joint, bone) | 27.8 | shoulder-elbow length 36.3 minus about 3.5 from the acromion to the joint = about 32.8 | -5.0 cm (-15 %) |
| forearm (elbow joint to wrist, bone) | 27.2 | radiale-stylion 26.7 | +0.6 cm (+2 %) |
| hand length (wrist to the middle finger's bone tail, 18.1; the skin adds about 1) | 19.1 | hand length 19.3 | -0.2 cm (-1 %) |
| hand breadth (knuckle centres; the skin adds about 1.5) | 8.6 | hand breadth 8.8 | -0.2 cm (-3 %) |
| upper arm girth (skin, at the middle, relaxed) | 34.8 | biceps circumference flexed 35.7 (relaxed about 33) | +1.8 cm (+6 %) |
| forearm girth (skin, at the middle) | 26.4 | forearm circumference flexed 31.0 (relaxed about 29) | -2.6 cm (-9 %) |

Finger segments (bone, cm): thumb 4.4 / 3.1 / 3.1, index 3.8 / 2.4 / 2.4, middle 4.8 / 2.3 / 2.3, ring 4.7 / 2.1 / 2.1, pinky 3.7 / 1.9 / 1.9. A real index runs about 4.5 / 2.5 / 2.0 (proximal, middle, distal phalanx, Buryanov 2010): the rig's end joints are equal to its middle ones, so the fingertips sit about 0.4 cm long and the knuckle segment 0.7 cm short.

What it means: the upper arm is about 5 cm (15 %) short of a man's; the hand length, the breadth, the forearm and the upper arm girth are at human size (a first read of 15.9 cm for the right hand was my measure's fault: the bone's tail, not its matrix times its length); the forearm is 2.6 cm slim. A gun built to its true length meets an arm that reaches 5 cm less than a real one (the upper arm): the support hand slides back 14 to 17 cm along the handguard (slid_back_cm in every run) and the wrist bends to reach the grip. The owner's reading is right.