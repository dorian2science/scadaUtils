import pandas as pd,numpy as np
import subprocess as sp, os,re, pickle
import time, datetime as dt, pytz
from scipy import linalg, integrate
from dateutil import parser
from dorianUtils.utilsD import Utils

pd.options.mode.chained_assignment = None  # default='warn'

class ConfigMaster:
    """docstring for ConfigMaster."""

    def __init__(self,folderPkl,folderFig=None,folderExport=None):
        self.utils      = Utils()
        self.folderPkl = folderPkl
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
        return sp.check_output('cd ' + '{:s}'.format(self.folderPkl) + ' && ls *' + self.validPattern +'*',shell=True).decode().split('\n')[:-1]

    def convert_csv2pkl(self,folderCSV,filename):
        self.utils.convert_csv2pkl(folderCSV,self.folderPkl,filename)

    def convert_csv2pkl_all(self,folderCSV,fileNbs=None):
        self.utils.convert_csv2pkl_all(folderCSV,self.folderPkl)


    def loadFile(self,filename,skip=1):
        if '*' in filename :
            filenames=self.utils.get_listFilesPklV2(self.folderPkl,filename)
            if len(filenames)>0 : filename=filenames[0]
            else : return pd.DataFrame()
        df = pickle.load(open(filename, "rb" ))
        return df[::skip]

class ConfigDashTagUnitTimestamp(ConfigMaster):
    def __init__(self,folderPkl,confFile,folderFig=None,folderExport=None,encode='utf-8'):
        super().__init__(folderPkl,folderFig=folderFig,folderExport=folderExport)
        self.confFile   = confFile
        self.modelAndFile = self.__getModelNumber()
        self.listFilesPkl     = self.get_ValidFiles()
        self.dfPLC        = pd.read_csv(confFile,encoding=encode)

        self.unitCol,self.descriptCol,self.tagCol = self.getPLC_ColName()
        self.listUnits    = self.getUnitsdfPLC()

        self.allPatterns = self.utils.listPatterns
        self.listPatterns = self.get_validPatterns()

    def __getModelNumber(self):
        modelNb = re.findall('\d{5}-\d{3}',self.confFile)
        if not modelNb: return ''
        else : return modelNb[0]

