import pandas as pd, numpy as np, pickle, re, time, datetime as dt,glob
import subprocess as sp, os
from dateutil import parser
import plotly.graph_objects as go
from pylab import cm
import matplotlib.colors as mtpcl
import matplotlib.pyplot as plt
import scipy
from scipy.optimize import curve_fit

class Utils:
    def __init__(self):
        self.confDir=os.path.dirname(os.path.realpath(__file__)) + '/conf'
        self.phyQties = self.df2dict(pd.read_csv(self.confDir+ '/units.csv'))
        self.unitMag = ['u','m','c','d','','da','h','k','M']
        self.buildNewUnits()
        self.listPatterns = ['.*',
        '[A-Z0-9]+',
        '[A-Z0-9]+_[A-Z0-9]+',
        '[A-Z0-9]+_[A-Z0-9]+_[A-Z0-9]+',
        '[A-Z0-9]+_[A-Z0-9]+_[A-Z0-9]+_[A-Z0-9]+',
        '[\w_]+[A-Z]+',
        '[A-Za-z]+',]
        self.cmapNames = pickle.load(open(self.confDir+"/colormaps.pkl",'rb'))[::3]

    # ==========================================================================
    #                           DEBUG
    # ==========================================================================

    def printCTime(self,start):
        print('time laps : {:.2f} seconds'.format(time.time()-start))

    # ==========================================================================
    #                           SYSTEM
    # ==========================================================================
    def read_csv_datetimeTZ(self,filename,**kwargs):
        start   = time.time()
        print("============================================")
        print('reading of file',filename)
        df      = pd.read_csv(filename,**kwargs,names=['tag','value','timestampUTC'])
        self.printCTime(start)
        start = time.time()
        print("============================================")
        print("parsing the dates : ",filename)
        df.timestampUTC=pd.to_datetime(df.timestampUTC,utc=True)# convert datetime to utc
        df['value'] = pd.to_numeric(df['value'],errors='coerce')
        self.printCTime(start)
        print("============================================")
        return df

    def convert_csv2pkl(self,folderCSV,folderPKL):
        for filename in self.get_filesDir(folderCSV,'.csv'):
            df=self.read_csv_datetimeTZ(folderCSV + filename)
            with open(folderPKL + filename[:-4] + '.pkl' , 'wb') as handle:
                pickle.dump(df, handle, protocol=pickle.HIGHEST_PROTOCOL)

    def get_filesDir(self,folderName=None,ext='.pkl'):
        if not folderName :folderName = os.getcwd()
        listFiles = sp.check_output('cd ' + '{:s}'.format(folderName) + ' && ls *' + ext,shell=True)
        listFiles=listFiles.decode().split('\n')[:-1]
        return listFiles

    def get_filesDirV2(self,folderName=None,pattern='*.pkl'):
        if not folderName :folderName = os.getcwd()
        return glob.glob(folderName+pattern)

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

    def datesBetween2Dates(self,dates,offset=0):
        times = [parser.parse(k) for k in dates]
        t0,t1 = [t-dt.timedelta(hours=t.hour,minutes=t.minute,seconds=t.second) for t in times]
        delta = t1 - t0       # as timedelta
        return [(t0 + dt.timedelta(days=i+offset)).strftime('%Y-%m-%d') for i in range(delta.days + 1)],times[1]-times[0]

    def slugify(self,value, allow_unicode=False):
        import unicodedata,re
        """
        Taken from https://github.com/django/django/blob/master/django/utils/text.py
        Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
        dashes to single dashes. Remove characters that aren't alphanumerics,
        underscores, or hyphens. Convert to lowercase. Also strip leading and
        trailing whitespace, dashes, and underscores.
        """
        value = str(value)
        if allow_unicode:value = unicodedata.normalize('NFKC', value)
        else:value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
        value = re.sub(r'[^\w\s-]', '', value.lower())
        return re.sub(r'[-\s]+', '-', value).strip('-_')

    def is_dst(self,t=None, timezone="UTC"):
        if t is None:t = dt.utcnow()
        timezone = pytz.timezone(timezone)
        timezone_aware_date = timezone.localize(t, is_dst=None)
        return timezone_aware_date.tzinfo._dst.seconds != 0

    # ==========================================================================
    #                           PHYSICS
    # ==========================================================================
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

    # ==========================================================================
    #                  lIST AND DICTIONNARIES AND DATAFRAMES
    # ==========================================================================
    def df2dict(self,df):
        return {df.columns[k] : list(df.iloc[:,k].dropna()) for k in range(len(df.columns))}

    def linspace(self,arr,numElems):
        idx = np.round(np.linspace(0, len(arr) - 1, numElems)).astype(int)
        return list([arr[k] for k in idx])

    def flattenList(self,l):
        return [item for sublist in l for item in sublist]

    def removeNaN(self,list2RmNan):
        tmp = pd.DataFrame(list2RmNan)
        return list(tmp[~tmp[0].isna()][0])

    def sortIgnoCase(self,lst):
        df = pd.DataFrame(lst)
        return list(df.iloc[df[0].str.lower().argsort()][0])

    def dfcolwithnbs(self,df):
        a = df.columns.to_list()
        coldict=dict(zip(range(0,len(a)),a))
        coldict
        return coldict

    def listWithNbs(self,l):
        return [k+ ' : '+ str(i) for i,k in zip(range(len(l)),l)]

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

    def convertSecstodHHMM(self,lt,t0=None,formatTime='%d - %H:%M'):
        if not t0:t0=parser.parse('00:00')
        if isinstance(t0,str):t0=parser.parse(t0)
        if isinstance(lt[0],str):
            lt = [int(t) for t in lt]
        return [(t0 + dt.timedelta(seconds=k)).strftime(formatTime) for k in lt]

    def convertToSecs(self,lt,t0=None):
        if not t0:t0=parser.parse('00:00')
        if isinstance(t0,str):t0=parser.parse(t0)
        tmp = [parser.parse(k) for k in lt]
        return [(t-t0).total_seconds() for t in tmp]

    def regExpNot(self,regexp):
        if regexp[:2] == '--': regexp = '^((?!' + regexp[2:] + ').)*$'
        return regexp

    def pivotDataFrame(self,df,colPivot=None,colValue=None,colTimestamp=None,resampleRate='60s',applyMethod='nanmean'):
        if not colPivot : colPivot = df.columns[0]
        if not colValue : colValue = df.columns[1]
        if not colTimestamp : colTimestamp = df.columns[2]

        listTags = list(df[colPivot].unique())
        t0 = df[colTimestamp].min()
        dfOut = pd.DataFrame()
        for tagname in listTags:
            dftmp=df[df[colPivot]==tagname]
            dftmp.index=list(dftmp[colTimestamp])
            dftmp = eval('dftmp.resample(resampleRate,origin=t0).apply(np.' + applyMethod + ')')
            dfOut[tagname] = dftmp[colValue]
        dfOut=dfOut.fillna(method='ffill')
        return dfOut
    # ==========================================================================
    #                           FITTING FUNCTIONS
    # ==========================================================================

    def expDown(self,x, a, b, c):
        return a * np.exp(-b * x) + c

    def expUp(self,x,a,b,c):
        return a *(1- np.exp(-b * x)) + c

    def poly2(self,x,a,b,c):
        return a*x**2 +b*x + c

    def expUpandDown(self,x,a1,b1,c1,a2,b2,c2):
        return self.expUp(x,a1,b1,c1) + self.expDown(x,a2,b2,c2)

    def generateSimuData(self,func='expDown'):
        x = np.linspace(0, 2, 150)
        y = eval(func)(x, 5.5, 10.3, 0.5)
        np.random.seed(1729)
        y_noise = 0.2 * np.random.normal(size=x.size)
        ydata = y + y_noise
        return x,ydata

    def fitSingle(self,dfx,func='expDown',plotYes=True,**kwargs):
        x = dfx.index
        y = dfx.iloc[:,0]
        if isinstance(dfx.index[0],pd._libs.tslibs.timestamps.Timestamp):
            xdata=np.arange(len(x))
        else :
            xdata=x
        popt, pcov = curve_fit(eval('self.'+func), xdata, y,**kwargs)
        if plotYes:
            plt.plot(x, y, 'bo', label='data')
            plt.plot(x, eval('self.'+func)(xdata, *popt), 'r-',
                label='fit: a=%.2f, b=%.2f, c=%.2f' % tuple(popt))
            plt.xlabel('x')
            plt.title(list(dfx.columns)[0])
            # plt.ylabel()
            plt.gcf().autofmt_xdate()
            plt.legend()
            plt.show()
        return popt

    # ==========================================================================
    #                           GRAPHICS
    # ==========================================================================
    def getColorHexSeq(self,N,colmap='jet'):
        cmap        = cm.get_cmap(colmap,N)
        colorList   = []
        for i in range(cmap.N):colorList.append(mtpcl.rgb2hex(cmap(i)))
        return colorList

    def updateColorMap(self,fig,colmap=None):
        listCols = self.getColorHexSeq(len(fig.data)+1,colmap=colmap)
        k,l=0,0
        listYaxis = [k for k in fig._layout.keys() if 'yax' in k]
        if len(listYaxis)>1:
            for yax in listYaxis :
                k+=1
                fig.layout[yax]['title']['font']['color'] = listCols[k]
                fig.layout[yax]['tickfont']['color'] = listCols[k]
        for d in fig._data :
            l+=1
            if 'marker' in d.keys():
                d['marker']['color']=listCols[l]
            if 'line' in d.keys():d['line']['color']=listCols[l]
        return fig

    def customLegend(self,fig, nameSwap,breakLine=None):
        if not isinstance(nameSwap,dict):
            print('not a dictionnary, there may be wrong assignment')
            namesOld = [k.name  for k in fig.data]
            nameSwap = dict(zip(namesOld,nameSwap))
        for i, dat in enumerate(fig.data):
            for elem in dat:
                if elem == 'name':
                    newName = nameSwap[fig.data[i].name]
                    if isinstance(breakLine,int):
                        newName = '<br>s'.join([newName[k:k+breakLine] for k in range(0,len(newName),breakLine)])
                    fig.data[i].name = newName
        return fig

    def makeFigureName(self,filename,patStop,toAdd):
        idx=filename.find(patStop)
        f=filename[:idx]
        f=re.sub('[\./]','_','_'.join([f]+toAdd))
        print(f)
        return f

    def buildTimeMarks(self,t0,t1,nbMarks=8,fontSize='12px'):
        maxSecs=int((t1-t0).total_seconds())
        listSeconds = [int(t) for t in np.linspace(0,maxSecs,nbMarks)]
        dictTimeMarks = {k : {'label':(t0+dt.timedelta(seconds=k)).strftime('%H:%M'),
                                'style' :{'font-size': fontSize}
                                } for k in listSeconds}
        return dictTimeMarks,maxSecs

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

    def multiYAxis(self,df,mapName='jet',names=None,inc=0.05):
        yList = df.columns
        cols = self.getColorHexSeq(len(yList),mapName)
        yNum=[str(k) for k in range(1,len(yList)+1)]
        graphLims,sides,anchors,positions,overlays = self.getAutoAxes(len(yList),inc=inc)
        fig = go.Figure()
        dictYaxis={}
        if not names :
            names = yList
        for y,name,side,anc,pos,col,k,overlay in zip(yList,names,sides,anchors,positions,cols,yNum,overlays):
            fig.add_trace(go.Scatter(x=df.index,y=df[y],name=y,yaxis='y'+k,
                                    marker=dict(color = col,size=10)))

            dictYaxis['yaxis'+k] = dict(
            title=name,
            titlefont=dict(color=col),
            tickfont=dict(color=col),
            anchor=anc,
            overlaying=overlay,
            side=side,
            position=pos
            )
        fig.update_layout(xaxis=dict(domain=graphLims))
        fig.update_layout(dictYaxis)
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
