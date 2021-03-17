import pandas as pd
import numpy as np
import subprocess as sp, os
import pickle
import re
import time, datetime
import plotly.graph_objects as go
from pylab import cm
import matplotlib.colors as mtpcl

class Utils:
    def __init__(self):
        self.phyQties = {
                'power'     : ['W'],
                'voltage'   : ['V'],
                'current'   : ['A'],
                'time'      : ['h','min','s','day'],
                'temperature' : ['°C','K'],
                'pressure'  : ['bar','Pa','Barg'],
                'distance'  : ['m'],
                'surface'   : ['m2'],
                'volume'    : ['l','L','m3'],
                'weight'    : ['g'],
                'energy'    : ['J']}
        self.unitMag = ['u','m','c','d','','da','h','k','M']
        self.buildNewUnits()
        self.listPatterns = ['.*',
        '[A-Z0-9]+',
        '[A-Z0-9]+_[A-Z0-9]+',
        '[A-Z0-9]+_[A-Z0-9]+_[A-Z0-9]+',
        '[A-Z0-9]+_[A-Z0-9]+_[A-Z0-9]+_[A-Z0-9]+',
        '[\w_]+[A-Z]+',
        '[A-Za-z]+',]
        self.cmapNames = pickle.load(open("conf/colormaps.pkl",'rb'))[::3]

    def isTimeFormat(self,input,formatT='%Y-%m-%d %H:%M:%S.%f'):
        try:
            time.strptime(input, formatT)
            return True
        except ValueError:
            return False

    def convert_csv2pkl(self,folderCSV,saveFolder,filename):
        start       = time.time()
        nameFile    = filename[:-4]
        df          = pd.read_csv(folderCSV + filename)
        df.columns  = ['Tag','value','timestamp']
        tags        = np.unique(df.Tag)
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

    def buildNewUnits(self):
        self.phyQties['speed'] = self.combineUnits(self.phyQties['distance'],self.phyQties['time'])
        self.phyQties['mass flow'] = self.combineUnits(self.phyQties['weight'],self.phyQties['time'])
        tmp = self.combineUnits(['','N'],self.phyQties['volume'],'')
        self.phyQties['volumetric flow'] = self.combineUnits(tmp,self.phyQties['time'])

    def combineUnits(self,units1,units2,oper='/'):
        return [x1 + oper + x2 for x2 in units2 for x1 in units1]

    def detectUnit(self,unit):
        phId = ''
        for phyQt in self.phyQties.keys():
            # listUnits = [x1+x2 for x2 in self.phyQts[phyQt] for x1 in self.unitMag]
            listUnits = self.combineUnits(self.unitMag,self.phyQties[phyQt],'')
            if unit in listUnits : phId = phyQt
        return phId

    def detectUnits(self,listUnits,check=0):
        tmp = [self.detectUnit(unit) for unit in listUnits]
        if check :
            listUnitsDf = pd.DataFrame()
            listUnitsDf['units'] = listUnits
            listUnitsDf['grandeur'] = tmp
            return listUnitsDf
        else :
            return tmp

    def removeNaN(self,list2RmNan):
        tmp = pd.DataFrame(list2RmNan)
        return list(tmp[~tmp[0].isna()][0])
        # return list(tmp[~tmp.isna()])
    def sortIgnoCase(self,lst):
        df = pd.DataFrame(lst)
        return list(df.iloc[df[0].str.lower().argsort()][0])

    def get_filesDir(self,folderName,ext='.pkl'):
        return sp.check_output('cd ' + '{:s}'.format(folderName) + ' && ls *' + ext,
                                shell=True).decode().split('\n')[:-1]

    def dfcolwithnbs(self,df):
        a=df.columns.to_list()
        coldict=dict(zip(range(0,len(a)),a))
        coldict
        return coldict

    def dspDict(self,dict,showRows=1):
        '''display dictionnary in a easy readable way :
        dict_disp(dict,showRows)
        showRows = 1 : all adjusted '''
        maxLen =max([len(v) for v in dict])
        for key, value in dict.items():
            valToShow = value
            if showRows == 0:
                rowTxt = key.ljust(maxLen)
            if showRows == 1:
                if len(key)>8:
                    rowTxt = (key[:8]+'..').ljust(10)
                else:
                    rowTxt = key.ljust(10)
            if showRows==-1:
                rowTxt      = key.ljust(maxLen)
                valToShow   = type(value)
            if showRows==-2:
                rowTxt      = key.ljust(maxLen)
                valToShow   = value.shape
            print(colored(rowTxt, 'red', attrs=['bold']), ' : ', valToShow)

# '''to do '''
    def combineFilter(self,df,columns,filters):
        cf  = [df[col]==f for col,f in zip(columns,filters)]
        dfF = [all([cfR[k] for cfR in cf]) for k in range(len(cf[0]))]
        return df[dfF]

    def getColorMapHex(self, cmapName,N):
        cmap        = cm.get_cmap(cmapName, N)
        colorList   = []
        for i in range(cmap.N):colorList.append(mtpcl.rgb2hex(cmap(i)))
        return colorList
