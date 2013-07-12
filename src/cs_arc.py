#add option to set core areas to zero 

##
## Circuitscape for ArcGIS (C) 2013, Brad McRae 
##
#########################################################

import os
import time
import gc
import sys
import traceback
from numpy import *
import string
import ConfigParser
import shutil
import arcpy
# from arcpy.sa import *

# arcpy.CheckOutExtension("spatial")

_SCRIPT_NAME = "cs_arc.py version 2013-07-12"


gwarn = arcpy.AddWarning

GP_NULL = '#'

def get_inputs(options):        
    try:
        if len(sys.argv) < 2: #Manual inputs
            ### USER SETTABLE VARIABLES
            options['scenario']='pairwise' # 'pairwise' 'advanced' 'one-to-all' or 'all-to-one'

            # Resistance file
            options['habitat_file']='C:\\Program Files\\Circuitscape\\examples\\habitat.asc'
            options['habitat_map_is_resistances'] = True
            
            # pairwise, all-to-one, and one-to all mode options
            # point_file is the focal node file.  Must be ESRI or ASCII grid format
            options['point_file']='c:\\program files\\circuitscape\\examples\\focal_points_grid.asc' 
            
            # Advanced mode options
            options['source_file']='c:\\program files\\circuitscape\\examples\\sources_grid.asc'
            options['ground_file']='c:\\program files\\circuitscape\\examples\\grounds_grid.asc'
        
            # Short-circuit region file
            options['use_polygons']=False
            options['polygon_file']='(Browse for a short-circuit region file)'

            # Cell connection scheme
            options['connect_four_neighbors_only']=False
            
            # Output options
            options['output_file'] = 'C:\\temp\\test.out'

            # Write current and/or voltage maps
            options['write_cur_maps']=True
            options['write_volt_maps']=False

            # Additional options (from Circuitscape pull-down menu)
            options['print_timings']=True
            options['write_cum_cur_map_only']=True
            options['remove_src_or_gnd']='not entered'
            options['use_variable_source_strengths']=False
            options['variable_source_file']='None'
            options['write_max_cur_maps']=False
            options['set_focal_node_currents_to_zero']=True
            options['use_included_pairs']=False
            options['included_pairs_file']='None'
            
        else: # Called from ArcToolbox
            scenario =sys.argv[1]
            if 'Pairwise' in scenario:
                options['scenario']='pairwise' #'pairwise' 'advanced'... etc
            elif 'Advanced' in scenario:
                options['scenario']='advanced'
            elif 'One-to-all' in scenario:
                options['scenario']='one-to-all'
            else:
                options['scenario']='all-to-one'
            # Resistance file
            options['habitat_file'] = get_file_path(sys.argv[2])  
            if str2bool(sys.argv[3]):
                options['habitat_map_is_resistances'] = False
            # pairwise, all-to-one, and one-to all mode options
            # point_file is the focal node file.  Raster format.
            options['point_file'] = get_file_path(sys.argv[4])  
            
            # Advanced mode options
            options['source_file']=get_file_path(sys.argv[5])
            options['ground_file']=get_file_path(sys.argv[6])

            #Output options
            options['output_file'] = nullstring(sys.argv[7])
            
            options['write_cur_maps'] = str2bool(sys.argv[8])
            options['write_volt_maps'] = str2bool(sys.argv[9])

            # Additional options (most from Circuitscape pull-down menu)
            #Cell connection scheme
            connectionScheme = sys.argv[10]
            if 'EIGHT' in connectionScheme:
                options['connect_four_neighbors_only']=False
            else:
                options['connect_four_neighbors_only']=True
            options['print_timings']=str2bool(sys.argv[11])
            removeGround = str2bool(sys.argv[12])
            removeSource = str2bool(sys.argv[13])
            if removeGround and removeSource:
                options['remove_src_or_gnd'] = 'rmvall'
            elif removeSource:
                options['remove_src_or_gnd'] = 'rmvsrc'
            else:
                options['remove_src_or_gnd'] = 'rmvgnd'

            options['compress_grids']=str2bool(sys.argv[14])
            options['log_transform_maps']=str2bool(sys.argv[15])            
            options['write_cum_cur_map_only']=str2bool(sys.argv[16])
        
            # Beta options
            options['write_max_cur_maps']=str2bool(sys.argv[17])
            options['mask_file']=get_file_path(sys.argv[18])
            if options['mask_file'] != 'None':
                options['use_mask'] = True        
            else: options['use_mask'] = False        
            
            options['variable_source_file']=nullstring(sys.argv[19])
            
            options['included_pairs_file'] =nullstring(sys.argv[20])
            if options['included_pairs_file'] != 'None':
                options['use_included_pairs'] = True               
            else: options['use_included_pairs']=False
            
            #Short-circuit region file
            options['polygon_file']=get_file_path(sys.argv[21])
            if options['polygon_file'] != 'None': 
                options['use_polygons'] = True
            else: options['use_polygons'] = False
            
            # Options not in ArcGIS GUI
            options['set_focal_node_currents_to_zero']=True
            options['solver']='cg+amg'
            options['connect_using_avg_resistances']=True
            options['ground_file_is_resistances']=True
            options['use_unit_currents']=False
            options['use_direct_grounds']=False

        return options

    # Return any PYTHON or system specific errors
    except:
        exit_with_python_error(_SCRIPT_NAME)


