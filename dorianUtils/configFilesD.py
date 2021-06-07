import pandas as pd,numpy as np
from multiprocessing import Process, Queue, current_process,Pool
from pandas.tseries.frequencies import to_offset
import subprocess as sp, os,re, pickle
import time, datetime as dt, pytz
from scipy import linalg, integrate
from dateutil import parser
from dorianUtils.utilsD import Utils
from pyspark.sql import SparkSession
from dorianUtils.sparkUtils.sparkDfUtils import SparkDfUtils
import findspark, glob

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

    def _getValidFiles(self):
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
        self.confFile     = confFile
        self.modelAndFile = self.__getModelNumber()
        self.listFilesPkl = self._get_ValidFiles()
        self.dfPLC        = pd.read_csv(confFile,encoding=encode)

        self.unitCol,self.descriptCol,self.tagCol = self._getPLC_ColName()
        self.listUnits    = self._get_UnitsdfPLC()

        self.allPatterns  = self.utils.listPatterns
        self.listPatterns = self._get_validPatterns()

    def __getModelNumber(self):
        modelNb = re.findall('\d{5}-\d{3}',self.confFile)
        if not modelNb: return ''
        else : return modelNb[0]

# ==============================================================================
#                     basic functions
# ==============================================================================
    def _getPLC_ColName(self):
        l = self.dfPLC.columns
        v = l.to_frame()
        unitCol = ['unit' in k.lower() for k in l]
        descriptName = ['descript' in k.lower() for k in l]
        tagName = ['tag' in k.lower() for k in l]
        return [list(v[k][0])[0] for k in [unitCol,descriptName,tagName]]

    def _get_validPatterns(self):
        model = self.modelAndFile.split('-')[0]
        if model=='10001' :
            return [self.allPatterns[k] for k in [6,0]]
        if model=='10002' :
            return [self.allPatterns[k] for k in [1,2,3,4,5,0]]

    def _get_ValidFiles(self):
        return self.utils.get_listFilesPklV2(self.folderPkl)

    def _get_UnitsdfPLC(self):
        listUnits = self.dfPLC[self.unitCol]
        return listUnits[~listUnits.isna()].unique().tolist()

