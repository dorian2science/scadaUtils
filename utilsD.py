import pandas as pd, numpy as np
import subprocess as sp, os
import pickle
import re
import time, datetime as dt
import plotly.graph_objects as go
from pylab import cm
import matplotlib.colors as mtpcl
import scipy

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
        self.dirNameOfFileUtilsD=os.path.dirname(os.path.realpath(__file__))
        self.cmapNames = pickle.load(open(self.dirNameOfFileUtilsD + "/conf/colormaps.pkl",'rb'))[::3]

    def printCTime(self,start):
        print('time laps : {:.2f} seconds'.format(time.time()-start))

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
        print('time laps :',time.time()-start)

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

    def linspace(self,arr,numElems):
        idx = np.round(np.linspace(0, len(arr) - 1, numElems)).astype(int)
        return list([arr[k] for k in idx])

    def flattenList(self,l):
        return [item for sublist in l for item in sublist]

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

    def sortIgnoCase(self,lst):
        df = pd.DataFrame(lst)
        return list(df.iloc[df[0].str.lower().argsort()][0])

    def get_filesDir(self,folderName=None,ext='.pkl'):
        if not folderName :
            folderName = os.getcwd()
        return sp.check_output('cd ' + '{:s}'.format(folderName) + ' && ls *' + ext,
                                shell=True).decode().split('\n')[:-1]

    def dfcolwithnbs(self,df):
        a = df.columns.to_list()
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

    def combineFilter(self,df,columns,filters):
        cf  = [df[col]==f for col,f in zip(columns,filters)]
        dfF = [all([cfR[k] for cfR in cf]) for k in range(len(cf[0]))]
        return df[dfF]

    def skipWithMean(self,df,windowPts,idxForMean=None,col=None):
        ''' compress a dataframe by computing the mean around idxForMean points'''
        if not col :
            col = [k for k in range(len(df.columns))]
        print(col)
        if not idxForMean :
            idxForMean = list(range(windowPts,len(df),windowPts))
        ll = [df.iloc[k-windowPts:k+windowPts+1,col].mean().to_frame().transpose()
                for k in idxForMean]
        dfR = pd.concat(ll)
        dfR.index = df.index[idxForMean]
        return dfR


    def convertCSVtoPklWrap(self,func):
        def wrapper(folderCSV,saveFolder,filename):
            start       = time.time()
            nameFile    = filename[:-4]
            print("============================================")
            print("convert file to .pkl : ",filename)
            df = pd.read_csv(folderCSV + filename,low_memory=False)
            print("reading csv finished ")
            ######## fonction wrapped ###################
            df= func(df)
            print("wrapped function correctly executed ")
            ###########################
            # with open(saveFolder+nameFile + '.pkl', 'wb') as handle:# save the file
            #     pickle.dump(df, handle, protocol=pickle.HIGHEST_PROTOCOL)
            self.printCTime(start)
            print("============================================")
        return wrapper

    # ==========================================================================
    #                           GRAPHICS
    # ==========================================================================
    def customLegend(self,fig, nameSwap,breakLine=60):
        dictYes = isinstance(nameSwap,dict)
        if not dictYes:
            print('not a dictionnary, there may be wrong assignment')
            namesOld = [k.name  for k in fig.data]
            nameSwap = dict(zip(namesOld,nameSwap))
        for i, dat in enumerate(fig.data):
            for elem in dat:
                if elem == 'name':
                    # <br>s
                    newName = nameSwap[fig.data[i].name].capitalize()
                    newName = '<br>s'.join([newName[k:k+breakLine] for k in range(0,len(newName),breakLine)])
                    fig.data[i].name = newName
        return(fig)

    def makeFigureName(self,filename,patStop,toAdd):
        idx=filename.find(patStop)
        f=filename[:idx]
        f=re.sub('[\./]','_','_'.join([f]+toAdd))
        print(f)
        return f

    def buildTimeMarks(self,t0,mini=0,maxi=3600*24-1,nbMarks=10):
        listSeconds = [int(t) for t in np.linspace(0,maxi,nbMarks)]
        print(listSeconds)
        listMarksTime = [(t0+dt.timedelta(seconds=k)).strftime('%H:%M') for k in listSeconds]
        dictTimeMarks = dict(zip(listSeconds,listMarksTime))
        return dictTimeMarks

    def getColorMapHex(self, cmapName,N):
        cmap        = cm.get_cmap(cmapName, N)
        colorList   = []
        for i in range(cmap.N):colorList.append(mtpcl.rgb2hex(cmap(i)))
        return colorList

    def getAutoAxes(self,N,inc=0.05):
        allSides =['left','right']*6
        allAnch = ['free']*12

        t=round((N-2)/2)+1
        graphLims = [0+t*inc,1-t*inc]
        tmp     = [[graphLims[0]-k,graphLims[1]+k] for k in np.arange(0,0.3,inc)]
        positions  = [it for sub in tmp for it in sub][:N]

        sides       = allSides[:N]
        anchors     = allAnch[:N]
        overlays    = [None] + ['y']*(N-1)
        return [graphLims,sides,anchors,positions,overlays]

    def goMultYAxis(self,df,nameColX,nameColsY,names=None,inc=0.05):
        print('y : ',nameColsY)
        N = len(nameColsY)
        x = df[nameColX]
        yList = [df[colonne] for colonne in nameColsY]

        if not names:
            names = nameColsY

        cols = self.getColorMapHex('jet',N)
        yNum=[str(k) for k in range(1,N+1)]
        graphLims,sides,anchors,positions,overlays = self.getAutoAxes(N,inc=inc)

        fig = go.Figure()

        dictYaxis={}
        for nameVar,y,side,anc,pos,col,k,overlay in zip(names,yList,sides,anchors,positions,cols,yNum,overlays):
            fig.add_trace(go.Scatter(x=x,y=y,name=nameVar,yaxis='y'+k,mode='markers',
                                    marker=dict(color = col,size=10)))

            dictYaxis['yaxis'+k] = dict(
            title=nameVar,
            titlefont=dict(color=col),
            tickfont=dict(color=col),
            anchor=anc,
            overlaying=overlay,
            side=side,
            position=pos
            )
        fig.update_layout(xaxis=dict(domain=graphLims))
        fig.update_layout(dictYaxis)
        fig.update_layout(title_text="multiple y-axes example",font=dict(family="Courier New, monospace",size=18))
        return fig

    def printDFSpecial(self,df,allRows=True):
        # pd.describe_option('col',True)
        colWidthOri = pd.get_option('display.max_colwidth')
        rowNbOri = pd.get_option('display.max_rows')

        pd.set_option('display.max_colwidth',None)
        if allRows :
            pd.set_option('display.max_rows',None)
        print(df)
        pd.set_option('display.max_colwidth',colWidthOri)
        pd.set_option('display.max_rows',rowNbOri)
