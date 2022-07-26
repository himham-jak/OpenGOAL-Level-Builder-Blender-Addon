# eventually: separate out different pieces of the addon into modules
# https://b3d.interplanety.org/en/creating-multifile-add-on-for-blender/
# moduleNames = ['customUI', 'addActor', 'fileTemplates', 'meshData', 'iconData']
# create new python files for adding a new actor to these modules

# ------------------------------------------------------------------------
#    Addon Info
# ------------------------------------------------------------------------
bl_info = {
    "name": "OpenGOAL Custom Level Builder",
    "description": "modified from https://gist.github.com/p2or/2947b1aa89141caae182526a8fc2bc5a and https://github.com/blender/blender/blob/master/release/scripts/templates_py/addon_add_object.py",
    "author": "himham",
    "version": (1, 0, 1),
    "blender": (2, 92, 0),
    "location": "3D View > Level Info",
    "warning": "",
    "category": "Development"
    }

# ------------------------------------------------------------------------
#    Includes
# ------------------------------------------------------------------------
import bpy, bmesh, os, re, shutil, math, fileinput
from bpy.app.handlers import persistent
from bpy.props import (StringProperty,
                       BoolProperty,
                       IntProperty,
                       FloatProperty,
                       FloatVectorProperty,
                       EnumProperty,
                       PointerProperty,
                       )
from bpy.types import (Panel,
                       Menu,
                       Operator,
                       PropertyGroup,
                       )
from bpy.utils import previews
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector


# ------------------------------------------------------------------------
#    Scene Properties
# ------------------------------------------------------------------------

class MyProperties(PropertyGroup):
    
    level_title: StringProperty(
        name="Level Title",
        description="The name of your custom level.\nOnly letters and dashes are allowed, case will be ignored.\nDefault: my-level",
        default="my-level",
        maxlen=1024,
        )
        
    level_nickname: StringProperty(
        name="Level Nickname",
        description="The nickname of your custom level.\nThree letters, case will be ignored.\nDefault: lvl",
        default="lvl",
        maxlen=3,
        )
        
    anchor: StringProperty(
        name="Anchor",
        description="The Parent of all your level geometry. The anchor itself will not export.\nSuggestion: Create a new empty, Parent all your geometry to it. Select the empty here.",
        maxlen=1024,
        )
        
    level_location: FloatVectorProperty(
        name = "Level Location",
        description="The location in 3d space to place your custom level.\nDefault: 0,0,0",
        default=(0.0, 0.0, 0.0), 
        min= 0.0,
        max = 1.0
        )
        
    level_rotation: FloatVectorProperty(
        name = "Level Rotation",
        description="The quaternion rotation in 3d space to place your custom level.\nDefault: 0,0,0,1",
        default=(0.0, 0.0, 0.0), # Blender doesn't want me to make a 4d vector
        min= 0.0,
        max = 1.0
        )
        
    custom_levels_path: StringProperty(
        name = "Custom Levels Path",
        description="The path to /custom_levels/ in the OpenGOAL distribution",
        default="",
        maxlen=1024,
        subtype='DIR_PATH'
        )
        
    should_export_level_info: BoolProperty(
        name="Level Info",
        description="Check if you'd like the level info to be included when you export",
        default = True
        )
        
    should_export_actor_info: BoolProperty(
        name="Actor Info",
        description="Check if you'd like the actor info to be included when you export",
        default = True
        )
        
    should_export_geometry: BoolProperty(
        name="Level Geometry",
        description="Check if you'd like the level geometry to be included when you export",
        default = True
        )
        
    should_playtest_level: BoolProperty(
        name="Playtest Level",
        description="Check if you'd like to launch the level immediately after export",
        default = True
        )
        
    actor_name: StringProperty(
        name="Actor Name",
        description="The name of your object (actor).\nOnly lowercase letters and dashes are allowed.\nDefault: my-level",
        default="my-actor",
        maxlen=1024,
        )
        
    actor_type: EnumProperty(
        name="Actor Type",
        description="Apply Data to attribute.",
        items=[ ('collectable', '', ''),
                ('eco-collectable', '', ''),
                ('eco', '', ''),
                ('eco-yellow', 'Yellow Eco', ''),
                ('eco-red', 'Red Eco', ''),
                ('eco-blue', 'Blue Eco', ''),
                ('health', 'Green Eco', ''),
                ('eco-pill', 'Green Eco Pill', ''),
                ('money', 'Precursor Orb', ''),
                ('fuel-cell', 'Power Cell', ''),
                ('buzzer', 'Scout Fly', ''),
                ('ecovalve', 'Eco Valve', ''),
                ('vent', '', ''),
                ('ventyellow', 'Yellow Eco Vent', ''),
                ('ventred', 'Red Eco Vent', ''),
                ('ventblue', 'Blue Eco Vent', ''),
                ('ecovent', 'Eco Vent', ''),
                ('vent-wait-for-touch', '', ''),
                ('vent-pickup', '', ''),
                ('vent-standard-event-handler', '', ''),
                ('vent-blocked', '', ''),
                ('ecovalve-init-by-other', '', ''),
                ('*ecovalve-sg*', '', ''),
                ('ecovalve-idle', '', ''),
                ('*eco-pill-count*', '', ''),
                ('birth-pickup-at-point', '', ''),
                ('*buzzer-sg*', '', ''),
                ('fuel-cell-pick-anim', '', ''),
                ('fuel-cell-clone-anim', '', ''),
                ('*fuel-cell-tune-pos*', '', ''),
                ('*fuel-cell-sg*', '', ''),
                ('othercam-init-by-other', '', ''),
                ('fuel-cell-animate', '', ''),
                ('*money-sg*', '', ''),
                ('add-blue-motion', '', ''),
                ('check-blue-suck', '', ''),
                ('initialize-eco-by-other', '', ''),
                ('add-blue-shake', '', ''),
                ('money-init-by-other', '', ''),
                ('money-init-by-other-no-bob', '', ''),
                ('fuel-cell-init-by-other', '', ''),
                ('fuel-cell-init-as-clone', '', ''),
                ('buzzer-init-by-other', '', ''),
                ('crate-post', '', ''),
                ('*crate-iron-sg*', '', ''),
                ('*crate-steel-sg*', '', ''),
                ('*crate-darkeco-sg*', '', ''),
                ('*crate-barrel-sg*', '', ''),
                ('*crate-bucket-sg*', '', ''),
                ('*crate-wood-sg*', '', ''),
                ('*CRATE-bank*', '', ''),
                ('crate-standard-event-handler', '', ''),
                ('crate-init-by-other', '', ''),
                ('crate-bank', '', ''),
                ('crate', '', ''), # eco-info [item,quantity] item: 1=yellow 2=red 3=green 4=cell 5=orb 6=blue 7=pill 8=fly 9+=empty, enames=crate/iron,steel,bucket,barrel
                ('barrel', '', ''),
                ('bucket', '', ''),
                ('crate-buzzer', 'Scout Fly Box', ''),
                ('pickup-spawner', '', ''),
                ('double-lurker', 'Double Lurker', ''),
                ('evilbro', 'Gol', ''),
                ('evilsis', 'Maya', ''),
                ('explorer', 'Explorer', ''),
                ('farmer', 'Farmer', ''),
                ('balloon', 'Balloon', ''),
                ('spike', 'Spike', ''),
                ('crate-darkeco-cluster', 'Cluster of Dark Eco Crates', ''),
                ('flutflut', 'Flut Flut', ''),
                ('geologist', 'Geologist', ''),
                ('hopper', 'Hopper', ''),
                ('junglesnake', 'Jungle Snake', ''),
                ('kermit', 'Kermit', ''),
                ('lurkercrab', 'Lurker Crab', ''),
                ('lurkerpuppy', 'Lurker Puppy', ''),
                ('lurkerworm', 'Lurker Worm', ''),
                ('mother-spider', 'Mother Spider', ''),
                ('muse', 'Muse', ''),
                ('swamp-rat', 'Swamp Rat', ''),
                ('yeti', 'Yeti', ''),
                ('yakow', 'Yakow', ''),
                ('orbit-plat', 'Orbiting Platform', ''),
                ('steam-cap', 'Steam Cap Platform', ''),
                ('citb-plat', 'Citadel B Platform', ''),
                ('citb-button', 'Citadel B Button', ''),
                ('citb-drop-plat', 'Citadel B Drop Platform', ''),
                ('wall-plat', 'Wall Platform', ''),
                ('wedge-plat', 'Wedge Platform', ''),
                ('wedge-plat-outer', 'Wedge Platform Outer', ''),
                ('puffer', 'Puffer', ''),
                ('babak', 'Gorilla', ''),
                ('babak-with-cannon', 'Gorilla with Cannon', ''),
                ('seaweed', 'Seaweed', ''),
                ('ropebridge', 'Rope Bridge', ''),
               ]
        )
        
    actor_location: FloatVectorProperty(
        name = "Actor Location",
        description="The location in 3d space to place your object (actor).\nDefault: -21.6238,20.0496,17.1191",
        default=(-21.6238, 20.0496, 17.1191), 
        min= 0.0,
        max = 25.0
        )
        
    actor_rotation: FloatVectorProperty(
        name = "Actor Rotation",
        description="The quaternion rotation in 3d space to place your object (actor.\nDefault: 0,0,0,1",
        default=(0.0, 0.0, 0.0), # Blender doesn't want me to make a 4d vector
        min= 0.0,
        max = 1.0
        )
        
    # In the future, it would be nice to select the level name and automatically receive the game_task number
    game_task: IntProperty( 
        name = "Game Task",
        description="Correct me if I'm wrong\nThe level number associated with the actor\nDefault: 0",
        default = 0,
        min = 0,
        max = 100
        )
        
    bounding_sphere: FloatVectorProperty(
        name = "Bounding Sphere",
        description="I'm not entirely sure what this is.\nDefault: -21.6238, 19.3496, 17.1191, 10",
        default=(0.0, 0.0, 0.0), 
        min= 0.0,
        max = 25.0
        )
        
        
    
    # unused properties

    my_bool: BoolProperty(
        name="Boolean",
        description="A bool property",
        default = False
        )

    my_float: FloatProperty(
        name = "Float Value",
        description = "A float property",
        default = 23.7,
        min = 0.01,
        max = 30.0
        )