# ==============================================================================
#                   functions filter on configuration file with tags
# ==============================================================================
    def getUnitsOfpivotedDF(self,df,asList=True):
        dfP,listTags,tagsWithUnits=self.dfPLC,df.columns,[]
        for tagName in listTags :
            tagsWithUnits.append(dfP[dfP[self.tagCol]==tagName][[self.tagCol,self.unitCol]])
        tagsWithUnits = pd.concat(tagsWithUnits)
        if asList :tagsWithUnits = [k + ' ( in ' + l + ')' for k,l in zip(tagsWithUnits[self.tagCol],tagsWithUnits[self.unitCol])]
        return tagsWithUnits

    def getTagsTU(self,patTag,units=None,onCol='tag',case=False,cols='tag',ds=True):
        if not units : units = self.listUnits
        if ds: res=self.dfPLC[self.dfPLC.DATASCIENTISM==True]
        else: res = self.dfPLC.copy()
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
        if not pattern:pattern = self.listPatterns[0]
        sameUnitTags = self.getTagsTU('',unitName)
        return list(pd.DataFrame([re.findall(pattern,k)[0] for k in sameUnitTags])[0].unique())

    def getDescriptionFromTagname(self,tagName):
        return list(self.dfPLC[self.dfPLC[self.tagCol]==tagName][self.descriptCol])[0]

    def getTagnamefromDescription(self,desName):
        return list(self.dfPLC[self.dfPLC[self.descriptCol]==desName][self.tagCol])[0]

    # ==============================================================================
    #                   functions filter on dataFrame
    # ==============================================================================
    def _DF_fromTagList(self,datum,tagList,rs):
        realDatum = self.utils.datesBetween2Dates([datum,datum],offset=+1)[0]
        df=self.loadFile('*' + realDatum[0]  + '*')
        df = df.drop_duplicates(subset=['timestampUTC', 'tag'], keep='last')

        if not isinstance(tagList,list):tagList =[tagList]
        df = df[df.tag.isin(tagList)]
        if not rs=='raw':df = df.pivot(index="timestampUTC", columns="tag", values="value")
        else : df = df.sort_values(by=['tag','timestampUTC']).set_index('timestampUTC')
        return df

    def _DF_cutTimeRange(self,df,timeRange,timezone='Europe/Paris'):
        '''df should have a timestamp object as index or raw column called timestampUTC'''
        t0 = parser.parse(timeRange[0]).astimezone(pytz.timezone('UTC'))
        t1 = parser.parse(timeRange[1]).astimezone(pytz.timezone('UTC'))
        df=df[(df.index>t0)&(df.index<t1)].sort_index()
        df.index=df.index.tz_convert(timezone)# convert utc to tzSel timezone
        return df

    def _loadDFTagDay(self,datum,tag,rs):
        # print(tag)
        folderDaySmallPower=self.folderPkl+'parkedData/'+ datum + '/'
        df = pickle.load(open(folderDaySmallPower + tag + '.pkl', "rb" ))
        df = df.drop_duplicates(subset=['timestampUTC', 'tag'], keep='last')
        # df.duplicated(subset=['timestampUTC', 'tag'], keep=False)
        if not rs=='raw':df = df.pivot(index="timestampUTC", columns="tag", values="value")
        else : df=df.set_index('timestampUTC')
        return df

    def _loadDFTagsDay(self,datum,listTags,rs,parked,pool):
        dfs=[]
        print(datum)
        if parked :
            if pool :
                print('pooled process')
                with Pool() as p:
                    dfs=p.starmap(self._loadDFTagDay, [(datum,tag,rs) for tag in listTags])
            else :
                for tag in listTags:
                    dfs.append(self._loadDFTagDay(datum,tag,rs))
        else :
            dfs.append(self._DF_fromTagList(datum,listTags,rs))
        if rs=='raw':df  = pd.concat(dfs,axis=0)
        else :
            df = pd.concat(dfs,axis=1)
            tmp = list(df.columns);tmp.sort();df=df[tmp]
        return df

    def DF_loadTimeRangeTags(self,timeRange,listTags,rs='auto',applyMethod='nanmean',parked=True,timezone='Europe/Paris',pool=True):
        listDates,delta = self.utils.datesBetween2Dates(timeRange,offset=0)
        if rs=='auto':rs = '{:.0f}'.format(max(1,delta.total_seconds()/6400)) + 's'
        dfs=[]
        if pool:
            with Pool() as p:
                dfs=p.starmap(self._loadDFTagsDay, [(datum,listTags,rs,parked,False) for datum in listDates])
        else:
            for datum in listDates:
                dfs.append(self._loadDFTagsDay(datum,listTags,rs,parked,True))
        df = pd.concat(dfs,axis=0)
        print("finish loading")
        if not rs=='raw':
            df = eval('df.resample(rs).apply(np.' + applyMethod + ')')
            rsOffset = str(max(1,int(float(re.findall('\d+',rs)[0])/2)))
            period=re.findall('[a-zA-z]+',rs)[0]
            df.index=df.index+to_offset(rsOffset +period)
        df = self._DF_cutTimeRange(df,timeRange,timezone)
        if rs=='raw' :
            df['timestamp']=df.index
            df=df.sort_values(by=['tag','timestamp'])
            df=df.drop(['timestamp'],axis=1)
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

