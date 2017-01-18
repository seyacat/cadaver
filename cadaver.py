bl_info = {
    "name": "Cadaver: Dynamic load and link objects",
    "author": "seyacat (Santiago Andrade)",
    "version": (1, 6),
    "blender": (2, 78, 0),
    "location": "View3D > Toolshelf > Edit Linked Library",
    "description": "Dynamic load and link objects",
    "warning": "",
    "wiki_url": "",
    "category": "Object",
    }

"""
ADD THIS LINE TO PATCH FBX CLEAN EXPORT
io_scene_fbx/__init__.py export execute function

if( "cadaver_limpiar" in dir(bpy.ops.wm) ):
    	     bpy.ops.wm.cadaver_limpiar();
"""

import bpy
import os
import threading
from bpy.app.handlers import persistent
from uuid import getnode as get_mac

import json
import urllib
import urllib.request
import time

    
class PanelCadaver(bpy.types.Panel):
    bl_label = "Cadaver 1.6"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Relations"

    @classmethod
    def poll(cls, context):
        return (True)
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        #icon = "OUTLINER_DATA_" + context.active_object.type

        layout.prop(scene.cadaver, "use_cadaver", text="Active Script")
        if(scene.cadaver.use_cadaver): 
            layout.label("Scene")            
            layout.prop(scene.cadaver, "cadaverizable", text="Linkable Scene")
            #layout.operator("wm.cadaver_makelocalscene", icon="NONE",text="Make Local Scene")
            #if context.active_object is not None and scene.cadaver.cadaverizable:
            if context.active_object is not None:
                layout.label("Selected Object")
                layout.prop(context.active_object, "cadaverizable" , text ="Linkable Ob: %s" % context.active_object.name)
                layout.prop(context.active_object, "cadaver_imported", text="Cadaver Imported")
            #layout.operator("wm.cadaver_makelocalselected", icon="NONE",text="Make Local: %s" % context.active_object.name) 
        layout.label("Actions") 
        if(scene.cadaver.use_cadaver):            
            layout.operator("wm.cadaver_cargar", icon="NONE",text="Load")
            target = context.active_object
        layout.operator("wm.cadaver_limpiar", icon="NONE",text="Clean")
        
        if(scene.cadaver.use_cadaver): 
            #layout.prop(scene.cadaver, "more", text='Advanced')
            #if(scene.cadaver.more):
            layout.prop(scene.cadaver, "as_proxy", text="Import as Proxy")
            layout.prop(scene.cadaver, "update_on_save", text="Load on update")
            layout.prop(scene.cadaver, "update_on_load", text="Load on Open File (Disable for Compatibility)")
            layout.prop(scene.cadaver, "clean_on_exec", text="Force Clean on Load (Recomended for Unity)")
            layout.prop(scene.cadaver, "alerta", text ="Alert Service" )
                     
        
        
 

class CadaverProperties(bpy.types.PropertyGroup):
    use_cadaver = bpy.props.BoolProperty(
        name="Cadaver",
        description="Activa Cadaver en este archivo",
        default=False)
    cadaverizable = bpy.props.BoolProperty(
        name="Cadaverizable",
        description="Incluye escena en otros archivos",
        default=False)   
    update_on_save = bpy.props.BoolProperty(
        name="Update On Save",
        description="Recarga Cadaver al guardar",
        default=True)
    update_on_load = bpy.props.BoolProperty(
        name="Update On Load",
        description="Recarga Cadaver al cargar",
        default=True)
    alerta = bpy.props.BoolProperty(
        name="Alerta",
        description="Alerta de que otra persona usa el archivo",
        default=True)
    en_uso = bpy.props.BoolProperty(
        name="En uso",
        description="Bandera de Alerta",
        default=False)
    mac = bpy.props.StringProperty(
        name="Mac",
        description="Mac de la maquina",
        default="")
    alerta_flag = bpy.props.BoolProperty(
        name="Flag Alerta",
        description="Alerta una sola vez",
        default=True)
    more = bpy.props.BoolProperty(
        name="More Menu",
        description="More Options",
        default=False)
    as_proxy = bpy.props.BoolProperty(
        name="AsProxy",
        description="Import as Proxy",
        default=False)
    clean_on_exec = bpy.props.BoolProperty(
        name="CleanOnExec",
        description="Clean before Execute",
        default=True)
    
        
class CadaverLimpiar(bpy.types.Operator):
    """Limpiar Cadaver"""
    bl_idname = "wm.cadaver_limpiar"
    bl_label = "Cadaver Limpiar"
    @classmethod
    def poll(cls,context):
        return True

    def execute(self, context):
        return self.invoke(context, None)
    def invoke(self,context,event):
        #CLEAN
        for scena in bpy.data.scenes:
            src = scena;
            if(not src.library):
                for ob in src.objects:
                    #src.objects.unlink(ob);
                    if(not ob.library):
                        ob.cadaver_imported = False;
                    if not ob.cadaver_imported:
                        continue
                    
                    obp = ob.proxy
                    for user in ob.users_scene:
                        user.objects.unlink(ob)
                    for user in ob.users_group:
                        user.objects.unlink(ob)
                    ob.user_clear();
                    bpy.data.objects.remove(ob)
                    if obp is not None:
                        for user in obp.users_scene:
                            user.objects.unlink(obp)
                        for user in obp.users_group:
                            user.objects.unlink(obp)
                        obp.user_clear();
                        bpy.data.objects.remove(obp)
            else:
                src.user_clear();
                bpy.data.scenes.remove(src) 
        return {'FINISHED'}