# ------------------------------------------------------------------------
#    Operators
# ------------------------------------------------------------------------
    
class WM_OT_Export(Operator):
    bl_label = "Export"
    bl_idname = "wm.export"
    bl_description = "Exports the Level Info, Level Geometry, and Actor Info.\nAfter exporting, be sure to read the README"

    def execute(self, context):
        scene = context.scene
        mytool = scene.my_tool
        
        # validate level info inputs
        # eventually want validation to live update while you're typing
        if not bool(re.match("^[A-Za-z-]*$", mytool.level_title)): # should have only letters and dashes
            show_message("Level Title can only contain letters and dashes","Error","ERROR")
            return {'CANCELLED'}
        
        if not bool(re.match("^[A-Za-z]*$", mytool.level_nickname)): # should have only letters
            show_message("Level Nickname can only contain letters","Error","ERROR")
            return {'CANCELLED'}
        
        if (mytool.anchor == "") & mytool.should_export_geometry:
            show_message("Anchor cannot be empty if exporting geometry","Error","ERROR")
            return {'CANCELLED'}
        
        if mytool.custom_levels_path == "": # can't be empty
            show_message("Custom Levels Path cannot be empty","Error","ERROR")
            return {'CANCELLED'}

        # create values needed to make files
        longtitle = mytool.level_title.lower()
        title = re.sub(r'[^\w\s]', '', mytool.level_title)[0:8] # create 8 digit alpha-only short title
        nick = mytool.level_nickname.lower()
        newpath = mytool.custom_levels_path+longtitle+"\\"
        
        # be extra
        print("\n   ---Beginning Export Process---\n")
        
        # keep track of what task we're on
        task_count = (mytool.should_export_level_info or mytool.should_export_actor_info)+mytool.should_export_geometry+mytool.should_playtest_level
        current_task = 1
        
        # update level info and actor info if needed
        current_task = update_files(task_count, current_task, mytool.should_export_level_info, mytool.should_export_actor_info, newpath, nick, longtitle, title)
        
        # export the geometry
        # may need to update renderer to cycles before exporting, just in case. make sure to notify user.
        if mytool.should_export_geometry:
            print("Task ("+str(current_task)+"/"+str(task_count)+")")
            current_task += 1
            export_geometry(context, mytool.anchor, newpath, longtitle)
        
        # open the level in game
        if mytool.should_playtest_level:
            print("Task ("+str(current_task)+"/"+str(task_count)+")")
            current_task += 1
            playtest_level(longtitle, newpath)
        
        return {'FINISHED'}
    
# ------------------------------------------------------------------------
#    Functions
# ------------------------------------------------------------------------
    
def show_message(message, title = "Message", icon = "INFO"):
    
    def draw(self, context):
        self.layout.label(text = message)
        
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)

def update_files(task_count, current_task, should_export_level_info, should_export_actor_info, newpath, nick, longtitle, title):
        
        print("Task ("+str(current_task)+"/"+str(task_count)+")")
        current_task += 1
        print("Updating the necessary files.\n")
        
        # make the new folder
        if not os.path.exists(newpath):
            os.mkdir(newpath)
            print("-Directory created.")
        
        # make paths for game.gp and level-info.gc
        gppath = os.path.dirname(os.path.dirname(os.path.dirname(newpath)))+"\\goal_src\\jak1\\"
        gcpath = gppath+"engine\\level\\"
        
        gd = [
            '("',
            nick,
            '.DGO"\n',
            '  ("static-screen.o" "static-screen")\n',
            '  ("',
            longtitle,
            '.go" "',
            longtitle,
            '")\n',
            '  )'
            ]
            
        jsonc = [
            '{\n',
            '  "long_name": "',
            longtitle,
            '",\n',
            '  "iso_name": "',
            title.upper(),
            '",\n',
            '  "nickname": "',
            nick.upper(),
            '", // 3 char name, all uppercase\n\n',
            '  "gltf_file": "custom_levels/',
            longtitle,
            '/',
            longtitle,
            '.glb",\n',
            '  "automatic_wall_detection": true,\n',
            '  "automatic_wall_angle": 45.0,\n',
            '  "actors" : [\n',
            '    {\n',
            '      "trans": [-21.6238, 20.0496, 17.1191], // translation\n',
            '      "etype": "fuel-cell",  // actor type\n',
            '      "game_task": 0, // associated game task (for powercells, etc)\n',
            '      "quat" : [0, 0, 0, 1], // quaternion\n',
            '      "bsphere": [-21.6238, 19.3496, 17.1191, 10], // bounding sphere\n',
            '      "lump": {\n',
            '        "name":"test-fuel-cell"\n',
            '      }\n',
            '    },\n\n',
            '    {\n',
            '      "trans": [-15.2818, 15.2461, 17.1360], // translation\n',
            '      "etype": "crate",  // actor type\n',
            '      "game_task": 0, // associated game task (for powercells, etc)\n',
            '      "quat" : [0, 0, 0, 1], // quaternion\n',
            '      "bsphere": [-15.2818, 15.2461, 17.1360, 10], // bounding sphere\n',
            '      "lump": {\n',
            '        "name":"test-crate",\n',
            '        "crate-type":"\'steel",\n',
            '        "eco-info": ["int32", 5, 10]\n',
            '      }\n',
            '    },\n\n',
            '    {\n',
            '      "trans": [-5.4630, 17.4553, 1.6169], // translation\n',
            '      "etype": "eco-yellow",  // actor type\n',
            '      "game_task": 0, // associated game task (for powercells, etc)\n',
            '      "quat" : [0, 0, 0, 1], // quaternion\n',
            '      "bsphere": [-5.4630, 17.4553, 1.6169, 10], // bounding sphere\n',
            '      "lump": {\n',
            '        "name":"test-eco"\n',
            '      }\n',
            '    }\n',
            '  ]\n',
            '}'
            ]
            
        readme = [
            "test line 1\n",
            "test line 2\n",
            "test line 3"
            ]
            
        gc = [
            "\n\n(define ",
            longtitle,
            " (new 'static 'level-load-info\n",
            "                           :index 26\n",
            "                           :name '",
            longtitle,
            "\n                           :visname '",
            longtitle,
            "-vis ;; name + -vis\n",
            "                           :nickname '",
            nick,
            "\n                           :packages '()\n",
            "                           :sound-banks '()\n",
            "                           :music-bank #f\n",
            "                           :ambient-sounds '()\n",
            "                           :mood '*default-mood*\n",
            "                           :mood-func 'update-mood-default\n",
            "                           :ocean #f\n",
            "                           :sky #t\n",
            "                           :continues '((new 'static 'continue-point\n",
            "                                             :name \"",
            longtitle,
            "-start\"\n",
            "                                             :level '",
            longtitle,
            "\n                                             :trans (new 'static 'vector :x 0.0 :y (meters 10.) :z (meters 10.) :w 1.0)\n",
            "                                             :quat (new 'static 'quaternion  :w 1.0)\n",
            "                                             :camera-trans (new 'static 'vector :x 0.0 :y 4096.0 :z 0.0 :w 1.0)\n",
            "                                             :camera-rot (new 'static 'array float 9 1.0 0.0 0.0 0.0 1.0 0.0 0.0 0.0 1.0)\n",
            "                                             :load-commands '()\n",
            "                                             :vis-nick 'none\n",
            "                                             :lev0 '",
            longtitle,
            "\n                                             :disp0 'display\n",
            "                                             :lev1 'village1\n",
            "                                             :disp1 'display\n",
            "                                             ))\n",
            "                           :tasks '()\n",
            "                           :priority 100\n",
            "                           :load-commands '()\n",
            "                           :alt-load-commands '()\n",
            "                           :bsp-mask #xffffffffffffffff\n",
            "                           :bsphere (new 'static 'sphere :w 167772160000.0)\n",
            "                           :bottom-height (meters -20)\n",
            "                           :run-packages '()\n",
            "                           :wait-for-load #t\n",
            "                           )\n",
            "        )\n\n",
            "(cons! *level-load-list* '",
            longtitle,
            ")"
            ]
            
        gp = '\n\n(build-custom-level "'+longtitle+'")\n'+'(custom-level-cgo "'+nick.upper()+'.DGO" "'+longtitle+'/'+title+'.gd")\n'
        
        # create gd
        path = newpath
        filename = title+".gd"
        contents = gd
        if not os.path.exists(path+filename):
            f = open(path+filename, 'w', encoding="utf-8")
            # write the contents
            f.writelines(contents)
            # close the file
            f.close()
            print("-"+title+".gd created.")
        else:
            print("-"+title+".gd already exists, creation skipped.")
            
        # create jsonc
        path = newpath
        filename = longtitle+".jsonc"
        contents = jsonc
        if not os.path.exists(path+filename):
            f = open(path+filename, 'w', encoding="utf-8")
            # write the contents
            f.writelines(contents)
            # close the file
            f.close()
            print("-"+longtitle+".jsonc created.")
        else:
            print("-"+longtitle+".jsonc already exists, creation skipped.")
            
        # create readme
        path = newpath
        filename = "README.MD"
        contents = readme
        if not os.path.exists(path+filename):
            f = open(path+filename, 'w', encoding="utf-8")
            # write the contents
            f.writelines(contents)
            # close the file
            f.close()
            print("-README.MD created.")
        else:
            print("-README.MD already exists, creation skipped.")
        
        # create a backup and append new level to level-info.gc
        path = gcpath
        filename = "level-info.gc"
        backupname = "level-info.bak"
        contents = gc
        shutil.copyfile(path+filename,path+backupname)
        print("-Backup of level-info.gc created")
        f = open(path+filename, 'a', encoding="utf-8")
        # write the contents
        f.writelines(contents)
        # close the file
        f.close()
        print("-level-info.gc updated.")
        
        # create a backup and append new level to game.gp
        path = gppath
        filename = "game.gp"
        backupname = "game.bak"
        contents = gp
        shutil.copyfile(path+filename,path+backupname)
        print("-Backup of game.gp created")
        
        match_string = "testzone.gd\")"
        with open(path+filename, 'r+') as f:
            current = f.readlines()
            if match_string in current[-1]: # this will fail if the levels have to be in order
                current.append(contents)
            else:
                for index, line in enumerate(current):
                    if match_string in line and contents not in current[index + 1]:
                        current.insert(index + 1, contents)
                        break
            f.seek(0)
            f.writelines(current)
            
        print("-game.gp updated.")
        
        print("\n--Done.\n")
        
        return current_task
        
