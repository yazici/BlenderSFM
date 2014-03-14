import os
import sys
import tempfile
import shutil
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import bpy
import subprocess
import threading
import osmbundler
import osmcmvs

from bpy.props import *

import imp
imp.reload(osmbundler)
imp.reload(osmcmvs)

bpy.types.Scene.photoPath = StringProperty(
    name="Path to photos",
    subtype="DIR_PATH",
    description="Path to the folder containing the JPG photos"
    )

bpy.types.Scene.currentStatus = StringProperty(
    name="Current Status",
    description=""
    )

# ==================================================================================================
# The Start SFM button operator
class StartSFMOperator(bpy.types.Operator):
    bl_idname = "sfm.start"
    bl_label = "Start SFM"
    bl_options = {'UNDO'}
    bl_description = "Start the Structure From Motion process to generate the point cloud"

    def execute(self, context):

        pluginPath = os.path.dirname(os.path.realpath(__file__))
        absolutePhotoPath = os.path.abspath(bpy.path.abspath(context.scene.photoPath))
        outputPath = tempfile.mkdtemp(prefix="blendersfm-")
        thr = threading.Thread(target=self.doSFM, args=(context, pluginPath, absolutePhotoPath, outputPath))
        thr.start()

        return {'FINISHED'}


    def doSFM(self, context, pluginPath, absolutePhotoPath, outputPath):
        print("Starting Structure From Motion")
        photos = osmbundler.getPhotosFromDirectory(absolutePhotoPath)
        numberOfPhotos = photos.__len__()

        # Initialize Bundler
        bundler = osmbundler.OsmBundler(pluginPath, absolutePhotoPath, outputPath, "siftvlfeat", 1200, 1)

        # Prepare photos
        bundler.openFiles()
        for i in range(0, numberOfPhotos):
            print("\n\nProcessing photo {0} of {1}...".format(i+1,numberOfPhotos))
            photoInfo = dict(dirname=absolutePhotoPath, basename=photos[i])
            bundler._preparePhoto(photoInfo)
        bundler.closeFiles()

        # Match features and do bundle adjustment
        print("\n\nMatching features...")
        bundler.matchFeatures()
        bundler.doBundleAdjustment()

        # Multi-view stereo
        cmvs = osmcmvs.OsmCmvs(pluginPath, outputPath, 10)
        cmvs.doBundle2PMVS()
        cmvs.doCMVS()
        bpy.ops.import_mesh.ply(filepath=outputPath + "\\pmvs\\models\\option-0000.ply")

        os.chdir("C:\\")
        print(outputPath)
        print("\nStructure From Motion finished.")

# ==================================================================================================
# The Panel
class OBJECT_PT_Panel(bpy.types.Panel):
    bl_idname = "mesh.point_cloud_add"
    bl_label = "Add Point Cloud"
    bl_description = "Generate a point cloud from photographs"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "photoPath")
        layout.operator("sfm.start")
        layout.label(context.scene.currentStatus)
        layout.label("This will take some time to process.")
        layout.label("For progress details, view the console.")
        layout.label("(Window -> Toggle System Console)")