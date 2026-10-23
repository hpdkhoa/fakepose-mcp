# fakepose-mcp

First-person hands on a gun, posed the way games pose them.

A hold is an authored preset placed on a mark (a socket) of the gun, not solved from anatomy. Each finger closes until
it touches. The arms reach the hands by two-bone IK. The one rule is the market's: no clipping the first-person camera
can see. Anatomy (wrist, elbow, finger angles) is reported, not enforced.

It runs inside [Weapon Lab](https://github.com/hpdkhoa/weaponlab-mcp)'s Gun Kit hands step, which keys and writes the
clips. Gun Kit's job option `pose_engine` picks the engine: `"fakepose"` (the default) or `"poselab"`.

## What it does, in order

1. **The body at rest.** Pelvis, spine, neck, head and collarbones take the rig's rest pose. A first-person template's
   idle can lift a shoulder above the head; at rest the shoulders sit below the eye, as on a person.
2. **The eye at the head.** The camera sits on the head bone with the offset of Unreal Engine 5.6's first-person
   template (5.89 cm ahead, 2.8 cm down).
3. **The gun at aim.** The sights are measured on the gun's mesh (rays down its middle plane). The gun is turned so the
   sight line runs along the view with no cant, and moved so the sight line passes through the eye. Its distance is
   the nearest at which both arms reach their holds.
4. **The holds from presets.** The firing grip is a captured, approved hand-to-gun pose. The support grip is that grip
   mirrored across the gun's middle plane, moved forward and down, then set down onto the gun. The other holds
   (magazine grab, overhand rack, press check) are authored by palm facing and finger direction in the gun's axes.
5. **Curl to contact.** Each digit turns toward a fist in equal steps. A segment that touches the gun stops its joint and
   the ones before it; the stop is found to a tenth of a step by halving.
6. **The clips.** Gun Kit's actions drive every frame: the gun's moves, the parts (slide, magazine, release), the hands
   blending between holds, a part riding a hand.
7. **The eye's check.** A ray from the eye through every pixel of the 90 degree, 16:9 view. A pixel clips when the first
   surface it meets is the gun inside the skin, or the skin inside the gun, deeper than the glove. Every 6th frame of
   every clip is checked, and a picture of each clip's start, middle and end is drawn.

## Result on the M1911A1 (the lab model)

All 11 clips written in about 4.5 minutes: idle, walk, run, fire, equip, holster, reload, reload_empty, charge,
check_chamber, check_mag. Clipping seen from the eye: 0 pixels on every checked frame and every pictured frame.
See [docs/results](docs/results).

## Tools (MCP)

| Tool | What it does |
|---|---|
| `list_presets` | The preset families and their holds, with sources; the captured grips. |
| `show_preset` | One hold in full. |
| `set_preset` | Adds or replaces an authored hold. |
| `run_hands` | Runs Gun Kit's hands step with fakepose on a gun's facts file. |
| `hold_report` | The last run's holds: curls, what stopped them, arm angles, set-down distance. |
| `clip_report` | The last run's clips: the eye's clipping per clip and the pictures. |

## Install

```bash
pip install -e .
```

Needs Blender 5.2 (headless) and Weapon Lab with Pose Lab installed; Gun Kit finds fakepose through the installed
package.

## Limits

- Pistol presets only so far. A rifle family is next.
- The eye sits 9.3 cm from the game's own camera place (`Shared.json`: the camera at the head bone's height). The game
  is not changed; set its arms offset to match if the clips should line up exactly in game.
- The idle is the aim pose for now; a lowered idle is the aim pulled down, still to make.
- Hands set down onto the gun may stand a little off it; hidden contact is allowed and listed, not fixed.
- On the magazine grab and the overhand rack the index finger closes to a fist without reaching the gun.

## Plan and decisions

[docs/PLAN.md](docs/PLAN.md) keeps the owner's words next to the design.