def cs_arc():
    try:
        dashline(0)
        gprint('Running script ' + _SCRIPT_NAME)

        options = set_circuitscape_options()
        options = get_inputs(options)
        check_output_dir(options['output_file'])
        useInputAsciis = check_input_rasters(options)

        outputDir, outputFile = os.path.split(options['output_file'])
        scratchDir = os.path.join(outputDir,'cs_scratch')
        if not os.path.exists(scratchDir):
            os.mkdir(scratchDir)
        scratchGDB = os.path.join(scratchDir,'scratch.gdb')
        if not arcpy.Exists(scratchGDB):
            arcpy.CreateFileGDB_management(scratchDir, 'scratch')

        outputFileBase, outputFileExt = os.path.splitext(outputFile)
        configFN = outputFileBase + '.ini'
        
        if not useInputAsciis: #Need to export grids or align them
            options = align_and_export_maps(scratchDir,scratchGDB,options)
        options = change_txt_extensions(scratchDir,options)
        check_location_settings(options)
            # arcpy.FeatureToRaster_conversion(cfg.COREFC, cfg.COREFN,
                                             # s8CoreRasPath, arcpy.env.cellSize)
            # binaryCoreRaster = path.join(cfg.SCRATCHDIR,"core_ras_bin")

            # The following commands cause file lock problems on save.  using gp
            # instead.
            # outCon = arcpy.sa.Con(S8CORE_RAS, 1, "#", "VALUE > 0")
            # outCon.save(binaryCoreRaster)
            # gp.Con_sa(s8CoreRasPath, 1, binaryCoreRaster, "#", "VALUE > 0")
            # outCon = arcpy.sa.Con(Raster(s8CoreRasPath) > 0, 1)
            # outCon.save(binaryCoreRaster)
            # s5corridorRas = path.join(cfg.OUTPUTGDB,cfg.PREFIX + "_corridors")
            
            # if not arcpy.Exists(s5corridorRas):
                # s5corridorRas = path.join(cfg.OUTPUTGDB,cfg.PREFIX + 
                                          # "_lcc_mosaic_int")

            # outCon = arcpy.sa.Con(Raster(s5corridorRas) <= cfg.CWDCUTOFF, Raster(
                                  # resRaster), arcpy.sa.Con(Raster(
                                  # binaryCoreRaster) > 0, Raster(resRaster)))

            # resRasClipPath = path.join(cfg.SCRATCHDIR,'res_ras_clip')
            # outCon.save(resRasClipPath)

            # Produce core raster with same extent as clipped resistance raster
            # added to ensure correct data type- nodata values were positive for 
            # cores otherwise
            # outCon = arcpy.sa.Con(arcpy.sa.IsNull(Raster(s8CoreRasPath)), 
                                  # -9999, Raster(s8CoreRasPath))  
            # outCon.save(s8CoreRasClipped)

            # resNpyFN = 'resistances.npy'
            # resNpyFile = path.join(outputDir, resNpyFN)
            # numElements, numResistanceNodes = export_ras_to_npy(RESRAST,resNpyFile)

            # totMem, availMem = get_mem()
            # # gprint('Total memory: str(totMem))
            # if numResistanceNodes / availMem > 2000000:
                # dashline(1)
                # gwarn('Warning:')
                # gwarn('Circuitscape can only solve 2-3 million nodes')
                # gwarn('per gigabyte of available RAM. \nTotal physical RAM '
                        # 'on your machine is ~' + str(totMem)
                        # + ' GB. \nAvailable memory is ~'+ str(availMem)
                        # + ' GB. \nYour resistance raster has '
                        # + str(numResistanceNodes) + ' nodes.')   
                # dashline(0)

            # coreNpyFN = 'cores.npy'
            # coreNpyFile = path.join(INCIRCUITDIR, coreNpyFN)
            # numElements, numNodes = export_ras_to_npy(s8CoreRasClipped,coreNpyFile)

            # arcpy.env.extent = "MINOF"
        if options['scenario'] != 'advanced':
            options['point_file_contains_polygons']=check_for_focal_regions(options['point_file'])
            if options['point_file_contains_polygons']:
                gprint('Note: Focal node file contains focal REGIONS, i.e. focal nodes consisting of multiple grid cells.')
        
        check_location_settings(options)
        outConfigFile = os.path.join(outputDir, configFN)
        writeCircuitscapeConfigFile(outConfigFile, options)
        # gprint('\nResistance map has ' + str(int(numResistanceNodes)) + ' nodes.') 

        CSPATH = get_cs_path()
        if CSPATH is None:
            msg = ('ERROR: Cannot find Circuitscape installation. '
            'Circuitscape 3.5.8 or greater must be installed.')
            raise RuntimeError(msg)

        dashline(1)
        gprint('If you try to cancel your run and the Arc dialog hangs, ')
        gprint('you can kill Circuitscape by opening Windows Task Manager')
        gprint('and ending the cs_run.exe process.')             
        dashline(0)
        
        call_circuitscape(CSPATH, outConfigFile)

        # delete_dir(scratchDir)
        
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
        