class ConfigDashRealTime():
    def __init__(self,confFolder,timeWindow=2*60*60,connParameters=None,
                    folderFig=None,folderExport=None,encode='utf-8'):
        import glob
        self.confFile   = glob.glob(confFolder+'*PLC*')[0]
        self.dfPLC      = pd.read_csv(self.confFile,encoding=encode)
        self.usefulTags = pd.read_csv(glob.glob(confFolder+'*predefinedCategories*')[0] + '',index_col=0)
        self.timeWindow = timeWindow #seconds
        self.utils      = Utils()
        self.connParameters = connParameters
        if not self.connParameters :
        # self.modelAndFile = self.__getModelNumber()
        # self.unitCol,self.descriptCol,self.tagCol = self._getPLC_ColName()
        # self.listUnits    = self._get_UnitsdfPLC()
        self.unitCol,self.descriptCol,self.tagCol = self._getPLC_ColName()

    def _getPLC_ColName(self):
        l = self.dfPLC.columns
        v = l.to_frame()
        unitCol = ['unit' in k.lower() for k in l]
        descriptName = ['descript' in k.lower() for k in l]
        tagName = ['tag' in k.lower() for k in l]
        return [list(v[k][0])[0] for k in [unitCol,descriptName,tagName]]

    def connectToDB(self):
        return self.utils.connectToPSQLsDataBase(self.connParameters)

    def realtimeDF(self,preSelGraph,rs,rsMethod='mean'):
        preSelGraph = self.usefulTags.loc[preSelGraph]
        conn = self.connectToDB(self.connParameters)
        df   = self.utils.readSQLdataBase(conn,preSelGraph.Pattern,secs=self.timeWindow)
        df['value'] = pd.to_numeric(df['value'],errors='coerce')
        df = df.sort_values(by=['timestampz','tag'])
        print(df)
        df['timestampz'] = df.timestampz.dt.tz_convert('Europe/Paris')
        df = self.utils.pivotDataFrame(df,resampleRate=rs,applyMethod='nan'+rsMethod)
        conn.close()
        return df, preSelGraph.Unit

    def getDescriptionFromTagname(self,tagName):
        return list(self.dfPLC[self.dfPLC[self.tagCol]==tagName][self.descriptCol])[0]

    def getTagnamefromDescription(self,desName):
        return list(self.dfPLC[self.dfPLC[self.descriptCol]==desName][self.tagCol])[0]