class CadaverCargar(bpy.types.Operator):
    """Cargar Cadaver"""
    bl_idname = "wm.cadaver_cargar"
    bl_label = "Cadaver Cargar"
    @classmethod
    def poll(cls,context):        
        return context
    
    def execute(self, context):
        return self.invoke(context, None)
    def invoke(self,context,event):
        tg = bpy.context.scene  
        active =  bpy.context.scene.objects.active 
        #selected =  bpy.context.selected_objects 
        if not tg.cadaver.use_cadaver:
            return {'FINISHED'}
        #LOAD SCENES
        #for subdir, dirs, files in os.walk( bpy.path.abspath("//") ):
        for file in os.listdir( bpy.path.abspath("//") ):
            if file.endswith(".blend"):
                filepath = "//"+file;
                try:
                    with bpy.data.libraries.load(filepath,True) as (data_from, data_to):
                        data_to.scenes = data_from.scenes
                except:
                    print("ERROR LOAD BLEND "+filepath);
    

        #LINK OBJECTS
        for scena in bpy.data.scenes:
            src = scena;
            if(not src.cadaver.cadaverizable):
                continue;            
            if(src.library):
                #print(src)
                for ob in src.objects:                    
                    if(not ob.cadaverizable or ob.cadaver_imported):
                        continue; 
                    exists = False;
                    for sob in tg.objects:
                        #print(sob.proxy)
                        #print(ob)
                        if ob is sob.proxy:
                            exists=True
                    if exists:
                    	   continue;	           
                    ob.cadaver_imported=True;          
                    layers = []
                    for la in ob.layers:
                        layers.append(la); 
                    try:                         
                        obt = tg.objects.link(ob) 
                        obt.layers = layers;
                        ob.select=True;
                        bpy.context.scene.objects.active=ob
                        
                        if bpy.data.groups['RigidBodyWorld'] is not None: 
                            bpy.ops.object.group_link(group='RigidBodyWorld') 
                        #bpy.context.scene.objects.active.select=False
                        bpy.context.scene.objects.active=bpy.context.scene.objects[ob.name]
                        if(bpy.context.scene.cadaver.as_proxy):
                        	bpy.ops.object.proxy_make()
                        ob.select=False;
                        bpy.context.scene.objects[ob.name].select=False;
                        if(bpy.context.scene.cadaver.as_proxy):
                            bpy.context.scene.objects[ob.name+"_proxy"].select=False;
                    except Exception as inst:
                        #print(inst)
                        #print("Duplicado")
                        pass
                    pass  
                #src.user_clear()
                src.user_clear();
                bpy.data.scenes.remove(src)
            else:
                pass                               
        if active is not None:
            active.select=True;
        bpy.context.scene.objects.active=active        
        for src in bpy.data.scenes:                   
            if(not src.library):                
                for ob in src.objects:
                    if(not ob.library):                      
                        ob.cadaver_imported = False;                    
        return {'FINISHED'}


        
class AlertWorker(threading.Thread):

    def __init__(self):
        #self.values = values
        threading.Thread.__init__(self)

    def run(self):
        if not bpy.context.scene.cadaver.use_cadaver and not bpy.context.scene.cadaver.alerta:
            bpy.context.scene.cadaver.en_uso=False;
            return
        mac = bpy.context.scene.cadaver.mac
        file = bpy.path.basename(bpy.context.blend_data.filepath)
        url = "http://www.seyanim.com/cadaweb/io.php?mac="+mac+"&fila="+file;
        url = urllib.request.urlopen(url)
        #print(file);
        mybytes = url.read()
        mystr = mybytes.decode("utf8")
        url.close()
        dat = json.loads( mystr );
        #print(dat);
        mytime = dat[mac];
        bpy.context.scene.cadaver.en_uso=False;
        for t in dat:            
            if( abs(dat[t] - mytime) < 30 and  t != mac ):
                bpy.context.scene.cadaver.en_uso=True;
            #print(mytime)