def export_geometry(context, anchor, newpath, longtitle):
        
        print("Exporting geometry.\n")
        
        if not os.path.exists(newpath+longtitle+".glb"):
            bpy.ops.object.select_all(action='DESELECT') # deselect everything, probably not necessary
            bpy.context.scene.objects[anchor].select_set(True) # select the anchor
            bpy.ops.object.select_grouped(type='CHILDREN_RECURSIVE') # select the anchor's children
            bpy.ops.export_scene.gltf( # actually export
                filepath=newpath+longtitle+".glb",
                use_selection=True # export only the selection
            )
            print("-"+longtitle+".glb created.\n")
        else:
            print("-"+longtitle+".glb already exists, creation skipped.\n")
        
        
        print("--Done.\n")
        
def playtest_level(longtitle,newpath):
        
        print("Beginning playtest.\n")
        
        opengoalpath = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(newpath))))
        print(opengoalpath)
        #os.system('''start cmd @cmd /c "cd ..\Games\opengoal-v0.1.19-windows && gk -boot -fakeiso -debug" ''') # open the game in debug mode
        #os.system('''start cmd @cmd /k "cd ..\Games\opengoal-v0.1.19-windows && goalc --startup-cmd "(mi) (lt)"" ''') # open the repl, rebuild, and link to game
        os.system('''start cmd @cmd /c "cd '''+opengoalpath+''' && gk -boot -fakeiso -debug" ''') # open the game in debug mode
        os.system('''start cmd @cmd /k "cd '''+opengoalpath+''' && goalc --startup-cmd "(mi) (lt)"" ''') # open the repl, rebuild, and link to game
        # run (bg-custom 'longtitle-vis) in the repl
        
        print("Message: Sorry, for now you'll have to run (ml \"goal_src/jak1/engine/level/level-info.gc\") and then (bg-custom '"+longtitle+"-vis) in goalc manually.\n")
        
        print("--Done.\n")
        
#delete
class WM_OT_PrintActors(Operator):
    bl_label = "Print"
    bl_idname = "wm.print"

    def execute(self, context):
        #bpy.context.object["MyOwnProperty"] = 7
        #print(bpy.context.object)
        #print(bpy.context.object["MyOwnProperty"])

        return {'FINISHED'}

# ------------------------------------------------------------------------
#    Panel in Object Mode
# ------------------------------------------------------------------------

