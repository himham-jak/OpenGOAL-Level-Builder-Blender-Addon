

# OpenGOAL-Level-Builder-Blender-Addon

README v1.1.0

This is an addon for Blender 2.92 (may be compatible with other versions) developed specifically to build custom levels for the current (v0.1.21) distribution of <u>[OpenGoal](https://github.com/open-goal/jak-project/)</u> on Windows 10. It has not been tested with the launcher distribution.

## How to install

Download `LevelBuilder.py`. Open Blender and navigate to `Edit > Preferences > Add-ons > Install` and select the file you downloaded. Check the box next to its name to enable the addon.

If you have an older version of the addon, you need to remove it from the same menu and install the new one.

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
- Any files edited are checked for content and backed up before editing.
- Playtesting boots `(bg-custom)` in an open REPL (goalc) as long as its already connected to the game (gk).
- Actors are added as a mesh.
- Actors are assigned custom properties when they're added (i.e. "game task", "bounding sphere radius", etc).
- Live input validation of all necessary fields

## Known Issues

- `.gbl` files can sometimes crash the game. This may be remedied by ensuring the cycles renderer is enabled before exporting, but I'm not certain. They also cannot be above a certain size, that size being unclear.
- The code is somewhat ugly. It's well commented, but several sections need to be moved to different modules to improve readability. Most notably, the vertex data for the actor mesh, but also the document templates for file creation and other tasks.
- I probably don't properly unregister everything I need to.
- The Edit Mode version of the panel is underutilized at best and program crashing at worst.

## What needs to be done in the future?

- `.glb` files need to be fully tested. Might add a renderer test before export.
- Modules need to be implemented. (Splitting data and functions off into separate files for readability and futureproofing)
- Flesh out the `unregister()` function.
- More actor types need to be added.
- Actor info exporting needs to be enabled.
- A much deeper understanding of actor properties, that I don't have, needs to be implemented.
- Selecting multiple actors should allow you to change all of their properties (except name) at once
- Actors should be defined in one class with an attribute that distiguishes the types. At the moment they're the same class and one actor for all actor types. This pushes the boundaries of my knowledge of classes.
- UI to add manual properties to actors
- Actor translations need to be properly scaled
- Potentially an overlay of the game geometry to allow precise positioning of both geometry and actors.
- String formatting should be overhauled
- Loading zone support
- Path implementation

## FAQ

#### What do actors do?

At the moment, nothing. They're a proof of concept soon to be implemented properly.

#### Why does my playtest start but doesn't enter the level?

When you don't have the REPL and game open before playtesting, the addon tries to do this for you. It probably won't do it effectively. Playtesting is only the final step in the custom level implementation process. Have the appropriate steps taken before you try it.

#### Can you add _____?

This tool implements automations for mods that are possible manually. If you can do it manually, send me your process and I will do my best to implement it. If it can't be done manually, this tool won't somehow be able do it.
