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
from logging import raiseExceptions
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

def cleanUp(*argv):
    for arg in argv:
        if os.path.exists(arg): #if the concat file already exists, delete it.
            os.remove(arg)
            print("Output file", arg, "already exists. Deleting previous version...")

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
    
        #create a list of title:value pairs from the metadata
        metadata = [["Protocol", protocol], ["Plate Name",plateName], ["Readout" ,  readout], ["Emission Filter" ,   emissionFilter], ["Acceptor Filter", acceptorFilter], ["Integration Time" ,    integrationTime]]
        newDf = pd.DataFrame(metadata, columns = ["Category", "Value"]) #append the pairs to a dataframe
    
    elif protocol == "Protocol: Nano-Glo" or "CellTiter-Glo":   #if the readout is luminescence, just get the integration time (no acceptor listed)
        fileType = 'Luminescence'
        integrationTime = np_metadata[7,3]
        #create a list of title:value pairs from the metadata
        metadata = [["Protocol", protocol], ["Plate Name",plateName], ["Readout" ,  readout], ["Emission Filter" ,   emissionFilter], ["Integration Time" ,    integrationTime]]

        newDf = pd.DataFrame(metadata, columns = ["Category", "Value"]) #append the pairs to a dataframe
    
    else:
        raise TypeError
    
    return(np_metadata, newDf, fileType) #return the dataframe and original metadata array (can probably eliminate np_metadata once comfortable with script functionability)

#for a given xlsx file, finds the corresponding .csv and imports raw data
def importCSV(file, fileType):
    
    #initiate empty dataframe with full plate's-worth of columns and rows
    emptyDf = pd.DataFrame({
        'Row': sorted(['A','B','C','D','E','F','G','H']*12),
        'Column' : ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']*8
        })
    
    csvFile = file.rsplit(".",1)[0] + ".csv"  #Sets the name of the .csv file (original file name + .csv)

    #read the csv files according to the assay type. 
    if fileType == 'Luminescence':
        csvDf = pd.read_csv(csvFile, usecols=['WellPosition', 'RLU']) 
    
    else:
        csvDf = pd.read_csv(csvFile, usecols=['WellPosition', 'Donor_RLU', 'Acceptor_RLU', 'Ratio'])    #read the csv file and extract the relevant columns
    
    csvDf[['Row', 'Column']] = csvDf['WellPosition'].str.split(':', expand=True)                    #split the WellPosition column into two parts
    csvDf['Column'] = csvDf['Column'].str.pad(width=2, side='left', fillchar= "0")                  #pad the well column numbers with 0s (01, 02...)
    csvDf = pd.merge(emptyDf, csvDf, how="left") #merge the read csv file with the full plate emptyDf. Any missing values (from a partial plate read) remain as NaN.
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
bretOutputPath = os.path.join(targetWorkspace, 'BRET-concat.csv') #location of the final concatenated file
donorOutputPath = os.path.join(targetWorkspace, 'donor-concat.csv') #separate file of concatenated donor (for protocols that only read luminescence)

cleanUp(bretOutputPath, donorOutputPath) #remove any old versions of the concatenated files

paths = get_files(targetWorkspace) #list of path output from get_files

#for each xlsx file in the paths list, do the following:
for file in paths:
    name = os.path.basename(file)
    print("\nStarting file:", name)
    
    try: #try the import process, and filter out any unknown protocol types
        xlsxFile, metaData, fileType = importMetaData(file)   #import metadata into pandas dataframe
    
    except TypeError:
        print("ERROR: Glo-MAX protocol not supported. Skipping file...")
        continue

    csvDf= importCSV(file, fileType)                      #load the csv file columns into a dataframe
    
    
    if fileType == 'BRET':
        concatFile = bretOutputPath #data will be exported to the BRET concat file
        donor = extract_data(csvDf, 'Donor_RLU')        #extract and re-shuffle the donor data
        acceptor = extract_data(csvDf, 'Acceptor_RLU')  #extract and re-shuffle the acceptor data
        ratio = extract_data(csvDf, 'Ratio')            #extract and re-shuffle the ratio data
        list_of_dfs = [ratio, donor, acceptor]          #list of dataframes to concatenate
        
    elif fileType == "Luminescence":
        concatFile = donorOutputPath #data will be exported to the donor concat file
        donor = extract_data(csvDf, 'RLU')        #extract and re-shuffle the donor data
        list_of_dfs = [donor] #just concatenate donor
    

    #write the extracted data to the appropriate concatenated csv file (BRET or Donor)
    with open(concatFile,'a') as f:
        metaData.to_csv(f, index=False, header=False, lineterminator='\n')
        f.write('\n')
        for df in list_of_dfs:
            df.to_csv(f, index=False, lineterminator='\n')
        f.write('\n')
    f.close()

print("Done with script!")










