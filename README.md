# OpenGOAL-Level-Builder-Blender-Addon

This is an addon for Blender developed specifically to build custom levels for the current (v0.1.20) distribution of OpenGOAL.

## How to install

Download `LevelBuilder.py`. Open Blender and navigate to `Edit> Preferences> Addons> Install` and select the file you downloaded. Check the box to enable the addon.

## How to build a level

The creation of the level geometry is up to you. This is not a guide on using Blender.

Consider importing level geometry from a different game or using the `test-zone2.glb` if you can't build it yourself.

After the level geometry is created, parent all the geometry to one object that you don't want to export. Try an empty.

Press `n` in the 3d viewport to bring up the properties panel. There should be a panel called `Level Builder`.

Fill in the details for your level. They each have specific formats you must follow. The addon will let you know if you make a mistake.

The details with an asterisk are not currently implemented to export. This mostly stems from a lack of understanding about the game itself, not Blender or python. Someone with more information about the game itself can help implement these.

When you're finished entering the details, you can select from several options how much to export. Before exporting, I recommend opening Blender's command line in the `Window` tab so you can watch the process and ensure no mistakes have been made.

## What's been implemented so far?

- The addon accesses all necessary files within the OpenGOAL distribution to create a basic level.
- All of these files are automatically updated upon export so that the level can be played.
- New files associated with your level are created as well.
- Playtesting boots the game in debug mode, opens the REPL and connects the two together.
- Actors are added as a mesh

## What needs to be done in the future?

- Actors need to be assigned custom properties when they're added
- More actor types need to be added
- Actor info exporting needs to be enabled
- A much deeper understanding of actor properties, that I don't have, needs to be implemented.

## FAQ

#### What do actors do?

At the moment, nothing. They're a proof of concept soon to be implemented properly.

#### Why does my playtest start but doesn't enter the level?

The final step in the opening of a custom level is not yet automated.

After building and connecting, the level itself is loaded with `(bg-build)` as written in the `custom_levels` README that comes with OpenGOAL. When I automate this step, the previous step doesn't complete. Someone with more knowledge of the REPL can likely fix this.

If you keep the Blender command line open when exporting, it will walk you through this final step.

## Known Issues

- Playtesting, automatically or manually, fails due to what appears to be a failure of the REPL to reload `*level-load-list*`. This is probably an easy fix and eventually fixes itself given enough time.

- `.gbl` files can sometimes crash the game. This may be remedied by ensuring the cycles renderer is enabled before exporting, but I'm not certain.

- The code is somewhat ugly. It's well commented, but several sections need to be moved to different files to improve readability. Most notably, the vertex data for the actor mesh, but also the document templates for file creation.

- The exported level README file doesn't say anything. I'm not sure if it needs to exist.
