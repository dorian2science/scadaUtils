from .comUtils import (Basic_streamer,SuperDumper)
class Streamer_minutely(Basic_streamer):
    def __init__(self,*args,**kwargs):
        Basic_streamer.__init__(self,*args,**kwargs)
        self.format_folderminute=self.format_hourFolder + '/%M/'

    def create_minutefolder(self,folderminute):
        # print_file(folderminute)
        if not os.path.exists(folderminute):
            folderhour=os.paht.dirname(folderminute)
            if not os.path.exists(folderhour):
                # print_file(folderhour)
                folderday=os.paht.dirname(folderhour)
                parentFolder=os.paht.dirname(folderday)
                if not os.path.exists(parentFolder):
                    print_file(parentFolder,''' does not exist. Make sure
                    the path of the parent folder exists''',filename=self.log_file)
                    raise SystemExit
                if not os.path.exists(folderday):
                    # print_file(folderday)
                    os.mkdir(folderday)
                os.mkdir(folderhour)
            os.mkdir(folderminute)
            return folderminute +' created '
        else :
            return folderminute +' already exists '

    def delete_minutefolder(self,folderminute):
        # print_file(folderminute)
        if os.path.exists(folderminute):
            os.rmdir(folderminute)
            return folderminute +' deleted '
        else :
            return folderminute +' does not exist '

    def loaddata_minutefolder(self,folderminute,tag):
        if os.path.exists(folderminute):
            # print_file(folderminute)
            return pickle.load(open(folderminute + tag + '.pkl', "rb" ))
        else :
            print_file('no folder : ',folderminute,filename=self.log_file)
            return []

    def actionMinutes_pooled(self,t0,t1,folderPkl,actionminute,*args,pool=True):
        minutes=pd.date_range(t0,t1,freq='1T')
        minutefolders =[folderPkl + k.strftime(self.format_folderminute) for k in minutes]
        if pool:
            with Pool() as p:
                dfs = p.starmap(actionminute,[(folderminute,*args) for folderminute in minutefolders])
        else:
            dfs = [actionminute(folderminute,*args) for folderminute in minutefolders]
        return {minute.strftime(self.format_folderminute):df for minute,df in zip(minutes,dfs)}

    def foldersaction(self,t0,t1,folderPkl,actionminute,pooldays=False,**kwargs):
        '''
        -t0,t1 are timestamps
        '''
        def actionMinutes(minutes,folderhour):
            dfs = []
            for m in minutes:
                folderminute = folderhour + '{:02d}'.format(m) +'/'
                dfs.append(actionminute(folderminute,**kwargs))
            return dfs
        def actionHours(hours,folderDay):
            dfs=[]
            for h in hours:
                folderHour = folderDay + '{:02d}'.format(h) + '/'
                dfs.append(actionMinutes(range(60),folderHour))
            return dfs
        def actionDays(days,folderPkl,pool=False):
            dfs=[]
            def actionday(day,folderPkl):
                folderDay = folderPkl + str(day) + '/'
                return actionHours(range(24),folderDay)
            if pool:
                with Pool() as p:
                    dfs = p.starmap(actionday,[(day,folderPkl) for day in days])
            else:
                for day in days:
                    dfs.append(actionday(day,folderPkl))
            return dfs

        dfs=[]
        # first day
        folderDay0 = folderPkl + t0.strftime(self.format_dayFolder) + '/'
        # first hour
        folderhour00 = folderDay0 + '{:02d}'.format(t0.hour) + '/'
        # single day-hour
        if (t1.day-t0.day)==0 and (t1.hour-t0.hour)==0:
            # minutes of single day-hour
            dfs.append(actionMinutes(range(t0.minute,t1.minute),folderhour00))
        else:
            # minutes of first hour of first day
            dfs.append(actionMinutes(range(t0.minute,60),folderhour00))
            # single day
            if (t1.day-t0.day)==0:
                #in-between hours of single day
                dfs.append(actionHours(range(t0.hour+1,t1.hour),folderDay0))
                folderhour01 = folderDay0 + '{:02d}'.format(t1.hour) + '/'
                #minutes of last hour of single day
                dfs.append(actionMinutes(range(0,t1.minute),folderhour01))
            # multiples days
            else:
                # next hours of first day
                dfs.append(actionHours(range(t0.hour+1,24),folderDay0))
                #next days
                #in-between days
                daysBetween = [k for k in range(1,(t1-t0).days)]
                days = [(t1-dt.timedelta(days=d)).strftime(self.format_dayFolder) for d in daysBetween]
                dfs.append(actionDays(days,folderPkl,pooldays))
                #last day
                folderDayLast = folderPkl + t1.strftime(self.format_dayFolder) + '/'
                #first hours of last day
                if not t1.hour==0:
                    dfs.append(actionHours(range(0,t1.hour),folderDayLast))
                #last hour
                folderHour11 = folderDayLast + '{:02d}'.format(t1.hour) + '/'
                dfs.append(actionMinutes(range(0,t1.minute),folderHour11))
        return self._fs.flatten(dfs)

    def parktagminute(self,folderminute,dftag):
        tag = dftag.tag[0]
        #get only the data for that minute
        minute = folderminute.split('/')[-2]
        hour   = folderminute.split('/')[-3]
        day    = folderminute.split('/')[-4]
        time2save = day+' '+hour+':'+minute
        t1 = pd.to_datetime(time2save).tz_localize(self.tz_record)
        t2 = t1+dt.timedelta(minutes=1)
        dfminute = dftag[(dftag.index<t2)&(dftag.index>=t1)]
        # if dfminute.empty:
        #     print_file(tag,t1,t2)
        #     print_file(dfminute)
        #     time.sleep(1)
        #create folder if necessary
        if not os.path.exists(folderminute):
            return 'no folder : ' + folderminute

        #park tag-minute
        pickle.dump(dfminute,open(folderminute + tag + '.pkl', "wb" ))
        return tag + ' parked in : ' + folderminute

    def park_df_minute(self,folderminute,df_minute,listTags):
        if not os.path.exists(folderminute):os.mkdir(folderminute)
        # print_file(folderminute)
        # print_file(df_minute)
        for tag in listTags:
            df_tag=df_minute[df_minute['tag']==tag][['value']]
            # df_tag.columns=[tag]
            df_tag.to_pickle(folderminute + tag + '.pkl')
        return tag + ' parked in : ' + folderminute

    def dumy_minute(self,folderminute):
        print_file(folderminute)
        return 'ici'

    def loadtags_minutefolder(self,folderminute,tags):
        if os.path.exists(folderminute):
            # print_file(folderminute)
            dfs=[pickle.load(open(folderminute + tag + '.pkl', "rb" )) for tag in tags]
            for df,tag in zip(dfs,tags):df.columns=[tag]
            df=pd.concat(dfs,axis=1)
            return df
        else :
            print_file('NO FOLDER : ',folderminute)
            return pd.DataFrame()

