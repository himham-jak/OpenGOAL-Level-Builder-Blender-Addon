

# OpenGOAL-Level-Builder-Blender-Addon

This is an addon for Blender 2.92 (may be compatible with other versions) developed specifically to build custom levels for the current (v0.1.20) distribution of <u>[OpenGoal](https://github.com/open-goal/jak-project/)</u>.

## How to install

Download `LevelBuilder.py`. Open Blender and navigate to `Edit > Preferences > Add-ons > Install` and select the file you downloaded. Check the box next to its name to enable the addon.

## How to build a level

The creation of the level geometry is up to you. This is not a guide on using Blender.

Consider importing level geometry from a different game or using <u>[`test-zone2.glb`](https://github.com/open-goal/jak-project/blob/master/custom_levels/test-zone2.glb)</u> if you can't build it yourself.

After the level geometry is created, parent all the geometry to one object that you don't want to export. I recommend an empty.

Press `n` in the 3d viewport to bring up the properties panel. There should be a panel called `Level Builder`.

Fill in the details for your level. They each have specific formats you must follow. The addon will let you know if you make a mistake.

The details with an asterisk are not currently implemented to export. This mostly stems from a lack of understanding about the game itself, not Blender or python. Someone with more information about the game itself can help implement these.

When you're finished entering the details, you can select from several options how much to export. Before exporting, I recommend opening Blender's system console under `Window > Toggle System Console` so you can watch the process and ensure no mistakes have been made.

## What's been implemented so far?

- The addon accesses all necessary files within the OpenGOAL distribution to create a basic level.
- All of these files are automatically updated upon export so that the level can be played.
- New files associated with your level are created as well.
- Files are checked before creating so as not to override any existing. Eventually, the user will be able to force overwrite.
- Any files edited are backed up.
- Playtesting boots the game in debug mode, opens the REPL and links the two together.
- Actors are added as a mesh.
- Actors are assigned custom properties when they're added (i.e. "game task", "bounding sphere", etc).

## Known Issues

-  Two steps in playtesting are not currently automated, as noted in the FAQ. When i automate reloading the `*level-load-list*`, the command doesn't pass with quotes, even if I use escape characters, so it fails. When I automate `(bg-custom)`, the `(lt)` step doesn't complete and so it fails. Someone with more knowledge of the REPL can likely fix these issues.
- `.gbl` files can sometimes crash the game. This may be remedied by ensuring the cycles renderer is enabled before exporting, but I'm not certain. They also cannot be above a certain size, that size being unclear.
- The code is somewhat ugly. It's well commented, but several sections need to be moved to different modules to improve readability. Most notably, the vertex data for the actor mesh, but also the document templates for file creation and other tasks.
- The export README file doesn't say anything. I'm not sure if it needs to exist.
- I probably don't properly unregister everything I need to
- The Edit Mode version of the panel is underutilized at best and program crashing at worst.

## What needs to be done in the future?

- The last two steps in playtesting need to be automated.
- `.glb` files need to be fully tested.
- Modules need to be implemented.
- Write/remove the export README.
- Flesh out the `unregister()` function
- More actor types need to be added.

- Actor info exporting needs to be enabled.
- A much deeper understanding of actor properties, that I don't have, needs to be implemented.
- Exporting level info needs to check if game.gp and level-info.gc are already modified so it doesn't insert lines twice.
- Selecting multiple actors should allow you to change all of their properties (except name) at once
- Actors should be defined in one class with an attribute that distiguishes the types. At the moment they're the same class and one actor for all actor types. This pushes the boundaries of my knowledge of classes.

## FAQ

#### What do actors do?

At the moment, nothing. They're a proof of concept soon to be implemented properly.

#### Why does my playtest start but doesn't enter the level?

The final two steps in the playtesting a custom level are not yet automated.

After building and connecting, the `*level-load-list*` needs to be updated to include your level. This is done by running `(ml \"goal_src/jak1/engine/level/level-info.gc\")` in goalc.

The level itself is then loaded with `(bg-custom '<YOUR-LEVEL-NAME-vis)` as written in the `custom_levels` <u>[README](https://github.com/open-goal/jak-project/blob/master/custom_levels/README.md)</u> that comes with OpenGOAL.

If you keep Blender's system console open when exporting, it will walk you through these final steps.
