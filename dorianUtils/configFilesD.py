import pandas as pd,numpy as np
import subprocess as sp, os,re, pickle
import time, datetime as dt, pytz
from scipy import linalg, integrate
from dateutil import parser
from dorianUtils.utilsD import Utils

pd.options.mode.chained_assignment = None  # default='warn'

class ConfigMaster:
    """docstring for ConfigMaster."""

    def __init__(self,folderPath,folderFig=None,folderExport=None):
        self.utils      = Utils()
        self.folderPath = folderPath
        if not folderFig :
            folderFig = os.getenv('HOME') + '/Images/'
        self.folderFig  = folderFig
        if not folderExport :
            folderExport = os.getenv('HOME') + '/Documents/'
        self.folderExport  = folderExport
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

class ConfigDashTagUnitTimestamp(ConfigMaster):
    def __init__(self,folderPath,confFile,folderFig=None,folderExport=None,encode='utf-8'):
        super().__init__(folderPath,folderFig=folderFig,folderExport=folderExport)
        self.confFile   = confFile

        self.modelAndFile = ''
        self.filesDir     = self.get_ValidFiles()
        self.dfPLC        = pd.read_csv(confFile,encoding=encode)

        self.unitCol,self.descriptCol,self.tagCol = self.getPLC_ColName()
        self.listUnits    = self.getUnitsdfPLC()

        self.allPatterns = self.utils.listPatterns
        self.listPatterns = self.get_validPatterns()

# ==============================================================================
#                     basic functions
# ==============================================================================

    def formatRawDF(self,df,printCT=0,parseDatesManual=False):
        start=time.time()
        dfOut = df.copy()
        if parseDatesManual :
            t  = [parser.parse(k) for k in df.timestamp]
            dfOut['timestamp']  = t
        dfOut['value']      = pd.to_numeric(df['value'],errors='coerce')
        if printCT : self.utils.printCTime(start)
        return dfOut.sort_values(by=['timestamp','Tag'])

    def convertCSVtoPklFormatted(self,folderCSV,filenames=None,parseDatesManual=False):
        ''' get column value with numeric values
        and convert timestamp to datetime format'''
        listFiles = self.utils.get_filesDir(folderName=folderCSV,ext='.csv')
        if not filenames:
            filenames = listFiles
        if not isinstance(filenames,list):
            filenames = [filenames]
        if isinstance(filenames[0],int):
            filenames = [listFiles[k] for k in filenames]
        for filename in filenames :
            if not filename[:-4] + '_f.pkl' in self.filesDir:
                start       = time.time()
                if parseDatesManual : df = pd.read_csv(folderCSV + filename,names=['Tag','value','timestamp'])
                else : df = pd.read_csv(folderCSV + filename,parse_dates=[2],names=['Tag','value','timestamp'])
                print("============================================")
                print("file converted to .pkl in : ",filename)
                self.utils.printCTime(start)
                start = time.time()
                print("============================================")
                print("formatting file : ",filename)
                df = self.formatRawDF(df,parseDatesManual=parseDatesManual)
                self.utils.printCTime(start)
                with open(self.folderPath + filename[:-4] + '_f.pkl' , 'wb') as handle:# save the file
                    pickle.dump(df, handle, protocol=pickle.HIGHEST_PROTOCOL)
                print("============================================")
            else :
                print("============================================")
                print('filename : ' ,filename,' already in folder : ',self.folderPath)
                print("============================================")

    def getPLC_ColName(self):
        l = self.dfPLC.columns
        v = l.to_frame()
        unitCol = ['unit' in k.lower() for k in l]
        descriptName = ['descript' in k.lower() for k in l]
        tagName = ['tag' in k.lower() for k in l]
        return [list(v[k][0])[0] for k in [unitCol,descriptName,tagName]]

    def get_validPatterns(self):
        model = self.modelAndFile.split('-')[0]
        if model=='10001' :
            return [self.allPatterns[k] for k in [6,0]]
        if model=='10002' :
            return [self.allPatterns[k] for k in [1,2,3,4,5,0]]

    def get_ValidFiles(self):
        try :
            res = sp.check_output('cd ' + '{:s}'.format(self.folderPath) + ' && ls *' +
                                self.modelAndFile +'*',shell=True)
            # print(res)
            return res.decode().split('\n')[:-1]
        except :
            print('no formatted files in the folder : ', self.folderPath)
            return []

    def loadFile(self,filename=0,skip=1):
        if isinstance(filename,int):
            filename=self.filesDir[filename]
        print('absolute Path: ', self.folderPath)
        df=pickle.load(open(self.folderPath + filename, "rb" ))
        print('dataframe loaded : {}'.format(filename))
        return df[::skip]