def check_input_rasters(options):
    try:
        useInputAsciis = False
        if rasterType(options['habitat_file']) == 'ascii':
            check_location_settings(options)
            if options['scenario'] != 'advanced' and rasterType(options['point_file']) == 'ascii':
                useInputAsciis = check_headers(options)
            elif rasterType(options['source_file']) == 'ascii' and rasterType(options['ground_file']) == 'ascii':
                useInputAsciis = check_headers(options)
        return useInputAsciis
    except:
        exit_with_python_error(_SCRIPT_NAME)
    

def read_header(filename):
    """Reads header for ASCII grids (standard input) or numpy arrays (used

    for faster read/write when calling Circuitscape from ArcGIS python code).
    
    """    
    try:
        if os.path.isfile(filename)==False:
            raise RuntimeError('File "'  + filename + '" does not exist')
        fileBase, fileExtension = os.path.splitext(filename) 
        if fileExtension == '.npy': #numpy array will have an associated header file
            filename = fileBase + '.hdr'
        
        f = open(filename, 'r')
        try:
            [ign, ncols] = string.split(f.readline())
        except ValueError:
            raise  RuntimeError('Unable to read ASCII grid: "'  + filename + '". If file is a text list, please use .txt extension.')
        ncols = int(ncols)
        [ign, nrows] = string.split(f.readline())
        nrows = int(nrows)
        [ign, xllcorner] = string.split(f.readline())
        xllcorner = float(xllcorner)
        [ign, yllcorner] = string.split(f.readline())
        yllcorner = float(yllcorner)
        [ign, cellsize] = string.split(f.readline())
        cellsize = float(cellsize)
       
        try:
            [ign, nodata] = string.split(f.readline())
            try:
                nodata= int(nodata)
            except ValueError:
                nodata= float(nodata)
        except ValueError:
            nodata=False
      
        f.close()
     
        # print 'header',ncols, nrows, xllcorner, yllcorner, cellsize, nodata 
        return ncols, nrows, xllcorner, yllcorner, cellsize, nodata 

    except:
        exit_with_python_error(_SCRIPT_NAME)
        

