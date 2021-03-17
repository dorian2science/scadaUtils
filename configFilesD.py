import pandas as pd
import numpy as np
import subprocess as sp, os
import pickle
import re
import time, datetime as dt
from utilsD import Utils

class ConfigMaster:
    """docstring for ConfigMaster."""

    def __init__(self,folderPath,):
        self.utils      = Utils()
        self.folderPath = folderPath
        self.validPattern = ''
# ==============================================================================
#                                 functions
# ==============================================================================

    def get_ValidFiles(self):
        return sp.check_output('cd ' + '{:s}'.format(self.folderPath) + ' && ls *' + self.validPattern +'*',shell=True).decode().split('\n')[:-1]

    def convert_csv2pkl(self,folderCSV,saveFolder,filename):
        start       = time.time()
        nameFile    = filename[:-4]
        df          = pd.read_csv(folderCSV + filename)
        print("============================================")
        print("convert file to .pkl : ",filename)
        with open(saveFolder+nameFile + '.pkl', 'wb') as handle:# save the file
            pickle.dump(df, handle, protocol=pickle.HIGHEST_PROTOCOL)
        end = time.time()
        print('time laps :',end-start)

    def convert_csv2pkl_all(self,folderCSV,saveFolder,fileNbs=None):
        # filesPkl = sp.check_output('cd ' + '{:s}'.format(saveFolder) + ' && ls *.pkl',shell=True).decode().split('\n')
        filesPkl = self.get_filesDir(saveFolder,'.pkl')
        filesCSV = self.get_filesDir(folderCSV,'.csv')
        print(filesPkl)
        if fileNbs:
            filesCSV = [filesCSV[k] for k in fileNbs]
        for filename in filesCSV:
            namePkl=filename[:-4] + '.pkl'
            # make sure that it has not been already read
            if not namePkl in filesPkl:
                self.convert_csv2pkl(folderCSV,saveFolder,filename)

    def loadFile(self,filename,skip=1):
        print('absolute Path: ', self.folderPath)
        print('loading dataframe : {}'.format(filename))
        return pickle.load(open(self.folderPath + filename, "rb" ))[::skip]
