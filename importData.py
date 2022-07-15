from genericpath import exists
from operator import index
import pandas as pd
import numpy as np
import os
from tkinter.filedialog import askdirectory


def get_files(targetWorkspace):
    origPaths = [] #future list of paths to all original files
    filenames = [] #future list of file names

    for dirpath, dirnames, files in os.walk(targetWorkspace): #walks through targetWorkspace
        files = [f for f in files if not f[0] == '.' and f.endswith('.xlsx')]         #excludes hidden files in the files list
        dirnames[:] = [d for d in dirnames if not d[0] == '.']   #excludes hidden directories in dirnames list

        for file in files:                                    
            filenames.append(file)                            #append each file name to the filenames list
            print(file)
            origPaths.append(os.path.join(dirpath, file))     #for each file, get the full path to it's location
    return(origPaths)

def importMetaData(file):
    metadata_xlsx = pd.read_excel(file, "Results")

    np_metadata = np.array(metadata_xlsx)

    protocol = np_metadata[0,3]
    plateName = np_metadata[1,3]
    readout = np_metadata[5,0]
    emissionFilter = np_metadata[6,3]

    if readout == "BRET":
        acceptorFilter = np_metadata[7,3]
        integrationTime = np_metadata[8,3]
    else:
        integrationTime = np_metadata[7,3]

    metadata = [["Protocol", protocol],     ["Plate Name",plateName], ["Readout" ,  readout], ["Emission Filter" ,   emissionFilter], ["Integration Time" ,    integrationTime]]

    newDf = pd.DataFrame(metadata, columns = ["Category", "Value"])
    return(np_metadata, newDf)

def importCSV(file):
    csvFile = file.rsplit(".",1)[0] + ".csv"                                                        #take original file name and replace suffix with .csv
    csvDf = pd.read_csv(csvFile, usecols=['WellPosition', 'Donor_RLU', 'Acceptor_RLU', 'Ratio'])    #read the csv file and extract the relevant columns
    csvDf[['Row', 'Column']] = csvDf['WellPosition'].str.split(':', expand=True)                    #split the WellPosition column into two parts
    csvDf['Column'] = csvDf['Column'].str.pad(width=2, side='left', fillchar= "0")                  #pad the well column numbers with 0s (01, 02...)
    return(csvDf)

def extract_data(csvDf, signal):
    df = csvDf[['Row', 'Column', signal]].copy() #extract the relevant column to a dataframe
    dfSorted = df.pivot(index='Row', columns='Column', values = signal)
    dfSorted= dfSorted.reset_index(level=0)
    dfSorted.insert(0, column='Label', value=signal)
    return(dfSorted)


###### MAIN #######
# Choose your raw data location
targetWorkspace = askdirectory(title="SELECT YOUR DATA LOCATION")
concatFile = os.path.join(targetWorkspace, 'data-concat.csv')

if os.path.exists(concatFile):
    os.remove(concatFile)
    print("output file already exists. deleting previous version")

paths = get_files(targetWorkspace)

for file in paths:
    xlsxFile, metaData = importMetaData(file)   #imports metadata into pandas dataframe
    csvDf= importCSV(file)                      #loads the csv file columns into a dataframe
    data = csvDf[['Row', 'Column', 'Donor_RLU', 'Acceptor_RLU', 'Ratio']]

    donor = extract_data(csvDf, 'Donor_RLU')
    acceptor = extract_data(csvDf, 'Acceptor_RLU')
    ratio = extract_data(csvDf, 'Ratio')

    list_of_dfs = [donor, acceptor, ratio]
    
    #write them to an excel file.
    concatFile = os.path.join(targetWorkspace, 'data-concat.csv')
    with open(concatFile,'a') as f:
        metaData.to_csv(f, index=False, header=False, line_terminator='\n')
        f.write('\n')
        for df in list_of_dfs:
            df.to_csv(f, index=False, line_terminator='\n')
        f.write('\n')
    f.close()