def check_headers(options):
    """Checks to make sure headers (with cell size, number of cols, etc) match for input rasters."""  
    try:
        HEADERSMATCH=True
        (ncols, nrows, xllcorner, yllcorner, cellsize, nodata)=read_header(options['habitat_file'])
        if options['use_polygons']==True: 
            (ncols2, nrows2, xllcorner2, yllcorner2, cellsize2, nodata2)=read_header(options['polygon_file'])                        
            if (ncols2!=ncols) or (nrows2!=nrows) or (abs(xllcorner2- xllcorner) > cellsize/3) or (abs(yllcorner2- yllcorner) > cellsize/3) or (cellsize2!=cellsize):
                HEADERSMATCH=False

        if options['scenario'] != 'advanced':
            filename=options['point_file']
            (ncols3, nrows3, xllcorner3, yllcorner3, cellsize3, nodata3)=read_header(options['point_file'])                                    
            if (ncols3!=ncols) or (nrows3!=nrows) or (abs(xllcorner3- xllcorner) > cellsize/3) or (abs(yllcorner3- yllcorner) > cellsize/3) or (cellsize3!=cellsize):
                HEADERSMATCH=False
        else:
            (ncols2, nrows2, xllcorner2, yllcorner2, cellsize2, nodata2)=read_header(options['source_file'])                        
            if (ncols2!=ncols) or (nrows2!=nrows) or (abs(xllcorner2- xllcorner) > cellsize/3) or (abs(yllcorner2- yllcorner) > cellsize/3) or (cellsize2!=cellsize):
                HEADERSMATCH=False
            (ncols2, nrows2, xllcorner2, yllcorner2, cellsize2, nodata2)=read_header(options['ground_file'])                        
            if (ncols2!=ncols) or (nrows2!=nrows) or (abs(xllcorner2- xllcorner) > cellsize/3) or (abs(yllcorner2- yllcorner) > cellsize/3) or (cellsize2!=cellsize):
                HEADERSMATCH=False

        if options['use_mask']==True: 
            (ncols2, nrows2, xllcorner2, yllcorner2, cellsize2, nodata2)=read_header(options['mask_file'])                        
            if (ncols2!=ncols) or (nrows2!=nrows) or (abs(xllcorner2- xllcorner) > cellsize/3) or (abs(yllcorner2- yllcorner) > cellsize/3) or (cellsize2!=cellsize):
                HEADERSMATCH=False

        return HEADERSMATCH
    except:
        exit_with_python_error(_SCRIPT_NAME)

    
def check_location_settings(options):
    """Reads first 7 lines of ASCII grids to ensure decimal points used instad of commas."""    
    try:
        filename = options['habitat_file']
        desc = arcpy.Describe(filename)
        filename = desc.catalogPath
        # filename = filename.replace("\\", "/")
        if os.path.isfile(filename)==False:
            return
        f = open(filename, 'r')
        try:
            [ign,ncols] = string.split(f.readline())
        except ValueError:
            return
        [ign,nrows] = string.split(f.readline())
        [ign,xllcorner] = string.split(f.readline())
        [ign,yllcorner] = string.split(f.readline())
        [ign,cellsize] = string.split(f.readline())
        try:
            [ign,nodata] = string.split(f.readline())
        except:
            pass
        dataLine = f.readline() # Read a line of data to check for commas
        f.close()
        if ',' in xllcorner or ',' in yllcorner or ',' in dataLine:
            msg = 'Commas instead of decimal points found in ASCII input raster. \nPlease change your Windows regional settings to North America before creating ASCII rasters.'
            arcpy.AddError(msg)
            msg2 = 'Commas instead of decimal points found in ASCII input raster. Please change your Windows regional settings to North America before creating ASCII rasters.'
            raise RuntimeError(msg2)

    except:
        exit_with_python_error(_SCRIPT_NAME)


