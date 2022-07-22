# ------------------------------------------------------------------------
#    Addon Info
# ------------------------------------------------------------------------
bl_info = {
    "name": "OpenGOAL Custom Level Builder",
    "description": "modified from https://gist.github.com/p2or/2947b1aa89141caae182526a8fc2bc5a and https://github.com/blender/blender/blob/master/release/scripts/templates_py/addon_add_object.py",
    "author": "himham",
    "version": (1, 0, 0),
    "blender": (2, 92, 0),
    "location": "3D View > Level Info",
    "warning": "",
    "category": "Development"
    }

# ------------------------------------------------------------------------
#    Includes
# ------------------------------------------------------------------------
import bpy, bmesh, os, re, shutil
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
        items=[ ('fuel-cell', "Power Cell", ""),
                ('crate', "Crate", ""),
                ('eco-yellow', "Yellow Eco", ""),
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
            playtest_level(longtitle)
        
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
            
        gp = [
            '\n\n(build-custom-level "',
            longtitle,
            '")\n',
            '(custom-level-cgo "',
            title.upper(),
            '.DGO" "',
            longtitle,
            '/',
            title,
            '.gd")'
            ]
        
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
        #f.writelines(contents)
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
        f = open(path+filename, 'a', encoding="utf-8")
        # write the contents
        #f.writelines(contents)
        # close the file
        f.close()
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
        
def playtest_level(longtitle):
        
        print("Beginning playtest.\n")
        
        os.system('''start cmd @cmd /c "cd ..\Games\opengoal-v0.1.19-windows && gk -boot -fakeiso -debug" ''') # open the game in debug mode
        os.system('''start cmd @cmd /k "cd ..\Games\opengoal-v0.1.19-windows && goalc --startup-cmd "(mi) (lt)"" ''') # open the repl, rebuild, and link to game
        # run (bg-custom 'longtitle-vis) in the repl
        
        print("Message: Sorry, for now you'll have to run (bg-custom '"+longtitle+"-vis) in goalc manually.\n")
        
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
        layout.prop(mytool, "level_title")
        layout.prop(mytool, "level_nickname")
        layout.prop_search(mytool, "anchor", scene, "objects")
        layout.prop(mytool, "level_location", text="Level Location*")
        layout.prop(mytool, "level_rotation", text="Level Rotation*")
        layout.prop(mytool, "custom_levels_path")
        layout.prop(mytool, "should_export_level_info")
        layout.prop(mytool, "should_export_actor_info", text="Actor Info*")
        layout.prop(mytool, "should_export_geometry")
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

        layout.prop(mytool, "actor_name") # dummy
        layout.prop(context.active_object, "name")
        layout.prop(mytool, "actor_type") # dummy
        layout.prop(context.active_object, "type")
        layout.prop(mytool, "actor_location") # dummy
        layout.prop(context.active_object, "location")
        layout.prop(mytool, "actor_rotation") # dummy
        layout.prop(context.active_object, "rotation_quaternion") # this won't display properly unless the object is in quaternion mode, can I put it into quat mode when added?
        
        # set these properties manually
        layout.prop(mytool, "game_task") # how do I add this custom property to all actors when added
        layout.prop(mytool, "bounding_sphere") # how do I add this custom property to all actors when added
        layout.operator("wm.print") # this is a debug button to print all the current actors and their attributes before exporting
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

        layout.prop(mytool, "level_title")
        layout.prop(mytool, "level_nickname")
        layout.prop_search(mytool, "anchor", scene, "objects")
        layout.prop(mytool, "level_location")
        layout.prop(mytool, "level_rotation")
        layout.prop(mytool, "custom_levels_path")
        layout.label(text="Switch to Object Mode to export.", icon="ERROR")
        layout.separator()
        
class EDIT_PT_ActorInfoPanel(Panel):
    bl_label = "Actor Info"
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

        layout.prop(mytool, "actor_name")
        layout.prop(mytool, "actor_type")
        layout.prop(mytool, "actor_location")
        layout.prop(mytool, "actor_rotation")
        layout.prop(mytool, "game_task")
        layout.prop(mytool, "bounding_sphere")
        layout.separator()

# ------------------------------------------------------------------------
#    New Mesh Initialization               # This will be cleaned up with the verts,edges,faces in a separate file for each actor model
# ------------------------------------------------------------------------       

def add_object(self, context):

    verts = [
        Vector((0.0,0.0,-1.0)),
        Vector((0.7236073017120361,-0.5257253050804138,-0.44721952080726624)),
        Vector((-0.276388019323349,-0.8506492376327515,-0.4472198486328125)),
        Vector((-0.8944262266159058,0.0,-0.44721561670303345)),
        Vector((-0.276388019323349,0.8506492376327515,-0.4472198486328125)),
        Vector((0.7236073017120361,0.5257253050804138,-0.44721952080726624)),
        Vector((0.276388019323349,-0.8506492376327515,0.4472198486328125)),
        Vector((-0.7236073017120361,-0.5257253050804138,0.44721952080726624)),
        Vector((-0.7236073017120361,0.5257253050804138,0.44721952080726624)),
        Vector((0.276388019323349,0.8506492376327515,0.4472198486328125)),
        Vector((0.8944262266159058,0.0,0.44721561670303345)),
        Vector((0.0,0.0,1.0)),
        Vector((-0.2579365074634552,-0.7938604354858398,-0.5506852865219116)),
        Vector((-0.2328215092420578,-0.7165631055831909,-0.6575192213058472)),
        Vector((-0.2006884515285492,-0.6176661252975464,-0.7604029774665833)),
        Vector((-0.16245554387569427,-0.49999526143074036,-0.8506543636322021)),
        Vector((-0.12041264772415161,-0.37059831619262695,-0.9209548234939575)),
        Vector((-0.07760664075613022,-0.23885273933410645,-0.9679497480392456)),
        Vector((-0.036847732961177826,-0.11340758949518204,-0.9928650856018066)),
        Vector((0.09647056460380554,-0.07008914649486542,-0.9928649663925171)),
        Vector((0.2031809240579605,-0.14761784672737122,-0.9679495692253113)),
        Vector((0.3152507543563843,-0.22904038429260254,-0.920954704284668)),
        Vector((0.42532262206077576,-0.3090113699436188,-0.8506541848182678)),
        Vector((0.5254196524620056,-0.38173529505729675,-0.7604027390480042)),
        Vector((0.6095466017723083,-0.4428563714027405,-0.6575188636779785)),
        Vector((0.675299882888794,-0.49062833189964294,-0.5506849884986877)),
        Vector((0.6384524703025818,-0.6040375828742981,-0.47698739171028137)),
        Vector((0.5319408774375916,-0.6817124485969543,-0.5023016929626465)),
        Vector((0.4050084352493286,-0.752338171005249,-0.5195724368095398)),
        Vector((0.2628687620162964,-0.809011697769165,-0.5257376432418823)),
        Vector((0.11456390470266342,-0.8467109799385071,-0.5195724964141846)),
        Vector((-0.029639290645718575,-0.8641842007637024,-0.5023019313812256)),
        Vector((-0.16146525740623474,-0.8639512658119202,-0.47698771953582764)),
        Vector((0.771771252155304,0.4205385744571686,-0.4769868552684784)),
        Vector((0.8127292394638062,0.2952377200126648,-0.5023006200790405)),
        Vector((0.8406726717948914,0.15269432961940765,-0.5195708274841309)),
        Vector((0.8506478667259216,-1.7517470141115155e-08,-0.5257359147071838)),
        Vector((0.8406726717948914,-0.15269434452056885,-0.5195708274841309)),
        Vector((0.8127292394638062,-0.2952377200126648,-0.5023006200790405)),
        Vector((0.771771252155304,-0.4205385744571686,-0.4769868552684784)),
        Vector((0.09647056460380554,0.07008914649486542,-0.9928649663925171)),
        Vector((0.2031809240579605,0.14761784672737122,-0.9679495692253113)),
        Vector((0.3152507543563843,0.22904038429260254,-0.920954704284668)),
        Vector((0.42532262206077576,0.3090113699436188,-0.8506541848182678)),
        Vector((0.5254196524620056,0.38173529505729675,-0.7604027390480042)),
        Vector((0.6095466017723083,0.4428563714027405,-0.6575188636779785)),
        Vector((0.675299882888794,0.49062833189964294,-0.5506849884986877)),
        Vector((-0.8347159028053284,0.0,-0.5506807565689087)),
        Vector((-0.7534416913986206,0.0,-0.657514750957489)),
        Vector((-0.6494559645652771,0.0,-0.7603991627693176)),
        Vector((-0.5257298350334167,0.0,-0.8506516218185425)),
        Vector((-0.3896734416484833,0.0,-0.920953094959259)),
        Vector((-0.2511470317840576,0.0,-0.9679490327835083)),
        Vector((-0.1192450001835823,0.0,-0.9928648471832275)),
        Vector((-0.3771830201148987,-0.7938612699508667,-0.4769876003265381)),
        Vector((-0.4839714467525482,-0.7165645360946655,-0.5023016929626465)),
        Vector((-0.5903657674789429,-0.6176679134368896,-0.5195717811584473)),
        Vector((-0.6881893873214722,-0.4999968707561493,-0.5257361531257629)),
        Vector((-0.7698720693588257,-0.37059953808784485,-0.5195701122283936)),
        Vector((-0.8310506343841553,-0.23885339498519897,-0.5022986531257629)),
        Vector((-0.8715648055076599,-0.11340782791376114,-0.4769837558269501)),
        Vector((-0.2579365074634552,0.7938604354858398,-0.5506852865219116)),
        Vector((-0.2328215092420578,0.7165631055831909,-0.6575192213058472)),
        Vector((-0.2006884515285492,0.6176661252975464,-0.7604029774665833)),
        Vector((-0.16245554387569427,0.49999526143074036,-0.8506543636322021)),
        Vector((-0.12041264772415161,0.37059831619262695,-0.9209548234939575)),
        Vector((-0.07760664075613022,0.23885273933410645,-0.9679497480392456)),
        Vector((-0.036847732961177826,0.11340758949518204,-0.9928650856018066)),
        Vector((-0.8715648055076599,0.11340785026550293,-0.47698381543159485)),
        Vector((-0.8310505747795105,0.23885342478752136,-0.5022986531257629)),
        Vector((-0.7698720097541809,0.37059956789016724,-0.5195701122283936)),
        Vector((-0.6881893277168274,0.49999696016311646,-0.5257362127304077)),
        Vector((-0.5903657078742981,0.6176679134368896,-0.5195717811584473)),
        Vector((-0.48397138714790344,0.7165645360946655,-0.5023016929626465)),
        Vector((-0.3771829903125763,0.7938612699508667,-0.4769876003265381)),
        Vector((-0.16146525740623474,0.8639512658119202,-0.47698771953582764)),
        Vector((-0.029639264568686485,0.8641841411590576,-0.5023019313812256)),
        Vector((0.1145639643073082,0.8467110395431519,-0.5195725560188293)),
        Vector((0.26286882162094116,0.8090116381645203,-0.5257376432418823)),
        Vector((0.405008465051651,0.752338171005249,-0.5195724368095398)),
        Vector((0.5319408774375916,0.6817123889923096,-0.5023016929626465)),
        Vector((0.6384525299072266,0.6040375828742981,-0.47698745131492615)),
        Vector((0.9311879277229309,-0.07008931785821915,0.3577378988265991)),
        Vector((0.956625759601593,-0.147618368268013,0.251149445772171)),
        Vector((0.9647113680839539,-0.22904130816459656,0.12989258766174316)),
        Vector((0.9510578513145447,-0.30901262164115906,-8.758743952341774e-09)),
        Vector((0.9150983095169067,-0.3817366659641266,-0.1298929899930954)),
        Vector((0.8606976270675659,-0.442857563495636,-0.25115084648132324)),
        Vector((0.7945469617843628,-0.4906289875507355,-0.3577406406402588)),
        Vector((0.7945469617843628,0.4906289577484131,-0.3577406406402588)),
        Vector((0.8606976270675659,0.4428575038909912,-0.25115084648132324)),
        Vector((0.9150984287261963,0.3817366361618042,-0.1298929899930954)),
        Vector((0.9510578513145447,0.30901259183883667,8.758743952341774e-09)),
        Vector((0.9647113680839539,0.22904129326343536,0.12989260256290436)),
        Vector((0.956625759601593,0.1476183384656906,0.2511494755744934)),
        Vector((0.9311879277229309,0.07008931040763855,0.3577378988265991)),
        Vector((0.2210889458656311,-0.9072710871696472,0.3577411472797394)),
        Vector((0.1552150994539261,-0.955422043800354,0.25115153193473816)),
        Vector((0.0802759900689125,-0.9882730841636658,0.12989352643489838)),
        Vector((-8.758793690333277e-09,-0.9999999403953552,-8.758793690333277e-09)),
        Vector((-0.0802759900689125,-0.9882729649543762,-0.12989352643489838)),
        Vector((-0.1552150994539261,-0.955422043800354,-0.25115153193473816)),
        Vector((-0.2210889458656311,-0.9072710871696472,-0.3577411472797394)),
        Vector((0.7121502757072449,-0.6040389537811279,-0.3577413558959961)),
        Vector((0.6871585249900818,-0.6817154288291931,-0.2511519193649292)),
        Vector((0.645839273929596,-0.7523425221443176,-0.12989383935928345)),
        Vector((0.587785542011261,-0.809016764163971,8.758819447507449e-09)),
        Vector((0.515945553779602,-0.8467158675193787,0.12989386916160583)),
        Vector((0.4360068142414093,-0.8641878962516785,0.25115203857421875)),
        Vector((0.35440918803215027,-0.8639531135559082,0.3577415645122528)),
        Vector((-0.7945469617843628,-0.4906289577484131,0.3577406406402588)),
        Vector((-0.8606976270675659,-0.4428575038909912,0.25115084648132324)),
        Vector((-0.9150984287261963,-0.3817366361618042,0.1298929899930954)),
        Vector((-0.9510578513145447,-0.30901259183883667,-8.758743952341774e-09)),
        Vector((-0.9647113680839539,-0.22904129326343536,-0.12989260256290436)),
        Vector((-0.956625759601593,-0.1476183384656906,-0.2511494755744934)),
        Vector((-0.9311879277229309,-0.07008931040763855,-0.3577378988265991)),
        Vector((-0.35440918803215027,-0.8639531135559082,-0.3577415645122528)),
        Vector((-0.4360068440437317,-0.8641878366470337,-0.25115203857421875)),
        Vector((-0.5159456729888916,-0.8467158675193787,-0.12989388406276703)),
        Vector((-0.5877856016159058,-0.8090167045593262,8.758819447507449e-09)),
        Vector((-0.645839273929596,-0.7523424029350281,0.12989383935928345)),
        Vector((-0.6871585845947266,-0.6817153096199036,0.2511519491672516)),
        Vector((-0.7121503353118896,-0.6040388941764832,0.3577413558959961)),
        Vector((-0.7121502757072449,0.6040389537811279,0.3577413558959961)),
        Vector((-0.6871585249900818,0.6817154288291931,0.2511519193649292)),
        Vector((-0.645839273929596,0.7523425221443176,0.12989383935928345)),
        Vector((-0.587785542011261,0.809016764163971,-8.758819447507449e-09)),
        Vector((-0.515945553779602,0.8467158675193787,-0.12989386916160583)),
        Vector((-0.4360068142414093,0.8641878962516785,-0.25115203857421875)),
        Vector((-0.35440918803215027,0.8639531135559082,-0.3577415645122528)),
        Vector((-0.9311879277229309,0.07008931785821915,-0.3577378988265991)),
        Vector((-0.956625759601593,0.147618368268013,-0.251149445772171)),
        Vector((-0.9647113680839539,0.22904130816459656,-0.12989258766174316)),
        Vector((-0.9510578513145447,0.30901262164115906,8.758743952341774e-09)),
        Vector((-0.9150983095169067,0.3817366659641266,0.1298929899930954)),
        Vector((-0.8606976270675659,0.442857563495636,0.25115084648132324)),
        Vector((-0.7945469617843628,0.4906289875507355,0.3577406406402588)),
        Vector((0.35440918803215027,0.8639531135559082,0.3577415645122528)),
        Vector((0.4360068440437317,0.8641878366470337,0.25115203857421875)),
        Vector((0.5159456729888916,0.8467158675193787,0.12989388406276703)),
        Vector((0.5877856016159058,0.8090167045593262,-8.758819447507449e-09)),
        Vector((0.645839273929596,0.7523424029350281,-0.12989383935928345)),
        Vector((0.6871585845947266,0.6817153096199036,-0.2511519491672516)),
        Vector((0.7121503353118896,0.6040388941764832,-0.3577413558959961)),
        Vector((-0.2210889458656311,0.9072710871696472,-0.3577411472797394)),
        Vector((-0.1552150994539261,0.955422043800354,-0.25115153193473816)),
        Vector((-0.0802759900689125,0.9882730841636658,-0.12989352643489838)),
        Vector((8.758793690333277e-09,0.9999999403953552,8.758793690333277e-09)),
        Vector((0.0802759900689125,0.9882729649543762,0.12989352643489838)),
        Vector((0.1552150994539261,0.955422043800354,0.25115153193473816)),
        Vector((0.2210889458656311,0.9072710871696472,0.3577411472797394)),
        Vector((0.8715648055076599,-0.11340785026550293,0.47698381543159485)),
        Vector((0.8310505747795105,-0.23885342478752136,0.5022986531257629)),
        Vector((0.7698720097541809,-0.37059956789016724,0.5195701122283936)),
        Vector((0.6881893277168274,-0.49999696016311646,0.5257362127304077)),
        Vector((0.5903657078742981,-0.6176679134368896,0.5195717811584473)),
        Vector((0.48397138714790344,-0.7165645360946655,0.5023016929626465)),
        Vector((0.3771829903125763,-0.7938612699508667,0.4769876003265381)),
        Vector((0.16146525740623474,-0.8639512658119202,0.47698771953582764)),
        Vector((0.029639264568686485,-0.8641841411590576,0.5023019313812256)),
        Vector((-0.1145639643073082,-0.8467110395431519,0.5195725560188293)),
        Vector((-0.26286882162094116,-0.8090116381645203,0.5257376432418823)),
        Vector((-0.405008465051651,-0.752338171005249,0.5195724368095398)),
        Vector((-0.5319408774375916,-0.6817123889923096,0.5023016929626465)),
        Vector((-0.6384525299072266,-0.6040375828742981,0.47698745131492615)),
        Vector((-0.771771252155304,-0.4205385744571686,0.4769868552684784)),
        Vector((-0.8127292394638062,-0.2952377200126648,0.5023006200790405)),
        Vector((-0.8406726717948914,-0.15269432961940765,0.5195708274841309)),
        Vector((-0.8506478667259216,1.7517470141115155e-08,0.5257359147071838)),
        Vector((-0.8406726717948914,0.15269434452056885,0.5195708274841309)),
        Vector((-0.8127292394638062,0.2952377200126648,0.5023006200790405)),
        Vector((-0.771771252155304,0.4205385744571686,0.4769868552684784)),
        Vector((-0.6384524703025818,0.6040375828742981,0.47698739171028137)),
        Vector((-0.5319408774375916,0.6817124485969543,0.5023016929626465)),
        Vector((-0.4050084352493286,0.752338171005249,0.5195724368095398)),
        Vector((-0.2628687620162964,0.809011697769165,0.5257376432418823)),
        Vector((-0.11456390470266342,0.8467109799385071,0.5195724964141846)),
        Vector((0.029639290645718575,0.8641842007637024,0.5023019313812256)),
        Vector((0.16146525740623474,0.8639512658119202,0.47698771953582764)),
        Vector((0.3771830201148987,0.7938612699508667,0.4769876003265381)),
        Vector((0.4839714467525482,0.7165645360946655,0.5023016929626465)),
        Vector((0.5903657674789429,0.6176679134368896,0.5195717811584473)),
        Vector((0.6881893873214722,0.4999968707561493,0.5257361531257629)),
        Vector((0.7698720693588257,0.37059953808784485,0.5195701122283936)),
        Vector((0.8310506343841553,0.23885339498519897,0.5022986531257629)),
        Vector((0.8715648055076599,0.11340782791376114,0.4769837558269501)),
        Vector((0.036847736686468124,-0.11340759694576263,0.9928650856018066)),
        Vector((0.07760664075613022,-0.23885273933410645,0.9679496884346008)),
        Vector((0.12041264772415161,-0.37059831619262695,0.9209547638893127)),
        Vector((0.16245554387569427,-0.49999523162841797,0.8506543636322021)),
        Vector((0.2006884664297104,-0.6176660656929016,0.7604029774665833)),
        Vector((0.232821524143219,-0.7165630459785461,0.6575192213058472)),
        Vector((0.2579365372657776,-0.7938604354858398,0.5506852865219116)),
        Vector((0.8347159028053284,0.0,0.5506807565689087)),
        Vector((0.7534416913986206,0.0,0.657514750957489)),
        Vector((0.6494559645652771,0.0,0.7603991627693176)),
        Vector((0.5257298350334167,0.0,0.8506516218185425)),
        Vector((0.3896734416484833,0.0,0.920953094959259)),
        Vector((0.2511470317840576,0.0,0.9679490327835083)),
        Vector((0.1192450001835823,0.0,0.9928648471832275)),
        Vector((-0.09647056460380554,-0.07008914649486542,0.9928649663925171)),
        Vector((-0.2031809240579605,-0.14761784672737122,0.9679495692253113)),
        Vector((-0.3152507543563843,-0.22904038429260254,0.920954704284668)),
        Vector((-0.42532262206077576,-0.3090113699436188,0.8506541848182678)),
        Vector((-0.5254196524620056,-0.38173529505729675,0.7604027390480042)),
        Vector((-0.6095466017723083,-0.4428563714027405,0.6575188636779785)),
        Vector((-0.675299882888794,-0.49062833189964294,0.5506849884986877)),
        Vector((-0.09647056460380554,0.07008914649486542,0.9928649663925171)),
        Vector((-0.2031809240579605,0.14761784672737122,0.9679495692253113)),
        Vector((-0.3152507543563843,0.22904038429260254,0.920954704284668)),
        Vector((-0.42532262206077576,0.3090113699436188,0.8506541848182678)),
        Vector((-0.5254196524620056,0.38173529505729675,0.7604027390480042)),
        Vector((-0.6095466017723083,0.4428563714027405,0.6575188636779785)),
        Vector((-0.675299882888794,0.49062833189964294,0.5506849884986877)),
        Vector((0.036847736686468124,0.11340759694576263,0.9928650856018066)),
        Vector((0.07760664075613022,0.23885273933410645,0.9679496884346008)),
        Vector((0.12041264772415161,0.37059831619262695,0.9209547638893127)),
        Vector((0.16245554387569427,0.49999523162841797,0.8506543636322021)),
        Vector((0.2006884664297104,0.6176660656929016,0.7604029774665833)),
        Vector((0.232821524143219,0.7165630459785461,0.6575192213058472)),
        Vector((0.2579365372657776,0.7938604354858398,0.5506852865219116)),
        Vector((0.16619767248630524,0.12074927240610123,0.9786715507507324)),
        Vector((0.30716726183891296,0.1265178918838501,0.9432080388069153)),
        Vector((0.2152448147535324,0.2530357837677002,0.9432086944580078)),
        Vector((0.45137476921081543,0.12973062694072723,0.8828536868095398)),
        Vector((0.36180031299591064,0.2628629505634308,0.8944291472434998)),
        Vector((0.26286181807518005,0.3891919255256653,0.8828551769256592)),
        Vector((0.5877828598022461,0.12973089516162872,0.7985493540763855)),
        Vector((0.5067286491394043,0.26640263199806213,0.8199120759963989)),
        Vector((0.40995073318481445,0.399603933095932,0.8199129104614258)),
        Vector((0.305013507604599,0.5189236402511597,0.7985517978668213)),
        Vector((0.7062577605247498,0.1265186071395874,0.6965579986572266)),
        Vector((0.6381935477256775,0.2628640830516815,0.7236100435256958)),
        Vector((0.5500081777572632,0.39960482716560364,0.733353316783905)),
        Vector((0.4472092092037201,0.525728166103363,0.7236116528511047)),
        Vector((0.3385685086250305,0.6325930953025818,0.6965611577033997)),
        Vector((0.8010216355323792,0.12075036019086838,0.586330771446228)),
        Vector((0.7473660707473755,0.25303778052330017,0.6143419742584229)),
        Vector((0.672086775302887,0.38919439911842346,0.6299420595169067)),
        Vector((0.5778303742408752,0.5189258456230164,0.6299428343772888)),
        Vector((0.4715990722179413,0.6325944066047668,0.61434406042099)),
        Vector((0.3623656630516052,0.7245020270347595,0.586334228515625)),
        Vector((-0.06348263472318649,0.19537577033042908,0.978671669960022)),
        Vector((-0.02540796995162964,0.33122730255126953,0.9432088136672974)),
        Vector((-0.17413824796676636,0.2829011380672455,0.9432088136672974)),
        Vector((0.01609816774725914,0.46936896443367004,0.8828554153442383)),
        Vector((-0.13819725811481476,0.42531946301460266,0.8944298624992371)),
        Vector((-0.2889159023761749,0.37026217579841614,0.8828552961349487)),
        Vector((0.0582495778799057,0.599100649356842,0.7985520362854004)),
        Vector((-0.09677919000387192,0.5642478466033936,0.8199135661125183)),
        Vector((-0.2533661425113678,0.5133687853813171,0.8199135065078735)),
        Vector((-0.3992724120616913,0.45044028759002686,0.7985519170761108)),
        Vector((0.09791495651006699,0.7107846736907959,0.696561336517334)),
        Vector((-0.052789539098739624,0.688184916973114,0.723612368106842)),
        Vector((-0.21008750796318054,0.646571159362793,0.7333546280860901)),
        Vector((-0.3618036210536957,0.5877784490585327,0.7236122488975525)),
        Vector((-0.49700927734375,0.5174788236618042,0.6965611577033997)),
        Vector((0.13268426060676575,0.7991287112236023,0.5863344669342041)),
        Vector((-0.00970846600830555,0.7889780402183533,0.6143447160720825)),
        Vector((-0.16246283054351807,0.7594580054283142,0.6299439668655396)),
        Vector((-0.3149706721305847,0.7099043130874634,0.62994384765625)),
        Vector((-0.4559023082256317,0.6439983248710632,0.6143444776535034)),
        Vector((-0.5770661234855652,0.5685129165649414,0.5863342881202698)),
        Vector((-0.20543155074119568,0.0,0.9786714911460876)),
        Vector((-0.32286837697029114,0.0781916081905365,0.9432083964347839)),
        Vector((-0.32286837697029114,-0.07819162309169769,0.9432083964347839)),
        Vector((-0.441422700881958,0.16035431623458862,0.882854700088501)),
        Vector((-0.44720983505249023,-1.5667978914279956e-08,0.894429087638855)),
        Vector((-0.441422700881958,-0.16035431623458862,0.882854700088501)),
        Vector((-0.5517793297767639,0.24053187668323517,0.7985512018203735)),
        Vector((-0.5665393471717834,0.08232202380895615,0.8199123740196228)),
        Vector((-0.5665393471717834,-0.08232203871011734,0.8199123740196228)),
        Vector((-0.5517793297767639,-0.24053187668323517,0.7985512018203735)),
        Vector((-0.6457397937774658,0.31276795268058777,0.6965605020523071)),
        Vector((-0.6708166599273682,0.16245701909065247,0.7236109375953674)),
        Vector((-0.6798480153083801,-1.6619770448755844e-08,0.7333530783653259)),
        Vector((-0.6708166599273682,-0.16245707869529724,0.7236109375953674)),
        Vector((-0.6457396745681763,-0.31276795268058777,0.6965603828430176)),
        Vector((-0.7190154790878296,0.37313511967658997,0.5863336324691772)),
        Vector((-0.7533634305000305,0.2345760464668274,0.6143432259559631)),
        Vector((-0.7724922895431519,0.0801774114370346,0.6299422383308411)),
        Vector((-0.7724922895431519,-0.0801774114370346,0.6299422383308411)),
        Vector((-0.7533634305000305,-0.2345760613679886,0.6143432259559631)),
        Vector((-0.7190154790878296,-0.37313511967658997,0.5863336324691772)),
        Vector((-0.06348264217376709,-0.19537577033042908,0.978671669960022)),
        Vector((-0.17413823306560516,-0.28290116786956787,0.9432088136672974)),
        Vector((-0.025407958775758743,-0.3312273621559143,0.9432088136672974)),
        Vector((-0.2889159023761749,-0.37026217579841614,0.8828552961349487)),
        Vector((-0.13819722831249237,-0.42531949281692505,0.8944299221038818)),
        Vector((0.01609816588461399,-0.46936893463134766,0.8828554153442383)),
        Vector((-0.3992723822593689,-0.45044028759002686,0.7985519170761108)),
        Vector((-0.253366082906723,-0.5133687257766724,0.8199135065078735)),
        Vector((-0.09677914530038834,-0.564247727394104,0.8199135661125183)),
        Vector((0.05824961140751839,-0.5991005897521973,0.7985520362854004)),
        Vector((-0.49700927734375,-0.5174788236618042,0.6965611577033997)),
        Vector((-0.3618036210536957,-0.5877784490585327,0.7236122488975525)),
        Vector((-0.21008750796318054,-0.6465710997581482,0.7333546280860901)),
        Vector((-0.052789539098739624,-0.6881848573684692,0.723612368106842)),
        Vector((0.09791495651006699,-0.7107846736907959,0.696561336517334)),
        Vector((-0.5770661234855652,-0.5685129165649414,0.5863342881202698)),
        Vector((-0.4559022784233093,-0.6439983248710632,0.6143445372581482)),
        Vector((-0.31497064232826233,-0.7099043130874634,0.6299440264701843)),
        Vector((-0.16246280074119568,-0.7594580054283142,0.6299440264701843)),
        Vector((-0.009708431549370289,-0.7889779806137085,0.6143447160720825)),
        Vector((0.13268427550792694,-0.7991287112236023,0.5863345265388489)),
        Vector((0.16619765758514404,-0.12074927240610123,0.9786715507507324)),
        Vector((0.2152448147535324,-0.2530357837677002,0.9432086944580078)),
        Vector((0.30716726183891296,-0.1265178918838501,0.9432080388069153)),
        Vector((0.26286181807518005,-0.3891919255256653,0.8828551769256592)),
        Vector((0.36180034279823303,-0.2628629505634308,0.8944291472434998)),
        Vector((0.45137476921081543,-0.12973062694072723,0.8828536868095398)),
        Vector((0.305013507604599,-0.5189236402511597,0.7985517978668213)),
        Vector((0.40995076298713684,-0.399603933095932,0.819912850856781)),
        Vector((0.5067286491394043,-0.26640260219573975,0.8199120163917542)),
        Vector((0.5877828598022461,-0.12973088026046753,0.7985493540763855)),
        Vector((0.3385685086250305,-0.6325930953025818,0.6965611577033997)),
        Vector((0.4472092092037201,-0.525728166103363,0.7236116528511047)),
        Vector((0.5500081777572632,-0.399604856967926,0.733353316783905)),
        Vector((0.6381935477256775,-0.2628640830516815,0.7236100435256958)),
        Vector((0.7062577605247498,-0.1265186220407486,0.6965579986572266)),
        Vector((0.3623656630516052,-0.7245020270347595,0.5863341689109802)),
        Vector((0.4715990722179413,-0.6325944662094116,0.61434406042099)),
        Vector((0.5778303742408752,-0.5189259052276611,0.6299428343772888)),
        Vector((0.6720868349075317,-0.3891944885253906,0.6299421191215515)),
        Vector((0.7473660111427307,-0.25303778052330017,0.6143419146537781)),
        Vector((0.8010216951370239,-0.12075036764144897,0.586330771446228)),
        Vector((0.9037396907806396,0.195376455783844,0.3808972239494324)),
        Vector((0.9215078353881836,0.28290241956710815,0.26606282591819763)),
        Vector((0.8549919724464417,0.3312287926673889,0.39909422397613525)),
        Vector((0.9188563227653503,0.3702641427516937,0.13640964031219482)),
        Vector((0.8618042469024658,0.42532187700271606,0.2763961851596832)),
        Vector((0.7824464440345764,0.4693712294101715,0.4092288613319397)),
        Vector((0.8928053975105286,0.4504426419734955,-3.129755299369208e-08)),
        Vector((0.8466597199440002,0.513372004032135,0.14005902409553528)),
        Vector((0.7766301035881042,0.5642513036727905,0.28011810779571533)),
        Vector((0.6881902813911438,0.599103569984436,0.4092296063899994)),
        Vector((0.8452902436256409,0.51748126745224,-0.1330321580171585)),
        Vector((0.8090192675590515,0.587782084941864,0.0)),
        Vector((0.7498822808265686,0.6465755105018616,0.1400594264268875)),
        Vector((0.6708205342292786,0.6881890892982483,0.2763974070549011)),
        Vector((0.5792259573936462,0.7107878923416138,0.3990964889526367)),
        Vector((0.7825014591217041,0.5685149431228638,-0.25393348932266235)),
        Vector((0.7533684372901917,0.6440019607543945,-0.13303242623806)),
        Vector((0.704293429851532,0.7099090218544006,5.1137831746927986e-08)),
        Vector((0.6360882520675659,0.7594630122184753,0.13641062378883362)),
        Vector((0.5538198351860046,0.7889822721481323,0.26606500148773193)),
        Vector((0.4650847017765045,0.7991315126419067,0.3809003531932831)),
        Vector((0.09345106780529022,0.9198816418647766,0.38089999556541443)),
        Vector((0.01569979451596737,0.9638274312019348,0.2660643756389618)),
        Vector((-0.05081630125641823,0.9154998064041138,0.3990963101387024)),
        Vector((-0.06820499151945114,0.988301694393158,0.13641005754470825)),
        Vector((-0.13819849491119385,0.951055109500885,0.27639704942703247)),
        Vector((-0.2046150267124176,0.8891925811767578,0.40923014283180237)),
        Vector((-0.15250857174396515,0.9883021712303162,-3.442731610903138e-07)),
        Vector((-0.22661800682544708,0.9638608694076538,0.14005902409553528)),
        Vector((-0.2966475784778595,0.9129807949066162,0.2801184356212616)),
        Vector((-0.35712355375289917,0.839638888835907,0.40923023223876953)),
        Vector((-0.23094788193702698,0.9638285040855408,-0.13303276896476746)),
        Vector((-0.3090164363384247,0.9510566592216492,-4.919724574392603e-07)),
        Vector((-0.3832067549228668,0.9129819869995117,0.14005909860134125)),
        Vector((-0.4472150504589081,0.8506487607955933,0.2763972580432892)),
        Vector((-0.49701187014579773,0.770520031452179,0.39909639954566956)),
        Vector((-0.2988852560520172,0.9198831915855408,-0.25393402576446533)),
        Vector((-0.379680335521698,0.9155026078224182,-0.1330329030752182)),
        Vector((-0.4575267434120178,0.8891957998275757,-3.835337736290967e-07)),
        Vector((-0.5257319211959839,0.8396416902542114,0.13641023635864258)),
        Vector((-0.5792287588119507,0.7705216407775879,0.26606470346450806)),
        Vector((-0.6163017749786377,0.6892656683921814,0.38090014457702637)),
        Vector((-0.8459820747375488,0.3731357455253601,0.3808988630771637)),
        Vector((-0.911803662776947,0.31276896595954895,0.2660633325576782)),
        Vector((-0.8863956332206726,0.23457658290863037,0.3990947902202606)),
        Vector((-0.9610079526901245,0.24053287506103516,0.13640950620174408)),
        Vector((-0.9472132325172424,0.1624576449394226,0.27639588713645935)),
        Vector((-0.9089024662971497,0.08017763495445251,0.40922850370407104)),
        Vector((-0.9870594143867493,0.16035498678684235,1.0954136087093502e-07)),
        Vector((-0.9867151379585266,0.08232229948043823,0.1400587409734726)),
        Vector((-0.9599658250808716,-8.033694598452712e-08,0.280117392539978)),
        Vector((-0.9089023470878601,-0.08017761260271072,0.409228652715683)),
        Vector((-0.9880227446556091,0.07819174975156784,-0.133030965924263)),
        Vector((-0.9999999403953552,-3.6077901199860207e-07,6.395627565325412e-07)),
        Vector((-0.9867148995399475,-0.08232277631759644,0.14005929231643677)),
        Vector((-0.9472128748893738,-0.1624578833580017,0.27639660239219666)),
        Vector((-0.8863953948020935,-0.23457662761211395,0.3990953266620636)),
        Vector((-0.9672223329544067,-4.045784294248733e-07,-0.2539307773113251)),
        Vector((-0.9880226850509644,-0.07819267362356186,-0.13303016126155853)),
        Vector((-0.9870592951774597,-0.16035592555999756,1.4574237638953491e-06)),
        Vector((-0.9610076546669006,-0.24053366482257843,0.13641104102134705)),
        Vector((-0.911803126335144,-0.31276944279670715,0.2660646140575409)),
        Vector((-0.8459816575050354,-0.3731359541416168,0.380899578332901)),
        Vector((-0.6163020730018616,-0.6892655491828918,0.38089999556541443)),
        Vector((-0.5792291760444641,-0.770521342754364,0.26606449484825134)),
        Vector((-0.49701234698295593,-0.7705199122428894,0.39909619092941284)),
        Vector((-0.5257324576377869,-0.8396413326263428,0.1364099681377411)),
        Vector((-0.4472157955169678,-0.8506485223770142,0.27639684081077576)),
        Vector((-0.35712411999702454,-0.8396387696266174,0.40922993421554565)),
        Vector((-0.45752736926078796,-0.8891955614089966,-6.259507472350379e-07)),
        Vector((-0.38320764899253845,-0.9129815697669983,0.14005868136882782)),
        Vector((-0.2966485023498535,-0.9129805564880371,0.2801179885864258)),
        Vector((-0.20461566746234894,-0.889192521572113,0.40922990441322327)),
        Vector((-0.3796807825565338,-0.9155024290084839,-0.13303306698799133)),
        Vector((-0.3090171813964844,-0.9510564208030701,-7.871547040849691e-07)),
        Vector((-0.22661884129047394,-0.9638606309890747,0.14005866646766663)),
        Vector((-0.13819925487041473,-0.9510550498962402,0.276396781206131)),
        Vector((-0.050816766917705536,-0.915499746799469,0.39909616112709045)),
        Vector((-0.2988854944705963,-0.9198830723762512,-0.2539340555667877)),
        Vector((-0.23094826936721802,-0.9638283252716064,-0.13303285837173462)),
        Vector((-0.15250909328460693,-0.9883021116256714,-4.943312319483084e-07)),
        Vector((-0.06820552796125412,-0.9883017539978027,0.1364099234342575)),
        Vector((0.015699392184615135,-0.9638274312019348,0.26606428623199463)),
        Vector((0.09345085173845291,-0.9198817014694214,0.38089996576309204)),
        Vector((0.46508464217185974,-0.7991315722465515,0.3809000551700592)),
        Vector((0.5538197159767151,-0.7889826893806458,0.266064316034317)),
        Vector((0.5792258977890015,-0.710788369178772,0.3990958333015442)),
        Vector((0.6360878944396973,-0.759463369846344,0.13640964031219482)),
        Vector((0.6708202362060547,-0.6881898045539856,0.27639612555503845)),
        Vector((0.688190221786499,-0.5991043448448181,0.4092288613319397)),
        Vector((0.7042929530143738,-0.7099093794822693,-1.0954139497698634e-06)),
        Vector((0.7498818635940552,-0.646576464176178,0.14005771279335022)),
        Vector((0.7766298055648804,-0.5642523765563965,0.2801164984703064)),
        Vector((0.7824463248252869,-0.46937209367752075,0.4092279374599457)),
        Vector((0.7533678412437439,-0.6440023183822632,-0.13303354382514954)),
        Vector((0.809018611907959,-0.5877830982208252,-1.9022907054022653e-06)),
        Vector((0.846659243106842,-0.5133733749389648,0.14005693793296814)),
        Vector((0.8618040680885315,-0.4253232777118683,0.27639445662498474)),
        Vector((0.8549920916557312,-0.3312295973300934,0.39909330010414124)),
        Vector((0.7825009226799011,-0.5685153007507324,-0.25393447279930115)),
        Vector((0.845289409160614,-0.5174821019172668,-0.13303394615650177)),
        Vector((0.8928046822547913,-0.45044392347335815,-2.2756275939173065e-06)),
        Vector((0.9188560843467712,-0.3702656626701355,0.13640743494033813)),
        Vector((0.9215080142021179,-0.2829037010669708,0.2660611867904663)),
        Vector((0.903739869594574,-0.1953771859407425,0.38089635968208313)),
        Vector((0.2988855540752411,0.9198831915855408,0.2539339065551758)),
        Vector((0.3796808421611786,0.9155024290084839,0.13303260505199432)),
        Vector((0.23094835877418518,0.963828444480896,0.13303250074386597)),
        Vector((0.4575273394584656,0.8891956210136414,-4.545200216199419e-09)),
        Vector((0.30901721119880676,0.9510564208030701,-1.307440585646396e-14)),
        Vector((0.15250910818576813,0.9883021116256714,4.5451740149360376e-09)),
        Vector((0.5257324576377869,0.8396413922309875,-0.1364106386899948)),
        Vector((0.3832074701786041,0.9129815697669983,-0.1400596648454666)),
        Vector((0.22661873698234558,0.9638606309890747,-0.14005959033966064)),
        Vector((0.06820547580718994,0.988301694393158,-0.1364104151725769)),
        Vector((0.5792291164398193,0.7705212831497192,-0.26606500148773193)),
        Vector((0.44721558690071106,0.8506482839584351,-0.2763977348804474)),
        Vector((0.296648234128952,0.9129803776741028,-0.2801189422607422)),
        Vector((0.1381990760564804,0.9510549306869507,-0.27639758586883545)),
        Vector((-0.015699468553066254,0.96382737159729,-0.26606473326683044)),
        Vector((0.616301953792572,0.6892654895782471,-0.3809002935886383)),
        Vector((0.4970121681690216,0.7705198526382446,-0.39909669756889343)),
        Vector((0.35712382197380066,0.8396386504173279,-0.4092305600643158)),
        Vector((0.20461535453796387,0.8891923427581787,-0.409230500459671)),
        Vector((0.05081656202673912,0.9154996871948242,-0.39909660816192627)),
        Vector((-0.09345093369483948,0.9198814630508423,-0.380900114774704)),
        Vector((-0.7825012803077698,0.5685152411460876,0.25393351912498474)),
        Vector((-0.7533679008483887,0.644002377986908,0.1330324411392212)),
        Vector((-0.8452897667884827,0.5174818634986877,0.13303214311599731)),
        Vector((-0.7042927145957947,0.7099096775054932,-4.545214871143344e-09)),
        Vector((-0.8090184330940247,0.5877832770347595,-3.9223242980380296e-14)),
        Vector((-0.8928048610687256,0.4504436254501343,4.54513759962083e-09)),
        Vector((-0.6360872983932495,0.7594637870788574,-0.13641051948070526)),
        Vector((-0.7498810291290283,0.646577000617981,-0.14005939662456512)),
        Vector((-0.8466586470603943,0.5133736729621887,-0.14005912840366364)),
        Vector((-0.9188557863235474,0.37026533484458923,-0.136409729719162)),
        Vector((-0.5538188219070435,0.7889830470085144,-0.2660648822784424)),
        Vector((-0.6708190441131592,0.6881906986236572,-0.27639731764793396)),
        Vector((-0.7766284942626953,0.5642533898353577,-0.2801181375980377)),
        Vector((-0.8618031144142151,0.4253239035606384,-0.27639633417129517)),
        Vector((-0.9215074777603149,0.28290367126464844,-0.26606303453445435)),
        Vector((-0.4650837481021881,0.7991321086883545,-0.38090017437934875)),
        Vector((-0.5792242884635925,0.7107893228530884,-0.39909622073173523)),
        Vector((-0.6881885528564453,0.5991057753562927,-0.409229576587677)),
        Vector((-0.7824448347091675,0.4693736433982849,-0.40922895073890686)),
        Vector((-0.85499107837677,0.3312307894229889,-0.39909446239471436)),
        Vector((-0.903739333152771,0.19537760317325592,-0.3808974325656891)),
        Vector((-0.7825013399124146,-0.5685151219367981,0.25393351912498474)),
        Vector((-0.8452898859977722,-0.517481803894043,0.13303214311599731)),
        Vector((-0.7533679604530334,-0.6440023183822632,0.1330324411392212)),
        Vector((-0.8928048014640808,-0.4504435062408447,-4.54513671144241e-09)),
        Vector((-0.8090184330940247,-0.5877832174301147,4.0157127297914263e-14)),
        Vector((-0.7042927145957947,-0.7099096179008484,4.545215315232554e-09)),
        Vector((-0.9188558459281921,-0.37026533484458923,-0.136409729719162)),
        Vector((-0.8466586470603943,-0.5133736729621887,-0.14005911350250244)),
        Vector((-0.7498810291290283,-0.6465769410133362,-0.14005938172340393)),
        Vector((-0.6360873579978943,-0.7594636678695679,-0.13641051948070526)),
        Vector((-0.9215075373649597,-0.28290364146232605,-0.26606303453445435)),
        Vector((-0.8618031740188599,-0.42532387375831604,-0.27639633417129517)),
        Vector((-0.7766286134719849,-0.5642533302307129,-0.2801181375980377)),
        Vector((-0.6708190441131592,-0.6881906390190125,-0.2763972878456116)),
        Vector((-0.5538188815116882,-0.7889829874038696,-0.2660648822784424)),
        Vector((-0.9037392735481262,-0.19537760317325592,-0.3808974325656891)),
        Vector((-0.8549910187721252,-0.3312307894229889,-0.39909449219703674)),
        Vector((-0.7824448347091675,-0.4693736135959625,-0.40922898054122925)),
        Vector((-0.6881885528564453,-0.5991057753562927,-0.4092296063899994)),
        Vector((-0.5792242884635925,-0.7107893228530884,-0.3990962505340576)),
        Vector((-0.4650837481021881,-0.7991320490837097,-0.38090020418167114)),
        Vector((0.2988855540752411,-0.9198831915855408,0.2539339065551758)),
        Vector((0.2309482991695404,-0.963828444480896,0.13303248584270477)),
        Vector((0.3796807527542114,-0.9155024290084839,0.13303259015083313)),
        Vector((0.15250907838344574,-0.9883021116256714,-4.545173570846828e-09)),
        Vector((0.3090171813964844,-0.9510564208030701,1.4008291868063821e-14)),
        Vector((0.4575273096561432,-0.8891956210136414,4.5452011043778384e-09)),
        Vector((0.06820550560951233,-0.9883017539978027,-0.1364104151725769)),
        Vector((0.22661876678466797,-0.9638606309890747,-0.14005957543849945)),
        Vector((0.38320744037628174,-0.9129815101623535,-0.14005963504314423)),
        Vector((0.5257323980331421,-0.8396413922309875,-0.13641062378883362)),
        Vector((-0.01569944992661476,-0.9638273119926453,-0.2660646438598633)),
        Vector((0.1381990760564804,-0.9510548710823059,-0.2763974964618683)),
        Vector((0.296648234128952,-0.9129804372787476,-0.2801189124584198)),
        Vector((0.4472155272960663,-0.8506483435630798,-0.2763976454734802)),
        Vector((0.5792290568351746,-0.770521342754364,-0.26606494188308716)),
        Vector((-0.09345091879367828,-0.9198815822601318,-0.380900114774704)),
        Vector((0.050816573202610016,-0.9154996275901794,-0.3990965485572815)),
        Vector((0.20461535453796387,-0.8891922831535339,-0.40923044085502625)),
        Vector((0.35712379217147827,-0.8396385908126831,-0.40923047065734863)),
        Vector((0.49701210856437683,-0.7705198526382446,-0.39909666776657104)),
        Vector((0.6163018941879272,-0.6892655491828918,-0.3809002935886383)),
        Vector((0.9672222137451172,-1.5066220271364728e-08,0.2539314329624176)),
        Vector((0.9880226254463196,-0.07819194346666336,0.13303130865097046)),
        Vector((0.9880226254463196,0.07819194346666336,0.13303130865097046)),
        Vector((0.9870593547821045,-0.16035503149032593,-4.545149590029496e-09)),
        Vector((1.0,-1.5667986019707314e-08,4.669423705252205e-16)),
        Vector((0.9870593547821045,0.16035498678684235,4.545149590029496e-09)),
        Vector((0.9610080718994141,-0.24053287506103516,-0.13640962541103363)),
        Vector((0.9867150783538818,-0.0823223888874054,-0.14005857706069946)),
        Vector((0.9867151379585266,0.08232235908508301,-0.14005857706069946)),
        Vector((0.9610080122947693,0.240532785654068,-0.13640959560871124)),
        Vector((0.911803662776947,-0.3127688765525818,-0.26606354117393494)),
        Vector((0.9472131133079529,-0.16245757043361664,-0.2763960063457489)),
        Vector((0.9599657654762268,-3.323955866108008e-08,-0.2801172137260437)),
        Vector((0.9472132325172424,0.16245754063129425,-0.2763960361480713)),
        Vector((0.911803662776947,0.312768816947937,-0.26606354117393494)),
        Vector((0.8459820747375488,-0.37313565611839294,-0.380899041891098)),
        Vector((0.8863955140113831,-0.23457643389701843,-0.39909499883651733)),
        Vector((0.9089024066925049,-0.08017755299806595,-0.4092285633087158)),
        Vector((0.9089024066925049,0.08017755299806595,-0.4092285633087158)),
        Vector((0.8863955140113831,0.23457643389701843,-0.39909499883651733)),
        Vector((0.8459820747375488,0.37313565611839294,-0.380899041891098)),
        Vector((0.5770661234855652,0.5685129761695862,-0.5863341689109802)),
        Vector((0.4970092475414276,0.5174791812896729,-0.6965609192848206)),
        Vector((0.4559022784233093,0.6439986228942871,-0.6143442988395691)),
        Vector((0.3992723226547241,0.4504408836364746,-0.7985515594482422)),
        Vector((0.36180350184440613,0.5877792239189148,-0.72361159324646)),
        Vector((0.31497058272361755,0.7099047899246216,-0.6299434304237366)),
        Vector((0.2889157831668854,0.37026312947273254,-0.8828549385070801)),
        Vector((0.2533658444881439,0.5133700966835022,-0.8199127316474915)),
        Vector((0.21008720993995667,0.6465722322463989,-0.7333536148071289)),
        Vector((0.16246263682842255,0.7594585418701172,-0.6299432516098022)),
        Vector((0.17413800954818726,0.2829022705554962,-0.9432085752487183)),
        Vector((0.13819681107997894,0.4253212809562683,-0.8944291472434998)),
        Vector((0.09677863121032715,0.5642496347427368,-0.819912314414978)),
        Vector((0.0527891144156456,0.6881863474845886,-0.723611056804657)),
        Vector((0.00970824621617794,0.7889786958694458,-0.6143438816070557)),
        Vector((0.06348231434822083,0.1953769475221634,-0.9786714911460876)),
        Vector((0.02540736272931099,0.3312293589115143,-0.9432080984115601)),
        Vector((-0.01609889790415764,0.46937131881713867,-0.8828540444374084)),
        Vector((-0.058250296860933304,0.599102795124054,-0.7985503673553467)),
        Vector((-0.09791545569896698,0.7107861638069153,-0.6965597867965698)),
        Vector((-0.13268449902534485,0.7991294264793396,-0.5863335132598877)),
        Vector((-0.36236658692359924,0.7245014905929565,-0.5863343477249146)),
        Vector((-0.3385693430900574,0.6325925588607788,-0.6965610980987549)),
        Vector((-0.47160059213638306,0.6325932145118713,-0.6143441796302795)),
        Vector((-0.30501431226730347,0.518923282623291,-0.7985517382621765)),
        Vector((-0.4472106099128723,0.5257271528244019,-0.7236115336418152)),
        Vector((-0.5778321027755737,0.5189241170883179,-0.6299427151679993)),
        Vector((-0.2628624439239502,0.3891916871070862,-0.8828551173210144)),
        Vector((-0.40995195508003235,0.3996032178401947,-0.8199126124382019)),
        Vector((-0.550009548664093,0.3996034562587738,-0.7333528995513916)),
        Vector((-0.6720882654190063,0.38919249176979065,-0.6299417018890381)),
        Vector((-0.21524524688720703,0.25303563475608826,-0.9432085752487183)),
        Vector((-0.3618011772632599,0.26286256313323975,-0.8944289088249207)),
        Vector((-0.5067297220230103,0.26640182733535767,-0.819911539554596)),
        Vector((-0.638194739818573,0.26286283135414124,-0.723609447479248)),
        Vector((-0.7473670244216919,0.25303614139556885,-0.6143413782119751)),
        Vector((-0.16619794070720673,0.12074923515319824,-0.9786714315414429)),
        Vector((-0.30716779828071594,0.12651774287223816,-0.9432079195976257)),
        Vector((-0.4513755440711975,0.12973032891750336,-0.8828534483909607)),
        Vector((-0.587783694267273,0.12973037362098694,-0.7985489368438721)),
        Vector((-0.7062584161758423,0.1265178620815277,-0.6965574026107788)),
        Vector((-0.8010220527648926,0.12074943631887436,-0.5863302946090698)),
        Vector((-0.8010219931602478,-0.12074960768222809,-0.5863304138183594)),
        Vector((-0.7062582969665527,-0.12651827931404114,-0.6965575218200684)),
        Vector((-0.7473668456077576,-0.2530365288257599,-0.6143413782119751)),
        Vector((-0.5877835154533386,-0.12973102927207947,-0.7985489964485168)),
        Vector((-0.6381945013999939,-0.2628636658191681,-0.723609209060669)),
        Vector((-0.6720882058143616,-0.38919302821159363,-0.629941463470459)),
        Vector((-0.45137542486190796,-0.129731222987175,-0.8828533291816711)),
        Vector((-0.5067297220230103,-0.2664031982421875,-0.8199112415313721)),
        Vector((-0.5500094890594482,-0.3996047377586365,-0.7333523035049438)),
        Vector((-0.5778319835662842,-0.5189248323440552,-0.6299421787261963)),
        Vector((-0.30716776847839355,-0.12651878595352173,-0.9432077407836914)),
        Vector((-0.36180129647254944,-0.26286429166793823,-0.8944283723831177)),
        Vector((-0.40995195508003235,-0.39960500597953796,-0.8199116587638855)),
        Vector((-0.44721052050590515,-0.5257285833358765,-0.7236104607582092)),
        Vector((-0.4716005325317383,-0.6325939297676086,-0.6143434643745422)),
        Vector((-0.16619813442230225,-0.12075037509202957,-0.9786712527275085)),
        Vector((-0.21524566411972046,-0.2530376613140106,-0.9432079792022705)),
        Vector((-0.2628628611564636,-0.3891940712928772,-0.8828539252281189)),
        Vector((-0.30501461029052734,-0.5189254283905029,-0.7985502481460571)),
        Vector((-0.3385694921016693,-0.632594108581543,-0.6965596675872803)),
        Vector((-0.36236661672592163,-0.7245023250579834,-0.5863334536552429)),
        Vector((0.71901535987854,0.3731350898742676,-0.5863335728645325)),
        Vector((0.7533634901046753,0.2345760017633438,-0.6143432259559631)),
        Vector((0.6457397937774658,0.3127678334712982,-0.6965603232383728)),
        Vector((0.772492527961731,0.08017722517251968,-0.6299420595169067)),
        Vector((0.670816957950592,0.16245679557323456,-0.7236106395721436)),
        Vector((0.551779568195343,0.24053171277046204,-0.7985510230064392)),
        Vector((0.7724925875663757,-0.08017772436141968,-0.6299418210983276)),
        Vector((0.6798486113548279,-4.820208232558798e-07,-0.733352541923523)),
        Vector((0.566540002822876,0.08232154697179794,-0.8199118375778198)),
        Vector((0.4414231777191162,0.16035401821136475,-0.8828544616699219)),
        Vector((0.7533637881278992,-0.23457643389701843,-0.6143426299095154)),
        Vector((0.6708175539970398,-0.16245774924755096,-0.7236100435256958)),
        Vector((0.566540539264679,-0.0823228657245636,-0.8199114799499512)),
        Vector((0.44721096754074097,-7.379555313491437e-07,-0.8944284915924072)),
        Vector((0.32286909222602844,0.07819120585918427,-0.9432082176208496)),
        Vector((0.7190158367156982,-0.3731355369091034,-0.5863327383995056)),
        Vector((0.6457407474517822,-0.31276875734329224,-0.6965590715408325)),
        Vector((0.5517808794975281,-0.24053305387496948,-0.7985497713088989)),
        Vector((0.44142448902130127,-0.1603555679321289,-0.882853627204895)),
        Vector((0.32286983728408813,-0.07819262892007828,-0.9432077407836914)),
        Vector((0.20543238520622253,-5.632360284835158e-07,-0.9786713719367981)),
        Vector((-0.13268408179283142,-0.7991288900375366,-0.5863344073295593)),
        Vector((-0.09791456907987595,-0.7107849717140198,-0.6965610980987549)),
        Vector((0.00970886554569006,-0.7889782190322876,-0.6143444180488586)),
        Vector((-0.05824904888868332,-0.5991010665893555,-0.7985516786575317)),
        Vector((0.052790332585573196,-0.6881853938102722,-0.7236118316650391)),
        Vector((0.16246339678764343,-0.7594581842422485,-0.6299435496330261)),
        Vector((-0.016097456216812134,-0.4693695604801178,-0.8828551173210144)),
        Vector((0.09678030759096146,-0.5642486214637756,-0.819912850856781)),
        Vector((0.21008870005607605,-0.6465717554092407,-0.7333537340164185)),
        Vector((0.3149714171886444,-0.7099046111106873,-0.6299432516098022)),
        Vector((0.02540876902639866,-0.33122798800468445,-0.9432085156440735)),
        Vector((0.13819867372512817,-0.4253205955028534,-0.8944292068481445)),
        Vector((0.25336769223213196,-0.5133697986602783,-0.819912314414978)),
        Vector((0.3618049621582031,-0.58777916431427,-0.7236109375953674)),
        Vector((0.455903023481369,-0.6439986228942871,-0.6143436431884766)),
        Vector((0.06348352879285812,-0.19537650048732758,-0.9786714911460876)),
        Vector((0.1741398125886917,-0.28290238976478577,-0.9432081580162048)),
        Vector((0.2889178395271301,-0.37026360630989075,-0.8828540444374084)),
        Vector((0.39927417039871216,-0.45044147968292236,-0.7985502481460571)),
        Vector((0.49701055884361267,-0.517479658126831,-0.6965596675872803)),
        Vector((0.5770666599273682,-0.5685132145881653,-0.5863333344459534)),
        ]

    edges = [[18,0],[25,1],[32,2],[39,1],[46,5],[53,0],[60,3],[67,0],[74,4],[81,5],[88,1],[95,10],[102,2],[109,6],[116,3],[123,7],[130,4],[137,8],[144,5],[151,9],[158,6],[165,7],[172,8],[179,9],[186,10],[193,6],[200,11],[207,7],[214,8],[221,9],[2,12],[12,13],[13,14],[14,15],[15,16],[16,17],[17,18],[0,19],[19,20],[20,21],[21,22],[22,23],[23,24],[24,25],[1,26],[26,27],[27,28],[28,29],[29,30],[30,31],[31,32],[5,33],[33,34],[34,35],[35,36],[36,37],[37,38],[38,39],[0,40],[40,41],[41,42],[42,43],[43,44],[44,45],[45,46],[3,47],[47,48],[48,49],[49,50],[50,51],[51,52],[52,53],[2,54],[54,55],[55,56],[56,57],[57,58],[58,59],[59,60],[4,61],[61,62],[62,63],[63,64],[64,65],[65,66],[66,67],[3,68],[68,69],[69,70],[70,71],[71,72],[72,73],[73,74],[4,75],[75,76],[76,77],[77,78],[78,79],[79,80],[80,81],[10,82],[82,83],[83,84],[84,85],[85,86],[86,87],[87,88],[5,89],[89,90],[90,91],[91,92],[92,93],[93,94],[94,95],[6,96],[96,97],[97,98],[98,99],[99,100],[100,101],[101,102],[1,103],[103,104],[104,105],[105,106],[106,107],[107,108],[108,109],[7,110],[110,111],[111,112],[112,113],[113,114],[114,115],[115,116],[2,117],[117,118],[118,119],[119,120],[120,121],[121,122],[122,123],[8,124],[124,125],[125,126],[126,127],[127,128],[128,129],[129,130],[3,131],[131,132],[132,133],[133,134],[134,135],[135,136],[136,137],[9,138],[138,139],[139,140],[140,141],[141,142],[142,143],[143,144],[4,145],[145,146],[146,147],[147,148],[148,149],[149,150],[150,151],[10,152],[152,153],[153,154],[154,155],[155,156],[156,157],[157,158],[6,159],[159,160],[160,161],[161,162],[162,163],[163,164],[164,165],[7,166],[166,167],[167,168],[168,169],[169,170],[170,171],[171,172],[8,173],[173,174],[174,175],[175,176],[176,177],[177,178],[178,179],[9,180],[180,181],[181,182],[182,183],[183,184],[184,185],[185,186],[11,187],[187,188],[188,189],[189,190],[190,191],[191,192],[192,193],[10,194],[194,195],[195,196],[196,197],[197,198],[198,199],[199,200],[11,201],[201,202],[202,203],[203,204],[204,205],[205,206],[206,207],[11,208],[208,209],[209,210],[210,211],[211,212],[212,213],[213,214],[11,215],[215,216],[216,217],[217,218],[218,219],[219,220],[220,221],[200,215],[222,216],[199,222],[224,217],[198,223],[223,224],[227,218],[197,225],[225,226],[226,227],[231,219],[196,228],[228,229],[229,230],[230,231],[236,220],[195,232],[232,233],[233,234],[234,235],[235,236],[242,221],[194,237],[237,238],[238,239],[239,240],[240,241],[241,242],[200,222],[215,222],[199,223],[222,223],[222,224],[216,224],[198,225],[223,225],[223,226],[224,226],[224,227],[217,227],[197,228],[225,228],[225,229],[226,229],[226,230],[227,230],[227,231],[218,231],[196,232],[228,232],[228,233],[229,233],[229,234],[230,234],[230,235],[231,235],[231,236],[219,236],[195,237],[232,237],[232,238],[233,238],[233,239],[234,239],[234,240],[235,240],[235,241],[236,241],[236,242],[220,242],[194,186],[237,186],[237,185],[238,185],[238,184],[239,184],[239,183],[240,183],[240,182],[241,182],[241,181],[242,181],[242,180],[221,180],[215,208],[243,209],[216,243],[245,210],[217,244],[244,245],[248,211],[218,246],[246,247],[247,248],[252,212],[219,249],[249,250],[250,251],[251,252],[257,213],[220,253],[253,254],[254,255],[255,256],[256,257],[263,214],[221,258],[258,259],[259,260],[260,261],[261,262],[262,263],[215,243],[208,243],[216,244],[243,244],[243,245],[209,245],[217,246],[244,246],[244,247],[245,247],[245,248],[210,248],[218,249],[246,249],[246,250],[247,250],[247,251],[248,251],[248,252],[211,252],[219,253],[249,253],[249,254],[250,254],[250,255],[251,255],[251,256],[252,256],[252,257],[212,257],[220,258],[253,258],[253,259],[254,259],[254,260],[255,260],[255,261],[256,261],[256,262],[257,262],[257,263],[213,263],[221,179],[258,179],[258,178],[259,178],[259,177],[260,177],[260,176],[261,176],[261,175],[262,175],[262,174],[263,174],[263,173],[214,173],[208,201],[264,202],[209,264],[266,203],[210,265],[265,266],[269,204],[211,267],[267,268],[268,269],[273,205],[212,270],[270,271],[271,272],[272,273],[278,206],[213,274],[274,275],[275,276],[276,277],[277,278],[284,207],[214,279],[279,280],[280,281],[281,282],[282,283],[283,284],[208,264],[201,264],[209,265],[264,265],[264,266],[202,266],[210,267],[265,267],[265,268],[266,268],[266,269],[203,269],[211,270],[267,270],[267,271],[268,271],[268,272],[269,272],[269,273],[204,273],[212,274],[270,274],[270,275],[271,275],[271,276],[272,276],[272,277],[273,277],[273,278],[205,278],[213,279],[274,279],[274,280],[275,280],[275,281],[276,281],[276,282],[277,282],[277,283],[278,283],[278,284],[206,284],[214,172],[279,172],[279,171],[280,171],[280,170],[281,170],[281,169],[282,169],[282,168],[283,168],[283,167],[284,167],[284,166],[207,166],[201,187],[285,188],[202,285],[287,189],[203,286],[286,287],[290,190],[204,288],[288,289],[289,290],[294,191],[205,291],[291,292],[292,293],[293,294],[299,192],[206,295],[295,296],[296,297],[297,298],[298,299],[305,193],[207,300],[300,301],[301,302],[302,303],[303,304],[304,305],[201,285],[187,285],[202,286],[285,286],[285,287],[188,287],[203,288],[286,288],[286,289],[287,289],[287,290],[189,290],[204,291],[288,291],[288,292],[289,292],[289,293],[290,293],[290,294],[190,294],[205,295],[291,295],[291,296],[292,296],[292,297],[293,297],[293,298],[294,298],[294,299],[191,299],[206,300],[295,300],[295,301],[296,301],[296,302],[297,302],[297,303],[298,303],[298,304],[299,304],[299,305],[192,305],[207,165],[300,165],[300,164],[301,164],[301,163],[302,163],[302,162],[303,162],[303,161],[304,161],[304,160],[305,160],[305,159],[193,159],[187,200],[306,199],[188,306],[308,198],[189,307],[307,308],[311,197],[190,309],[309,310],[310,311],[315,196],[191,312],[312,313],[313,314],[314,315],[320,195],[192,316],[316,317],[317,318],[318,319],[319,320],[326,194],[193,321],[321,322],[322,323],[323,324],[324,325],[325,326],[187,306],[200,306],[188,307],[306,307],[306,308],[199,308],[189,309],[307,309],[307,310],[308,310],[308,311],[198,311],[190,312],[309,312],[309,313],[310,313],[310,314],[311,314],[311,315],[197,315],[191,316],[312,316],[312,317],[313,317],[313,318],[314,318],[314,319],[315,319],[315,320],[196,320],[192,321],[316,321],[316,322],[317,322],[317,323],[318,323],[318,324],[319,324],[319,325],[320,325],[320,326],[195,326],[193,158],[321,158],[321,157],[322,157],[322,156],[323,156],[323,155],[324,155],[324,154],[325,154],[325,153],[326,153],[326,152],[194,152],[95,186],[327,185],[94,327],[329,184],[93,328],[328,329],[332,183],[92,330],[330,331],[331,332],[336,182],[91,333],[333,334],[334,335],[335,336],[341,181],[90,337],[337,338],[338,339],[339,340],[340,341],[347,180],[89,342],[342,343],[343,344],[344,345],[345,346],[346,347],[95,327],[186,327],[94,328],[327,328],[327,329],[185,329],[93,330],[328,330],[328,331],[329,331],[329,332],[184,332],[92,333],[330,333],[330,334],[331,334],[331,335],[332,335],[332,336],[183,336],[91,337],[333,337],[333,338],[334,338],[334,339],[335,339],[335,340],[336,340],[336,341],[182,341],[90,342],[337,342],[337,343],[338,343],[338,344],[339,344],[339,345],[340,345],[340,346],[341,346],[341,347],[181,347],[89,144],[342,144],[342,143],[343,143],[343,142],[344,142],[344,141],[345,141],[345,140],[346,140],[346,139],[347,139],[347,138],[180,138],[151,179],[348,178],[150,348],[350,177],[149,349],[349,350],[353,176],[148,351],[351,352],[352,353],[357,175],[147,354],[354,355],[355,356],[356,357],[362,174],[146,358],[358,359],[359,360],[360,361],[361,362],[368,173],[145,363],[363,364],[364,365],[365,366],[366,367],[367,368],[151,348],[179,348],[150,349],[348,349],[348,350],[178,350],[149,351],[349,351],[349,352],[350,352],[350,353],[177,353],[148,354],[351,354],[351,355],[352,355],[352,356],[353,356],[353,357],[176,357],[147,358],[354,358],[354,359],[355,359],[355,360],[356,360],[356,361],[357,361],[357,362],[175,362],[146,363],[358,363],[358,364],[359,364],[359,365],[360,365],[360,366],[361,366],[361,367],[362,367],[362,368],[174,368],[145,130],[363,130],[363,129],[364,129],[364,128],[365,128],[365,127],[366,127],[366,126],[367,126],[367,125],[368,125],[368,124],[173,124],[137,172],[369,171],[136,369],[371,170],[135,370],[370,371],[374,169],[134,372],[372,373],[373,374],[378,168],[133,375],[375,376],[376,377],[377,378],[383,167],[132,379],[379,380],[380,381],[381,382],[382,383],[389,166],[131,384],[384,385],[385,386],[386,387],[387,388],[388,389],[137,369],[172,369],[136,370],[369,370],[369,371],[171,371],[135,372],[370,372],[370,373],[371,373],[371,374],[170,374],[134,375],[372,375],[372,376],[373,376],[373,377],[374,377],[374,378],[169,378],[133,379],[375,379],[375,380],[376,380],[376,381],[377,381],[377,382],[378,382],[378,383],[168,383],[132,384],[379,384],[379,385],[380,385],[380,386],[381,386],[381,387],[382,387],[382,388],[383,388],[383,389],[167,389],[131,116],[384,116],[384,115],[385,115],[385,114],[386,114],[386,113],[387,113],[387,112],[388,112],[388,111],[389,111],[389,110],[166,110],[123,165],[390,164],[122,390],[392,163],[121,391],[391,392],[395,162],[120,393],[393,394],[394,395],[399,161],[119,396],[396,397],[397,398],[398,399],[404,160],[118,400],[400,401],[401,402],[402,403],[403,404],[410,159],[117,405],[405,406],[406,407],[407,408],[408,409],[409,410],[123,390],[165,390],[122,391],[390,391],[390,392],[164,392],[121,393],[391,393],[391,394],[392,394],[392,395],[163,395],[120,396],[393,396],[393,397],[394,397],[394,398],[395,398],[395,399],[162,399],[119,400],[396,400],[396,401],[397,401],[397,402],[398,402],[398,403],[399,403],[399,404],[161,404],[118,405],[400,405],[400,406],[401,406],[401,407],[402,407],[402,408],[403,408],[403,409],[404,409],[404,410],[160,410],[117,102],[405,102],[405,101],[406,101],[406,100],[407,100],[407,99],[408,99],[408,98],[409,98],[409,97],[410,97],[410,96],[159,96],[109,158],[411,157],[108,411],[413,156],[107,412],[412,413],[416,155],[106,414],[414,415],[415,416],[420,154],[105,417],[417,418],[418,419],[419,420],[425,153],[104,421],[421,422],[422,423],[423,424],[424,425],[431,152],[103,426],[426,427],[427,428],[428,429],[429,430],[430,431],[109,411],[158,411],[108,412],[411,412],[411,413],[157,413],[107,414],[412,414],[412,415],[413,415],[413,416],[156,416],[106,417],[414,417],[414,418],[415,418],[415,419],[416,419],[416,420],[155,420],[105,421],[417,421],[417,422],[418,422],[418,423],[419,423],[419,424],[420,424],[420,425],[154,425],[104,426],[421,426],[421,427],[422,427],[422,428],[423,428],[423,429],[424,429],[424,430],[425,430],[425,431],[153,431],[103,88],[426,88],[426,87],[427,87],[427,86],[428,86],[428,85],[429,85],[429,84],[430,84],[430,83],[431,83],[431,82],[152,82],[138,151],[432,150],[139,432],[434,149],[140,433],[433,434],[437,148],[141,435],[435,436],[436,437],[441,147],[142,438],[438,439],[439,440],[440,441],[446,146],[143,442],[442,443],[443,444],[444,445],[445,446],[452,145],[144,447],[447,448],[448,449],[449,450],[450,451],[451,452],[138,432],[151,432],[139,433],[432,433],[432,434],[150,434],[140,435],[433,435],[433,436],[434,436],[434,437],[149,437],[141,438],[435,438],[435,439],[436,439],[436,440],[437,440],[437,441],[148,441],[142,442],[438,442],[438,443],[439,443],[439,444],[440,444],[440,445],[441,445],[441,446],[147,446],[143,447],[442,447],[442,448],[443,448],[443,449],[444,449],[444,450],[445,450],[445,451],[446,451],[446,452],[146,452],[144,81],[447,81],[447,80],[448,80],[448,79],[449,79],[449,78],[450,78],[450,77],[451,77],[451,76],[452,76],[452,75],[145,75],[124,137],[453,136],[125,453],[455,135],[126,454],[454,455],[458,134],[127,456],[456,457],[457,458],[462,133],[128,459],[459,460],[460,461],[461,462],[467,132],[129,463],[463,464],[464,465],[465,466],[466,467],[473,131],[130,468],[468,469],[469,470],[470,471],[471,472],[472,473],[124,453],[137,453],[125,454],[453,454],[453,455],[136,455],[126,456],[454,456],[454,457],[455,457],[455,458],[135,458],[127,459],[456,459],[456,460],[457,460],[457,461],[458,461],[458,462],[134,462],[128,463],[459,463],[459,464],[460,464],[460,465],[461,465],[461,466],[462,466],[462,467],[133,467],[129,468],[463,468],[463,469],[464,469],[464,470],[465,470],[465,471],[466,471],[466,472],[467,472],[467,473],[132,473],[130,74],[468,74],[468,73],[469,73],[469,72],[470,72],[470,71],[471,71],[471,70],[472,70],[472,69],[473,69],[473,68],[131,68],[110,123],[474,122],[111,474],[476,121],[112,475],[475,476],[479,120],[113,477],[477,478],[478,479],[483,119],[114,480],[480,481],[481,482],[482,483],[488,118],[115,484],[484,485],[485,486],[486,487],[487,488],[494,117],[116,489],[489,490],[490,491],[491,492],[492,493],[493,494],[110,474],[123,474],[111,475],[474,475],[474,476],[122,476],[112,477],[475,477],[475,478],[476,478],[476,479],[121,479],[113,480],[477,480],[477,481],[478,481],[478,482],[479,482],[479,483],[120,483],[114,484],[480,484],[480,485],[481,485],[481,486],[482,486],[482,487],[483,487],[483,488],[119,488],[115,489],[484,489],[484,490],[485,490],[485,491],[486,491],[486,492],[487,492],[487,493],[488,493],[488,494],[118,494],[116,60],[489,60],[489,59],[490,59],[490,58],[491,58],[491,57],[492,57],[492,56],[493,56],[493,55],[494,55],[494,54],[117,54],[96,109],[495,108],[97,495],[497,107],[98,496],[496,497],[500,106],[99,498],[498,499],[499,500],[504,105],[100,501],[501,502],[502,503],[503,504],[509,104],[101,505],[505,506],[506,507],[507,508],[508,509],[515,103],[102,510],[510,511],[511,512],[512,513],[513,514],[514,515],[96,495],[109,495],[97,496],[495,496],[495,497],[108,497],[98,498],[496,498],[496,499],[497,499],[497,500],[107,500],[99,501],[498,501],[498,502],[499,502],[499,503],[500,503],[500,504],[106,504],[100,505],[501,505],[501,506],[502,506],[502,507],[503,507],[503,508],[504,508],[504,509],[105,509],[101,510],[505,510],[505,511],[506,511],[506,512],[507,512],[507,513],[508,513],[508,514],[509,514],[509,515],[104,515],[102,32],[510,32],[510,31],[511,31],[511,30],[512,30],[512,29],[513,29],[513,28],[514,28],[514,27],[515,27],[515,26],[103,26],[82,95],[516,94],[83,516],[518,93],[84,517],[517,518],[521,92],[85,519],[519,520],[520,521],[525,91],[86,522],[522,523],[523,524],[524,525],[530,90],[87,526],[526,527],[527,528],[528,529],[529,530],[536,89],[88,531],[531,532],[532,533],[533,534],[534,535],[535,536],[82,516],[95,516],[83,517],[516,517],[516,518],[94,518],[84,519],[517,519],[517,520],[518,520],[518,521],[93,521],[85,522],[519,522],[519,523],[520,523],[520,524],[521,524],[521,525],[92,525],[86,526],[522,526],[522,527],[523,527],[523,528],[524,528],[524,529],[525,529],[525,530],[91,530],[87,531],[526,531],[526,532],[527,532],[527,533],[528,533],[528,534],[529,534],[529,535],[530,535],[530,536],[90,536],[88,39],[531,39],[531,38],[532,38],[532,37],[533,37],[533,36],[534,36],[534,35],[535,35],[535,34],[536,34],[536,33],[89,33],[46,81],[537,80],[45,537],[539,79],[44,538],[538,539],[542,78],[43,540],[540,541],[541,542],[546,77],[42,543],[543,544],[544,545],[545,546],[551,76],[41,547],[547,548],[548,549],[549,550],[550,551],[557,75],[40,552],[552,553],[553,554],[554,555],[555,556],[556,557],[46,537],[81,537],[45,538],[537,538],[537,539],[80,539],[44,540],[538,540],[538,541],[539,541],[539,542],[79,542],[43,543],[540,543],[540,544],[541,544],[541,545],[542,545],[542,546],[78,546],[42,547],[543,547],[543,548],[544,548],[544,549],[545,549],[545,550],[546,550],[546,551],[77,551],[41,552],[547,552],[547,553],[548,553],[548,554],[549,554],[549,555],[550,555],[550,556],[551,556],[551,557],[76,557],[40,67],[552,67],[552,66],[553,66],[553,65],[554,65],[554,64],[555,64],[555,63],[556,63],[556,62],[557,62],[557,61],[75,61],[61,74],[558,73],[62,558],[560,72],[63,559],[559,560],[563,71],[64,561],[561,562],[562,563],[567,70],[65,564],[564,565],[565,566],[566,567],[572,69],[66,568],[568,569],[569,570],[570,571],[571,572],[578,68],[67,573],[573,574],[574,575],[575,576],[576,577],[577,578],[61,558],[74,558],[62,559],[558,559],[558,560],[73,560],[63,561],[559,561],[559,562],[560,562],[560,563],[72,563],[64,564],[561,564],[561,565],[562,565],[562,566],[563,566],[563,567],[71,567],[65,568],[564,568],[564,569],[565,569],[565,570],[566,570],[566,571],[567,571],[567,572],[70,572],[66,573],[568,573],[568,574],[569,574],[569,575],[570,575],[570,576],[571,576],[571,577],[572,577],[572,578],[69,578],[67,53],[573,53],[573,52],[574,52],[574,51],[575,51],[575,50],[576,50],[576,49],[577,49],[577,48],[578,48],[578,47],[68,47],[47,60],[579,59],[48,579],[581,58],[49,580],[580,581],[584,57],[50,582],[582,583],[583,584],[588,56],[51,585],[585,586],[586,587],[587,588],[593,55],[52,589],[589,590],[590,591],[591,592],[592,593],[599,54],[53,594],[594,595],[595,596],[596,597],[597,598],[598,599],[47,579],[60,579],[48,580],[579,580],[579,581],[59,581],[49,582],[580,582],[580,583],[581,583],[581,584],[58,584],[50,585],[582,585],[582,586],[583,586],[583,587],[584,587],[584,588],[57,588],[51,589],[585,589],[585,590],[586,590],[586,591],[587,591],[587,592],[588,592],[588,593],[56,593],[52,594],[589,594],[589,595],[590,595],[590,596],[591,596],[591,597],[592,597],[592,598],[593,598],[593,599],[55,599],[53,18],[594,18],[594,17],[595,17],[595,16],[596,16],[596,15],[597,15],[597,14],[598,14],[598,13],[599,13],[599,12],[54,12],[33,46],[600,45],[34,600],[602,44],[35,601],[601,602],[605,43],[36,603],[603,604],[604,605],[609,42],[37,606],[606,607],[607,608],[608,609],[614,41],[38,610],[610,611],[611,612],[612,613],[613,614],[620,40],[39,615],[615,616],[616,617],[617,618],[618,619],[619,620],[33,600],[46,600],[34,601],[600,601],[600,602],[45,602],[35,603],[601,603],[601,604],[602,604],[602,605],[44,605],[36,606],[603,606],[603,607],[604,607],[604,608],[605,608],[605,609],[43,609],[37,610],[606,610],[606,611],[607,611],[607,612],[608,612],[608,613],[609,613],[609,614],[42,614],[38,615],[610,615],[610,616],[611,616],[611,617],[612,617],[612,618],[613,618],[613,619],[614,619],[614,620],[41,620],[39,25],[615,25],[615,24],[616,24],[616,23],[617,23],[617,22],[618,22],[618,21],[619,21],[619,20],[620,20],[620,19],[40,19],[12,32],[621,31],[13,621],[623,30],[14,622],[622,623],[626,29],[15,624],[624,625],[625,626],[630,28],[16,627],[627,628],[628,629],[629,630],[635,27],[17,631],[631,632],[632,633],[633,634],[634,635],[641,26],[18,636],[636,637],[637,638],[638,639],[639,640],[640,641],[12,621],[32,621],[13,622],[621,622],[621,623],[31,623],[14,624],[622,624],[622,625],[623,625],[623,626],[30,626],[15,627],[624,627],[624,628],[625,628],[625,629],[626,629],[626,630],[29,630],[16,631],[627,631],[627,632],[628,632],[628,633],[629,633],[629,634],[630,634],[630,635],[28,635],[17,636],[631,636],[631,637],[632,637],[632,638],[633,638],[633,639],[634,639],[634,640],[635,640],[635,641],[27,641],[18,19],[636,19],[636,20],[637,20],[637,21],[638,21],[638,22],[639,22],[639,23],[640,23],[640,24],[641,24],[641,25],[26,25]]

    faces = [[0,19,18],[1,25,39],[0,18,53],[0,53,67],[0,67,40],[1,39,88],[2,32,102],[3,60,116],[4,74,130],[5,81,144],[1,88,103],[2,102,117],[3,116,131],[4,130,145],[5,144,89],[6,158,193],[7,165,207],[8,172,214],[9,179,221],[10,186,194],[200,215,11],[199,222,200],[198,223,199],[197,225,198],[196,228,197],[195,232,196],[194,237,195],[200,222,215],[222,216,215],[199,223,222],[223,224,222],[222,224,216],[224,217,216],[198,225,223],[225,226,223],[223,226,224],[226,227,224],[224,227,217],[227,218,217],[197,228,225],[228,229,225],[225,229,226],[229,230,226],[226,230,227],[230,231,227],[227,231,218],[231,219,218],[196,232,228],[232,233,228],[228,233,229],[233,234,229],[229,234,230],[234,235,230],[230,235,231],[235,236,231],[231,236,219],[236,220,219],[195,237,232],[237,238,232],[232,238,233],[238,239,233],[233,239,234],[239,240,234],[234,240,235],[240,241,235],[235,241,236],[241,242,236],[236,242,220],[242,221,220],[194,186,237],[186,185,237],[237,185,238],[185,184,238],[238,184,239],[184,183,239],[239,183,240],[183,182,240],[240,182,241],[182,181,241],[241,181,242],[181,180,242],[242,180,221],[180,9,221],[215,208,11],[216,243,215],[217,244,216],[218,246,217],[219,249,218],[220,253,219],[221,258,220],[215,243,208],[243,209,208],[216,244,243],[244,245,243],[243,245,209],[245,210,209],[217,246,244],[246,247,244],[244,247,245],[247,248,245],[245,248,210],[248,211,210],[218,249,246],[249,250,246],[246,250,247],[250,251,247],[247,251,248],[251,252,248],[248,252,211],[252,212,211],[219,253,249],[253,254,249],[249,254,250],[254,255,250],[250,255,251],[255,256,251],[251,256,252],[256,257,252],[252,257,212],[257,213,212],[220,258,253],[258,259,253],[253,259,254],[259,260,254],[254,260,255],[260,261,255],[255,261,256],[261,262,256],[256,262,257],[262,263,257],[257,263,213],[263,214,213],[221,179,258],[179,178,258],[258,178,259],[178,177,259],[259,177,260],[177,176,260],[260,176,261],[176,175,261],[261,175,262],[175,174,262],[262,174,263],[174,173,263],[263,173,214],[173,8,214],[208,201,11],[209,264,208],[210,265,209],[211,267,210],[212,270,211],[213,274,212],[214,279,213],[208,264,201],[264,202,201],[209,265,264],[265,266,264],[264,266,202],[266,203,202],[210,267,265],[267,268,265],[265,268,266],[268,269,266],[266,269,203],[269,204,203],[211,270,267],[270,271,267],[267,271,268],[271,272,268],[268,272,269],[272,273,269],[269,273,204],[273,205,204],[212,274,270],[274,275,270],[270,275,271],[275,276,271],[271,276,272],[276,277,272],[272,277,273],[277,278,273],[273,278,205],[278,206,205],[213,279,274],[279,280,274],[274,280,275],[280,281,275],[275,281,276],[281,282,276],[276,282,277],[282,283,277],[277,283,278],[283,284,278],[278,284,206],[284,207,206],[214,172,279],[172,171,279],[279,171,280],[171,170,280],[280,170,281],[170,169,281],[281,169,282],[169,168,282],[282,168,283],[168,167,283],[283,167,284],[167,166,284],[284,166,207],[166,7,207],[201,187,11],[202,285,201],[203,286,202],[204,288,203],[205,291,204],[206,295,205],[207,300,206],[201,285,187],[285,188,187],[202,286,285],[286,287,285],[285,287,188],[287,189,188],[203,288,286],[288,289,286],[286,289,287],[289,290,287],[287,290,189],[290,190,189],[204,291,288],[291,292,288],[288,292,289],[292,293,289],[289,293,290],[293,294,290],[290,294,190],[294,191,190],[205,295,291],[295,296,291],[291,296,292],[296,297,292],[292,297,293],[297,298,293],[293,298,294],[298,299,294],[294,299,191],[299,192,191],[206,300,295],[300,301,295],[295,301,296],[301,302,296],[296,302,297],[302,303,297],[297,303,298],[303,304,298],[298,304,299],[304,305,299],[299,305,192],[305,193,192],[207,165,300],[165,164,300],[300,164,301],[164,163,301],[301,163,302],[163,162,302],[302,162,303],[162,161,303],[303,161,304],[161,160,304],[304,160,305],[160,159,305],[305,159,193],[159,6,193],[187,200,11],[188,306,187],[189,307,188],[190,309,189],[191,312,190],[192,316,191],[193,321,192],[187,306,200],[306,199,200],[188,307,306],[307,308,306],[306,308,199],[308,198,199],[189,309,307],[309,310,307],[307,310,308],[310,311,308],[308,311,198],[311,197,198],[190,312,309],[312,313,309],[309,313,310],[313,314,310],[310,314,311],[314,315,311],[311,315,197],[315,196,197],[191,316,312],[316,317,312],[312,317,313],[317,318,313],[313,318,314],[318,319,314],[314,319,315],[319,320,315],[315,320,196],[320,195,196],[192,321,316],[321,322,316],[316,322,317],[322,323,317],[317,323,318],[323,324,318],[318,324,319],[324,325,319],[319,325,320],[325,326,320],[320,326,195],[326,194,195],[193,158,321],[158,157,321],[321,157,322],[157,156,322],[322,156,323],[156,155,323],[323,155,324],[155,154,324],[324,154,325],[154,153,325],[325,153,326],[153,152,326],[326,152,194],[152,10,194],[95,186,10],[94,327,95],[93,328,94],[92,330,93],[91,333,92],[90,337,91],[89,342,90],[95,327,186],[327,185,186],[94,328,327],[328,329,327],[327,329,185],[329,184,185],[93,330,328],[330,331,328],[328,331,329],[331,332,329],[329,332,184],[332,183,184],[92,333,330],[333,334,330],[330,334,331],[334,335,331],[331,335,332],[335,336,332],[332,336,183],[336,182,183],[91,337,333],[337,338,333],[333,338,334],[338,339,334],[334,339,335],[339,340,335],[335,340,336],[340,341,336],[336,341,182],[341,181,182],[90,342,337],[342,343,337],[337,343,338],[343,344,338],[338,344,339],[344,345,339],[339,345,340],[345,346,340],[340,346,341],[346,347,341],[341,347,181],[347,180,181],[89,144,342],[144,143,342],[342,143,343],[143,142,343],[343,142,344],[142,141,344],[344,141,345],[141,140,345],[345,140,346],[140,139,346],[346,139,347],[139,138,347],[347,138,180],[138,9,180],[151,179,9],[150,348,151],[149,349,150],[148,351,149],[147,354,148],[146,358,147],[145,363,146],[151,348,179],[348,178,179],[150,349,348],[349,350,348],[348,350,178],[350,177,178],[149,351,349],[351,352,349],[349,352,350],[352,353,350],[350,353,177],[353,176,177],[148,354,351],[354,355,351],[351,355,352],[355,356,352],[352,356,353],[356,357,353],[353,357,176],[357,175,176],[147,358,354],[358,359,354],[354,359,355],[359,360,355],[355,360,356],[360,361,356],[356,361,357],[361,362,357],[357,362,175],[362,174,175],[146,363,358],[363,364,358],[358,364,359],[364,365,359],[359,365,360],[365,366,360],[360,366,361],[366,367,361],[361,367,362],[367,368,362],[362,368,174],[368,173,174],[145,130,363],[130,129,363],[363,129,364],[129,128,364],[364,128,365],[128,127,365],[365,127,366],[127,126,366],[366,126,367],[126,125,367],[367,125,368],[125,124,368],[368,124,173],[124,8,173],[137,172,8],[136,369,137],[135,370,136],[134,372,135],[133,375,134],[132,379,133],[131,384,132],[137,369,172],[369,171,172],[136,370,369],[370,371,369],[369,371,171],[371,170,171],[135,372,370],[372,373,370],[370,373,371],[373,374,371],[371,374,170],[374,169,170],[134,375,372],[375,376,372],[372,376,373],[376,377,373],[373,377,374],[377,378,374],[374,378,169],[378,168,169],[133,379,375],[379,380,375],[375,380,376],[380,381,376],[376,381,377],[381,382,377],[377,382,378],[382,383,378],[378,383,168],[383,167,168],[132,384,379],[384,385,379],[379,385,380],[385,386,380],[380,386,381],[386,387,381],[381,387,382],[387,388,382],[382,388,383],[388,389,383],[383,389,167],[389,166,167],[131,116,384],[116,115,384],[384,115,385],[115,114,385],[385,114,386],[114,113,386],[386,113,387],[113,112,387],[387,112,388],[112,111,388],[388,111,389],[111,110,389],[389,110,166],[110,7,166],[123,165,7],[122,390,123],[121,391,122],[120,393,121],[119,396,120],[118,400,119],[117,405,118],[123,390,165],[390,164,165],[122,391,390],[391,392,390],[390,392,164],[392,163,164],[121,393,391],[393,394,391],[391,394,392],[394,395,392],[392,395,163],[395,162,163],[120,396,393],[396,397,393],[393,397,394],[397,398,394],[394,398,395],[398,399,395],[395,399,162],[399,161,162],[119,400,396],[400,401,396],[396,401,397],[401,402,397],[397,402,398],[402,403,398],[398,403,399],[403,404,399],[399,404,161],[404,160,161],[118,405,400],[405,406,400],[400,406,401],[406,407,401],[401,407,402],[407,408,402],[402,408,403],[408,409,403],[403,409,404],[409,410,404],[404,410,160],[410,159,160],[117,102,405],[102,101,405],[405,101,406],[101,100,406],[406,100,407],[100,99,407],[407,99,408],[99,98,408],[408,98,409],[98,97,409],[409,97,410],[97,96,410],[410,96,159],[96,6,159],[109,158,6],[108,411,109],[107,412,108],[106,414,107],[105,417,106],[104,421,105],[103,426,104],[109,411,158],[411,157,158],[108,412,411],[412,413,411],[411,413,157],[413,156,157],[107,414,412],[414,415,412],[412,415,413],[415,416,413],[413,416,156],[416,155,156],[106,417,414],[417,418,414],[414,418,415],[418,419,415],[415,419,416],[419,420,416],[416,420,155],[420,154,155],[105,421,417],[421,422,417],[417,422,418],[422,423,418],[418,423,419],[423,424,419],[419,424,420],[424,425,420],[420,425,154],[425,153,154],[104,426,421],[426,427,421],[421,427,422],[427,428,422],[422,428,423],[428,429,423],[423,429,424],[429,430,424],[424,430,425],[430,431,425],[425,431,153],[431,152,153],[103,88,426],[88,87,426],[426,87,427],[87,86,427],[427,86,428],[86,85,428],[428,85,429],[85,84,429],[429,84,430],[84,83,430],[430,83,431],[83,82,431],[431,82,152],[82,10,152],[138,151,9],[139,432,138],[140,433,139],[141,435,140],[142,438,141],[143,442,142],[144,447,143],[138,432,151],[432,150,151],[139,433,432],[433,434,432],[432,434,150],[434,149,150],[140,435,433],[435,436,433],[433,436,434],[436,437,434],[434,437,149],[437,148,149],[141,438,435],[438,439,435],[435,439,436],[439,440,436],[436,440,437],[440,441,437],[437,441,148],[441,147,148],[142,442,438],[442,443,438],[438,443,439],[443,444,439],[439,444,440],[444,445,440],[440,445,441],[445,446,441],[441,446,147],[446,146,147],[143,447,442],[447,448,442],[442,448,443],[448,449,443],[443,449,444],[449,450,444],[444,450,445],[450,451,445],[445,451,446],[451,452,446],[446,452,146],[452,145,146],[144,81,447],[81,80,447],[447,80,448],[80,79,448],[448,79,449],[79,78,449],[449,78,450],[78,77,450],[450,77,451],[77,76,451],[451,76,452],[76,75,452],[452,75,145],[75,4,145],[124,137,8],[125,453,124],[126,454,125],[127,456,126],[128,459,127],[129,463,128],[130,468,129],[124,453,137],[453,136,137],[125,454,453],[454,455,453],[453,455,136],[455,135,136],[126,456,454],[456,457,454],[454,457,455],[457,458,455],[455,458,135],[458,134,135],[127,459,456],[459,460,456],[456,460,457],[460,461,457],[457,461,458],[461,462,458],[458,462,134],[462,133,134],[128,463,459],[463,464,459],[459,464,460],[464,465,460],[460,465,461],[465,466,461],[461,466,462],[466,467,462],[462,467,133],[467,132,133],[129,468,463],[468,469,463],[463,469,464],[469,470,464],[464,470,465],[470,471,465],[465,471,466],[471,472,466],[466,472,467],[472,473,467],[467,473,132],[473,131,132],[130,74,468],[74,73,468],[468,73,469],[73,72,469],[469,72,470],[72,71,470],[470,71,471],[71,70,471],[471,70,472],[70,69,472],[472,69,473],[69,68,473],[473,68,131],[68,3,131],[110,123,7],[111,474,110],[112,475,111],[113,477,112],[114,480,113],[115,484,114],[116,489,115],[110,474,123],[474,122,123],[111,475,474],[475,476,474],[474,476,122],[476,121,122],[112,477,475],[477,478,475],[475,478,476],[478,479,476],[476,479,121],[479,120,121],[113,480,477],[480,481,477],[477,481,478],[481,482,478],[478,482,479],[482,483,479],[479,483,120],[483,119,120],[114,484,480],[484,485,480],[480,485,481],[485,486,481],[481,486,482],[486,487,482],[482,487,483],[487,488,483],[483,488,119],[488,118,119],[115,489,484],[489,490,484],[484,490,485],[490,491,485],[485,491,486],[491,492,486],[486,492,487],[492,493,487],[487,493,488],[493,494,488],[488,494,118],[494,117,118],[116,60,489],[60,59,489],[489,59,490],[59,58,490],[490,58,491],[58,57,491],[491,57,492],[57,56,492],[492,56,493],[56,55,493],[493,55,494],[55,54,494],[494,54,117],[54,2,117],[96,109,6],[97,495,96],[98,496,97],[99,498,98],[100,501,99],[101,505,100],[102,510,101],[96,495,109],[495,108,109],[97,496,495],[496,497,495],[495,497,108],[497,107,108],[98,498,496],[498,499,496],[496,499,497],[499,500,497],[497,500,107],[500,106,107],[99,501,498],[501,502,498],[498,502,499],[502,503,499],[499,503,500],[503,504,500],[500,504,106],[504,105,106],[100,505,501],[505,506,501],[501,506,502],[506,507,502],[502,507,503],[507,508,503],[503,508,504],[508,509,504],[504,509,105],[509,104,105],[101,510,505],[510,511,505],[505,511,506],[511,512,506],[506,512,507],[512,513,507],[507,513,508],[513,514,508],[508,514,509],[514,515,509],[509,515,104],[515,103,104],[102,32,510],[32,31,510],[510,31,511],[31,30,511],[511,30,512],[30,29,512],[512,29,513],[29,28,513],[513,28,514],[28,27,514],[514,27,515],[27,26,515],[515,26,103],[26,1,103],[82,95,10],[83,516,82],[84,517,83],[85,519,84],[86,522,85],[87,526,86],[88,531,87],[82,516,95],[516,94,95],[83,517,516],[517,518,516],[516,518,94],[518,93,94],[84,519,517],[519,520,517],[517,520,518],[520,521,518],[518,521,93],[521,92,93],[85,522,519],[522,523,519],[519,523,520],[523,524,520],[520,524,521],[524,525,521],[521,525,92],[525,91,92],[86,526,522],[526,527,522],[522,527,523],[527,528,523],[523,528,524],[528,529,524],[524,529,525],[529,530,525],[525,530,91],[530,90,91],[87,531,526],[531,532,526],[526,532,527],[532,533,527],[527,533,528],[533,534,528],[528,534,529],[534,535,529],[529,535,530],[535,536,530],[530,536,90],[536,89,90],[88,39,531],[39,38,531],[531,38,532],[38,37,532],[532,37,533],[37,36,533],[533,36,534],[36,35,534],[534,35,535],[35,34,535],[535,34,536],[34,33,536],[536,33,89],[33,5,89],[46,81,5],[45,537,46],[44,538,45],[43,540,44],[42,543,43],[41,547,42],[40,552,41],[46,537,81],[537,80,81],[45,538,537],[538,539,537],[537,539,80],[539,79,80],[44,540,538],[540,541,538],[538,541,539],[541,542,539],[539,542,79],[542,78,79],[43,543,540],[543,544,540],[540,544,541],[544,545,541],[541,545,542],[545,546,542],[542,546,78],[546,77,78],[42,547,543],[547,548,543],[543,548,544],[548,549,544],[544,549,545],[549,550,545],[545,550,546],[550,551,546],[546,551,77],[551,76,77],[41,552,547],[552,553,547],[547,553,548],[553,554,548],[548,554,549],[554,555,549],[549,555,550],[555,556,550],[550,556,551],[556,557,551],[551,557,76],[557,75,76],[40,67,552],[67,66,552],[552,66,553],[66,65,553],[553,65,554],[65,64,554],[554,64,555],[64,63,555],[555,63,556],[63,62,556],[556,62,557],[62,61,557],[557,61,75],[61,4,75],[61,74,4],[62,558,61],[63,559,62],[64,561,63],[65,564,64],[66,568,65],[67,573,66],[61,558,74],[558,73,74],[62,559,558],[559,560,558],[558,560,73],[560,72,73],[63,561,559],[561,562,559],[559,562,560],[562,563,560],[560,563,72],[563,71,72],[64,564,561],[564,565,561],[561,565,562],[565,566,562],[562,566,563],[566,567,563],[563,567,71],[567,70,71],[65,568,564],[568,569,564],[564,569,565],[569,570,565],[565,570,566],[570,571,566],[566,571,567],[571,572,567],[567,572,70],[572,69,70],[66,573,568],[573,574,568],[568,574,569],[574,575,569],[569,575,570],[575,576,570],[570,576,571],[576,577,571],[571,577,572],[577,578,572],[572,578,69],[578,68,69],[67,53,573],[53,52,573],[573,52,574],[52,51,574],[574,51,575],[51,50,575],[575,50,576],[50,49,576],[576,49,577],[49,48,577],[577,48,578],[48,47,578],[578,47,68],[47,3,68],[47,60,3],[48,579,47],[49,580,48],[50,582,49],[51,585,50],[52,589,51],[53,594,52],[47,579,60],[579,59,60],[48,580,579],[580,581,579],[579,581,59],[581,58,59],[49,582,580],[582,583,580],[580,583,581],[583,584,581],[581,584,58],[584,57,58],[50,585,582],[585,586,582],[582,586,583],[586,587,583],[583,587,584],[587,588,584],[584,588,57],[588,56,57],[51,589,585],[589,590,585],[585,590,586],[590,591,586],[586,591,587],[591,592,587],[587,592,588],[592,593,588],[588,593,56],[593,55,56],[52,594,589],[594,595,589],[589,595,590],[595,596,590],[590,596,591],[596,597,591],[591,597,592],[597,598,592],[592,598,593],[598,599,593],[593,599,55],[599,54,55],[53,18,594],[18,17,594],[594,17,595],[17,16,595],[595,16,596],[16,15,596],[596,15,597],[15,14,597],[597,14,598],[14,13,598],[598,13,599],[13,12,599],[599,12,54],[12,2,54],[33,46,5],[34,600,33],[35,601,34],[36,603,35],[37,606,36],[38,610,37],[39,615,38],[33,600,46],[600,45,46],[34,601,600],[601,602,600],[600,602,45],[602,44,45],[35,603,601],[603,604,601],[601,604,602],[604,605,602],[602,605,44],[605,43,44],[36,606,603],[606,607,603],[603,607,604],[607,608,604],[604,608,605],[608,609,605],[605,609,43],[609,42,43],[37,610,606],[610,611,606],[606,611,607],[611,612,607],[607,612,608],[612,613,608],[608,613,609],[613,614,609],[609,614,42],[614,41,42],[38,615,610],[615,616,610],[610,616,611],[616,617,611],[611,617,612],[617,618,612],[612,618,613],[618,619,613],[613,619,614],[619,620,614],[614,620,41],[620,40,41],[39,25,615],[25,24,615],[615,24,616],[24,23,616],[616,23,617],[23,22,617],[617,22,618],[22,21,618],[618,21,619],[21,20,619],[619,20,620],[20,19,620],[620,19,40],[19,0,40],[12,32,2],[13,621,12],[14,622,13],[15,624,14],[16,627,15],[17,631,16],[18,636,17],[12,621,32],[621,31,32],[13,622,621],[622,623,621],[621,623,31],[623,30,31],[14,624,622],[624,625,622],[622,625,623],[625,626,623],[623,626,30],[626,29,30],[15,627,624],[627,628,624],[624,628,625],[628,629,625],[625,629,626],[629,630,626],[626,630,29],[630,28,29],[16,631,627],[631,632,627],[627,632,628],[632,633,628],[628,633,629],[633,634,629],[629,634,630],[634,635,630],[630,635,28],[635,27,28],[17,636,631],[636,637,631],[631,637,632],[637,638,632],[632,638,633],[638,639,633],[633,639,634],[639,640,634],[634,640,635],[640,641,635],[635,641,27],[641,26,27],[18,19,636],[19,20,636],[636,20,637],[20,21,637],[637,21,638],[21,22,638],[638,22,639],[22,23,639],[639,23,640],[23,24,640],[640,24,641],[24,25,641],[641,25,26],[25,1,26]]

    mesh = bpy.data.meshes.new(name="OpenGOAL Actor") # placeholder name. eventually will be the actor type
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

        add_object(self, context)

        return {'FINISHED'}


# Registration

def add_object_button(self, context):
    self.layout.operator(
        OBJECT_OT_add_object.bl_idname,
        text="OpenGOAL Actor",
        icon='EVENT_A')


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
    # Register custom UI
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Scene.my_tool = PointerProperty(type=MyProperties)

    # Register new mesh type
    bpy.utils.register_class(OBJECT_OT_add_object)
    bpy.utils.register_manual_map(add_object_manual_map)
    bpy.types.VIEW3D_MT_mesh_add.append(add_object_button)

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