##
## Convert features to raster for Circuitscape 
## (C) 2013, Brad McRae 
##
#########################################################

import os
import time
import gc
import sys
import traceback
# import numpy as npy
import string
import shutil
import arcpy
# from arcpy.sa import *

# arcpy.CheckOutExtension("spatial")

_SCRIPT_NAME = "convertFCs.py version 2013-05-09"


gwarn = arcpy.AddWarning

GP_NULL = '#'

        
def get_inputs():        
    if len(sys.argv) < 2: #Manual inputs
        ### USER SETTABLE VARIABLES
        templateRaster = 'C:\\Program Files\\Circuitscape\\examples\\habitat.asc'
        # inputFC = 
        # inputField =
        # outputRaster =
        
    else: # Called from ArcToolbox
        templateRaster = sys.argv[1]
        inputFC = sys.argv[2]
        inputField = sys.argv[3]
        outputRaster = sys.argv[4]
    return templateRaster, inputFC, inputField, outputRaster        
        
def convert_fcs():
    try:
        dashline(0)
        gprint('Running script ' + _SCRIPT_NAME)
        templateRaster, inputFC, inputField, outputRaster = get_inputs()
        outputDir, outputFN = os.path.split(outputRaster)
        scratchDir = os.path.join(outputDir,'cs_scratch')
        if not os.path.exists(scratchDir):
            os.mkdir(scratchDir)
        
        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = scratchDir
        arcpy.env.scratchWorkspace = scratchDir
        arcpy.env.pyramid = "NONE"
        arcpy.env.rasterstatistics = "NONE"
        descData = arcpy.Describe(templateRaster)
        SR = descData.spatialReference
        cellSize = descData.meanCellHeight
        
        tempRast = os.path.join(scratchDir,'cs_template')
        if arcpy.Exists(tempRast):
            delete_data(tempRast)
        arcpy.CopyRaster_management(templateRaster,tempRast) 
        arcpy.DefineProjection_management(tempRast, SR)
        templateRaster = tempRast
        arcpy.env.cellSize = cellSize
        arcpy.env.snapRaster = templateRaster
        arcpy.env.extent = templateRaster     
        arcpy.FeatureToRaster_conversion(inputFC, inputField, outputRaster, arcpy.env.cellSize)    
        arcpy.DefineProjection_management(outputRaster, SR)
        delete_dir(scratchDir)
        
        gprint('Raster written to '+outputRaster)
    # Return GEOPROCESSING specific errors
    except arcpy.ExecuteError:
        exit_with_geoproc_error(_SCRIPT_NAME)

    # Return any PYTHON or system specific errors
    except:
        exit_with_python_error(_SCRIPT_NAME)

        
def rasterType(filePath):
    outputFileBase, outputFileExt = os.path.splitext(filePath)        
    if outputFileExt == '.asc' or outputFileExt == '.txt':
        return 'ascii'
    else:
        return 'other'
        

def gprint(string):
    arcpy.AddMessage(string)
    # try:
        # if cfg.LOGMESSAGES:
            # write_log(string)
    # except:
        # pass
 
    
def dashline(lspace=0):
    """Output dashed line in tool output dialog.

       0 = No empty line
       1 = Empty line before
       2 = Empty line after

    """
    if lspace == 1:
        gprint(' ')
    gprint('---------------------------------')
    if lspace == 2:
        gprint(' ')
    
    

def delete_file(file):
    try:
        if os.path.isfile(file):
            os.remove(file)
            gc.collect()
    except:
        pass
    return


def delete_dir(dir):
    try:
        if arcpy.Exists(dir):
            shutil.rmtree(dir)
        return
    except:
        snooze(5)
        try: #Try again following cleanup attempt
            gc.collect()
            shutil.rmtree(dir)
        except:
            pass
        return

def delete_data(dataset):
    try:
        if arcpy.Exists(dataset):
            arcpy.Delete_management(dataset)

            # Users are reporting stray vat and other files.  Below is attempt
            # to rid directory of them as they may be causing grid write
            # problems.
            dir = os.path.dirname(dataset)
            base = os.path.basename(dataset)
            baseName, extension = os.path.splitext(base)
            basepath = os.path.join(dir,baseName)
            fileList = glob.glob(basepath + '.*')
            for item in fileList:
                try:
                    os.remove(item)
                except:
                    pass
            gc.collect()
    except:
        pass


def snooze(sleepTime):
    for i in range(1,int(sleepTime)+1):
        time.sleep(1)
        # Dummy operations to give user ability to cancel:
        installD = arcpy.GetInstallInfo("desktop")

        
def exit_with_geoproc_error(filename):
    """Handle geoprocessor errors and provide details to user"""
    dashline(1)
    gprint('****cs_arc.py failed. Details follow.****')
    dashline()
    tb = sys.exc_info()[2]  # get the traceback object
    # tbinfo contains the error's line number and the code
    tbinfo = traceback.format_tb(tb)[0]
    line = tbinfo.split(", ")[1]
    msg = ("Geoprocessing error on **" + line + "** of " + filename + " ")
                # "in Linkage Mapper Version " + str(cfg.releaseNum) + ":")
    arcpy.AddError(msg)
    # write_log(msg) #xxx
    dashline(1)
    msg=arcpy.GetMessages(2)
    arcpy.AddError(arcpy.GetMessages(2))
    # write_log(msg)
    # for msg in range(0, gp.MessageCount):
        # if gp.GetSeverity(msg) == 2:
            # gp.AddReturnMessage(msg)
            # #write_log(msg) #xxx
    dashline()
    # print_drive_warning()
    # close_log_file()
    exit(1)


def exit_with_python_error(filename):
    """Handle python errors and provide details to user"""
    dashline(1)
    gprint('****cs_arc.py failed. Details follow.****')
    dashline()
    tb = sys.exc_info()[2]  # get the traceback object
    # tbinfo contains the error's line number and the code
    tbinfo = traceback.format_tb(tb)[0]
    line = tbinfo.split(", ")[1]

    err = traceback.format_exc().splitlines()[-1]
    msg = ("Python error on **" + line + "** of " + filename + " ")
                # "in Linkage Mapper Version " + str(cfg.releaseNum) + ":")
    arcpy.AddError(msg)
    arcpy.AddError(err)
    exit(1)
            
convert_fcs()

