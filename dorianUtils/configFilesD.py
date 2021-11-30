import pandas as pd,numpy as np
from multiprocessing import Process, Queue, current_process,Pool
from pandas.tseries.frequencies import to_offset
import subprocess as sp, os,re, pickle,glob
import time, datetime as dt, pytz
from scipy import linalg, integrate
from dateutil import parser
from dorianUtils.utilsD import Utils
from dorianUtils.comUtils import Modebus_utils
from opcua import Client

pd.options.mode.chained_assignment = None  # default='warn'

class ConfigMaster:
    """docstring for ConfigMaster."""

    def __init__(self,folderPkl):
        self.utils      = Utils()
        self.folderPkl = folderPkl
        self.listFiles = self.utils.get_listFilesPklV2(folderPkl)
        # self.dfPLC = self._loadDF_PLC()
# ==============================================================================
#                                 functions
# ==============================================================================
    def _loadDF_PLC(self):
        if len(self.listFiles)>0:
            start=time.time()
            df = self.loadFile(self.listFiles[0])
            print('dfplc loaded in {:.2f} milliseconds'.format((time.time()-start)*1000))
            return pd.DataFrame(df.tag.unique(),columns=['TAG'])
        else : return pd.DataFrame()

    def _getValidFiles(self):
        return sp.check_output('cd ' + '{:s}'.format(self.folderPkl) + ' && ls *' + self.validPattern +'*',shell=True).decode().split('\n')[:-1]

    def loadFile(self,filename,skip=1):
        if '*' in filename :
            filenames=self.utils.get_listFilesPklV2(self.folderPkl,filename)
            if len(filenames)>0 : filename=filenames[0]
            else : return pd.DataFrame()
        df = pickle.load(open(filename, "rb" ))
        return df[::skip]

    def _parkTag(self,df,tag,folder):
        print(tag)
        # colTag = [k for k in df.columns if k.lower()=='tag']
        dfTag=df[df.tag==tag]
        with open(folder + tag + '.pkl' , 'wb') as handle:
            pickle.dump(dfTag, handle, protocol=pickle.HIGHEST_PROTOCOL)

    def parkDayPKL(self,datum,offset=1,pool=False):
        print(datum)
        realDatum=parser.parse(datum)+dt.timedelta(days=offset)
        df = self.loadFile('*'+ realDatum.strftime('%Y-%m-%d') + '*')
        if not df.empty:
            folder=self.folderPkl+'parkedData/'+ datum + '/'
            if not os.path.exists(folder):os.mkdir(folder)
            # listTags=list(self.dfPLC.TAG.unique())
            listTags=list(df.tag.unique())
            if pool:
                with Pool() as p:p.starmap(self._parkTag,[(df,tag,folder) for tag in listTags])
            else:
                for tag in listTags:
                    self._parkTag(df,tag,folder)
        else : print('no data loaded')

    def parkDates(self,listDates,nCores=4,offset=0):
        if nCores>1:
            with Pool(nCores) as p:
                p.starmap(self.parkDayPKL,[(datum,offset,False) for datum in listDates])
        else :
            for datum in listDates:
                self.parkDayPKL(datum)