# ==============================================================================
#                     basic functions
# ==============================================================================
    def convertCSVtoPklFormatted(self,folderCSV,filenames=None,parseDatesManual=False):
        ''' get column value with numeric values
        and convert timestamp to datetime format'''
        listFiles = self.utils.get_listFilesPkl(folderName=folderCSV,ext='.csv')
        if not filenames:filenames = listFiles
        if not isinstance(filenames,list):filenames = [filenames]
        if isinstance(filenames[0],int):filenames = [listFiles[k] for k in filenames]
        for filename in filenames :
            if not filename[:-4] + '_f.pkl' in self.listFilesPkl:
                start       = time.time()
                if parseDatesManual : df = pd.read_csv(folderCSV + filename,names=['Tag','value','timestamp'])
                else : df = pd.read_csv(folderCSV + filename,parse_dates=[2],names=['Tag','value','timestamp'])
                print("============================================")
                print("file converted to .pkl in : ",filename)
                self.utils.printCTime(start)
                start = time.time()
                print("============================================")
                print("formatting file : ",filename)
                dfOut['value'] = pd.to_numeric(df['value'],errors='coerce')
                self.utils.printCTime(start)
                with open(self.folderPkl + filename[:-4] + '_f.pkl' , 'wb') as handle:# save the file
                    pickle.dump(df, handle, protocol=pickle.HIGHEST_PROTOCOL)
                print("============================================")
            else :
                print("============================================")
                print('filename : ' ,filename,' already in folder : ',self.folderPkl)
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
        return self.utils.get_listFilesPklV2(self.folderPkl)

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

    def getTagsTU(self,patTag,units=None,onCol='tag',case=False,ds=True,cols='tag'):
        if not units : units = self.listUnits
        res = self.dfPLC.copy()
        if 'tag' in onCol.lower():whichCol = self.tagCol
        elif 'des' in onCol.lower():whichCol = self.descriptCol
        filter1 = res[whichCol].str.contains(patTag,case=case)
        if isinstance(units,str):units = [units]
        filter2 = res[self.unitCol].isin(units)
        res = res[filter1&filter2]
        if cols=='tdu' :
            return res.loc[:,[self.tagCol,self.descriptCol,self.unitCol]]
        elif cols=='tag' : return list(res[self.tagCol])
        elif cols=='print':return self.utils.printDFSpecial(res)

    def getCatsFromUnit(self,unitName,pattern=None):
        if not pattern:
            pattern = self.listPatterns[0]
        sameUnitTags = self.getTagsSameUnit(unitName)
        return list(pd.DataFrame([re.findall(pattern,k)[0] for k in sameUnitTags])[0].unique())

    def getDescriptionFromTagname(self,tagName):
        return list(self.dfPLC[self.dfPLC[self.tagCol]==tagName][self.descriptCol])[0]

    def getTagnamefromDescription(self,desName):
        return list(self.dfPLC[self.dfPLC[self.descriptCol]==desName][self.tagCol])[0]

    def getTagDescription(self,df,cols=1):
        if 'tag' in [k.lower() for k in df.columns]:listTags = list(df.Tag.unique())
        else : listTags = list(df.columns)
        if cols==1:listCols = [self.descriptCol]
        if cols==2:listCols = [self.tagCol,self.descriptCol]
        return self.dfPLC[self.dfPLC[self.tagCol].isin(listTags)][listCols]

    # ==============================================================================
    #                   functions filter on dataFrame
    # ==============================================================================
    def getDFfromTagList(self,df,tagList,formatted=1):
        if not isinstance(tagList,list):tagList =[tagList]
        dfOut = df[df.tag.isin(tagList)]
        if not formatted :dfOut.value = pd.to_numeric(dfOut['value'],errors='coerce')
        return dfOut.sort_values(by=['tag','timestampUTC'])

    def getDFTimeRange(self,df,timeRange,col='timestampUTC'):
        t0 = parser.parse(timeRange[0]).astimezone(pytz.timezone('UTC'))
        t1 = parser.parse(timeRange[1]).astimezone(pytz.timezone('UTC'))
        if col == 'index': return df[(df.index>t0)&(df.index<t1)].sort_index()
        else : return df[(df[col]>t0)&(df[col]<t1)].sort_values(by=col)

    def loadDF_TimeRange_Tags_raw(self,timeRange,listTags,skip=1,conditionFile='',tzSel='Europe/Paris'):
        lfs = [k for k in self.listFilesPkl if conditionFile in k]
        listDates,delta = self.utils.datesBetween2Dates(timeRange,offset=1)
        listFiles = [f for d in listDates for f in lfs if d in f]
        if not listFiles : print('there are no files to load')
        else :
            dfs = []
            for filename in listFiles :
                print(filename)
                df = self.loadFile(filename,skip=skip)
                df = self.getDFfromTagList(df,listTags)
                dfs.append(df)
            df= self.getDFTimeRange(pd.concat(dfs),timeRange)
            # df.timestamp = df.timestampUTC.tz_convert(tzSel)
            return df

    def loadDF_TimeRange_Tags(self,timeRange,tags,rs='auto',applyMethod='mean',tzSel='Europe/Paris'):
        listDates,delta = self.utils.datesBetween2Dates(timeRange,offset=1)
        if rs=='auto':rs = '{:.0f}'.format(max(1,delta.total_seconds()/3600)) + 's'
        dfs = []
        for d in listDates:
            print(d)
            dftmp  = self.loadFile('*'+d+'*')
            if 'tag' in dftmp.columns :
                dftmp = self.getDFfromTagList(dftmp,tags)
            if len(dftmp.columns)>0:
                df = self.utils.pivotDataFrame(dftmp,colPivot='tag',colValue='value',colTimestamp='timestampUTC',resampleRate=rs,applyMethod=applyMethod)
                dfs.append(df)
        if not dfs : print('there are no files to load')
        else :
            # start = time.time()
            df=pd.concat(dfs,axis=0)
            # self.utils.printCTime(start,'concatenation')
            # start = time.time()
            # df.index=df.index.tz_convert(tzSel)# convert utc to tzSel timezone
            # self.utils.printCTime(start,'converting timestamp')
            # start = time.time()
            # self.getDFTimeRange(df,timeRange,'index')
            # self.utils.printCTime(start,'filtering timerange')
            return df

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