class CadaverTimerOperator(bpy.types.Operator):
    """Operator which runs its self from a timer"""
    bl_idname = "wm.cadaver_timer_operator"
    bl_label = "Modal Timer Operator"

    _timer = None
    
    def alerta(self,context):
        # change theme color, silly!
        color = context.user_preferences.themes[0].view_3d.space.gradients.high_gradient
        
                
        if(bpy.context.scene.cadaver.en_uso):
            #bpy.ops.object.dialog_operator('INVOKE_DEFAULT')
            color.r = 0.8;color.g = 0.2275;color.b = 0.2275;
            try:  
            	context.scene.use_autosave = False   
            except:
            	pass        
        else:
            color.r = 0.2275;color.g = 0.2275;color.b = 0.2275;
            #color.h += 0.01
        
        ##REPORTA ACTIVIDAD
        thread = AlertWorker()
        thread.start()

    def modal(self, context, event):
        if event.type == 'TIMER':
            self.alerta(context);
                       

        return {'PASS_THROUGH'}


    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(5, context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)

class CadaverMakeLocalSelected(bpy.types.Operator):
    bl_idname = "wm.cadaver_makelocalselected"
    bl_label = "Make Local Selected"

    def execute(self, context):
        active =  bpy.context.scene.objects.active 
        if active is not None:            
            bpy.ops.object.make_local(type='SELECT_OBDATA_MATERIAL')
            active.cadaver_imported=False;
        return {'FINISHED'}
class CadaverMakeLocalScene(bpy.types.Operator):
    bl_idname = "wm.cadaver_makelocalscene"
    bl_label = "Make Local Scene"

    def execute(self, context):
        active =  bpy.context.scene.objects.active 
        for ob in context.scene.objects:
            bpy.context.scene.objects.active=ob
            bpy.ops.object.make_local(type='SELECT_OBDATA_MATERIAL')
            ob.cadaver_imported=False;
        if active is not None:
            active.select=True;
        bpy.context.scene.objects.active=active
        return {'FINISHED'}



@persistent
def limpiar(scene):
    if bpy.context.scene.cadaver.use_cadaver and bpy.context.scene.cadaver.update_on_save and bpy.context.scene.cadaver.clean_on_exec:
        bpy.ops.wm.cadaver_limpiar('EXEC_DEFAULT')
@persistent
def cargar(scene):
    if bpy.context.scene.cadaver.use_cadaver and bpy.context.scene.cadaver.update_on_save:
        bpy.ops.wm.cadaver_cargar('EXEC_DEFAULT')
        
@persistent
def onload(scene):
    if bpy.context.scene.cadaver.use_cadaver and bpy.context.scene.cadaver.update_on_load:
        if bpy.context.scene.cadaver.clean_on_exec:
            bpy.ops.wm.cadaver_limpiar('EXEC_DEFAULT')
        bpy.ops.wm.cadaver_cargar('EXEC_DEFAULT') 
    bpy.context.scene.cadaver.alerta_flag=False; 
    bpy.context.scene.cadaver.more = False;  
@persistent
def onscene(scene):    
    if bpy.context.scene.cadaver.use_cadaver and not bpy.context.scene.cadaver.alerta_flag:
        bpy.context.scene.cadaver.alerta_flag=True
        bpy.context.scene.cadaver.mac = str(get_mac());
        bpy.ops.wm.cadaver_timer_operator()
           
def register():
    bpy.utils.register_class(CadaverLimpiar)
    bpy.utils.register_class(CadaverCargar)
    bpy.utils.register_class(PanelCadaver)
    bpy.utils.register_class(CadaverProperties)
    bpy.types.Scene.cadaver = bpy.props.PointerProperty(type=CadaverProperties)
    bpy.types.Object.cadaverizable = bpy.props.BoolProperty(name="cadaverizable",
            description="Es el objeto cadaverizable",
            default=True)
    bpy.types.Object.cadaver_imported = bpy.props.BoolProperty(name="cadaverimported",
            description="es el objeto linkeable importado por cadaver",
            default=False)
    bpy.app.handlers.save_pre.append( limpiar );
    bpy.app.handlers.save_post.append( cargar );
    bpy.app.handlers.load_post.append( onload );
    bpy.app.handlers.scene_update_post.append( onscene );
    bpy.utils.register_class(CadaverTimerOperator)
    bpy.utils.register_class(CadaverMakeLocalSelected)
    bpy.utils.register_class(CadaverMakeLocalScene)
    #bpy.utils.register_class(AlertWorker);
    #DEBUG
    
    

def unregister():
    bpy.utils.unregister_class(CadaverLimpiar)
    bpy.utils.unregister_class(CadaverCargar)
    bpy.utils.unregister_class(PanelCadaver)
    bpy.utils.unregister_class(CadaverProperties)
    del bpy.types.Scene.cadaver
    del bpy.types.Object.cadaverizable
    del bpy.types.Object.cadaver_imported
    bpy.app.handlers.save_pre.remove( limpiar );
    bpy.app.handlers.save_post.remove( cargar );
    bpy.app.handlers.load_post.remove( onload );
    bpy.app.handlers.scene_update_post.remove( onscene );
    bpy.utils.unregister_class(CadaverTimerOperator)
    bpy.utils.unregister_class(CadaverMakeLocalSelected);
    bpy.utils.unregister_class(CadaverMakeLocalScene);
    #bpy.utils.unregister_class(AlertWorker)

if __name__ == "__main__":
    register()
