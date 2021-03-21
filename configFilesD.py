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
# ==============================================================================
#                                 functions
# ==============================================================================

    def get_ValidFiles(self):
        return sp.check_output('cd ' + '{:s}'.format(self.folderPath) + ' && ls *' + self.validPattern +'*',shell=True).decode().split('\n')[:-1]

    def convert_csv2pkl(self,folderCSV,filename):
        self.utils.convert_csv2pkl(folderCSV,self.folderPath,filename)

    def convert_csv2pkl_all(self,folderCSV,fileNbs=None):
        self.utils.convert_csv2pkl_all(folderCSV,self.folderPath)

    def loadFile(self,filename,skip=1):
        print('absolute Path: ', self.folderPath)
        print('loading dataframe : {}'.format(filename))
        return pickle.load(open(self.folderPath + filename, "rb" ))[::skip]