# ==============================================================================
#                   functions filter on configuration file with tags
# ==============================================================================
    def getUnitPivotedDF(self,df,asList=True):
        dfP,listTags,tagsWithUnits=self.dfPLC,df.columns,[]
        for tagName in listTags :
            tagsWithUnits.append(dfP[dfP[self.tagCol]==tagName][[self.tagCol,self.unitCol]])
        tagsWithUnits = pd.concat(tagsWithUnits)
        if asList :tagsWithUnits = [k + ' ( in ' + l + ')' for k,l in zip(tagsWithUnits[self.tagCol],tagsWithUnits[self.unitCol])]
        return tagsWithUnits

    def getUnitsdfPLC(self):
        listUnits = self.dfPLC[self.unitCol]
        return listUnits[~listUnits.isna()].unique().tolist()

    def getTagsSameUnit(self,unitName,showPLC=0):
        res = self.dfPLC.copy()
        if not showPLC :
            return res[res[self.unitCol]==unitName][self.tagCol]
        if showPLC==1 :
            return res[res[self.unitCol]==unitName]
        if showPLC==2 :
            res = res[res[self.unitCol]==unitName][[self.tagCol,self.descriptCol]]
            # self.utils.printDFSpecial(res)
            return res

    def getTagsTU(self,patTag,units,onCol='tag',case=False,ds=True,format='tag'):
        res = self.dfPLC.copy()
        if 'tag' in onCol.lower():whichCol = self.tagCol
        elif 'des' in onCol.lower():whichCol = self.descriptCol
        filter1 = res[whichCol].str.contains(patTag,case=case)
        if isinstance(units,str):
            units = [units]
        filter2 = res[self.unitCol].isin(units)
        res = res[filter1&filter2]
        if format=='tdu':
            res = res[[self.tagCol,self.descriptCol,self.unitCol]]
        elif format=='tag':
            res = list(res[self.tagCol])
        elif format=='print':
            res = self.utils.printDFSpecial(res)
        return res

    def getCatsFromUnit(self,unitName,pattern=None):
        if not pattern:
            pattern = self.listPatterns[0]
        sameUnitTags = self.getTagsSameUnit(unitName)
        return list(pd.DataFrame([re.findall(pattern,k)[0] for k in sameUnitTags])[0].unique())

    def getDescriptionFromTagname(self,tagName):
        res = self.dfPLC[self.dfPLC[self.tagCol]==tagName][self.descriptCol]
        # print(res)
        if not res :
            return res.iloc[0]
        else:
            return ''

    def getTagDescription(self,df,cols=1):
        if 'tag' in [k.lower() for k in df.columns]:listTags = list(df.Tag.unique())
        else : listTags = list(df.columns)
        if cols==1:listCols = [self.descriptCol]
        if cols==2:listCols = [self.tagCol,self.descriptCol]
        return self.dfPLC[self.dfPLC[self.tagCol].isin(listTags)][listCols]

    # ==============================================================================
    #                   functions filter on dataFrame
    # ==============================================================================

    def getDFsameCat(self,df,unitName,cats,pattern=None,formatted=1):
        dfOut = df.copy()
        if not pattern:
            pattern = self.listPatterns[0]
        sameUnitTags    = self.getTagsSameUnit(unitName)
        dfOut             = dfOut[dfOut.Tag.isin(sameUnitTags)]
        if not cats:
            cats = self.getCatsFromUnit(unitName,pattern)
        for cat in cats:
            tagSels = dfOut[dfOut.Tag.str.contains(cat,case=True)].Tag.unique()
            dfOut.at[dfOut.Tag.isin(tagSels),'categorie'] = cat
        dfOut = dfOut[~dfOut.categorie.isna()]
        if not formatted :
            dfOut.value = pd.to_numeric(dfOut['value'],errors='coerce')
            return dfOut.sort_values(by=['Tag','timestamp'])
        else :
            return dfOut

    def getDFfromTagList(self,df,ll,formatted=1):
        if not isinstance(ll,list):ll =[ll]
        dfOut = df[df.Tag.isin(ll)]
        if not formatted :dfOut.value = pd.to_numeric(dfOut['value'],errors='coerce')
        return dfOut.sort_values(by=['Tag','timestamp'])

    def getDFTagsTU(self,df,patTags,units,formatted=1,**kwargs):
        lls=[]
        if isinstance(patTags,str) : patTags = [patTags]
        for patTag in patTags : lls.append(self.getTagsTU(patTag,units,format='tag',**kwargs))
        ll = self.utils.flattenList(lls)
        return self.getDFfromTagList(df,ll,formatted)

    def getDFTime(self,dfF,timeRange,t0=None):
        if not 'timestamp' in dfF.columns:timestamp = dfF.index
        else : timestamp = dfF.timestamp
        if not isinstance(t0,dt.datetime): t0 = timestamp[0]
        print('t0 : ',t0)
        if isinstance(timeRange[0],str):
            timeRange = self.utils.convertToSecs(timeRange,t0)
            print('timeRange : ',timeRange)
        t1 = t0 + dt.timedelta(seconds=timeRange[0])
        t2 = t0 + dt.timedelta(seconds=timeRange[1])
        return dfF[(timestamp>t1)&(timestamp<t2)]

    def getDFTimeRange(self,df,timeRange,col='timestamp'):
        t0 = parser.parse(timeRange[0]).astimezone(pytz.timezone('UTC'))
        t1 = parser.parse(timeRange[1]).astimezone(pytz.timezone('UTC'))
        if col == 'index': return df[(df.index>t0)&(df.index<t1)].sort_index()
        else : return df[(df[col]>t0)&(df[col]<t1)].sort_values(by=col)

    def loadDFTimeRange(self,timeRange,conditionFile='',skipEveryHours=24):
        lfs = [k for k in self.filesDir if conditionFile in k]
        listDates,delta = self.utils.datesBetween2Dates(timeRange,offset=1)
        listFiles = [f for d in listDates for f in lfs if d in f]
        skip = (parser.parse(timeRange[1])-parser.parse(timeRange[0])).total_seconds()/(3600*skipEveryHours)
        skip = max(1,round(skip))
        print('skip : ',skip)
        if not listFiles : print('there are no files to load')
        else :
            dfs = []
            for filename in listFiles :
                df = self.loadFile(filename,skip=skip)
                if not '00-00' in filename: # remvove the part of the dataframe that expands over the next date
                    t0      = df.timestamp.iloc[0]
                    tmax    = t0+dt.timedelta(days=1)-dt.timedelta(hours=t0.hour,minutes=t0.minute,seconds=t0.second+1)
                    df      = df[df.timestamp<tmax]
                dfs.append(df)
            return self.getDFTimeRange(pd.concat(dfs),timeRange)

    def pivotDF(self,df,resampleRate='60s',applyMethod='nanmean'):
        listTags=list(df.Tag.unique())
        t0=df.timestamp.min()
        dfOut = pd.DataFrame()
        for tagname in listTags :
            dftmp=df[df.Tag==tagname]
            dftmp.index=list(dftmp.timestamp)
            dftmp = eval('dftmp.resample(resampleRate,origin=t0).apply(np.' + applyMethod + ')')
            dfOut[tagname]= dftmp['value']
        dfOut=dfOut.fillna(method='ffill')
        return dfOut


    def loadDF_TimeRange_TU(self,timeRange,tagPat,unit,rs='auto',applyMethod='mean'):
        lfs = [k for k in self.filesDir]
        listDates,delta = self.utils.datesBetween2Dates(timeRange,offset=1)
        listFiles = [f for d in listDates for f in lfs if d in f]
        if rs=='auto':
            rs = '{:.0f}'.format(max(1,delta.total_seconds()/3600)) + 's'
            print(rs)
        if not listFiles : print('there are no files to load')
        else :
            dfs = []
            for filename in listFiles :
                df = self.loadFile(filename)
                df = self.getDFTagsTU(df,tagPat,unit)
                df = self.pivotDF(df,resampleRate=rs,applyMethod=applyMethod)
                if not '00-00' in filename: # remvove the part of the dataframe that expands over the next date
                    t0      = df.timestamp.iloc[0]
                    tmax    = t0+dt.timedelta(days=1)-dt.timedelta(hours=t0.hour,minutes=t0.minute,seconds=t0.second+1)
                    df      = df[df.timestamp<tmax]
                dfs.append(df)
        return self.getDFTimeRange(pd.concat(dfs),timeRange,'index')

    def loadDF_TimeRange_Tags(self,timeRange,tagPat,unit=None,rs='auto',applyMethod='mean'):
        lfs = [k for k in self.filesDir]
        listDates,delta = self.utils.datesBetween2Dates(timeRange,offset=1)
        listFiles = [f for d in listDates for f in lfs if d in f]
        if rs=='auto':
            rs = '{:.0f}'.format(max(1,delta.total_seconds()/3600)) + 's'
            print(rs)
        if not listFiles : print('there are no files to load')
        else :
            dfs = []
            for filename in listFiles :
                df = self.loadFile(filename)
                if not unit : df = self.getDFfromTagList(df,tagPat)
                else : df = self.getDFTagsTU(df,tagPat,unit)
                df = self.pivotDF(df,resampleRate=rs,applyMethod=applyMethod)
                if not '00-00' in filename: # remvove the part of the dataframe that expands over the next date
                    t0      = df.timestamp.iloc[0]
                    tmax    = t0+dt.timedelta(days=1)-dt.timedelta(hours=t0.hour,minutes=t0.minute,seconds=t0.second+1)
                    df      = df[df.timestamp<tmax]
                dfs.append(df)
        return self.getDFTimeRange(pd.concat(dfs),timeRange,'index')

    # ==============================================================================
    #                   functions to compute new variables
    # ==============================================================================

    def integrateDFTag(self,df,tagname,timeWindow=60,formatted=1):
        dfres = df[df.Tag==tagname]
        if not formatted :
            dfres = self.formatRawDF(dfres)
        dfres = dfres.sort_values(by='timestamp')
        dfres.index=dfres.timestamp
        dfres=dfres.resample('100ms').ffill()
        dfres=dfres.resample(str(timeWindow) + 's').mean()
        dfres['Tag'] = tagname
        return dfres

    def integrateDF(self,df,pattern,**kwargs):
        ts = time.time()
        dfs = []
        listTags = self.getTagsTU(pattern[0],pattern[1])[self.tagCol]
        # print(listTags)
        for tag in listTags:
            dfs.append(self.integrateDFTag(df,tagname=tag,**kwargs))
        print('integration of pattern : ',pattern[0],' finished in ')
        self.utils.printCTime(ts)
        return pd.concat(dfs,axis=0)

    # ==============================================================================
    #                   functions computation
    # ==============================================================================

    def prepareDFforFit(self,filename,ts=None,group='temperatures Stack 1',rs='30s'):
        df = self.loadFile(filename)
        a  = self.usefulTags[group]
        df = self.getDFTagsTU(df,a[0],a[1])
        df = self.pivotDF(df,resampleRate=rs)
        if not not ts :
            df= self.getDFTime(df,ts)
        return df

    def fitDataframe(self,df,func='expDown',plotYes=True,**kwargs):
        res = {}
        period = re.findall('\d',df.index.freqstr)[0]
        print(df.index[0].freqstr)
        for k,tagName in zip(range(len(df)),list(df.columns)):
             tmpRes = self.utils.fitSingle(df.iloc[:,[k]],func=func,**kwargs,plotYes=plotYes)
             res[tagName] = [tmpRes[0],tmpRes[1],tmpRes[2],
                            1/tmpRes[1]/float(period),tmpRes[0]+tmpRes[2]]
        res  = pd.DataFrame(res,index = ['a','b','c','tau(s)','T0'])
        return res