def align_and_export_maps(scratchDir,scratchGDB,options):
    try:
        gprint('Exporting maps')
        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = scratchDir
        arcpy.env.scratchWorkspace = scratchDir
        arcpy.env.pyramid = "NONE"
        arcpy.env.rasterstatistics = "NONE"

        # set the analysis extent and cell size to that of the resistance
        # surface
        descData = arcpy.Describe(options['habitat_file'])
        SR = descData.spatialReference
        cellSize = descData.meanCellHeight
        resRast = os.path.join(scratchGDB,'resistances')
        if arcpy.Exists(resRast):
            delete_data(resRast)
        arcpy.CopyRaster_management(options['habitat_file'],resRast)
        arcpy.DefineProjection_management(resRast, SR)       
        arcpy.env.cellSize = cellSize 
        arcpy.env.snapRaster = resRast
        arcpy.env.extent = resRast # Does not work for asciis or with space in path- that's why copy made above
        resRastAscii = os.path.join(scratchDir,'resistances.asc')
        gprint('Exporting ' + resRast + ' to ' + resRastAscii)
        arcpy.RasterToASCII_conversion(resRast, resRastAscii)
        options['habitat_file'] = resRastAscii
        
        if options['use_polygons']==True:
            polygonFileAscii = os.path.join(scratchDir,'short_circuit_regions.asc')            
            gprint('Exporting ' + options['polygon_file'] + ' to ' + polygonFileAscii)
            arcpy.RasterToASCII_conversion(options['polygon_file'], polygonFileAscii) #Seems to match resistance data even if point file is already ascii
            options['polygon_file'] = polygonFileAscii
            
        if options['scenario'] != 'advanced':
            pointFileAscii = os.path.join(scratchDir,'points.asc')
            
            gprint('Exporting ' + options['point_file'] + ' to ' + pointFileAscii)
            arcpy.RasterToASCII_conversion(options['point_file'], pointFileAscii) #Seems to match resistance data even if point file is already ascii
            options['point_file'] = pointFileAscii
        else:
            groundFileAscii = os.path.join(scratchDir,'grounds.asc')
            gprint('Exporting ' + options['ground_file'] + ' to ' + groundFileAscii)
            arcpy.RasterToASCII_conversion(options['ground_file'], groundFileAscii) #Seems to match resistance data even if point file is already ascii
            options['ground_file'] = groundFileAscii
            sourceFileAscii = os.path.join(scratchDir,'sources.asc')
            gprint('Exporting ' + options['source_file'] + ' to ' + sourceFileAscii)
            arcpy.RasterToASCII_conversion(options['source_file'], sourceFileAscii) #Seems to match resistance data even if point file is already ascii
            options['source_file'] = sourceFileAscii    
        return options
    # Return GEOPROCESSING specific errors
    except arcpy.ExecuteError:
        exit_with_geoproc_error(_SCRIPT_NAME)

    # Return any PYTHON or system specific errors
    except:
        exit_with_python_error(_SCRIPT_NAME)
        
        
def change_txt_extensions(scratchDir, options):  # .txt extensions don't seem to work for direct rastertoascii conversion, may need to assume .asc
    fileExt = extension(options['habitat_file']) 
    if fileExt == '.txt':
        shutil.copyfile(options['habitat_file'],ospath.join(scratchDir,'resistances.asc'))
        options['habitat_file'] = ospath.join(scratchDir,'resistances.asc')
        
    if options['scenario'] != 'advanced':
        if extension(options['point_file']) == '.txt':
            shutil.copyfile(options['point_file'],ospath.join(scratchDir,'points.asc'))
            options['point_file'] = os.path.join(scratchDir,'points.asc')
    else:
        if extension(options['ground_file']) == '.txt':
            shutil.copyfile(options['ground_file'],os.path.join(scratchDir,'grounds.asc')) 
            options['ground_file'] = os.path.join(scratchDir,'grounds.asc')
        if extension(options['source_file']) == '.txt':
            shutil.copyfile(options['source_file'],os.path.join(scratchDir,'sources.asc')) 
            options['source_file'] = os.path.join(scratchDir,'sources.asc')

    return options    
    
    
def extension(filePath):
    fileBase, fileExt = os.path.splitext(filePath)        
    return fileExt

    
def gprint(string):
    arcpy.AddMessage(string)
    # try:
        # if cfg.LOGMESSAGES:
            # write_log(string)
    # except:
        # pass
    