class ConfigDashTagUnitTimestamp(ConfigMaster):
    def __init__(self,folderPkl,confFolder,encode='utf-8'):
        ConfigMaster.__init__(self,folderPkl)
        self.confFolder   = confFolder
        self.confFile     = glob.glob(self.confFolder + '*PLC*')[0]
        self.modelAndFile = self.__getModelNumber()
        self.listFilesPkl = self._get_ValidFiles()
        self.parked   = False
        if os.path.exists(self.folderPkl+'/parkedData'):
            self.parked     = True
            self.parkedDays =[k.split('/')[-1] for k in glob.glob(self.folderPkl+'parkedData/*')]
            self.parkedDays.sort()
        self.dfPLC        = pd.read_csv(self.confFile,encoding=encode)
        try :
            self.usefulTags = pd.read_csv(self.confFolder+'/predefinedCategories.csv',index_col=0)
            self.usefulTags.index = self.utils.uniformListStrings(list(self.usefulTags.index))
        except :
            self.usefulTags = pd.DataFrame()

        self.unitCol,self.descriptCol,self.tagCol = self._getPLC_ColName()
        self.listUnits    = self._get_UnitsdfPLC()

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

    def _get_ValidFiles(self):
        return self.utils.get_listFilesPklV2(self.folderPkl)

    def _get_UnitsdfPLC(self):
        listUnits = self.dfPLC[self.unitCol]
        return listUnits[~listUnits.isna()].unique().tolist()

    def getUsefulTags(self,usefulTag):
        category = self.usefulTags.loc[usefulTag]
        return self.getTagsTU(category.Pattern,category.Unit)

    def checkDiffbetweenPLCandDF(self,df):
        '''difference between tags in df and dfPLC'''
        listTagsDf = pd.DataFrame(df.tag.unique(),columns=['tag'])
        listTagsDf = listTagsDf.sort_values(by='tag')
        dfplc = pd.DataFrame(self.dfPLC.TAG.sort_values())
        dfplc['id']='dfplc'
        listTagsDf['id']='listTagsDf'
        listTagsDf.columns=['TAG','id']
        return pd.concat([dfplc,listTagsDf],axis=0).drop_duplicates(subset='TAG',keep=False)

    def checkDFvsPLCTags(self,df):
        df2=df.tag.unique()
        df2.columns='TAG'
        dupl = pd.concat([df2,self.dfPLC.TAG]).duplicated(subset=['TAG'])
        return dupl

    def renameColsPkl(self):
        import pickle
        for f in self.listFilesPkl:
            print(f)
            df=self.loadFile(f)
            df.columns=['tag','value','timestampUTC']
            with open(f, 'wb') as handle:
                pickle.dump(df, handle, protocol=pickle.HIGHEST_PROTOCOL)

