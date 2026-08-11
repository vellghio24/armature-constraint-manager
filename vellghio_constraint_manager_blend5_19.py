bl_info = {
    "name": "Armature Constraint Manager",
    "author": "3D ARTIST VELL GHIO",
    "version": (2, 1),
    "blender": (5, 0, 0),
    "location": "3D Viewport → Sidebar → Constraint Manager",
    "description": "Tab label always visible; content hides when no armature selected",
    "category": "Rigging",
}

import bpy
from bpy.types import PropertyGroup, Panel, Operator
from bpy.props import StringProperty, CollectionProperty, IntProperty


# ─── STORE ARMATURE REFERENCES ───
class ManagedArmature(PropertyGroup):
    name: StringProperty(name="Armature Name")
    obj_name: StringProperty(name="Object Name")


# ─── MAIN PROPERTIES ───
class ConstraintManagerProps(PropertyGroup):
    tracked_armatures: CollectionProperty(type=ManagedArmature)
    active_armature_index: IntProperty(default=0)


# ─── MSGBUS: AUTO-HIGHLIGHT — RE‑SUBSCRIBES ON FILE LOAD ───
MSG_OWNER = object()
_last_active_obj_name = ""


def get_constraint_type_name(constraint_type):
    names = {
        'COPY_LOCATION': "Copy Location",
        'COPY_ROTATION': "Copy Rotation",
        'COPY_SCALE': "Copy Scale",
        'COPY_TRANSFORMS': "Copy Transforms",
        'DAMPED_TRACK': "Damped Track",
        'TRACK_TO': "Track To",
        'IK': "IK",
        'FOLLOW_PATH': "Follow Path",
        'FLOOR': "Floor",
        'CLAMP_TO': "Clamp To",
        'CHILD_OF': "Child Of",
        'ARMATURE': "Armature",
        'ACTION': "Action Constraint",
        'LIMIT_LOCATION': "Limit Location",
        'LIMIT_ROTATION': "Limit Rotation",
        'LIMIT_SCALE': "Limit Scale",
        'LIMIT_TRANSFORM': "Limit Transform",
        'PIVOT': "Pivot",
        'RIGID_BODY_JOINT': "Rigid Body Joint",
        'SHRINKWRAP': "Shrinkwrap",
        'STRETCH_TO': "Stretch To",
    }
    return names.get(constraint_type, constraint_type.replace('_', ' ').title())


def get_armature_constraint_summary(armature_obj):
    summary = {}
    if not armature_obj or armature_obj.type != 'ARMATURE':
        return summary
    for bone in armature_obj.pose.bones:
        for const in bone.constraints:
            ctype = const.type
            if ctype not in summary:
                summary[ctype] = []
            summary[ctype].append((bone, const))
    return summary


def sync_viewport_selection(*args):
    """Auto-highlight armature — NEVER auto-add"""
    global _last_active_obj_name
    ctx = bpy.context
    if not ctx or not ctx.scene:
        return
    obj = ctx.active_object
    if not obj:
        _last_active_obj_name = ""
        return
    if obj.name == _last_active_obj_name:
        return
    _last_active_obj_name = obj.name

    if obj.type == 'ARMATURE':
        props = ctx.scene.constraint_manager_props
        for idx, item in enumerate(props.tracked_armatures):
            if item.obj_name == obj.name:
                if props.active_armature_index != idx:
                    props.active_armature_index = idx
                return


def setup_msgbus():
    bpy.msgbus.clear_by_owner(MSG_OWNER)
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.LayerObjects, "active"),
        owner=MSG_OWNER,
        args=(),
        notify=sync_viewport_selection,
    )


@bpy.app.handlers.persistent
def on_file_load_post(scene, depsgraph):
    setup_msgbus()


# ─── OPERATORS ───
class MGR_OT_AddArmature(Operator):
    bl_idname = "mgr.add_armature"
    bl_label = "Add Armature"

    def execute(self, context):
        obj = context.active_object
        if obj and obj.type == 'ARMATURE':
            props = context.scene.constraint_manager_props
            exists = any(a.obj_name == obj.name for a in props.tracked_armatures)
            if not exists:
                item = props.tracked_armatures.add()
                item.name = obj.name
                item.obj_name = obj.name
                props.active_armature_index = len(props.tracked_armatures) - 1
                self.report({'INFO'}, f"✅ Added: {obj.name}")
            else:
                for i, a in enumerate(props.tracked_armatures):
                    if a.obj_name == obj.name:
                        props.active_armature_index = i
                        break
                self.report({'INFO'}, f"Already in list: {obj.name}")
        else:
            self.report({'WARNING'}, "⚠️ Select an armature in 3D Viewport first!")
        return {'FINISHED'}


class MGR_OT_RefreshConstraints(Operator):
    bl_idname = "mgr.refresh_constraints"
    bl_label = "Refresh Constraints"

    def execute(self, context):
        self.report({'INFO'}, "🔄 Constraints refreshed!")
        return {'FINISHED'}


class MGR_OT_EnableByType(Operator):
    bl_idname = "mgr.enable_by_type"
    bl_label = "Enable All"
    constraint_type: StringProperty()

    def execute(self, context):
        props = context.scene.constraint_manager_props
        idx = props.active_armature_index
        if 0 <= idx < len(props.tracked_armatures):
            arm = bpy.data.objects.get(props.tracked_armatures[idx].obj_name)
            if arm:
                count = 0
                for bone in arm.pose.bones:
                    for const in bone.constraints:
                        if const.type == self.constraint_type:
                            const.mute = False
                            count += 1
                self.report({'INFO'}, f"✅ Enabled {count} constraint(s)")
        return {'FINISHED'}


