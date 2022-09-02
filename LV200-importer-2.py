'''
LV200 importer script
Author: Ani Michaud
Description: This script will take a list of folders (1 for each stack collected), and make a maximum projection of all the average .tif files.

Dependencies:
This script assumes data organization is as follows:
    - A parent folder with all of your data for the experiment
    - Sub folders for each sample (ex: "HEK293_Live_G600_exp1000ms_A1")
    - Inside each subfolder, a series of .tif files corresponding to avgs to be maximum projected together, ending in "_T001.tif", "_T002.tif", etc.

You can have brightfield images or other things inside the subfolders too. The script will look for the "T00?.tif" files and only pull those. 


'''

import os
from tkinter.filedialog import askdirectory
import skimage
import skimage.io
import numpy as np
import glob, os, shutil, tifffile


# Make a list of the subfolders in the parent folder
def list_subfolders(targetWorkspace):
    subfolderList = []
    for item in sorted(os.listdir(targetWorkspace)): #for each item in the listed parent folder
        dirpath = os.path.join(targetWorkspace, item) # Makes a complete path to the item
        if os.path.isdir(dirpath): # If the item is a directory, add it to subfolderList. If it's a file, do not add it.
            subfolderList.append(dirpath)
    subfolderList.remove(outputPath) #remove the "processed" folder from the list
    return(subfolderList)

#For each subfolder, get all of the .tif averages and make a stack
def make_stacks(subfolder, baseName):    
    images = glob.glob(os.path.join(subfolder,baseName+"_T0*")) #find all images in the subfolder that match the pattern "_T0*"
    ic = skimage.io.ImageCollection(images, conserve_memory=False) #open the images as a collection
    stack = skimage.io.concatenate_images(ic) #concatenate the collection to a single stack
    return (stack)
    
##################################

targetWorkspace = askdirectory(title="SELECT YOUR DATA LOCATION") # GUI to choose your raw data location
outputPath = os.path.join(targetWorkspace, "processed") #sets path to output location

if os.path.exists(outputPath): #if a processed folder exists already, remove the old one and overwrite.
    print("Processed folder already exists. Overwriting...")
    shutil.rmtree(outputPath)
os.mkdir(outputPath)

subfolderList = list_subfolders(targetWorkspace) #List the contents of the parent folder and create a list of all the subfolders

for subfolder in subfolderList: #for each subfolder, find all the .tif files and make a max projection
    baseName = os.path.basename(subfolder) #Gets the name of the subfolder
    print("Starting", baseName)
    stack = make_stacks(subfolder, baseName) #open the .tif files and make a stack
    
    MAXdata = np.max(stack, axis=0) #make a maximum projection of the stack
    savePath = os.path.join(outputPath, baseName) #Sets the path for saving the stack. Inside "processed" under the same name as the original subfolder
    tifffile.imwrite(savePath+"_max.tif", MAXdata) #saves the max projections with "_max" suffix
    #tifffile.imwrite(savePath+".tif", stack) #option for saving the unprojected stack

print("Done with script!")