# ==============================================================================
#                   functions filter on configuration file with tags
# ==============================================================================
    def DF_standardProcessing(self,df,rs='auto',applyMethod='mean',timezone='Europe/Paris'):
        if df.duplicated().any():
            df = df.drop_duplicates()
            print("attention il y a des doublons dans la base de donnees Jules")
        df['timestampz'] = df.timestampz.dt.tz_convert(timezone)
        df = df.pivot(index="timestampz", columns="tag", values="value")
        deltaT=(df.index[-1]-df.index[0]).total_seconds()
        if rs=='auto':rs = '{:.0f}'.format(max(1,deltaT//1000)) + 's'
        df['value'] = pd.to_numeric(df['value'],errors='coerce')
        df = df.sort_values(by=['timestampz','tag'])
        df = eval("df.resample('100ms').ffill().ffill().resample(rs).apply(np." + applyMethod + ")")
        return df

    def getUnitsOfpivotedDF(self,df,asList=True):
        dfP,listTags,tagsWithUnits=self.dfPLC,df.columns,[]
        for tagName in listTags :
            tagsWithUnits.append(dfP[dfP[self.tagCol]==tagName][[self.tagCol,self.unitCol]])
        tagsWithUnits = pd.concat(tagsWithUnits)
        if asList :tagsWithUnits = [k + ' ( in ' + l + ')' for k,l in zip(tagsWithUnits[self.tagCol],tagsWithUnits[self.unitCol])]
        return tagsWithUnits

    def getUnitofTag(self,tag):
        unit=self.dfPLC.loc[tag].UNITE
        # print(unit)
        if not isinstance(unit,str):
            unit='u.a'
        return unit

    def getTagsTU(self,patTag,units=None,onCol='index',cols='tag'):
        #patTag
        if onCol=='index':
            df = self.dfPLC[self.dfPLC.index.str.contains(patTag,case=False)]
        else:
            df = self.dfPLC[self.dfPLC[onCol].str.contains(patTag,case=False)]

        #units
        if not units : units = self.listUnits
        if isinstance(units,str):units = [units]
        df = df[df['UNITE'].isin(units)]

        #return
        if cols=='tdu' :
            return df[['DESCRIPTION','UNITE']]
        elif cols=='tag':
            return list(df.index)
        else :
            return df

    def getCatsFromUnit(self,unitName,pattern=None):
        if not pattern:pattern = self.listPatterns[0]
        sameUnitTags = self.getTagsTU('',unitName)
        return list(pd.DataFrame([re.findall(pattern,k)[0] for k in sameUnitTags])[0].unique())

    def getDescriptionFromTagname(self,tagName):
        return list(self.dfPLC[self.dfPLC[self.tagCol]==tagName][self.descriptCol])[0]

    def getTagnamefromDescription(self,desName):
        return list(self.dfPLC[self.dfPLC[self.descriptCol]==desName][self.tagCol])[0]

    def get_randomListTags(self,n=5):
        import random
        allTags = self.getTagsTU('',ds=True)
        return [allTags[random.randint(0,len(allTags))] for k in range(n)]


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
        t0 = parser.parse(timeRange[0]).astimezone(pytz.timezone('UTC'))
        t1 = parser.parse(timeRange[1]).astimezone(pytz.timezone('UTC'))
        df=df[(df.index>t0)&(df.index<t1)].sort_index()
        df.index=df.index.tz_convert(timezone)# convert utc to tzSel timezone
        return df

    def _loadDFTagDay(self,datum,tag,raw=False):
        # print(tag)
        folderDaySmallPower=self.folderPkl+'parkedData/'+ datum + '/'
        try:
            df = pickle.load(open(folderDaySmallPower + tag + '.pkl', "rb" ))
            df = df.drop_duplicates(subset=['timestampUTC', 'tag'], keep='last')
            # df.duplicated(subset=['timestampUTC', 'tag'], keep=False)
            if not raw:df = df.pivot(index="timestampUTC", columns="tag", values="value")
            else : df=df.set_index('timestampUTC')
        except :
            df = pd.DataFrame()
            print('loading of file :',folderDaySmallPower + tag + '.pkl' ,' was not possible')
        return df

    def _loadDFTagsDay(self,datum,listTags,parked,pool,raw=False):
        dfs=[]
        print(datum)
        if parked :
            if pool :
                print('pooled process')
                with Pool() as p:
                    dfs=p.starmap(self._loadDFTagDay, [(datum,tag,raw) for tag in listTags])
            else :
                for tag in listTags:
                    dfs.append(self._loadDFTagDay(datum,tag,raw))
        else :
            dfs.append(self._DF_fromTagList(datum,listTags,raw))
        if raw:df  = pd.concat(dfs,axis=0)
        else :
            df = pd.concat(dfs,axis=1)
        return df

    def DF_loadTimeRangeTags(self,timeRange,listTags,rs='auto',applyMethod='mean',
                                parked=True,timezone='Europe/Paris',pool=True):
        if not timeRange:
            if parked : day = self.parkedDays[-1]
            else : day = re.findall('\d{4}-\d{2}-\d{2}',self.listFilesPkl[-1])[0]
            timeRange = [day + ' 9:00',day + ' 18:00']

        listDates,delta = self.utils.datesBetween2Dates(timeRange,offset=0)

        if rs=='auto':rs = '{:.0f}'.format(max(1,delta.total_seconds()//1000)) + 's'
        dfs=[]
        if len(listTags)>0:
            if pool:
                with Pool() as p:
                    dfs=p.starmap(self._loadDFTagsDay, [(datum,listTags,parked,False,rs=='raw') for datum in listDates])
            else:
                for datum in listDates:
                    dfs.append(self._loadDFTagsDay(datum,listTags,parked,True,rs=='raw'))
        else:
            return pd.DataFrame()
        if len(dfs)>0 :
            df = pd.concat(dfs,axis=0)
            print("finish loading")
            if not df.empty:
                if not rs=='raw':
                    df = self._DF_cutTimeRange(df,timeRange,timezone)
                    df = df[~df.index.duplicated()]
                    df = eval("df.resample('100ms').ffill().ffill().resample(rs).apply(np." + applyMethod + ")")
                    df = df.loc[:,~df.columns.duplicated()]
                    df = df.reindex(sorted(df.columns),axis=1)
                else:
                    df['timestamp']=df.index
                    df = df.sort_values(by=['tag','timestamp'])
                    df = df.drop(['timestamp'],axis=1)
                    df = self._DF_cutTimeRange(df,timeRange,timezone)
            else : df= pd.DataFrame()
        else : df= pd.DataFrame()
        return df

    def plotMultiUnitGraph(self,timeRange,listTags=[],**kwargs):
        if not listTags : listTags=self.get_randomListTags()
        tagMapping = {t:self.getUnitofTag(t) for t in listTags}
        df  = self.DF_loadTimeRangeTags(timeRange,listTags,**kwargs)
        return self.utils.multiUnitGraph(df,tagMapping)

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

class ConfigDashRealTime(ConfigDashTagUnitTimestamp):
    def __init__(self,confFolder,connParameters):
        import glob
        from dorianUtils.utilsD import DataBase
        super().__init__(folderPkl='',confFolder=confFolder)
        self.dataBaseUtils  = DataBase()
        self.connParameters = connParameters

    def _getPLC_ColName(self):
        l = self.dfPLC.columns
        v = l.to_frame()
        unitCol = ['unit' in k.lower() for k in l]
        descriptName = ['descript' in k.lower() for k in l]
        tagName = ['tag' in k.lower() for k in l]
        return [list(v[k][0])[0] for k in [unitCol,descriptName,tagName]]

    def connectToDB(self):
        return self.dataBaseUtils.connectToPSQLsDataBase(self.connParameters)

    def processRawData(self,df,rs='1s',applyMethod='mean'):
        if df.duplicated().any():
            df = df.drop_duplicates()
            print("attention il y a des doublons dans la base de donnees Jules")
        df['value'] = pd.to_numeric(df['value'],errors='coerce')
        df = df.sort_values(by=['timestampz','tag'])
        df['timestampz'] = df.timestampz.dt.tz_convert('Europe/Paris')
        df = df.pivot(index="timestampz", columns="tag", values="value")
        df = eval("df.resample('100ms').ffill().ffill().resample(rs).apply(np." + applyMethod + ")")
        return df

    def realtimeDF(self,preSelGraph,rs='1s',applyMethod='mean',timeWindow=60*60*2):
        if rs=='auto':rs = '{:.0f}'.format(max(1,timeWindow//1000)) + 's'
        preSelGraph = self.usefulTags.loc[preSelGraph]
        conn = self.connectToDB()
        df   = self.dataBaseUtils.readSQLdataBase(conn,preSelGraph.Pattern,secs=timeWindow)
        if df.duplicated().any():
            df = df.drop_duplicates()
            print("attention il y a des doublons dans la base de donnees Jules")
        df['value'] = pd.to_numeric(df['value'],errors='coerce')
        df = df.sort_values(by=['timestampz','tag'])
        df['timestampz'] = df.timestampz.dt.tz_convert('Europe/Paris')
        df = df.pivot(index="timestampz", columns="tag", values="value")
        df = eval("df.resample('100ms').ffill().ffill().resample(rs).apply(np." + applyMethod + ")")
        conn.close()
        return df

    def realtimeTagsDF(self,tags,timeWindow=60*60*2,rs='1s',applyMethod='mean',simulated=False,timeRange=None):
        if rs=='auto':rs = '{:.0f}'.format(max(1,timeWindow//1000)) + 's'
        if simulated:
            t1 = pd.Timestamp.now('CET')
            idx = pd.date_range(start=t1-dt.timedelta(seconds=timeWindow),end=t1,freq=rs)
            df = pd.DataFrame([np.random.randint(0,100) + np.random.randn(len(idx)) for k in range(len(tags))]).transpose()
            df.columns=tags
            df.index=idx

        else :
            conn = self.connectToDB()
            df   = self.dataBaseUtils.readSeveralTagsSQL(conn,tags,secs=timeWindow,timeRange=timeRange)
            df   = self.processRawData(df,rs=rs,applyMethod=applyMethod)
        return df

    def doubleMultiUnitGraph(self,df,tags1,tags2,axSP=0.05):
        dictdictGroups={'graph1':{t:t for t in tags1},'graph2':{t:t for t in tags2}}
        fig = self.utils.multiUnitGraphSubPlots(df,dictdictGroups,axisSpace=axSP)
        hs=0.002
        for y in range(1,len(tags1)+1):
            fig.layout['yaxis1'+str(y)].domain=[0.5+hs,1]
        for y in range(1,len(tags2)+1):
            fig.layout['yaxis2'+str(y)].domain=[0,0.5-hs]
        fig.update_layout(xaxis_showticklabels=False)
        fig.update_yaxes(title_text='',showticklabels=False)
        fig.update_yaxes(showgrid=False)
        fig.update_xaxes(matches='x')
        fig.update_layout(height=900)
        return fig

class ConfigDashSpark(ConfigDashTagUnitTimestamp):
    try :
        from pyspark.sql import SparkSession
        from dorianUtils.sparkUtils.sparkDfUtils import SparkDfUtils
        import findspark

        def __init__(self,sparkData,sparkConfFile,confFolder,**kwargs):
            ConfigDashTagUnitTimestamp.__init(self,folderPkl=None,confFolder=confFolder,**kwargs)

            self.cfgSys     = self._getSysConf(sparkConfFile)
            self.spark      = self.__createSparkSession()
            self.sparkConf  = self.spark.sparkContext.getConf().getAll()

            self.sparkData  = sparkData

            self.sdu   = SparkDfUtils(self.spark)
        # ======================================================================
        #                         private functions
        # ======================================================================
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
        # ======================================================================
        #                         function on dataframe
        # ======================================================================

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
    except:
        print('not possible to load : module pyspark ')

class ConfigFilesRealTimeCSV(ConfigDashTagUnitTimestamp):
    def __init__(self,folderRT,confFolder):
        ConfigDashTagUnitTimestamp.__init__(self,folderRT,confFolder,folderFig='')
        self.folderRT = folderRT
        self.listParkedDays=[k for k in os.listdir(folderRT) if re.search('\d{4}-\d{2}-\d{2}',k)]
        self.mbUtils = Modebus_utils()
        self.listParkTags=self.getListTagsParked()

    def findUnitTagName(self,t,sep=['-']):
        listUnits = [k for s in list(self.utils.phyQties.values()) for k in s ]
        listUnits = self.utils.combineUnits(self.utils.unitMag,listUnits,'')
        listUnitsPat=[l + k + l for k in listUnits for l in seps]
        return [k for k in listUnitsPat if re.search(k,t)]

    def getListTagsParked(self):
        if len(self.listParkedDays)>0:
            return [k[:-4] for k in os.listdir(self.folderRT+self.listParkedDays[0])]
        else : return []

    def getTagsTU(self,patTag,units=None,onCol=None,case=False,cols=None,ds=True):
        return [k for k in self.dfPLC.TAG if re.search(patTag,k)]

    def realtimeTagsDF(self,listTags,**kwargs):
        return self.mbUtils.readTagsRealTime(self.folderRT,listTags,**kwargs)

class Config_opcua(ConfigDashTagUnitTimestamp):
    def __init__(self,plcfile,connected=False,endpointurl=None,nameSpace=None,login=None,passwd=None,maxNbPoints = 600,tags=[],speed=100):
        if not nameSpace:nameSpace = "ns=4;s=GVL."
        if not endpointurl:endpointurl = "opc.tcp://10.10.38.100:4840"
        if not login:login = "Alpha"
        if not endpointurl:endpointurl = "Alpha$01"
        self.appDir      = os.path.dirname(os.path.realpath(__file__))
        self.endpointurl = endpointurl
        self.nameSpace   = nameSpace
        self.plcFile     = plcfile
        self.dfPLC       = self._load_dfplc()
        self.alltags     = self.dfPLC['TAG']
        self.client      = Client(self.endpointurl)
        self.certif_path = self.appDir + "/my_cert.pem"
        self.key_path    = self.appDir + "/my_private_key.pem"
        self.maxNbPoints = maxNbPoints
        self.speed       = speed
        self.connected   = connected
        if self.connected:
            self.client.set_security_string('Basic256Sha256,Sign,' + self.certif_path + ',' + self.key_path)
            self.client.set_user(login)
            self.client.set_password(passwd)
            self.client.connect()
        else :
            values = [np.random.randint(a,b) for a,b in zip(self.dfPLC.MIN,self.dfPLC.MAX)]
            self.lastValues = {t:v for t,v in zip(self.alltags,values)}
        self.dfGlobal = pd.DataFrame(columns = ['timestamp','value']).set_index('timestamp')

    def _load_dfplc(self):
        dfplc = pd.read_excel(self.plcFile,sheet_name='FichierConf_Jules')
        dfplc = dfplc[dfplc.DATASCIENTISM==True]
        dfplc.loc[dfplc['TAG'].str.contains('JT_'),'MAX']=4000
        dfplc.loc[dfplc['TAG'].str.contains('JT_'),'MIN']=0
        dfplc.loc[dfplc['TAG'].str.contains('STK.*ET'),'MAX']=2.2
        dfplc.loc[dfplc['TAG'].str.contains('STK.*ET'),'MIN']=0
        dfplc.loc[dfplc['TAG'].str.contains('STK_ALIM.*ET'),'MAX']=30
        dfplc.loc[dfplc['TAG'].str.contains('STK_ALIM.*ET'),'MIN']=0
        dfplc.loc[dfplc['TAG'].str.contains('IT_'),'MAX']=50
        dfplc.loc[dfplc['TAG'].str.contains('IT_'),'MIN']=0
        dfplc.loc[dfplc['TAG'].str.contains('TT_'),'MIN']=0
        return dfplc


    def getValues(self,tags):
        if self.connected:
            nodes  = [self.client.get_node(self.nameSpace + t) for t in tags]
            values = self.client.get_values(nodes)
        else:
            values = [v + 0.002*v*np.random.randn() for v in self.lastValues.values()]
            self.lastValues = {t:v for t,v in zip(self.lastValues.keys(),values)}
            values = [self.lastValues[t] for t in tags]
        return values