def set_circuitscape_options():
    """Sets default options for calling Circuitscape.

    """
    options = {}
    options['data_type']='raster'
    options['version']='unknown'
    options['low_memory_mode']=False
    options['scenario']='pairwise'
    options['habitat_file']='(Browse for a habitat map file)'
    options['habitat_map_is_resistances']=True
    options['point_file']=('(Browse for file with '
                          'locations of focal points or areas)')
    options['point_file_contains_polygons']=True
    options['connect_four_neighbors_only']=False
    options['connect_using_avg_resistances']=True
    options['use_polygons']=False
    options['polygon_file']='(Browse for a short-circuit region file)'
    options['source_file']='(Browse for a current source file)'
    options['ground_file']='(Browse for a ground point file)'
    options['ground_file_is_resistances']=True
    options['use_unit_currents']=False
    options['use_direct_grounds']=False
    options['remove_src_or_gnd']='not entered'
    options['output_file']='(Choose a base name for output files)'
    options['write_cur_maps']=True
    options['write_cum_cur_map_only']=True
    options['log_transform_maps']=False
    options['write_volt_maps']=False
    options['solver']='cg+amg'
    options['compress_grids']=False
    options['print_timings']=False
    options['use_mask']=False
    options['mask_file']='None'
    options['use_included_pairs']=False
    options['included_pairs_file']='None'
    options['use_variable_source_strengths']=False
    options['variable_source_file']='None'
    options['write_max_cur_maps']=False
    options['set_focal_node_currents_to_zero']=True

    return options

def writeCircuitscapeConfigFile(configFile, options):
    """Creates a configuration file for calling Circuitscape.

    """
    config = ConfigParser.ConfigParser()

    sections={}
    section='Version'
    sections['version']=section

    section='Connection scheme for raster habitat data'
    sections['connect_four_neighbors_only']=section
    sections['connect_using_avg_resistances']=section

    section='Short circuit regions (aka polygons)'
    sections['use_polygons']=section
    sections['polygon_file']=section

    section='Options for advanced mode'
    sections['source_file']=section
    sections['ground_file']=section
    sections['ground_file_is_resistances']=section
    sections['use_unit_currents']=section
    sections['use_direct_grounds']=section
    sections['remove_src_or_gnd']=section

    section='Calculation options'
    sections['solver']=section
    sections['print_timings']=section
    sections['low_memory_mode']=section

    section='Output options'
    sections['output_file']=section
    sections['write_cur_maps']=section
    sections['write_cum_cur_map_only']=section
    sections['log_transform_maps']=section
    sections['write_volt_maps']=section
    sections['compress_grids']=section
    sections['write_max_cur_maps']=section
    sections['set_focal_node_currents_to_zero']=section

    section='Mask file'
    sections['use_mask']=section
    sections['mask_file']=section

    section='Options for pairwise and one-to-all and all-to-one modes'
    sections['use_included_pairs']=section
    sections['included_pairs_file']=section
    sections['point_file']=section
    sections['point_file_contains_polygons']=section

    section='Options for one-to-all and all-to-one modes'
    sections['use_variable_source_strengths']=section
    sections['variable_source_file']=section

    section='Habitat raster or graph'
    sections['habitat_file']=section
    sections['habitat_map_is_resistances']=section

    section="Circuitscape mode"
    sections['scenario']=section
    sections['data_type']=section

    if options['ground_file_is_resistances']=='not entered':
        options['ground_file_is_resistances'] = False
    if options['point_file_contains_polygons']=='not entered':
        options['point_file_contains_polygons'] = False

    for option in sections:
        try:
            config.add_section(sections[option])
        except:
            pass
    for option in sections:
        config.set(sections[option], option, options[option])

    f = open(configFile, 'w')
    config.write(f)
    f.close()
    
    
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
    
    
def get_cs_path():
    """Returns path to Circuitscape installation """
    envList = ["ProgramW6432", "ProgramFiles", "ProgramFiles(x86)"]
    for x in range (0,len(envList)):
        try:
            pfPath = os.environ[envList[x]]
            csPath = os.path.join(pfPath,'Circuitscape\\cs_run.exe')
            if os.path.exists(csPath): return csPath
        except: pass
    return None