class MGR_OT_DisableByType(Operator):
    bl_idname = "mgr.disable_by_type"
    bl_label = "Disable All"
    constraint_type: StringProperty()

    def execute(self, context):
        props = context.scene.constraint_manager_props
        idx = props.active_armature_index
        if 0 <= idx < len(props.tracked_armatures):
            arm = bpy.data.objects.get(props.tracked_armatures[idx].obj_name)
            if arm:
                count = 0
                for bone in arm.pose.bones:
                    for const in bone.constraints:
                        if const.type == self.constraint_type:
                            const.mute = True
                            count += 1
                self.report({'INFO'}, f"🛑 Disabled {count} constraint(s)")
        return {'FINISHED'}


class MGR_OT_RemoveArmature(Operator):
    bl_idname = "mgr.remove_armature"
    bl_label = "Remove"
    index: IntProperty()

    def execute(self, context):
        props = context.scene.constraint_manager_props
        if 0 <= self.index < len(props.tracked_armatures):
            props.tracked_armatures.remove(self.index)
            props.active_armature_index = min(props.active_armature_index, len(props.tracked_armatures) - 1)
        return {'FINISHED'}


class MGR_OT_SelectArmature(Operator):
    bl_idname = "mgr.select_armature"
    bl_label = "Select Armature"
    index: IntProperty()

    def execute(self, context):
        context.scene.constraint_manager_props.active_armature_index = self.index
        return {'FINISHED'}


# ─── MAIN PANEL — TAB LABEL ALWAYS VISIBLE ───
class CONSTRAINT_MGR_PT_Panel(Panel):
    bl_label = "Constraint Manager"
    bl_idname = "CONSTRAINT_MGR_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Constraint Manager"

    # ✅ TAB LABEL ALWAYS VISIBLE — NEVER HIDE THE TAB
    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout
        props = context.scene.constraint_manager_props
        active_obj = context.active_object

        # ─── NO ARMATURE SELECTED → SHOW SIMPLE MESSAGE + ADD BUTTON ───
        if not active_obj or active_obj.type != 'ARMATURE' or len(context.selected_objects) == 0:
            box = layout.box()
            box.label(text="⚠️ No Armature Selected", icon='INFO')
            box.label(text="Select an Armature in the 3D Viewport", icon='DOT')
            box.separator()
            box.label(text="Or select an Armature then click below", icon='HELP')
            box.separator()
            box.operator("mgr.add_armature", icon='ADD')
            return

        # ─── ✅ ARMATURE SELECTED → SHOW FULL PANEL ───
        active_viewport_name = active_obj.name

        # Add Armature section
        box = layout.box()
        box.label(text="➕ Add Armature", icon='ARMATURE_DATA')
        box.operator("mgr.add_armature", icon='ADD')

        # Tracked Armatures List
        box = layout.box()
        box.label(text="📋 Tracked Armatures", icon='OUTLINER')

        if len(props.tracked_armatures) == 0:
            box.label(text="No armatures added yet.", icon='INFO')
            box.label(text="Click 'Add Armature' above to begin", icon='DOT')
            return

        for i, item in enumerate(props.tracked_armatures):
            row = box.row()
            is_active_in_manager = (i == props.active_armature_index)
            is_selected_in_viewport = (item.obj_name == active_viewport_name)

            if is_selected_in_viewport:
                row.alert = True
            icon = 'RADIOBUT_ON' if is_active_in_manager else 'RADIOBUT_OFF'

            op = row.operator("mgr.select_armature", text=item.name, icon=icon)
            op.index = i
            rem = row.operator("mgr.remove_armature", text="", icon='X')
            rem.index = i

        # Constraint Summary
        idx = props.active_armature_index
        if 0 <= idx < len(props.tracked_armatures):
            arm_info = props.tracked_armatures[idx]
            arm_obj = bpy.data.objects.get(arm_info.obj_name)

            box = layout.box()
            header = box.row()
            header.label(text=f"🔍 Constraint Summary: {arm_info.name}", icon='CONSTRAINT')
            header.operator("mgr.refresh_constraints", icon='FILE_REFRESH', text="Refresh")

            if not arm_obj:
                box.label(text="Armature not found", icon='ERROR')
                return

            summary = get_armature_constraint_summary(arm_obj)

            if not summary:
                box.label(text="No constraints found on any bone.", icon='INFO')
                return

            for ctype, items in sorted(summary.items()):
                cname = get_constraint_type_name(ctype)
                total = len(items)
                muted = sum(1 for _, c in items if c.mute)
                active_count = total - muted

                row = box.box().row()
                row.label(text=f"{cname}  ({active_count} ON / {muted} OFF)")
                row.operator("mgr.enable_by_type", text="Enable All", icon='CHECKBOX_HLT').constraint_type = ctype
                row.operator("mgr.disable_by_type", text="Disable All", icon='CHECKBOX_DEHLT').constraint_type = ctype


# ─── REGISTRATION ───
classes = (
    ManagedArmature,
    ConstraintManagerProps,
    MGR_OT_AddArmature,
    MGR_OT_RefreshConstraints,
    MGR_OT_EnableByType,
    MGR_OT_DisableByType,
    MGR_OT_RemoveArmature,
    MGR_OT_SelectArmature,
    CONSTRAINT_MGR_PT_Panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.constraint_manager_props = bpy.props.PointerProperty(type=ConstraintManagerProps)
    bpy.app.handlers.load_post.append(on_file_load_post)
    setup_msgbus()


def unregister():
    bpy.msgbus.clear_by_owner(MSG_OWNER)
    if on_file_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(on_file_load_post)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.constraint_manager_props


if __name__ == "__main__":
    register()