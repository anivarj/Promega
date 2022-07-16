'''
Author: Ani Michaud
Description: 
This script will import data from Glo-MAX readers and concatenate multiple plates into a single .csv file.
Run the script, select your data location, and let it run!


DEPENDENCIES:
- Data MUST include .xlsx and .csv for metadata and raw data (respectively).
- This script has not been tested on partially acquired plate setups, but theoretically should work.

'''

#import packages needed
from genericpath import exists
from operator import index
import pandas as pd
import numpy as np
import os
from tkinter.filedialog import askdirectory

# Make a list of the xlsx files in the locations you specify
def get_files(targetWorkspace):
    origPaths = [] #future list of paths to all original files
    filenames = [] #future list of file names

    for dirpath, dirnames, files in os.walk(targetWorkspace):                   #Walks through targetWorkspace
        files = [f for f in files if not f[0] == '.' and f.endswith('.xlsx')]   #Finds all xlsx files. Excludes hidden files in the files list
        dirnames[:] = [d for d in dirnames if not d[0] == '.']                  #Excludes hidden directories in dirnames list

        for file in files:                                   
            filenames.append(file)                            #Append each file name to the filenames list
            origPaths.append(os.path.join(dirpath, file))     #For each file, get the full path to it's location
    return(origPaths) #returns a list of full paths to all xlsx files.

#For a given xlsx file, parses metadata and stores it
def importMetaData(file):
    metadata_xlsx = pd.read_excel(file, "Results") #load the file and read the results tab

    np_metadata = np.array(metadata_xlsx) #array from pandas dataframe

    protocol = np_metadata[0,3] #location of protocol field
    plateName = np_metadata[1,3] #location of plate name field
    readout = np_metadata[5,0]  #location of readout (BRET or Luminesence)
    emissionFilter = np_metadata[6,3] #location of emission filter info

    if protocol == "Protocol: BRET: NanoBRET 618":  #if the readout is BRET, get the location of acceptor filter info and integration time
        fileType = 'BRET'
        acceptorFilter = np_metadata[7,3]
        integrationTime = np_metadata[8,3]
    elif protocol == "Protocol: Nano-Glo":          #if the readout is luminescence, just get the integration time (no acceptor listed)
        fileType = 'Luminescence'
        integrationTime = np_metadata[7,3]
    else:
        print("The protocol type for ", file, " isn't recognized! Exiting script.")
    

    #create a list of title:value pairs from the metadata
    metadata = [["Protocol", protocol], ["Plate Name",plateName], ["Readout" ,  readout], ["Emission Filter" ,   emissionFilter], ["Integration Time" ,    integrationTime]]

    newDf = pd.DataFrame(metadata, columns = ["Category", "Value"]) #append the pairs to a dataframe
    return(np_metadata, newDf, fileType) #return the dataframe and original metadata array (can probably eliminate np_metadata once comfortable with script functionability)

#for a given xlsx file, finds the corresponding .csv and imports raw data
def importCSV(file, fileType):
    csvFile = file.rsplit(".",1)[0] + ".csv"                                                        #take original file name and replace suffix with .csv
    
    if fileType == 'Luminescence':
        csvDf = pd.read_csv(csvFile, usecols=['WellPosition', 'RLU']) 
    
    else:
        csvDf = pd.read_csv(csvFile, usecols=['WellPosition', 'Donor_RLU', 'Acceptor_RLU', 'Ratio'])    #read the csv file and extract the relevant columns
    
    csvDf[['Row', 'Column']] = csvDf['WellPosition'].str.split(':', expand=True)                    #split the WellPosition column into two parts
    csvDf['Column'] = csvDf['Column'].str.pad(width=2, side='left', fillchar= "0")                  #pad the well column numbers with 0s (01, 02...)
    return(csvDf) #returns a dataframe with extracted data for all donor, acceptor and ratios

#exctracts a single type of data (donor, acceptor or ratio) and reshuffles it to a classic plate layout
def extract_data(csvDf, signal):
    df = csvDf[['Row', 'Column', signal]].copy()                        #extract the relevant column to a dataframe
    dfSorted = df.pivot(index='Row', columns='Column', values = signal) #pivots into a plate layout (rows = letters, columns = numbers)
    dfSorted= dfSorted.reset_index(level=0)                             #resets the index
    dfSorted.insert(0, column='Label', value=signal)                    #insert a label field for the data category
    return(dfSorted) #returns the shuffled data


'''
###### MAIN FUNCTIONS BELOW #######
'''

# Choose your raw data location
targetWorkspace = askdirectory(title="SELECT YOUR DATA LOCATION")
#targetWorkspace = r"D:\test-data\mixed" #for quick testing
concatFile = os.path.join(targetWorkspace, 'data-concat.csv') #location of the final concatenated file

if os.path.exists(concatFile): #if the concat file already exists, delete it.
    os.remove(concatFile)
    print("output file already exists. deleting previous version")

paths = get_files(targetWorkspace) #list of path output from get_files

#for each xlsx file in the paths list, do the following:
for file in paths:
    xlsxFile, metaData, fileType = importMetaData(file)   #import metadata into pandas dataframe
  
    csvDf= importCSV(file, fileType)                      #load the csv file columns into a dataframe
    
    
    if fileType == 'BRET':
        donor = extract_data(csvDf, 'Donor_RLU')        #extract and re-shuffle the donor data
        acceptor = extract_data(csvDf, 'Acceptor_RLU')  #extract and re-shuffle the acceptor data
        ratio = extract_data(csvDf, 'Ratio')            #extract and re-shuffle the ratio data
        list_of_dfs = [donor, acceptor, ratio]          #list of dataframes to concatenate
    
    else:
        donor = extract_data(csvDf, 'RLU')        #extract and re-shuffle the donor data
        list_of_dfs = [donor] #just concatenate donor
        
    #write the donor, accepetor and ratio to an excel file
    with open(concatFile,'a') as f:
        metaData.to_csv(f, index=False, header=False, line_terminator='\n')
        f.write('\n')
        for df in list_of_dfs:
            df.to_csv(f, index=False, line_terminator='\n')
        f.write('\n')
    f.close()