class SuperDumper_minutely(SuperDumper):
    def start_dumping(self):
        return SuperDumper.start_dumping(self,'minute')

    def parktagfromdb(self,t0,t1,df,tag,compression='reduce'):
        dftag = df[df.tag==tag].set_index('timestampz')
        # print_file(dftag)
        dftag.index=dftag.index.tz_convert(self.tz_record)
        if dftag.empty:
            return dftag
        # print_file(tag + ' : ',self.dfplc.loc[tag,'DATATYPE'])
        if compression in ['reduce','diff','dynamic'] and not self.dfplc.loc[tag,'DATATYPE']=='STRING(40)':
            precision = self.dfplc.loc[tag,'PRECISION']
            dftag = dftag.replace('null',np.nan)
            dftag.value = dftag.value.astype(self.dataTypes[self.dfplc.loc[tag,'DATATYPE']])
            dftag.value = self.streamer.staticCompressionTag(dftag.value,precision,compression)
        return self.streamer.foldersaction(t0,t1,self.folderPkl,self.streamer.parktagminute,dftag=dftag)

    def park_database(self):
        listTags=self.alltags
        start = time.time()
        timenow = pd.Timestamp.now(tz=self.tz_record)
        t1 = timenow

        ### read database
        dbconn = self.connect2db()
        sqlQ ="select * from " + self.dbTable + " where timestampz < '" + t1.isoformat() +"'"
        # df = pd.read_sql_query(sqlQ,dbconn,parse_dates=['timestampz'],dtype={'value':'float'})
        df = pd.read_sql_query(sqlQ,dbconn,parse_dates=['timestampz'])
        print_file(computetimeshow('database read'+'for data <' + t1.isoformat(),start),filename=self.log_file)
        # close connection
        dbconn.close()

        # check if database not empty
        if not len(df)>0:
            print_file('database ' + self.dbParameters['dbname'] + ' empty',filename=self.log_file)
            return []

        ##### determine minimum time for parking folders
        t0 = df.set_index('timestampz').sort_index().index[0].tz_convert(self.tz_record)
        #### create Folders
        self.createFolders_period(t0,t1)

        #################################
        #           park now            #
        #################################
        start=time.time()

        # with Pool() as p:
        #     dfs=p.starmap(self.parktagfromdb,[(t0,t1,df,tag) for tag in listTags])
        dfs=[]
        for tag in listTags:
            dfs.append(self.parktagfromdb(t0,t1,df,tag))
        print_file(computetimeshow('database parked',start),filename=self.log_file)
        self.parkingTimes[timenow.isoformat()] = (time.time()-start)*1000
        # #FLUSH DATABASE
        start=time.time()
        self.flushdb(t1.isoformat())
        return dfs