class ConfigDashSpark():
    def __init__(self,sparkData,sparkConfFile,confFile,folderFig=None,folderExport=None,encode='utf-8'):
        if not folderFig : folderFig = os.getenv('HOME') + '/Images/'
        if not folderExport : folderExport = os.getenv('HOME') + '/Documents/'

        self.folderExport   = folderExport
        self.folderFig      = folderFig
        self.filePLC        = confFile
        self.dfPLC          = pd.read_csv(self.filePLC)
        self.unitCol,self.descriptCol,self.tagCol = self._getPLC_ColName()
        self.listUnits      = self._get_UnitsdfPLC()

        self.cfgSys     = self._getSysConf(sparkConfFile)
        self.spark      = self.__createSparkSession()
        self.sparkConf  = self.spark.sparkContext.getConf().getAll()

        self.sparkData  = sparkData

        self.sdu   = SparkDfUtils(self.spark)
        self.utils = Utils()
    # ==========================================================================
    #                         private functions
    # ==========================================================================

    def _getPLC_ColName(self):
        l = self.dfPLC.columns
        v = l.to_frame()
        unitCol = ['unit' in k.lower() for k in l]
        descriptName = ['descript' in k.lower() for k in l]
        tagName = ['tag' in k.lower() for k in l]
        return [list(v[k][0])[0] for k in [unitCol,descriptName,tagName]]

    def _get_UnitsdfPLC(self):
        listUnits = self.dfPLC[self.unitCol]
        return listUnits[~listUnits.isna()].unique().tolist()

    def _getSysConf(self,scriptFile):
        def toString(b):
            s = str(b).strip()
            if (s.startswith("b'")): s = s[2:].strip()
            if (s.endswith("'")): s = s[:-1].strip()
            return s
        import subprocess
        conf = None
        process = subprocess.Popen(scriptFile.split(),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                shell=True,
                                executable="/bin/bash")
        stdout, stderr = process.communicate()
        stderr = toString(stderr)
        if (len(stderr) < 3):
            conf = {}
            stdout = toString(stdout)
            stdout = stdout.replace("\\n", '\n')
            stdout = stdout.split('\n')
            for kv in stdout:
                kv = kv.split('=', 1)
                if (len(kv)==2 and not ' ' in kv[0] and kv[0] != '_'):
                    kv[0] = kv[0].strip()
                    conf.update({kv[0]: kv[1]})
        return conf

    def _getSparkParams(self):
        def clean(line, sep, index):
            value = line.split(sep, 1)[index]
            value = value.strip()
            if (value.startswith('"') or value.startswith("'")): value = value[1:]
            if (value.endswith('"') or value.endswith("'")): value = value[:-1]
            return value
        sparkCmd = self.cfgSys.get("SPARK_CMD")
        if (sparkCmd == None):
            print("")
            print("ERROR: 'SPARK_CMD' environment variable is missing !")
            print("")
            sys.exit(0)
        lines = sparkCmd.split("--")
        params = []
        for line in lines:
            line = line.strip()
            # name
            if (line.startswith("name ")):
                params.append({ "type": "name", "key": "name", "value": clean(line, ' ', 1) })
            # master
            elif (line.startswith("master ")):
                params.append({ "type": "master", "key": "master", "value": clean(line, ' ', 1) })
            # deploy-mode
            elif (line.startswith("deploy-mode ")):
                params.append({ "type": "conf", "key": "spark.submit.deployMode", "value": clean(line, ' ', 1) })
            # conf
            elif (line.startswith("conf ")):
                kvpair = line.split(' ', 1)[1]
                params.append({ "type": "conf", "key": clean(kvpair, '=', 0), "value": clean(kvpair, '=', 1) })
            # packages
            elif (line.startswith("packages ")):
                libs = [lib.strip() for lib in line[8:].split(',')]
                libs = ','.join(libs)
                params.append({ "type": "packages", "key": "spark.jars.packages", "value": libs })
            # jars
            elif (line.startswith("jars ")):
                libs = [lib.strip() for lib in line[4:].split(',')]
                libs = ','.join(libs)
                params.append({ "type": "jars", "key": "spark.jars", "value": libs })
            # driver-class-path
            elif (line.startswith("driver-class-path ")):
                libs = [lib.strip() for lib in line[17:].split(',')]
                libs = ','.join(libs)
                params.append({ "type": "driver-class-path", "key": "spark.driver.extraClassPath", "value": libs })
        return params

    def __createSparkSession(self):
        params = self._getSparkParams()
        # Get the builder
        builder = SparkSession.builder
        # Set name
        for param in params:
            if (param.get("type")=="name"):
                builder = builder.appName(param.get("value"))
                break
        # Set master
        for param in params:
            if (param.get("type")=="master"):
                builder = builder.master(param.get("value"))
                break
        # Set conf params - Include "spark.submit.deployMode" (--deploy-mode) and "spark.jars.packages" (--packages)
        for param in params:
            if (param.get("type")=="conf"):
                builder = builder.config(param.get("key"), param.get("value"))
        # Set packages
        for param in params:
            if (param.get("type")=="packages"):
                builder = builder.config(param.get("key"), param.get("value"))
        # Set jars libs
        for param in params:
            if (param.get("type")=="jars"):
                builder = builder.config(param.get("key"), param.get("value"))
        # Set driver-class-path libs
        for param in params:
            if (param.get("type")=="driver-class-path"):
                builder = builder.config(param.get("key"), param.get("value"))
        # Enable HIVE support
        ehs = self.cfgSys.get("ENABLE_HIVE_SUPPORT")
        if (ehs != None):
            ehs = ehs.strip().lower()
            if (ehs == "true"):
                builder = builder.enableHiveSupport()
                print(" - Spark HIVE support enabled")
        # Create the Spark session
        spark = builder.getOrCreate()
        spark.conf.set("spark.sql.execution.arrow.pyspark.enabled", "true")
        return spark

    # ==========================================================================
    #                         functions on dataframe
    # ==========================================================================
    def getTagsTU(self,patTag,units=None,onCol='tag',case=False,cols='tag'):
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

    def getPartitions(self,timeRange):
        from dateutil import parser

        def createSinglePartition(curDay,hours):
            vars = ['year','month','day']
            # partoch=[l.upper() + "=" + str(eval('curDay.'+ l)) for l in vars] # doesn't work !!
            partoch = []
            for k in vars:partoch.append(k.upper() + "=" + str(eval('curDay.'+k)))
            tmp = '{' + ','.join([str(k) for k in range(hours[0],hours[1])]) + '}'
            partoch.append('HOUR=' + tmp)
            partoch = '/'.join(partoch)
            return partoch

        t0,t1     = [parser.parse(k) for k in timeRange]
        lastDay=(t1-t0).days
        if lastDay==0:
            curDay=t0
            partitions = [createSinglePartition(t0,[t0.hour,t1.hour])]
        else :
            curDay=t0
            partitions = [createSinglePartition(t0,[t0.hour,24])]
            for k in range(1,lastDay):
                curDay=t0+dt.timedelta(days=k)
                curDay=curDay-dt.timedelta(hours=curDay.hour,minutes=curDay.minute)
                partitions.append(createSinglePartition(curDay,[0,24]))
            curDay=t1
            partitions.append(createSinglePartition(t1,[0,t1.hour]))
        return partitions

    def getPartitions_v0(self,timeRange):
        t0,t1 = [parser.parse(k) for k in timeRange]
        yearRange = str(t0.year)
        monthRange="{" + str(t0.month) + "," + str(t1.month) + "}"
        dayRange="{" + str(t0.day) + "," + str(t1.day) + "}"
        hourRange="[" + str(t0.hour) + "," + str(t1.hour) + "]"
        # hourRange="{" + str(t0.hour) + "," + str(t1.hour) + "}"
        partitions = {
                    "YEAR" : yearRange,
                    "MONTH" : monthRange,
                    "DAY" : dayRange,
                    "HOUR" : hourRange,
        }
        partitions = [k + "=" + v for k,v in partitions.items()]
        return '/'.join(partitions)

    def loadSparkTimeDF(self,timeRange,typeData="EncodedData"):
        ''' typeData = {
        encoded data : "EncodedData"
        aggregated data : "AggregatedData`"
        populated data :"PopulatedData"
        }
        '''
        df = self.sdu.loadParquet(inputDir=self.sparkData+typeData+"/",partitions=self.getPartitions(timeRange))
        df = self.sdu.organizeColumns(df, columns=["YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "SECOND"], atStart=True)
        timeSQL = "TIMESTAMP_UTC" + " BETWEEN '" + timeRange[0] +"' AND '" + timeRange[1] +"'"
        return df.where(timeSQL)

    def getSparkTU(self,df,listTags):
        dfs=[]
        if not isinstance(listTags,list):listTags=[listTags]
        for tag in listTags:
            print(tag)
            df2 = df.where("TAG == "+ "'" + tag + "'")
            df3 = df2.select('TAG','VALUE','TIMESTAMP_UTC')
            dfs.append(df3.toPandas())
        pdf = pd.concat(dfs).sort_values(by=['TIMESTAMP_UTC','TAG'])
        return pdf

    def getSparkTU_v2(self,df,listTags):
        dfs=self.sdu.createDataFrame(schema=[["TAG","string"],["VALUE","double"],["TIMESTAMP_UTC","timestamp"]])

        if not isinstance(listTags,list):listTags=[listTags]
        for tag in listTags:
            print(tag)
            df2 = df.where("TAG == "+ "'" + tag + "'").select('TAG','VALUE','TIMESTAMP_UTC')
            dfs=dfs.unionByName(df2)
        pdf = dfs.toPandas().sort_values(by=['TIMESTAMP_UTC','TAG'])
        return pdf
        # return dfs