class OBJECT_PT_LevelInfoPanel(Panel):
    bl_label = "Level Info"
    bl_idname = "OBJECT_PT_level_info_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Level Editing"
    bl_context = "objectmode"

    @classmethod
    def poll(self,context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.my_tool
        

        # set these properties manually
        layout.prop(mytool, "level_title", icon="TEXT") # validate not in list? "training","village1","beach","jungle","jungleb","misty","firecanyon","village2","sunken","sunkenb","swamp","rolling","ogre","village3","snow","maincave","darkcave","robocave","lavatube","citadel","finalboss","intro","demo","title","halfpipe","default-level"
        layout.prop(mytool, "level_nickname", icon="TEXT")
        layout.prop_search(mytool, "anchor", scene, "objects", icon="EMPTY_AXIS")
        layout.prop(mytool, "level_location", text="Level Location*")
        layout.prop(mytool, "level_rotation", text="Level Rotation*")
        layout.prop(mytool, "custom_levels_path")
        layout.prop(mytool, "should_export_level_info")
        layout.prop(mytool, "should_export_actor_info", text="Actor Info*")
        layout.prop(mytool, "should_export_geometry", )
        layout.prop(mytool, "should_playtest_level")
        layout.operator("wm.export")
        layout.label(text="Options with * do not currently export.", icon="ERROR")
        layout.separator()
        
class OBJECT_PT_ActorInfoPanel(Panel):
    bl_label = "Actor Info*"
    bl_idname = "OBJECT_PT_actor_info_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Level Editing"
    bl_context = "objectmode"

    @classmethod
    def poll(self,context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.my_tool
        
        if "Game Task" in bpy.data.objects[bpy.context.object.data.name].keys(): # only check for custom properties on actors, not other objects
            layout.prop(context.active_object, "name", text = "Actor Name")
            layout.prop(mytool, "actor_type") # dummy
            layout.prop(context.active_object, "type")
            
            # these properties auto populate
            layout.prop(context.active_object, "location", text = "Actor Location")
            layout.prop(context.active_object, "rotation_quaternion", text = "Actor Rotation") # this won't display properly unless the object is in quaternion mode, so I force all actors into quat mode when added
        
            # set these properties manually in the panel
            layout.prop(bpy.data.objects[bpy.context.object.data.name], '["Actor Type"]')
            layout.prop(bpy.data.objects[bpy.context.object.data.name], '["Game Task"]')
            layout.prop(bpy.data.objects[bpy.context.object.data.name], '["Bounding Sphere"]')
            #layout.operator("wm.print") # this is a debug button to print all the current actors and their attributes before exporting
        else:
            layout.label(text="Select an actor to see its properties.", icon="ERROR")
        
        layout.separator()
        
# ------------------------------------------------------------------------
#    Panel in Mesh Edit Mode          # At the moment, i don't really use this
# ------------------------------------------------------------------------
            
class EDIT_PT_LevelInfoPanel(Panel):
    bl_label = "Level Info"
    bl_idname = "EDIT_PT_level_info_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Level Editing"
    bl_context = "mesh_edit"

    @classmethod
    def poll(self,context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.my_tool
        

        # set these properties manually
        layout.prop(mytool, "level_title", icon="TEXT") # validate not in list? "training","village1","beach","jungle","jungleb","misty","firecanyon","village2","sunken","sunkenb","swamp","rolling","ogre","village3","snow","maincave","darkcave","robocave","lavatube","citadel","finalboss","intro","demo","title","halfpipe","default-level"
        layout.prop(mytool, "level_nickname", icon="TEXT")
        layout.prop_search(mytool, "anchor", scene, "objects", icon="EMPTY_AXIS")
        layout.prop(mytool, "level_location", text="Level Location*")
        layout.prop(mytool, "level_rotation", text="Level Rotation*")
        layout.prop(mytool, "custom_levels_path")
        layout.prop(mytool, "should_export_level_info")
        layout.prop(mytool, "should_export_actor_info", text="Actor Info*")
        layout.prop(mytool, "should_export_geometry", )
        layout.prop(mytool, "should_playtest_level")
        layout.label(text="Switch to Object Mode to export.", icon="ERROR")
        layout.label(text="Options with * do not currently export.", icon="ERROR")
        layout.separator()
        
class EDIT_PT_ActorInfoPanel(Panel):
    bl_label = "Actor Info*"
    bl_idname = "EDIT_PT_actor_info_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Level Editing"
    bl_context = "mesh_edit"

    @classmethod
    def poll(self,context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.my_tool
        
        if "Game Task" in bpy.data.objects[bpy.context.object.data.name].keys(): # only check for custom properties on actors, not other objects
            layout.prop(context.active_object, "name", text = "Actor Name")
            layout.prop(mytool, "actor_type") # dummy
            layout.prop(context.active_object, "type")
            
            # these properties auto populate
            layout.prop(context.active_object, "location", text = "Actor Location")
            layout.prop(context.active_object, "rotation_quaternion", text = "Actor Rotation") # this won't display properly unless the object is in quaternion mode, so I force all actors into quat mode when added
        
            # set these properties manually in the panel
            layout.prop(bpy.data.objects[bpy.context.object.data.name], '["Actor Type"]')
            layout.prop(bpy.data.objects[bpy.context.object.data.name], '["Game Task"]')
            layout.prop(bpy.data.objects[bpy.context.object.data.name], '["Bounding Sphere"]')
            #layout.operator("wm.print") # this is a debug button to print all the current actors and their attributes before exporting
        else:
            layout.label(text="Select an actor to see its properties.", icon="ERROR")
        
        layout.separator()

# ------------------------------------------------------------------------
#    New Mesh Initialization               # This will be cleaned up with the verts,edges,faces in a separate file for each actor model
# ------------------------------------------------------------------------       

actor_types = [
                ["Precursor Orb","orb"],
                ["Power Cell","cell"]
            ]

def add_object(self, context, actor_type):

    verts = [
        Vector((0.0849609375,0.0234375,0.06640625)),
        Vector((0.1220703125,0.025390625,-0.064453125)),
        Vector((0.12109375,0.025390625,0.068359375)),
        Vector((0.1220703125,0.025390625,-0.064453125)),
        Vector((0.1240234375,0.0537109375,0.068359375)),
        Vector((0.1240234375,0.0537109375,-0.06640625)),
        Vector((0.08984375,0.052734375,0.099609375)),
        Vector((-0.0888671875,0.0537109375,0.1005859375)),
        Vector((0.0869140625,0.0244140625,0.1015625)),
        Vector((-0.0859375,0.0244140625,0.1005859375)),
        Vector((0.087890625,0.17578125,0.0947265625)),
        Vector((-0.087890625,0.17578125,0.0947265625)),
        Vector((0.087890625,0.14453125,0.09375)),
        Vector((-0.087890625,0.14453125,0.09375)),
        Vector((0.087890625,0.140625,-0.0966796875)),
        Vector((-0.0869140625,0.14453125,-0.0966796875)),
        Vector((0.0869140625,0.1796875,-0.09765625)),
        Vector((-0.0869140625,0.177734375,-0.09765625)),
        Vector((0.0869140625,0.0244140625,-0.099609375)),
        Vector((-0.091796875,0.0234375,-0.1044921875)),
        Vector((0.08984375,0.052734375,-0.0986328125)),
        Vector((-0.0947265625,0.052734375,-0.103515625)),
        Vector((0.0859375,0.0234375,-0.0634765625)),
        Vector((-0.0908203125,0.0234375,-0.0673828125)),
        Vector((0.0869140625,0.0244140625,-0.099609375)),
        Vector((-0.091796875,0.0234375,-0.1044921875)),
        Vector((0.0869140625,0.0244140625,0.1015625)),
        Vector((-0.0859375,0.0244140625,0.1005859375)),
        Vector((-0.083984375,0.0234375,0.0654296875)),
        Vector((0.126953125,0.1787109375,-0.0634765625)),
        Vector((0.126953125,0.14453125,-0.064453125)),
        Vector((0.12109375,0.1787109375,0.0029296875)),
        Vector((0.126953125,0.146484375,0.064453125)),
        Vector((0.126953125,0.177734375,0.064453125)),
        Vector((0.1279296875,0.1416015625,-0.103515625)),
        Vector((0.125,0.0537109375,-0.099609375)),
        Vector((0.125,0.0537109375,-0.099609375)),
        Vector((0.126953125,0.14453125,-0.064453125)),
        Vector((0.1279296875,0.1416015625,-0.103515625)),
        Vector((0.126953125,0.0546875,0.103515625)),
        Vector((0.1298828125,0.142578125,0.099609375)),
        Vector((0.138671875,0.1474609375,-0.015625)),
        Vector((0.1357421875,0.1552734375,-0.0146484375)),
        Vector((0.1328125,0.1435546875,-0.0283203125)),
        Vector((0.1220703125,0.1533203125,-0.0146484375)),
        Vector((0.126953125,0.140625,-0.01953125)),
        Vector((0.138671875,0.1474609375,0.0224609375)),
        Vector((0.1328125,0.1435546875,0.0341796875)),
        Vector((0.1357421875,0.1552734375,0.0205078125)),
        Vector((0.126953125,0.140625,0.025390625)),
        Vector((0.1220703125,0.1533203125,0.0205078125)),
        Vector((0.0859375,0.0234375,-0.0634765625)),
        Vector((0.12109375,0.025390625,0.068359375)),
        Vector((-0.126953125,0.0,-0.1025390625)),
        Vector((-0.125,0.0,-0.0693359375)),
        Vector((-0.1279296875,0.142578125,-0.103515625)),
        Vector((-0.130859375,0.052734375,-0.1044921875)),
        Vector((-0.1298828125,0.0537109375,-0.0703125)),
        Vector((-0.126953125,0.142578125,-0.0654296875)),
        Vector((-0.130859375,0.052734375,-0.1044921875)),
        Vector((-0.1279296875,0.142578125,-0.103515625)),
        Vector((-0.1279296875,0.0244140625,-0.0703125)),
        Vector((-0.125,0.0,-0.0693359375)),
        Vector((-0.0908203125,0.0234375,-0.0673828125)),
        Vector((-0.0947265625,0.0,-0.0703125)),
        Vector((-0.0908203125,0.0234375,-0.0673828125)),
        Vector((-0.0947265625,0.0,-0.0703125)),
        Vector((-0.091796875,0.0234375,-0.1044921875)),
        Vector((-0.0947265625,0.0,-0.1025390625)),
        Vector((-0.1318359375,0.1103515625,-0.0224609375)),
        Vector((-0.126953125,0.140625,-0.01953125)),
        Vector((-0.146484375,0.111328125,-0.021484375)),
        Vector((-0.138671875,0.1474609375,-0.015625)),
        Vector((-0.140625,0.1103515625,-0.0341796875)),
        Vector((-0.1328125,0.1435546875,-0.0283203125)),
        Vector((-0.1318359375,0.1103515625,-0.0224609375)),
        Vector((-0.126953125,0.140625,-0.01953125)),
        Vector((-0.146484375,0.111328125,-0.021484375)),
        Vector((-0.14453125,0.0986328125,-0.0224609375)),
        Vector((-0.140625,0.1103515625,-0.0341796875)),
        Vector((-0.1337890625,0.1005859375,-0.0224609375)),
        Vector((-0.1318359375,0.1103515625,-0.0224609375)),
        Vector((-0.138671875,0.1474609375,-0.015625)),
        Vector((-0.1328125,0.1435546875,-0.0283203125)),
        Vector((-0.1357421875,0.1552734375,-0.0146484375)),
        Vector((-0.126953125,0.140625,-0.01953125)),
        Vector((-0.1220703125,0.1533203125,-0.0146484375)),
        Vector((-0.126953125,0.140625,0.025390625)),
        Vector((-0.1318359375,0.1103515625,0.0283203125)),
        Vector((-0.138671875,0.1474609375,0.0224609375)),
        Vector((-0.1455078125,0.1103515625,0.03125)),
        Vector((-0.1328125,0.1435546875,0.0341796875)),
        Vector((-0.140625,0.1103515625,0.041015625)),
        Vector((-0.126953125,0.140625,0.025390625)),
        Vector((-0.1318359375,0.1103515625,0.0283203125)),
        Vector((-0.1455078125,0.1103515625,0.03125)),
        Vector((-0.14453125,0.0986328125,0.0283203125)),
        Vector((-0.140625,0.1103515625,0.041015625)),
        Vector((-0.1337890625,0.1005859375,0.0283203125)),
        Vector((-0.1318359375,0.1103515625,0.0283203125)),
        Vector((-0.138671875,0.1474609375,0.0224609375)),
        Vector((-0.1357421875,0.1552734375,0.0205078125)),
        Vector((-0.1328125,0.1435546875,0.0341796875)),
        Vector((-0.1220703125,0.1533203125,0.0205078125)),
        Vector((-0.126953125,0.140625,0.025390625)),
        Vector((-0.0947265625,0.0,-0.1025390625)),
        Vector((-0.0947265625,0.0,-0.0703125)),
        Vector((0.0859375,0.0,0.099609375)),
        Vector((0.119140625,0.0,0.099609375)),
        Vector((0.08984375,0.052734375,0.099609375)),
        Vector((0.126953125,0.0546875,0.103515625)),
        Vector((0.087890625,0.14453125,0.09375)),
        Vector((0.1298828125,0.142578125,0.099609375)),
        Vector((0.0849609375,0.0234375,0.06640625)),
        Vector((0.12109375,0.025390625,0.068359375)),
        Vector((0.0849609375,0.0,0.068359375)),
        Vector((0.1171875,0.0,0.068359375)),
        Vector((0.0869140625,0.0244140625,0.1015625)),
        Vector((0.0849609375,0.0234375,0.06640625)),
        Vector((0.0859375,0.0,0.099609375)),
        Vector((0.0849609375,0.0,0.068359375)),
        Vector((-0.0859375,0.0244140625,0.1005859375)),
        Vector((-0.08203125,0.0,0.1005859375)),
        Vector((-0.083984375,0.0234375,0.0654296875)),
        Vector((-0.0810546875,0.0,0.06640625)),
        Vector((0.12109375,0.025390625,0.068359375)),
        Vector((0.1240234375,0.0244140625,0.1025390625)),
        Vector((0.1171875,0.0,0.068359375)),
        Vector((0.119140625,0.0,0.099609375)),
        Vector((0.146484375,0.111328125,-0.021484375)),
        Vector((0.138671875,0.1474609375,-0.015625)),
        Vector((0.1318359375,0.1103515625,-0.0224609375)),
        Vector((0.126953125,0.140625,-0.01953125)),
        Vector((0.140625,0.1103515625,-0.0341796875)),
        Vector((0.1328125,0.1435546875,-0.0283203125)),
        Vector((0.146484375,0.111328125,-0.021484375)),
        Vector((0.138671875,0.1474609375,-0.015625)),
        Vector((0.146484375,0.111328125,-0.021484375)),
        Vector((0.14453125,0.0986328125,-0.0224609375)),
        Vector((0.140625,0.1103515625,-0.0341796875)),
        Vector((0.1337890625,0.1005859375,-0.0224609375)),
        Vector((0.1318359375,0.1103515625,-0.0224609375)),
        Vector((0.138671875,0.1474609375,0.0224609375)),
        Vector((0.1455078125,0.1103515625,0.03125)),
        Vector((0.126953125,0.140625,0.025390625)),
        Vector((0.1318359375,0.1103515625,0.0283203125)),
        Vector((0.1328125,0.1435546875,0.0341796875)),
        Vector((0.140625,0.1103515625,0.041015625)),
        Vector((0.138671875,0.1474609375,0.0224609375)),
        Vector((0.1455078125,0.1103515625,0.03125)),
        Vector((0.1455078125,0.1103515625,0.03125)),
        Vector((0.14453125,0.0986328125,0.0283203125)),
        Vector((0.140625,0.1103515625,0.041015625)),
        Vector((0.1337890625,0.1005859375,0.0283203125)),
        Vector((0.1318359375,0.1103515625,0.0283203125)),
        Vector((0.126953125,0.0546875,0.103515625)),
        Vector((0.1240234375,0.0537109375,0.068359375)),
        Vector((0.0849609375,0.0,0.068359375)),
        Vector((0.1171875,0.0,0.068359375)),
        Vector((0.12890625,0.1767578125,0.099609375)),
        Vector((0.0869140625,0.1796875,-0.09765625)),
        Vector((0.126953125,0.1787109375,-0.1015625)),
        Vector((0.087890625,0.140625,-0.0966796875)),
        Vector((0.1279296875,0.1416015625,-0.103515625)),
        Vector((0.126953125,0.14453125,-0.064453125)),
        Vector((0.1279296875,0.1416015625,-0.103515625)),
        Vector((0.126953125,0.1787109375,-0.0634765625)),
        Vector((0.126953125,0.1787109375,-0.1015625)),
        Vector((0.1298828125,0.142578125,0.099609375)),
        Vector((0.126953125,0.146484375,0.064453125)),
        Vector((0.12890625,0.1767578125,0.099609375)),
        Vector((0.126953125,0.177734375,0.064453125)),
        Vector((0.0869140625,0.0244140625,0.1015625)),
        Vector((0.1240234375,0.0244140625,0.1025390625)),
        Vector((0.126953125,0.0546875,0.103515625)),
        Vector((0.08984375,0.052734375,-0.0986328125)),
        Vector((0.125,0.0537109375,-0.099609375)),
        Vector((0.0869140625,0.0244140625,-0.099609375)),
        Vector((0.123046875,0.0244140625,-0.099609375)),
        Vector((0.1220703125,0.025390625,-0.064453125)),
        Vector((0.123046875,0.0244140625,-0.099609375)),
        Vector((0.1240234375,0.0537109375,-0.06640625)),
        Vector((0.125,0.0537109375,-0.099609375)),
        Vector((0.0869140625,0.0,-0.09765625)),
        Vector((0.1181640625,0.0,-0.09765625)),
        Vector((0.0859375,0.0,-0.0654296875)),
        Vector((0.1162109375,0.0,-0.0654296875)),
        Vector((0.0869140625,0.0,-0.09765625)),
        Vector((0.1181640625,0.0,-0.09765625)),
        Vector((0.1181640625,0.0,-0.09765625)),
        Vector((0.1162109375,0.0,-0.0654296875)),
        Vector((0.1220703125,0.025390625,-0.064453125)),
        Vector((0.0859375,0.0234375,-0.0634765625)),
        Vector((0.1162109375,0.0,-0.0654296875)),
        Vector((0.0859375,0.0,-0.0654296875)),
        Vector((0.0859375,0.0234375,-0.0634765625)),
        Vector((0.0869140625,0.0244140625,-0.099609375)),
        Vector((0.0859375,0.0,-0.0654296875)),
        Vector((0.0869140625,0.0,-0.09765625)),
        Vector((0.119140625,0.0,0.099609375)),
        Vector((0.0859375,0.0,0.099609375)),
        Vector((-0.0810546875,0.0,0.06640625)),
        Vector((-0.08203125,0.0,0.1005859375)),
        Vector((-0.1162109375,0.0,0.06640625)),
        Vector((-0.1181640625,0.0,0.1005859375)),
        Vector((0.123046875,0.212890625,-0.0908203125)),
        Vector((0.126953125,0.1787109375,-0.1015625)),
        Vector((0.0869140625,0.1796875,-0.09765625)),
        Vector((0.1240234375,0.208984375,0.08984375)),
        Vector((0.087890625,0.17578125,0.0947265625)),
        Vector((0.087890625,0.14453125,0.09375)),
        Vector((0.087890625,0.17578125,0.0947265625)),
        Vector((-0.126953125,0.142578125,-0.0654296875)),
        Vector((-0.126953125,0.1796875,-0.1025390625)),
        Vector((-0.1279296875,0.0244140625,-0.0703125)),
        Vector((-0.1220703125,0.0244140625,0.0673828125)),
        Vector((-0.1298828125,0.0537109375,-0.0703125)),
        Vector((-0.1240234375,0.0546875,0.068359375)),
        Vector((-0.126953125,0.177734375,0.064453125)),
        Vector((-0.126953125,0.146484375,0.064453125)),
        Vector((-0.12109375,0.1787109375,0.0029296875)),
        Vector((-0.126953125,0.1787109375,-0.0634765625)),
        Vector((-0.083984375,0.0234375,0.0654296875)),
        Vector((-0.1220703125,0.0244140625,0.0673828125)),
        Vector((-0.0908203125,0.0234375,-0.0673828125)),
        Vector((-0.1279296875,0.0244140625,-0.0703125)),
        Vector((0.0849609375,0.0234375,0.06640625)),
        Vector((0.0859375,0.0234375,-0.0634765625)),
        Vector((0.08984375,0.052734375,-0.0986328125)),
        Vector((-0.0947265625,0.052734375,-0.103515625)),
        Vector((0.087890625,0.140625,-0.0966796875)),
        Vector((-0.0869140625,0.14453125,-0.0966796875)),
        Vector((-0.1240234375,0.0546875,0.068359375)),
        Vector((-0.126953125,0.142578125,-0.0654296875)),
        Vector((-0.126953125,0.146484375,0.064453125)),
        Vector((0.087890625,0.14453125,0.09375)),
        Vector((-0.087890625,0.14453125,0.09375)),
        Vector((0.08984375,0.052734375,0.099609375)),
        Vector((-0.0888671875,0.0537109375,0.1005859375)),
        Vector((-0.123046875,0.212890625,-0.0908203125)),
        Vector((-0.0869140625,0.177734375,-0.09765625)),
        Vector((-0.126953125,0.1796875,-0.1025390625)),
        Vector((-0.12890625,0.1767578125,0.099609375)),
        Vector((-0.087890625,0.17578125,0.0947265625)),
        Vector((-0.1240234375,0.208984375,0.08984375)),
        Vector((-0.126953125,0.1796875,-0.1025390625)),
        Vector((-0.126953125,0.1787109375,-0.0634765625)),
        Vector((-0.123046875,0.212890625,-0.0908203125)),
        Vector((-0.12109375,0.1787109375,0.0029296875)),
        Vector((-0.1220703125,0.2373046875,-0.068359375)),
        Vector((-0.12109375,0.251953125,-0.03515625)),
        Vector((-0.12109375,0.2568359375,0.0029296875)),
        Vector((-0.12109375,0.25,0.0390625)),
        Vector((-0.1220703125,0.234375,0.0703125)),
        Vector((-0.1240234375,0.208984375,0.08984375)),
        Vector((-0.126953125,0.177734375,0.064453125)),
        Vector((-0.12890625,0.1767578125,0.099609375)),
        Vector((-0.126953125,0.1787109375,-0.0634765625)),
        Vector((-0.1279296875,0.142578125,-0.103515625)),
        Vector((0.1240234375,0.0537109375,0.068359375)),
        Vector((0.126953125,0.146484375,0.064453125)),
        Vector((0.12890625,0.1767578125,0.099609375)),
        Vector((0.126953125,0.177734375,0.064453125)),
        Vector((0.1240234375,0.208984375,0.08984375)),
        Vector((0.12109375,0.1787109375,0.0029296875)),
        Vector((0.1220703125,0.234375,0.0703125)),
        Vector((0.12109375,0.25,0.0390625)),
        Vector((0.12109375,0.2568359375,0.0029296875)),
        Vector((0.12109375,0.251953125,-0.03515625)),
        Vector((0.1220703125,0.2373046875,-0.068359375)),
        Vector((0.123046875,0.212890625,-0.0908203125)),
        Vector((0.126953125,0.1787109375,-0.0634765625)),
        Vector((0.126953125,0.1787109375,-0.1015625)),
        Vector((0.1318359375,0.1103515625,-0.0224609375)),
        Vector((0.1318359375,0.1103515625,0.0283203125)),
        Vector((0.146484375,0.111328125,-0.021484375)),
        Vector((0.1455078125,0.1103515625,0.03125)),
        Vector((0.14453125,0.0986328125,-0.0224609375)),
        Vector((0.14453125,0.0986328125,0.0283203125)),
        Vector((0.1337890625,0.1005859375,-0.0224609375)),
        Vector((0.1337890625,0.1005859375,0.0283203125)),
        Vector((0.138671875,0.1474609375,-0.015625)),
        Vector((0.138671875,0.1474609375,0.0224609375)),
        Vector((0.126953125,0.140625,-0.01953125)),
        Vector((0.126953125,0.140625,0.025390625)),
        Vector((0.1220703125,0.1533203125,-0.0146484375)),
        Vector((0.1220703125,0.1533203125,0.0205078125)),
        Vector((0.1357421875,0.1552734375,-0.0146484375)),
        Vector((0.1357421875,0.1552734375,0.0205078125)),
        Vector((0.1240234375,0.0537109375,-0.06640625)),
        Vector((0.126953125,0.14453125,-0.064453125)),
        Vector((-0.1298828125,0.1416015625,0.099609375)),
        Vector((-0.12890625,0.1767578125,0.099609375)),
        Vector((-0.1298828125,0.1416015625,0.099609375)),
        Vector((-0.12890625,0.1767578125,0.099609375)),
        Vector((-0.126953125,0.146484375,0.064453125)),
        Vector((-0.126953125,0.177734375,0.064453125)),
        Vector((-0.0859375,0.0244140625,0.1005859375)),
        Vector((-0.0888671875,0.0537109375,0.1005859375)),
        Vector((-0.125,0.0234375,0.103515625)),
        Vector((-0.1279296875,0.0546875,0.103515625)),
        Vector((-0.0947265625,0.052734375,-0.103515625)),
        Vector((-0.091796875,0.0234375,-0.1044921875)),
        Vector((-0.130859375,0.052734375,-0.1044921875)),
        Vector((-0.12890625,0.0244140625,-0.103515625)),
        Vector((-0.125,0.0234375,0.103515625)),
        Vector((-0.1279296875,0.0546875,0.103515625)),
        Vector((-0.1220703125,0.0244140625,0.0673828125)),
        Vector((-0.1240234375,0.0546875,0.068359375)),
        Vector((-0.1279296875,0.0546875,0.103515625)),
        Vector((-0.126953125,0.146484375,0.064453125)),
        Vector((-0.0888671875,0.0537109375,0.1005859375)),
        Vector((-0.1298828125,0.1416015625,0.099609375)),
        Vector((-0.0947265625,0.0,-0.1025390625)),
        Vector((-0.126953125,0.0,-0.1025390625)),
        Vector((-0.1162109375,0.0,0.06640625)),
        Vector((-0.1181640625,0.0,0.1005859375)),
        Vector((-0.1181640625,0.0,0.1005859375)),
        Vector((-0.08203125,0.0,0.1005859375)),
        Vector((-0.146484375,0.111328125,-0.021484375)),
        Vector((-0.1455078125,0.1103515625,0.03125)),
        Vector((-0.1318359375,0.1103515625,-0.0224609375)),
        Vector((-0.1318359375,0.1103515625,0.0283203125)),
        Vector((-0.1337890625,0.1005859375,-0.0224609375)),
        Vector((-0.1337890625,0.1005859375,0.0283203125)),
        Vector((-0.14453125,0.0986328125,-0.0224609375)),
        Vector((-0.14453125,0.0986328125,0.0283203125)),
        Vector((-0.126953125,0.140625,-0.01953125)),
        Vector((-0.126953125,0.140625,0.025390625)),
        Vector((-0.138671875,0.1474609375,-0.015625)),
        Vector((-0.138671875,0.1474609375,0.0224609375)),
        Vector((-0.1357421875,0.1552734375,-0.0146484375)),
        Vector((-0.1357421875,0.1552734375,0.0205078125)),
        Vector((-0.1220703125,0.1533203125,-0.0146484375)),
        Vector((-0.1220703125,0.1533203125,0.0205078125)),
        Vector((-0.087890625,0.14453125,0.09375)),
        Vector((-0.087890625,0.17578125,0.0947265625)),
        Vector((-0.126953125,0.1796875,-0.1025390625)),
        Vector((-0.1279296875,0.142578125,-0.103515625)),
        Vector((-0.1279296875,0.0244140625,-0.0703125)),
        Vector((-0.1298828125,0.0537109375,-0.0703125)),
        Vector((-0.12890625,0.0244140625,-0.103515625)),
        Vector((-0.130859375,0.052734375,-0.1044921875)),
        Vector((-0.126953125,0.0,-0.1025390625)),
        Vector((-0.125,0.0,-0.0693359375)),
        Vector((-0.083984375,0.0234375,0.0654296875)),
        Vector((-0.0810546875,0.0,0.06640625)),
        Vector((-0.1220703125,0.0244140625,0.0673828125)),
        Vector((-0.1162109375,0.0,0.06640625)),
        Vector((-0.0869140625,0.177734375,-0.09765625)),
        Vector((-0.0869140625,0.14453125,-0.0966796875)),
        Vector((-0.1220703125,0.2373046875,-0.068359375)),
        Vector((0.1220703125,0.2373046875,-0.068359375)),
        Vector((-0.123046875,0.212890625,-0.0908203125)),
        Vector((0.123046875,0.212890625,-0.0908203125)),
        Vector((-0.1240234375,0.208984375,0.08984375)),
        Vector((0.1240234375,0.208984375,0.08984375)),
        Vector((-0.1220703125,0.234375,0.0703125)),
        Vector((0.1220703125,0.234375,0.0703125)),
        Vector((-0.12109375,0.25,0.0390625)),
        Vector((0.12109375,0.25,0.0390625)),
        Vector((0.12109375,0.251953125,-0.03515625)),
        Vector((-0.12109375,0.251953125,-0.03515625)),
        Vector((0.12109375,0.2568359375,0.0029296875)),
        Vector((-0.12109375,0.2568359375,0.0029296875)),
        Vector((0.12109375,0.25,0.0390625)),
        Vector((-0.12109375,0.25,0.0390625)),
        Vector((-0.12109375,0.251953125,-0.03515625)),
        Vector((0.12109375,0.251953125,-0.03515625)),
        ]

    edges = [[257,258],[8,9],[265,266],[16,17],[273,274],[273,275],[273,279],[273,280],[24,25],[0,26],[0,27],[0,28],[281,287],[281,288],[32,33],[289,290],[179,181],[32,40],[297,298],[297,299],[48,49],[48,50],[0,51],[0,52],[274,276],[313,314],[305,315],[305,316],[297,317],[297,318],[321,322],[321,323],[358,360],[72,73],[72,74],[329,331],[80,81],[337,338],[320,322],[88,89],[88,90],[345,347],[337,349],[337,350],[96,97],[96,98],[282,284],[361,362],[361,363],[359,360],[144,145],[144,146],[152,153],[152,154],[112,159],[160,161],[160,162],[168,169],[168,170],[176,177],[176,178],[42,44],[184,185],[184,186],[73,74],[192,193],[192,194],[208,209],[112,210],[112,211],[216,217],[224,225],[224,227],[216,232],[216,233],[232,234],[240,241],[208,244],[353,354],[248,249],[248,250],[248,251],[248,252],[248,253],[248,254],[248,255],[264,265],[264,266],[264,267],[264,268],[264,269],[264,270],[264,271],[39,40],[357,358],[41,42],[41,43],[49,50],[1,51],[1,52],[43,44],[304,313],[57,58],[57,59],[320,321],[65,66],[65,67],[320,326],[281,283],[328,329],[328,330],[73,75],[328,334],[312,335],[89,90],[89,91],[352,353],[97,98],[97,99],[105,106],[352,368],[113,114],[113,115],[121,122],[121,123],[129,130],[129,131],[137,138],[137,139],[145,146],[145,147],[153,154],[70,72],[51,52],[161,162],[161,163],[169,170],[169,171],[177,178],[185,186],[177,187],[193,194],[201,202],[201,203],[233,234],[341,342],[209,243],[209,244],[352,354],[249,250],[78,79],[2,3],[2,4],[10,11],[10,12],[18,19],[18,20],[275,277],[26,27],[283,284],[283,285],[259,289],[259,290],[34,35],[291,292],[259,260],[42,43],[299,300],[307,308],[303,304],[58,59],[315,316],[299,317],[66,67],[323,324],[323,325],[74,75],[74,76],[331,333],[291,335],[291,336],[82,83],[82,84],[339,341],[339,343],[339,344],[90,91],[90,92],[98,99],[355,356],[355,357],[363,364],[363,365],[67,68],[114,115],[114,116],[122,123],[122,124],[29,30],[305,307],[130,131],[130,132],[138,139],[138,140],[267,268],[146,147],[146,148],[162,163],[170,171],[178,187],[178,188],[202,203],[202,204],[210,211],[75,76],[331,332],[218,219],[218,220],[226,227],[242,243],[242,244],[275,276],[250,251],[3,4],[3,5],[266,267],[11,12],[11,13],[212,221],[274,275],[66,68],[19,21],[274,280],[282,283],[27,28],[351,367],[282,288],[351,368],[298,299],[298,300],[43,45],[306,307],[306,308],[59,60],[322,323],[322,324],[330,331],[330,332],[83,84],[83,85],[346,347],[91,92],[91,93],[302,304],[7,8],[362,363],[107,108],[338,350],[115,116],[123,124],[300,311],[300,312],[131,132],[131,133],[139,140],[139,141],[147,148],[147,149],[155,156],[107,157],[107,158],[367,368],[346,348],[179,180],[329,330],[308,310],[187,188],[179,189],[179,190],[195,196],[195,197],[270,272],[203,204],[232,233],[219,220],[235,236],[235,237],[335,336],[243,244],[349,350],[300,335],[251,252],[213,257],[213,258],[4,5],[261,262],[261,263],[12,13],[269,270],[20,21],[277,278],[277,279],[285,286],[285,287],[4,32],[20,34],[20,35],[36,37],[36,38],[4,39],[4,40],[44,45],[301,302],[301,303],[23,24],[293,308],[293,309],[293,310],[317,318],[325,326],[333,334],[84,85],[84,86],[341,343],[92,93],[92,94],[100,101],[100,102],[357,359],[365,366],[362,364],[132,133],[132,134],[69,70],[140,141],[148,149],[286,288],[108,158],[164,165],[164,166],[172,173],[180,181],[180,182],[305,306],[180,189],[196,197],[196,198],[172,199],[172,200],[212,219],[212,220],[220,221],[228,229],[228,230],[236,237],[236,238],[332,334],[252,253],[58,60],[212,257],[212,258],[268,269],[276,277],[276,278],[284,285],[284,286],[29,31],[260,290],[5,36],[5,37],[37,38],[308,309],[53,54],[21,55],[21,56],[61,62],[61,63],[324,325],[324,326],[69,71],[332,333],[77,78],[77,79],[292,336],[340,341],[85,86],[340,342],[93,94],[356,357],[101,102],[101,103],[53,105],[53,106],[364,365],[109,110],[109,111],[117,118],[117,119],[125,126],[125,127],[133,134],[133,135],[125,155],[125,156],[157,158],[165,166],[165,167],[109,172],[109,173],[173,174],[181,182],[189,190],[197,198],[173,199],[205,206],[205,207],[293,294],[293,295],[229,230],[229,231],[237,238],[205,239],[245,246],[245,247],[253,254],[255,256],[6,7],[6,8],[263,265],[14,15],[14,16],[14,20],[22,23],[22,24],[30,31],[30,32],[14,34],[295,296],[356,358],[46,47],[46,48],[339,340],[62,63],[62,64],[319,321],[319,325],[319,326],[70,71],[327,328],[327,329],[327,333],[327,334],[311,335],[78,80],[343,344],[263,264],[351,352],[351,353],[102,103],[102,104],[54,106],[110,111],[110,112],[118,119],[118,120],[126,127],[126,128],[134,135],[134,136],[142,143],[142,144],[364,366],[281,282],[150,151],[150,152],[126,155],[347,348],[166,167],[271,272],[206,207],[214,215],[214,216],[222,223],[222,224],[222,226],[222,227],[230,231],[345,346],[246,247],[246,248],[254,255],[254,256],[262,263],[262,264],[7,9],[270,271],[15,16],[15,17],[15,21],[278,279],[278,280],[23,25],[286,287],[31,32],[31,33],[207,240],[294,295],[294,296],[279,280],[302,303],[47,48],[47,49],[15,55],[55,56],[302,313],[63,64],[71,72],[71,73],[79,80],[79,81],[87,88],[87,89],[95,96],[95,97],[358,359],[103,104],[111,112],[119,120],[127,128],[135,136],[319,320],[143,144],[143,145],[287,288],[151,152],[151,153],[304,314],[175,176],[175,177],[183,184],[183,185],[191,192],[191,193],[199,200],[159,208],[159,209],[159,211],[109,174],[215,216],[215,217],[223,224],[223,225],[307,315],[207,239],[239,240],[239,241],[247,248],[247,249],[19,20]]

    faces = [[0,51,52],[51,52,1],[2,3,4],[3,4,5],[6,7,8],[7,8,9],[10,11,12],[11,12,13],[14,15,16],[15,16,17],[18,19,20],[19,20,21],[22,23,24],[23,24,25],[27,0,26],[27,0,28],[29,30,31],[30,31,32],[31,32,33],[14,34,20],[34,20,35],[5,36,37],[36,37,38],[39,4,40],[4,40,32],[41,42,43],[42,43,44],[43,44,45],[46,47,48],[47,48,49],[48,49,50],[105,106,53],[106,53,54],[15,21,55],[21,55,56],[57,58,59],[58,59,60],[61,62,63],[62,63,64],[65,66,67],[66,67,68],[69,70,71],[70,71,72],[71,72,73],[72,73,74],[73,74,75],[74,75,76],[77,78,79],[78,79,80],[79,80,81],[82,83,84],[83,84,85],[84,85,86],[87,88,89],[88,89,90],[89,90,91],[90,91,92],[91,92,93],[92,93,94],[95,96,97],[96,97,98],[97,98,99],[100,101,102],[101,102,103],[102,103,104],[157,158,107],[158,107,108],[109,110,111],[110,111,112],[113,114,115],[114,115,116],[117,118,119],[118,119,120],[121,122,123],[122,123,124],[125,126,127],[126,127,128],[129,130,131],[130,131,132],[131,132,133],[132,133,134],[133,134,135],[134,135,136],[137,138,139],[138,139,140],[139,140,141],[142,143,144],[143,144,145],[144,145,146],[145,146,147],[146,147,148],[147,148,149],[150,151,152],[151,152,153],[152,153,154],[126,125,155],[125,155,156],[210,112,211],[112,211,159],[160,161,162],[161,162,163],[164,165,166],[165,166,167],[168,169,170],[169,170,171],[172,173,109],[173,109,174],[175,176,177],[176,177,178],[179,180,181],[180,181,182],[183,184,185],[184,185,186],[177,178,187],[178,187,188],[180,179,189],[179,189,190],[191,192,193],[192,193,194],[195,196,197],[196,197,198],[173,172,199],[172,199,200],[201,202,203],[202,203,204],[205,206,207],[159,208,209],[212,257,258],[257,258,213],[214,215,216],[215,216,217],[218,219,220],[219,220,212],[220,212,221],[222,223,224],[223,224,225],[226,222,227],[222,227,224],[228,229,230],[229,230,231],[216,232,233],[232,233,234],[235,236,237],[236,237,238],[205,207,239],[207,239,240],[239,240,241],[242,243,244],[243,244,209],[244,209,208],[245,246,247],[246,247,248],[247,248,249],[248,249,250],[250,251,248],[251,248,252],[248,252,253],[253,248,254],[248,254,255],[254,255,256],[289,290,259],[290,259,260],[261,262,263],[262,263,264],[263,264,265],[264,265,266],[266,267,264],[267,264,268],[264,268,269],[269,264,270],[264,270,271],[270,271,272],[273,274,275],[274,275,276],[275,276,277],[276,277,278],[277,278,279],[278,279,280],[279,280,273],[280,273,274],[281,282,283],[282,283,284],[283,284,285],[284,285,286],[285,286,287],[286,287,288],[287,288,281],[288,281,282],[335,336,291],[336,291,292],[293,294,295],[294,295,296],[297,298,299],[298,299,300],[301,302,303],[302,303,304],[305,306,307],[306,307,308],[309,293,308],[293,308,310],[311,335,300],[335,300,312],[302,313,304],[313,304,314],[307,315,305],[315,305,316],[299,317,297],[317,297,318],[319,320,321],[320,321,322],[321,322,323],[322,323,324],[323,324,325],[324,325,326],[325,326,319],[326,319,320],[327,328,329],[328,329,330],[329,330,331],[330,331,332],[331,332,333],[332,333,334],[333,334,327],[334,327,328],[349,350,337],[350,337,338],[339,340,341],[340,341,342],[341,343,339],[343,339,344],[345,346,347],[346,347,348],[367,368,351],[368,351,352],[351,352,353],[352,353,354],[355,356,357],[356,357,358],[357,358,359],[358,359,360],[361,362,363],[362,363,364],[363,364,365],[364,365,366]]

    mesh = bpy.data.meshes.new(name=actor_type)
    mesh.from_pydata(verts, edges, faces)
    # useful for development when the mesh may be invalid.
    # mesh.validate(verbose=True)
    object_data_add(context, mesh, operator=self)

class OBJECT_OT_add_object(Operator, AddObjectHelper):
    """Create a new Mesh Object"""
    bl_idname = "mesh.add_object"
    bl_label = "Add Mesh Object"
    bl_options = {'REGISTER', 'UNDO'}

    scale: FloatVectorProperty(
        name="scale",
        default=(1.0, 1.0, 1.0),
        subtype='TRANSLATION',
        description="scaling",
    )

    def execute(self, context):

        add_object(self, context, "Actor") # create the actor
        bpy.context.active_object.rotation_euler[0] = math.radians(90) # fix the rotation
        bpy.data.objects[bpy.context.object.data.name].active_material = bpy.data.materials.new("Color") # create a material
        bpy.data.objects[bpy.context.object.data.name].active_material.diffuse_color = (178/225,113/225,0,1) # add color

        actor_collection = bpy.data.collections.new('actor_collection') # create a collection to house the actors
        actor_collection.objects.link(bpy.data.objects[bpy.context.object.data.name]) # add the actor to a collection
        bpy.data.objects[bpy.context.object.data.name].rotation_mode = 'QUATERNION' # set rotation mode to quaternion
        bpy.data.objects[bpy.context.object.data.name]["Actor Type"] = "not implemented yet" # create custom property
        bpy.data.objects[bpy.context.object.data.name]["Game Task"] = 0 # create custom property
        bpy.data.objects[bpy.context.object.data.name]["Bounding Sphere"] = (0.0,0.0,0.0) # create custom property
        
        ''' #commenting this out because it messes with collections
        actor = bpy.data.objects[bpy.context.object.data.name] # rename duplicates in a less stupid way
        if '.' in actor.name:
            basename, suffix = actor.name.split('.')
            actor.name = basename + suffix'''

        return {'FINISHED'}


# add buttons for the new meshes
def add_object_button(self, context):
    for actor_type in actor_types:
        self.layout.operator(
            OBJECT_OT_add_object.bl_idname,
            text=actor_type[0],
            icon_value=custom_icons[actor_type[1]].icon_id)

# This allows you to right click on a button and link to documentation
def add_object_manual_map():
    url_manual_prefix = "https://docs.blender.org/manual/en/latest/"
    url_manual_mapping = (
        ("bpy.ops.mesh.add_object", "scene_layout/object/types.html"),
    )
    return url_manual_prefix, url_manual_mapping

# ------------------------------------------------------------------------
#    Registration
# ------------------------------------------------------------------------

classes = (
    MyProperties,
    WM_OT_Export,
    OBJECT_PT_LevelInfoPanel,
    EDIT_PT_LevelInfoPanel,
    OBJECT_PT_ActorInfoPanel,
    EDIT_PT_ActorInfoPanel,
    
    #remove
    WM_OT_PrintActors
)

def register():
    
    # Register classes
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    # register my properties
    bpy.types.Scene.my_tool = PointerProperty(type=MyProperties)

    # register new mesh type
    bpy.utils.register_class(OBJECT_OT_add_object)
    bpy.utils.register_manual_map(add_object_manual_map)
    bpy.types.VIEW3D_MT_mesh_add.append(add_object_button)
    
    # add custom icons
    global custom_icons
    custom_icons = bpy.utils.previews.new()
    addon_path =  os.path.dirname(__file__)
    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    icon_list = [
                "orb",
                "cell",
                "greeneco",
                "blueeco",
                "yelloweco",
                "redeco"
                ]
    for icon in icon_list:
        custom_icons.load(icon, os.path.join(icons_dir, icon+".png"), 'IMAGE')

def unregister():
    # Unregister custom UI
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.Scene.my_tool

    # Unregister new mesh type
    bpy.utils.unregister_class(OBJECT_OT_add_object)
    bpy.utils.unregister_manual_map(add_object_manual_map)
    bpy.types.VIEW3D_MT_mesh_add.remove(add_object_button)


if __name__ == "__main__":
    register()