class VisualisationMaster_minutely(VisualisationMaster):
    def _loadparkedtag(self,t0,t1,tag):
        # print_file(tag)
        dfs = self.streamer.foldersaction(t0,t1,self.folderPkl,self.streamer.loaddata_minutefolder,tag=tag)
        if len(dfs)>0:
            return pd.concat(dfs)
        else:
            return pd.DataFrame()

    def _load_parked_tags(self,t0,t1,tags,poolTags,*args,**kwargs):
        if not isinstance(tags,list):
            try:
                tags=list(tags)
            except:
                print_file('tags is not a list',filename=self.log_file)
                return pd.DataFrame()
        if len(tags)==0:
            return pd.DataFrame()

        start=time.time()
        if poolTags:
            print_file('pooling the data...',filename=self.log_file)
            with Pool() as p:
                dfs = p.starmap(self._loadparkedtag,[(timeRange[0],timeRange[1],tag) for tag in tags])
        else:
            dfs = []
            for tag in tags:
                dfs.append(self._loadparkedtag(timeRange[0],timeRange[1],tag))
        if len(dfs)==0:
            return pd.DataFrame()
        df = pd.concat(dfs).sort_index()
        if df.duplicated().any():
            print_file("="*60+'\n'+ "attention il y a des doublons dans les donnees parkes : ",filename=self.log_file)
            print_file(df[df.duplicated(keep=False)],'\n'+'='*60,filename=self.log_file)
            df = df.drop_duplicates()
        return df

class Streamer_hourly():
    def __init__(self,*args,**kwargs):
        Basic_streamer.__init__(self,*args,**kwargs)
        self.format_hourFolder=self.format_dayFolder+'%H/'

    def park_DF_hour(self,dfhour,folderpkl,pool=False,showtag=False):
        correctColumns=['tag','timestampz','value']
        if not list(dfhour.columns.sort_values())==correctColumns:
            print_file('PROBLEM: the df dataframe should have the following columns : ',correctColumns,'''
            instead your columns are ''',list(dfhour.columns.sort_values()),filename=self.log_file)
            return

        dfhour = dfhour.set_index('timestampz')
        if isinstance(dfhour.index.dtype,pd.DatetimeTZDtype):
            dfhour.index = dfhour.index.tz_convert('CET')
        else:### for cases with changing DST change as 31oct for example
            dfhour = [pd.Timestamp(k).astimezone('CET') for k in dfhour.index]
        listTags = dfhour.tag.unique()
        mean_time=dfhour.index.mean()
        folderday  = folderpkl +'/'+ mean_time.strftime(self.format_dayFolder)+'/'
        if not os.path.exists(folderday): os.mkdir(folderday)
        folderhour = folderpkl +'/'+ mean_time.strftime(self.format_hourFolder)+'/'
        if not os.path.exists(folderhour): os.mkdir(folderhour)
        ### park it
        dtype = 'object'
        if pool :
            with Pool() as p:dfs=p.starmap(self.park_tags,[(dfhour,tag,folderhour,dtype,showtag) for tag in listTags])
        else :
            dfs=[self.park_tags(dfhour,tag,folderhour,dtype,showtag) for tag in listTags]
        return dfs

    def park_zip_hour_file(self,filezip_hour,folderparked_hours):
        '''format of data in the zipFile should be 3 columns tag,value,timestampz with no header.'''
        #### unzip the file
        # try:
        with ZipFile(filezip_hour, 'r') as zipObj:
           zipObj.extractall(os.path.dirname(filezip_hour))
        ##### read the file
        f_csv = filezip_hour.replace('.zip','.csv')
        start   = time.time()
        df = pd.read_csv(f_csv,parse_dates=['timestampz'],names=['tag','value','timestampz'])
        print_file(computetimeshow('csv read ',start),filename=self.log_file)
        ##### remove the csv
        os.remove(f_csv)
        ##### park the file
        start   = time.time()
        message = self.park_DF_hour(df,folderparked_hours,pool=False)
        print_file(computetimeshow(filezip_hour+' parked ',start),filename=self.log_file)
        # except:
        #     print_file('\n'+'*'*60,filename=self.log_file)
        #     message = filezip_hour+' failed to be parked'
        #     print_file(message,filename=self.log_file)
        #     print_file('\n'+'*'*60,filename=self.log_file)
        return message

    def park_hourly2dayly(self,day,folderparked_hours,folderparked_days,pool_tags=False,showtag=False):
        """ -day :'ex : 2022-02-15' """
        listhours=glob.glob(folderparked_hours+day+'/*')
        listhours.sort()
        listTags = os.listdir(listhours[0])
        folderday=folderparked_days +'/'+ day+ '/'
        if not os.path.exists(folderday):os.mkdir(folderday)
        for tag in listTags:
            if showtag:print_file(tag)
            dfs = [pd.read_pickle(hour+'/' + tag) for hour in listhours]
            pd.concat(dfs).to_pickle(folderday + tag)
        return