def call_circuitscape(CSPATH, outConfigFile):
    memFlag = False
    failFlag = False
    gprint('     Calling Circuitscape:')
    import subprocess
    proc = subprocess.Popen([CSPATH, outConfigFile],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                           shell=True)
    while proc.poll() is None:
        output = proc.stdout.readline()

        if 'Traceback' in output or 'RuntimeError' in output:
            gprint("\nCircuitscape failed.")
            failFlag = True
            if 'memory' in output:
                memFlag = True
        if ('Processing' not in output and 'laplacian' not in output and 
                'node_map' not in output and (('--' in output) or 
                ('sec' in output) or (failFlag == True))):
            gprint("      " + output.replace("\r\n",""))                
    
    # Catch any output lost if process closes too quickly
    output=proc.communicate()[0]
    for line in output.split('\r\n'):
        if 'Traceback' in line:
            gprint("\nCircuitscape failed.")
            if 'memory' in line:
                memFlag = True
        if ('Processing' not in line and 'laplacian' not in line and 
                'node_map' not in line and (('--' in line) or 
                ('sec' in line) or (failFlag == True))):
           gprint("      " + str(line))#.replace("\r\n","")))              
    return memFlag
    
    
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
    # write_log(msg)
    # write_log(err)
    # close_log_file()
    exit(1)
        
def nullfloat(innum):
    """Convert ESRI float or null to Python float"""
    if innum == GP_NULL:
        nfloat = 'None'
    else:
        nfloat = float(innum)
        if nfloat == 0:
            nfloat = 'None'
    return nfloat


def nullstring(arg_string):
    """Convert ESRI nullstring to Python null"""
    if arg_string == GP_NULL:
        arg_string = 'None'
    return arg_string

def str2bool(pstr):
    """Convert ESRI boolean string to Python boolean type"""
    return pstr == 'true'


def check_output_dir(file):
    """Checks to make sure path name is not too long.

    Long path names can cause problems with ESRI grids.
    """
    PROJECTDIR = os.path.dirname(file)
    if len(PROJECTDIR) > 140:
        msg = ('ERROR: Output directory "' + PROJECTDIR +
               '" is too deep.  Please choose a shallow directory'
               '(something like "C:\PUMA").')
        raise RuntimeError(msg)

    if "-" in PROJECTDIR or " " in PROJECTDIR or "." in PROJECTDIR:
        msg = ('ERROR: Output directory cannot contain spaces, dashes, or '
                'special characters.')
        raise RuntimeError(msg)
    if not os.path.exists(PROJECTDIR):
        os.mkdir(PROJECTDIR)
    return

    
def check_for_focal_regions(filename):
    """Reads map of focal nodes from disk and determines whether they contain focal regions.
    
    """  
    if os.path.isfile(filename)==False:
        return False
    base, extension = os.path.splitext(filename)        
    (ncols, nrows, xllcorner, yllcorner, cellsize, nodata) = read_header(filename)
    point_map = reader(filename, 'int32')

    (rows, cols) = where(point_map > 0)

    values = zeros(rows.shape,dtype = 'int32') 
    for i in range(0, rows.size):
        values[i] = point_map[rows[i], cols[i]]
    points_rc = c_[values,rows,cols]
    try:            
        i = argsort(points_rc[:,0])
        points_rc = points_rc[i]
    except IndexError:
        return False
    if points_rc.shape[0]!= (unique(asarray(points_rc[:,0]))).shape[0]:
        return True
    else:
        return False

        
def reader(filename, type):
    """Reads rasters saved as ASCII grids or numpy arrays into Circuitscape."""    
    if os.path.isfile(filename)==False:      
        raise RuntimeError('File "'  + filename + '" does not exist')
    (ncols, nrows, xllcorner, yllcorner, cellsize, nodata) = read_header(filename)

    fileBase, fileExtension = os.path.splitext(filename)     

    if nodata==False:
        map = loadtxt(filename, skiprows=5, dtype=type)
    else:
        map = loadtxt(filename, skiprows=6, dtype=type)
        map = where(map==nodata, -9999, map)

    if nrows==1:
        temp=numpy.zeros((1,map.size))
        temp[0,:]=map
        map=temp
    if ncols==1:
        temp=numpy.zeros((map.size,1))
        temp[:,0]=map
        map=temp       
  
    return map

def get_file_path(arg):
    try:
        filename = nullstring(arg)
        if filename == 'None':
            return 'None'
        desc = arcpy.Describe(filename)
        return desc.catalogPath
        
    # Return GEOPROCESSING specific errors
    except arcpy.ExecuteError:
        exit_with_geoproc_error(_SCRIPT_NAME)

    # Return any PYTHON or system specific errors
    except:
        exit_with_python_error(_SCRIPT_NAME)
            
    
cs_arc()




