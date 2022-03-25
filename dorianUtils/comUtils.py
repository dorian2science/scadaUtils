# import importlib
import datetime as dt, time, pytz,sys
from time import sleep
import sys,os,re,threading,struct, glob, pickle,struct,subprocess as sp
import numpy as np, pandas as pd
import psycopg2
import threading
from multiprocessing import Pool
import traceback
from dorianUtils.utilsD import Utils
from dateutil.tz import tzlocal
from zipfile import ZipFile

# #######################
# #      BASIC Utils    #
# #######################
# basic utilities for Streamer and DumpingClientMaster
timenowstd=lambda :pd.Timestamp.now().strftime('%d %b %H:%M:%S')
computetimeshow=lambda x,y:print(timenowstd() + ' : ' + x + ' in {:.2f} ms'.format((time.time()-y)*1000))
class EmptyClass():pass

class Modebus_utils():
    def quick_modebus_decoder(self,regs,dtype,bo_out='=',bo_in='='):
        if dtype=='INT32' or dtype == 'UINT32':
            value = struct.unpack(bo_out + 'i',struct.pack(bo_in+"2H",*regs))[0]
        if dtype == 'IEEE754':
            value = struct.unpack(bo_out + 'f',struct.pack(bo_in+"2H",*regs))[0]
        elif dtype == 'INT64':
            value = struct.unpack(bo_out + 'q',struct.pack(bo_in+"4H",*regs))[0]
        return value

class FileSystem():
    ######################
    # FILE SYSTEMS  #
    ######################
    def load_confFile(self,filename,generate_func,generateAnyway=False):
        start    = time.time()
        if not os.path.exists(filename) or generateAnyway:
            print('Start generating the file '+filename+' with function : ')
            print(' '.ljust(20),generate_func)
            print('')
            # try:
            plcObj = generate_func()
            pickle.dump(plcObj,open(filename,'wb'))
            print('')
            print(filename + ' saved')
            print('')
            # except:
            #     print('failed to build plc file with filename :',filename)
            #     raise SystemExit
        # sys.exit()
        plcObj = pickle.load(open(filename,'rb'))
        computetimeshow(filename.split('/')[-1] + ' loaded',start)
        print('---------------------------------------')
        print('')
        return plcObj

    def getParentDir(self,folder):
        if folder[-1]=='/':
            folder=folder[:-1]
        return '/'.join(folder.split('/')[:-1]) + '/'

    def flatten(self,list_of_lists):
        if len(list_of_lists) == 0:
            return list_of_lists
        if isinstance(list_of_lists[0], list):
            return self.flatten(list_of_lists[0]) + self.flatten(list_of_lists[1:])
        return list_of_lists[:1] + self.flatten(list_of_lists[1:])

    def autoTimeRange(self,folderPkl,method='last'):
        listDays = [pd.Timestamp(k.split('/')[-1]) for k in glob.glob(folderPkl+'*')]
        if method=='last':
            lastDay = max(listDays).strftime('%Y-%m-%d')
            hmax    = max([k.split('/')[-1] for k in glob.glob(folderPkl+lastDay+'/*')])
            t1      = lastDay + ' ' + hmax + ':00:00'
        elif method=='random':
            t1 = (pd.Series(listDays).sample(n=1).iloc[0]+dt.timedelta(hours=np.random.randint(8))).strftime('%Y-%m-%d')

        t0      = (pd.Timestamp(t1)-dt.timedelta(hours=8)).isoformat()
        return [t0,t1]

    def get_parked_days_not_empty(self,folderPkl,minSize=3,dict_size=3):
        '''dict_size:minimum size in Mo of the folder to be taken into account '''
        sizes={'G':1000,'K':0.001,'M':1}
        folders=[k.split('\t') for k in sp.check_output('du -h --max-depth=1 '+ folderPkl + ' | sort -h',shell=True).decode().split('\n')]
        folders = [k for k in folders if len(k)==2]
        folders = [k for k in folders if len(re.findall('\d{4}-\d{2}-\d',k[1].split('/')[-1]))>0 ]
        folders={v.split('/')[-1]:float(k[:-1].replace(',','.'))*sizes[k[-1]] for k,v in folders}
        daysnotempty = pd.Series(folders)
        daysnotempty = [k for k in daysnotempty[daysnotempty>dict_size].index]
        daysnotempty = pd.Series([pd.Timestamp(k,tz='CET') for k in daysnotempty]).sort_values()
        return daysnotempty

    def createRandomInitalTagValues(self,listTags,dfplc):
        valueInit={}
        for tag in listTags:
            tagvar=dfplc.loc[tag]
            if tagvar.DATATYPE=='STRING(40)':
                valueInit[tag] = 'STRINGTEST'
            else:
                valueInit[tag] = np.random.randint(tagvar.MIN,tagvar.MAX)
        return valueInit

    def listfiles_folder(self,folder):
        listFiles=[]
        if os.path.exists(folder):
            listFiles = os.listdir(folder)
        return listFiles

    def listfiles_pattern_folder(self,folder,pattern):
        listFiles=[]
        if os.path.exists(folder):
            listFiles = [k.split('/')[-1] for k in glob.glob(folder+'/*'+pattern+'*')]
        return listFiles

    def getUnitofTag(self,tag,dfplc):
        unit=dfplc.loc[tag].UNITE
        # print(unit)
        if not isinstance(unit,str):
            unit='u.a'
        return unit

    def getTagsTU(self,patTag,dfplc,units,onCol='index',cols='tag',ds=True):
        if ds:dfplc=dfplc[dfplc.DATASCIENTISM]
        if onCol=='index':
            df = dfplc[dfplc.index.str.contains(patTag,case=False)]
        else:
            df = dfplc[dfplc[onCol].str.contains(patTag,case=False)]
        if isinstance(units,str):units = [units]
        df = df[df['UNITE'].isin(units)]
        if cols=='tdu' :
            return df[['DESCRIPTION','UNITE']]
        elif cols=='tag':
            return list(df.index)
        else :
            return df

class SetInterval:
    '''demarre sur un multiple de interval.col
    Saute donc les données intermédiaires si la tâche prends plus de temps
    que l'intervalle pour démarrer sur à pile.'''
    def __init__(self,interval,action,*args):
        self.argsAction=args
        self.interval  = interval
        self.action    = action
        self.stopEvent = threading.Event()
        self.thread    = threading.Thread(target=self.__SetInterval)

    def start(self):
        self.thread.start()

    def __SetInterval(self):
        nextTime=time.time()
        while not self.stopEvent.wait(nextTime-time.time()):
            self.action(*self.argsAction)
            nextTime+=self.interval
            while nextTime-time.time()<0:
                nextTime+=self.interval

    def stop(self):
        self.stopEvent.set()

# #######################
# #      DEVICES        #
# #######################
class Device():
    ''' for inheritance :
        - a function <collectData> should be written  to collect data from the device.
        - a function <connectDevice> to connect to the device.
    '''
    def __init__(self,device_name,endpointUrl,port,dfplc,timeoutreconnect=3):
        self.fs          = FileSystem()
        self.utils       = Utils()
        self.device_name = device_name
        self.endpointUrl = endpointUrl
        self.port        = port
        self.isConnected = True
        now = dt.datetime.now().astimezone()
        self.local_tzname = now.tzinfo.tzname(now)
        self.dfplc   = dfplc
        # print(dfplc)
        self.listUnits = self.dfplc.UNITE.dropna().unique().tolist()
        self.alltags = list(self.dfplc.index)
        self.collectingTimes = {}
        self.insertingTimes  = {}
        self.timeOUTreconnect = timeoutreconnect

    def checkConnection(self):
        if not self.isConnected:
            print('+++++++++++++++++++++++++++')
            self.isConnected = self.connectDevice()
            if self.isConnected:
                print(timenowstd(),' : ',self.device_name,'--> connexion established again!!')
            else :
                print(timenowstd(),' : ',self.device_name,'--> impossible to connect to device.',
                                    'try new connection in',self.timeOUTreconnect,'seconds')
            print('+++++++++++++++++++++++++++')
            print('')

    def insert_intodb(self,dbParameters,*args):
        ''' should have a function that gather data and returns them
        in form of a dictionnary tag:value.
        '''
        data={}
        try :
            connReq = ''.join([k + "=" + v + " " for k,v in dbParameters.items()])
            dbconn = psycopg2.connect(connReq)
        except :
            print('problem connecting to database ',dbParameters )
            return
        cur  = dbconn.cursor()
        start=time.time()
        ts = dt.datetime.now(tz=pytz.timezone(self.local_tzname))
        if self.isConnected:
            try :
                data = self.collectData(*args)
            except:
                print(timenowstd(),' : ',self.device_name,' --> connexion to device impossible.')
                self.isConnected = False
            self.collectingTimes[dt.datetime.now(tz=pytz.timezone(self.local_tzname)).isoformat()] = (time.time()-start)*1000
            for tag in data.keys():
                sqlreq = "insert into realtimedata (tag,value,timestampz) values ('"
                value = data[tag][0]
                if value==None:
                    value = 'null'
                value=str(value)
                sqlreq+= tag +"','" + value + "','" + data[tag][1]  + "');"
                sqlreq=sqlreq.replace('nan','null')
                print(sqlreq)
                cur.execute(sqlreq)
            self.insertingTimes[dt.datetime.now(tz=pytz.timezone(self.local_tzname)).isoformat()]=(time.time()-start)*1000
            dbconn.commit()
        cur.close()
        dbconn.close()

    def createRandomInitalTagValues(self):
        return self.fs.createRandomInitalTagValues(self.alltags,self.dfplc)

    def getUnitofTag(self,tag):
        return self.fs.getUnitofTag(tag,self.dfplc)

    def getTagsTU(self,patTag,units=None,*args,**kwargs):
        if not units : units = self.listUnits
        return self.fs.getTagsTU(patTag,self.dfplc,units,*args,**kwargs)

from pymodbus.client.sync import ModbusTcpClient as ModbusClient
class ModeBusDevice(Device):
    '''modebus_map should be loaded to use functions decodeRegisters.'''
    def __init__(self,device_name,endpointUrl,port,dfplc,modebus_map,multiple,freq,bo_in='=',bo_out='=',**kwargs):
        Device.__init__(self,device_name,endpointUrl,port,dfplc,**kwargs)
        self.modebus_map = modebus_map
        self.freq     = freq
        self.bo_in,self.bo_out = bo_in,bo_out
        self.multiple = multiple
        self.all_slave_ids = list(self.modebus_map.slave_unit.unique())
        self.client = ModbusClient(host=self.endpointUrl,port=int(self.port))
        dfplc['FREQUENCE_ECHANTILLONNAGE'] = self.freq

    def decodeRegisters(self,regs,block):
        '''block is dataframe with tags as index and columns intAdress,type(datatype)'''
        d={}
        firstReg = block['intAddress'][0]
        for tag in block.index:
            row = block.loc[tag]
            #### in order to make it work even if block is not continuous.
            curReg = int(row['intAddress'])-firstReg
            if row.type == 'INT32' or row.type == 'UINT32':
                # print(curReg)
                valueShorts = [regs[curReg+k] for k in [0,1]]
                # conversion of 2 shorts(=DWORD=word) into long(=INT32)
                value = struct.unpack(self.bo_out+'i',struct.pack(self.bo_in + "2H",*valueShorts))[0]
                # curReg+=2
            if row.type == 'IEEE754':
                valueShorts = [regs[curReg+k] for k in [0,1]]
                value = struct.unpack(self.bo_out+'f',struct.pack(self.bo_in + "2H",*valueShorts))[0]
                # curReg+=2
            elif row.type == 'INT64':
                valueShorts = [regs[curReg+k] for k in [0,1,2,3]]
                value = struct.unpack(self.bo_out+'q',struct.pack(self.bo_in + "4H",*valueShorts))[0]
                # curReg+=4
            d[tag]=[value*row.scale,dt.datetime.now().astimezone().isoformat()]
        return d

    def checkRegisterValueTag(self,tag,**kwargs):
        # self.connectDevice()
        tagid = self.modebus_map.loc[tag]
        regs  = self.client.read_holding_registers(tagid.intAddress,tagid['size(mots)'],unit=tagid.slave_unit).registers
        return self.decodeRegisters(regs,pd.DataFrame(tagid).T,**kwargs)

    def get_slave_values(self,unit_id):
        ptComptage = self.modebus_map[self.modebus_map['slave_unit']==unit_id].sort_values(by='intAddress')
        if self.multiple:
            lastReg    = ptComptage['intAddress'][-1]
            firstReg   = ptComptage['intAddress'][0]
            nbregs     = lastReg - firstReg + ptComptage['size(mots)'][-1]
            #read all registers in a single command for better performances
            regs = self.client.read_holding_registers(firstReg,nbregs,unit=unit_id).registers
            return self.decodeRegisters(regs,ptComptage)
        else:
            d={}
            self.connectDevice()
            for tag in ptComptage.index:
            # for tag in ptComptage.index[:40]:
                tagrow=ptComptage.loc[[tag],:]
                # print(tagrow)
                regs = self.client.read_holding_registers(tagrow['intAddress'][0],tagrow['size(mots)'][0],unit=unit_id).registers
                d.update(self.decodeRegisters(regs,tagrow))
            return d

    def connectDevice(self):
        return self.client.connect()

    def collectData(self,*args):
        d={}
        for idTCP in self.all_slave_ids:
            d.update(self.get_slave_values(unit_id=idTCP))
        return d

import opcua
class Opcua_Client(Device):
    def __init__(self,*args,nameSpace,**kwargs):
        Device.__init__(self,*args,**kwargs)
        self.nameSpace   = nameSpace
        self.endpointUrl= self.endpointUrl+":"+str(self.port)
        self.client      = opcua.Client(self.endpointUrl)
        ####### load nodes
        self.nodesDict  = {t:self.client.get_node(self.nameSpace + t) for t in self.alltags}
        self.nodes      = list(self.nodesDict.values())

    def loadPLC_file(self):
        listPLC = glob.glob(self.confFolder + '*Instrum*.pkl')
        if len(listPLC)<1:
            listPLC_xlsm = glob.glob(self.confFolder + '*Instrum*.xlsm')
            plcfile=listPLC_xlsm[0]
            print(plcfile,' is read and converted in .pkl')
            dfplc = pd.read_excel(plcfile,sheet_name='FichierConf_Jules',index_col=0)
            dfplc = dfplc[dfplc.DATASCIENTISM]
            pickle.dump(dfplc,open(plcfile[:-5]+'.pkl','wb'))
            listPLC = glob.glob(self.confFolder + '*Instrum*.pkl')

        self.file_plc = listPLC[0]
        dfplc = pickle.load(open(self.file_plc,'rb'))
        return dfplc

    def connectDevice(self):
        try:
            self.client.connect()
            return True
        except:
            return False

    def collectData(self,tags):
        nodes = {t:self.nodesDict[t] for t in tags}
        values = self.client.get_values(nodes.values())
        ts = dt.datetime.now().astimezone().isoformat()
        data = {tag:[val,ts] for tag,val in zip(nodes.keys(),values)}
        return data

import urllib.request, json
class Meteo_Client(Device):
    def __init__(self,freq=30,**kwargs):
        '''-freq: acquisition time in seconds '''
        self.freq=freq
        self.cities = pd.DataFrame({'le_cheylas':{'lat' : '45.387','lon':'6.0000'}})
        # self.cities = pd.DataFrame({'leCheylas':{'lat' : '45.387','lon':'6.0000'},
        #     'champet':{'lat':'45.466393','lon':'5.656045'},
        #     'stJoachim':{'lat':'47.382074','lon':'-2.196835'}})
        self.baseurl = 'https://api.openweathermap.org/data/2.5/'
        dfplc = self.build_plcmeteo(self.freq)
        Device.__init__(self,'meteo',self.baseurl,None,dfplc,timeoutreconnect=self.freq)
        self.apitoken = '79e8bbe89ac67324c6a6cdbf76a450c0'
        # self.apitoken = '2baff0505c3177ad97ec1b648b504621'# Marc
        self.t0 = dt.datetime(1970,1,1,1,0).astimezone(tz = pytz.timezone('Etc/GMT-3'))

    def build_plcmeteo(self,freq):
        vars = ['temp','pressure','humidity','clouds','wind_speed']
        tags=['XM_'+ city+'_' + var for var in vars for city in self.cities]
        descriptions=[var +' '+city for var in vars for city in self.cities]
        dfplc=pd.DataFrame()
        dfplc.index=tags
        dfplc.loc[[k for k in dfplc.index if 'temp' in k],'MIN']=-50
        dfplc.loc[[k for k in dfplc.index if 'temp' in k],'MAX']=50
        dfplc.loc[[k for k in dfplc.index if 'temp' in k],'UNITE']='°C'
        dfplc.loc[[k for k in dfplc.index if 'pressure' in k],'MIN']=-250
        dfplc.loc[[k for k in dfplc.index if 'pressure' in k],'MAX']=250
        dfplc.loc[[k for k in dfplc.index if 'pressure' in k],'UNITE']='mbar'
        dfplc.loc[[k for k in dfplc.index if 'humidity' in k or 'clouds' in k],'MIN']=0
        dfplc.loc[[k for k in dfplc.index if 'humidity' in k or 'clouds' in k],'MAX']=100
        dfplc.loc[[k for k in dfplc.index if 'humidity' in k or 'clouds' in k],'UNITE']='%'
        dfplc.loc[[k for k in dfplc.index if 'wind_speed' in k],'MIN']=0
        dfplc.loc[[k for k in dfplc.index if 'wind_speed' in k],'MAX']=250
        dfplc.loc[[k for k in dfplc.index if 'wind_speed' in k],'UNITE']='km/h'
        dfplc['DESCRIPTION'] = descriptions
        dfplc['DATATYPE'] = 'REAL'
        dfplc['DATASCIENTISM'] = True
        dfplc['PRECISION'] = 0.01
        dfplc['FREQUENCE_ECHANTILLONNAGE'] = freq
        dfplc['VAL_DEF'] = 0
        return dfplc

    def connectDevice(self):
        try:
            request = urllib.request.urlopen('https://www.google.com')
            print("Connected to the Internet")
            return True
        except:
            print("No internet connection.")
            return False

    def collectData(self,tags=None):
        df = pd.concat([self.get_dfMeteo(city) for city in self.cities])
        # df = df.abs
        return {k:[v,df.name] for k,v in zip(df.index,df)}

    def get_dfMeteo(self,city):
        gps = self.cities[city]
        url = self.baseurl + 'weather?lat='+gps.lat+'&lon=' + gps.lon + '&units=metric&appid=' + self.apitoken
        response = urllib.request.urlopen(url)
        data = json.loads(response.read())
        t0   = dt.datetime(1970,1,1,1,0).astimezone(tz = pytz.timezone('Etc/GMT-3'))
        timeCur=t0 + dt.timedelta(seconds=data['dt'])
        dfmain=pd.DataFrame(data['main'],index=[timeCur.isoformat()])
        dfmain['clouds']=data['clouds']['all']
        dfmain['visibility']=data['visibility']
        dfmain['main']=data['weather'][0]['description']
        dfwind=pd.DataFrame(data['wind'],index=[timeCur.isoformat()])
        dfwind.columns = ['XM_' + city + '_wind_' + k  for k in dfwind.columns]
        dfmain.columns = ['XM_' + city + '_' + k  for k in dfmain.columns]
        df = pd.concat([dfmain,dfwind],axis=1).squeeze()
        df = df.loc[self.dfplc.index]
        return df

    def dfMeteoForecast():
        url = baseurl + 'onecall?lat='+lat+'&lon=' + lon + '&units=metric&appid=' + apitoken ## prediction
        # url = 'http://history.openweathermap.org/data/2.5/history/city?q='+ +',' + country + '&appid=' + apitoken
        listInfos = list(data['hourly'][0].keys())
        listInfos = [listInfos[k] for k in [0,1,2,3,4,5,6,7,8,9,10,11]]
        dictMeteo = {tag  : [k[tag] for k in data['hourly']] for tag in listInfos}
        dfHourly = pd.DataFrame.from_dict(dictMeteo)
        dfHourly['dt'] = [t0+dt.timedelta(seconds=k) for k in dfHourly['dt']]

        listInfos = list(data['daily'][0].keys())
        listInfos = [listInfos[k] for k in [0,1,2,3,4,5,6,8,9,10,11,13,15,16,18]]
        dictMeteo = {tag  : [k[tag] for k in data['daily']] for tag in listInfos}
        dfDaily = pd.DataFrame.from_dict(dictMeteo)
        dfDaily['sunrise'] = [t0+dt.timedelta(seconds=k) for k in dfDaily['sunrise']]
        dfDaily['sunset'] = [t0+dt.timedelta(seconds=k) for k in dfDaily['sunset']]
        dfDaily['moonrise'] = [t0+dt.timedelta(seconds=k) for k in dfDaily['moonrise']]
        dfDaily['moonset'] = [t0+dt.timedelta(seconds=k) for k in dfDaily['moonset']]

        listInfos = list(data['minutely'][0].keys())
        dictMeteo = {tag  : [k[tag] for k in data['minutely']] for tag in listInfos}
        dfMinutely = pd.DataFrame.from_dict(dictMeteo)

# #######################
# #  SUPER INSTANCES    #
# #######################
class Streamer():
    '''Streamer enables to perform action on parked Day/Hour/Minute folders.
    It comes with basic functions like loaddata_minutefolder/create_minutefolder/parktagminute.'''
    def __init__(self):
        self.fs = FileSystem()
        self.format_dayFolder='%Y-%m-%d/'
        self.format_hourFolder=self.format_dayFolder+'%H/'
        self.format_folderminute=self.format_hourFolder + '/%M/'
        now = dt.datetime.now().astimezone()
        self.local_tzname = now.tzinfo.tzname(now)
        methods={}
        methods['forwardfill']= "df.ffill().resample(rs).ffill()"
        methods['raw']= None
        methods['interpolate'] = "pd.concat([df.resample(rs).asfreq(),df]).sort_index().interpolate('time').resample(rs).asfreq()"
        methods['max']  = "df.ffill().resample(rs,label='right',closed='right').max()"
        methods['min']  = "df.ffill().resample(rs,label='right',closed='right').min()"
        methods['meanright'] = "df.ffill().resample('100ms').ffill().resample(rs,label='right',closed='right').mean()"
        # maybe even more precise if the dynamic compression was too hard
        methods['meanrightInterpolated'] = "pd.concat([df.resample('100ms').asfreq(),df]).sort_index().interpolate('time').resample(rs,label='right',closed='right').mean()"
        methods['rolling_mean']="df.ffill().resample(rs).ffill().rolling(rmwindow).mean()"
        self.methods = methods


    # ########################
    #      HOURS FUNCTIONS   #
    # ########################
    def park_tags(self,df,tag,folder,dtype,showtag=False):
        if showtag:print(tag)
        dftag=df[df.tag==tag]['value'].astype(dtype)
        pickle.dump(dftag,open(folder + tag + '.pkl', "wb" ))

    def to_folderday(self,d):
        return d.strftime(self.format_dayFolder)+'/'
    # ########################
    #      HOURS FUNCTIONS   #
    # ########################
    def park_DF_hour(self,dfhour,folderpkl,pool=False,showtag=False):
        correctColumns=['tag','timestampz','value']
        if not list(dfhour.columns.sort_values())==correctColumns:
            print('PROBLEM: the df dataframe should have the following columns : ',correctColumns,'''
            instead your columns are ''',list(dfhour.columns.sort_values()))
            return

        dfhour = dfhour.set_index('timestampz')
        if isinstance(dfhour.index.dtype,pd.DatetimeTZDtype):
            dfhour.index = dfhour.index.tz_convert('CET')
        else:### for cases with changing DST 31.10 for example
            dfhour = [pd.Timestamp(k).astimezone('CET') for k in dfhour.index]
        listTags = dfhour.tag.unique()
        mean_time=dfhour.index.mean()
        folderday  = folderpkl +'/'+ mean_time.strftime(self.format_dayFolder)+'/'
        if not os.path.exists(folderday): os.mkdir(folderday)
        folderhour = folderpkl +'/'+ mean_time.strftime(self.format_hourFolder)+'/'
        if not os.path.exists(folderhour): os.mkdir(folderhour)
        #park it
        dtype = 'object'
        if pool :
            with Pool() as p:dfs=p.starmap(self.park_tags,[(dfhour,tag,folderhour,dtype,showtag) for tag in listTags])
        else :
            dfs=[self.park_tags(dfhour,tag,folderhour,dtype,showtag) for tag in listTags]
        return dfs

    # ########################
    #      DAY FUNCTIONS     #
    # ########################
    def create_dayfolder(self,folderday):
        if not os.path.exists(folderday):
            os.mkdir(folderday)
            return folderday +' created '
        else :
            return folderday +' already exists '

    def park_DFday(self,dfday,folderpkl,pool=False,showtag=False):
        correctColumns=['tag','timestampz','value']
        if not list(dfday.columns.sort_values())==correctColumns:
            print('PROBLEM: the df dataframe should have the following columns : ',correctColumns,'''
            instead your columns are ''',list(dfday.columns.sort_values()))
            return

        dfday = dfday.set_index('timestampz')
        if isinstance(dfday.index.dtype,pd.DatetimeTZDtype):
            dfday.index = dfday.index.tz_convert('UTC')
        else:### for cases with changing DST 31.10 for example
            dfday = [pd.Timestamp(k).astimezone('UTC') for k in dfday.index]
        listTags = dfday.tag.unique()
        folderday = folderpkl +'/'+ dfday.index.mean().strftime(self.format_dayFolder)+'/'
        print()
        if not os.path.exists(folderday): os.mkdir(folderday)
        #park tag-day
        if pool :
            with Pool() as p:dfs=p.starmap(self.parkdaytag,[(dfday,tag,folderday,showtag) for tag in listTags])
        else :
            dfs=[self.parkdaytag(dfday,tag,folderday,showtag) for tag in listTags]
        return dfs

    def parkdaytag(self,dfday,tag,folderday,showtag=False):
        if showtag:print(tag)
        '''SHOULD ADD DTYPE ACCORDING TO DTYPE IN DFPLC FOR TAGS '''
        dftag=dfday[dfday.tag==tag]['value'].astype('float')
        pickle.dump(dftag,open(folderday + tag + '.pkl', "wb" ))
        return tag + 'parked'

    def actiondays(self,t0,t1,folderPkl,action,*args,pool=True):
        '''
        -t0,t1:timestamps
        '''
        print(t0,t1)
        days=pd.date_range(t0,t1,freq='1D')
        dayfolders =[folderPkl + k.strftime(self.format_dayFolder)+'/' for k in days]
        if pool:
            with Pool() as p:
                dfs = p.starmap(action,[(d,*args) for d in dayfolders])
        else:
            dfs = [action(d,*args) for d in dayfolders]
        return {d.strftime(self.format_dayFolder):df for d,df in zip(days,dfs)}

    def remove_tags_day(self,d,tags):
        print(d)
        for t in tags:
            tagpath=d+'/'+t+'.pkl'
            try:
                os.remove(tagpath)
            except:
                pass
                # print('no file :',tagpath)

    def dumy_day(self,day):
        return day

    def zip_day(self,folderday,basename,zipfolder):
        listtags=glob.glob(folderday+'/*')
        dfs=[]
        for tag in listtags:
            dftag = pickle.load(open(tag,'rb')).reset_index()
            dftag['tag'] = tag.split('/')[-1].replace('.pkl','')
            dfs.append(dftag)
        df = pd.concat(dfs)
        ### save as zip file
        filecsv = zipfolder + '/' + folderday.split('/')[-2] +'_'+ basename + '.csv'
        df.to_csv(filecsv)
        file_csv_local = filecsv.split('/')[-1]
        filezip        = file_csv_local.replace('.csv','.zip')
        # sp.Popen(['libreoffice','/tmp/test.xlsx'])
        sp.check_output('cd ' + zipfolder + ' && zip '+filezip + ' ' + file_csv_local,shell=True)
        os.remove(filecsv)

    #   HIGH LEVEL FUNCTIONS #
    def dummy_daily(self,days=[],nCores=4):
        if len(days)==0:
            days=[k for k in pd.date_range(start='2021-10-02',end='2021-10-10',freq='1D')]
        with Pool(nCores) as p:
            dfs=p.map(self.dumy_day,days)
        return dfs

    def remove_tags_daily(self,tags,folderPkl,patPeriod='**',nCores=6):
        days=glob.glob(folderPkl + patPeriod)
        if len(days)==1:
            self.remove_tags_day(days[0])
        else :
            with Pool(nCores) as p:p.starmap(self.remove_tags_day,[(d,tags) for d in days])

    def process_tag(self,df,rsMethod='forwardfill',rs='auto',timezone='CET',rmwindow='3000s',checkTime=False):
        '''
            - df : pd.series with timestampz index and name=value
            - rsMethod : see self.methods
            - rs : argument for pandas.resample
            - rmwindow : argument for method rollingmean
        '''
        if df.empty:
            return df
        start=time.time()
        # remove duplicated index and pivot
        df = df.reset_index().drop_duplicates().dropna().set_index('timestampz').sort_index()
        if checkTime:computetimeshow('drop dupplicates ',start)
        ##### auto resample
        if rs=='auto' and not rsMethod=='raw':
            ptsCurve = 500
            deltat = (df.index.max()-df.index.min()).seconds//ptsCurve+1
            rs = '{:.0f}'.format(deltat) + 's'
        start  = time.time()
        ############ compute resample
        if not rsMethod=='raw':
            if df.value.dtype=='O':
                df=df.resample(rs).ffill()
            else:
                df = eval(self.methods[rsMethod])
        # print(df,rsMethod,rs,timezone)
        if checkTime:computetimeshow(rsMethod + ' data',start)
        df.index = df.index.tz_convert(timezone)
        return df

    def load_tag_daily(self,t0,t1,tag,folderpkl,rsMethod,rs,timezone,rmwindow='3000s',showTag=False,debug=False):
        if showTag:print(tag)
        start=time.time()
        dfs={}
        t=t0 - pd.Timedelta(hours=t0.hour,minutes=t0.minute,seconds=t0.second)
        while t<t1:
            filename=folderpkl+t.strftime(self.format_dayFolder)+'/'+tag+'.pkl'
            if os.path.exists(filename):
                if debug: print(filename,t.isoformat())
                dfs[filename]=pickle.load(open(filename,'rb'))
            else :
                print('no file : ',filename)
                dfs[filename] = pd.Series()
            t = t + pd.Timedelta(days=1)
        if debug:computetimeshow('raw pkl loaded in ',start)
        start=time.time()
        dftag = pd.DataFrame(pd.concat(dfs.values()),columns=['value'])
        if debug:computetimeshow('contatenation done in ',start)
        dftag.index.name='timestampz'
        try:
            start=time.time()
            dftag = self.process_tag(dftag,rsMethod,rs,timezone,rmwindow=rmwindow)
            dftag['tag'] = tag
            if debug:computetimeshow('processing done in ',start)
        except:
            print(tag+' could not be processed')
            dftag=[]
        return dftag

    def load_parkedtags_daily(self,t0,t1,tags,folderpkl,rsMethod='forwardfill',rs='auto',timezone='CET',rmwindow='3000s',pool=False,showTag=False):
        '''
        - rsMethod,rs,timezone,rmwindow of Streamer.process_tag
        - pool : on tags
        '''
        if not len(tags)>0:
            return pd.DataFrame()
        if pool:
            with Pool() as p:
                dftags=p.starmap(self.load_tag_daily,[(t0,t1,tag,folderpkl,rsMethod,rs,timezone,rmwindow,showTag) for tag in tags])
        else:
            dftags=[self.load_tag_daily(t0,t1,tag,folderpkl,rsMethod,rs,timezone,rmwindow,showTag) for tag in tags]
        # print(dftags)
        df = pd.concat(dftags,axis=0)
        df = df[df.index>=t0]
        df = df[df.index<=t1]
        return df

    # ########################
    #    MINUTE FUNCTIONS    #
    # ########################
    def create_minutefolder(self,folderminute):
        # print(folderminute)
        if not os.path.exists(folderminute):
            folderhour=self.fs.getParentDir(folderminute)
            if not os.path.exists(folderhour):
                # print(folderhour)
                folderday=self.fs.getParentDir(folderhour)
                parentFolder=self.fs.getParentDir(folderday)
                if not os.path.exists(parentFolder):
                    print(parentFolder,''' does not exist. Make sure
                    the path of the parent folder exists''')
                    raise SystemExit
                if not os.path.exists(folderday):
                    # print(folderday)
                    os.mkdir(folderday)
                os.mkdir(folderhour)
            os.mkdir(folderminute)
            return folderminute +' created '
        else :
            return folderminute +' already exists '

    def delete_minutefolder(self,folderminute):
        # print(folderminute)
        if os.path.exists(folderminute):
            os.rmdir(folderminute)
            return folderminute +' deleted '
        else :
            return folderminute +' does not exist '

    def loaddata_minutefolder(self,folderminute,tag):
        if os.path.exists(folderminute):
            # print(folderminute)
            return pickle.load(open(folderminute + tag + '.pkl', "rb" ))
        else :
            print('no folder : ',folderminute)
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
        return self.fs.flatten(dfs)

    def parktagminute(self,folderminute,dftag):
        tag = dftag.tag[0]
        #get only the data for that minute
        minute = folderminute.split('/')[-2]
        hour   = folderminute.split('/')[-3]
        day    = folderminute.split('/')[-4]
        time2save = day+' '+hour+':'+minute
        t1 = pd.to_datetime(time2save).tz_localize(self.local_tzname)
        t2 = t1+dt.timedelta(minutes=1)
        dfminute = dftag[(dftag.index<t2)&(dftag.index>=t1)]
        # if dfminute.empty:
        #     print(tag,t1,t2)
        #     print(dfminute)
        #     time.sleep(1)
        #create folder if necessary
        if not os.path.exists(folderminute):
            return 'no folder : ' + folderminute

        #park tag-minute
        pickle.dump(dfminute,open(folderminute + tag + '.pkl', "wb" ))
        return tag + ' parked in : ' + folderminute

    def park_df_minute(self,folderminute,df_minute,listTags):
        if not os.path.exists(folderminute):os.mkdir(folderminute)
        # print(folderminute)
        # print(df_minute)
        for tag in listTags:
            df_tag=df_minute[df_minute['tag']==tag][['value']]
            # df_tag.columns=[tag]
            df_tag.to_pickle(folderminute + tag + '.pkl')
        return tag + ' parked in : ' + folderminute

    def dumy_minute(self,folderminute):
        print(folderminute)
        return 'ici'

    def loadtags_minutefolder(self,folderminute,tags):
        if os.path.exists(folderminute):
            # print(folderminute)
            dfs=[pickle.load(open(folderminute + tag + '.pkl', "rb" )) for tag in tags]
            for df,tag in zip(dfs,tags):df.columns=[tag]
            df=pd.concat(dfs,axis=1)
            return df
        else :
            print('NO FOLDER : ',folderminute)
            return pd.DataFrame()

    # ########################
    #   HIGH LEVEL FUNCTIONS #
    # ########################
    def park_alltagsDF_minutely(self,df,folderpkl,pool=True):
        # check if the format of the file is correct
        correctColumns=['tag','timestampz','value']
        if not list(df.columns.sort_values())==correctColumns:
            print('PROBLEM: the df dataframe should have the following columns : ',correctColumns,'''
            or your columns are ''',list(df.columns.sort_values()))
            return
        df=df.set_index('timestampz')
        listTags=df.tag.unique()
        t0 = df.index.min()
        t1 = df.index.max()
        self.createFolders_period(t0,t1,folderpkl,'minute')
        nbHours=int((t1-t0).total_seconds()//3600)+1
        ### cut file into hours because otherwise file is to big
        for h in range(nbHours):
        # for h in range(nbHours)[3:4]:
            tm1=t0+dt.timedelta(hours=h)
            tm2=tm1+dt.timedelta(hours=1)
            tm2=min(tm2,t1)
            # print(tm1,tm2)
            dfhour=df[(df.index>tm1)&(df.index<tm2)]
            print('start for :', dfhour.index[-1])
            start=time.time()
            minutes=pd.date_range(tm1,tm2,freq='1T')
            df_minutes=[dfhour[(dfhour.index>a)&(dfhour.index<a+dt.timedelta(minutes=1))] for a in minutes]
            minutefolders =[folderpkl + k.strftime(self.format_folderminute) for k in minutes]
            # print(minutefolders)
            # sys.exit()
            if pool:
                with Pool() as p:
                    dfs = p.starmap(self.park_df_minute,[(fm,dfm,listTags) for fm,dfm in zip(minutefolders,df_minutes)])
            else:
                dfs = [self.park_df_minute(fm,dfm,listTags) for fm,dfm in zip(minutefolders,df_minutes)]
            print('done in {:.2f} s'.format((time.time()-start)))

    def createFolders_period(self,t0,t1,folderPkl,frequence='day'):
        if frequence=='minute':
            return self.foldersaction(t0,t1,folderPkl,self.create_minutefolder)
        elif frequence=='day':
            createfolderday=lambda x:os.mkdir(folderday)
            listDays = pd.date_range(t0,t1,freq='1D')
            listfolderdays = [folderPkl +'/'+ d.strftime(self.format_dayFolder) for d in listDays]
            with Pool() as p:
                dfs=p.starmap(createfolderday,[(d) for d in listfolderdays])
            return dfs

    def dumy_period(self,period,folderpkl,pool=True):
        t0,t1=period[0],period[1]
        return self.actionMinutes_pooled(t0,t1,folderpkl,self.dumy_minute,pool=pool)

    def load_parkedtags_period(self,tags,period,folderpkl,pool=True):
        t0,t1=period[0],period[1]
        # if t1 - t0 -dt.timedelta(hours=3)<pd.Timedelta(seconds=0):
        #     pool=False
        dfs=self.actionMinutes_pooled(t0,t1,folderpkl,self.loadtags_minutefolder,tags,pool=pool)
        return pd.concat(dfs.values())
        # return dfs

    def listfiles_pattern_period(self,t0,t1,pattern,folderpkl,pool=True):
        return self.actiondays(t0,t1,folderpkl,self.fs.listfiles_pattern_folder,pattern,pool=pool)
    # ########################
    #   STATIC COMPRESSION   #
    # ########################
    def staticCompressionTag(self,s,precision,method='reduce'):
        if method=='diff':
            return s[np.abs(s.diff())>precision]

        elif method=='dynamic':
            newtag=pd.Series()
            # newtag=[]
            valCourante = s[0]
            for row in s.iteritems():
                newvalue=row[1]
                if np.abs(newvalue - valCourante) > precision:
                    valCourante = newvalue
                    newtag[row[0]]=row[1]
            return newtag

        elif method=='reduce':
            from functools import reduce
            d = [[k,v] for k,v in s.to_dict().items()]
            newvalues=[d[0]]
            def compareprecdf(s,prec):
                def comparewithprec(x,y):
                    if np.abs(y[1]-x[1])>prec:
                        newvalues.append(y)
                        return y
                    else:
                        return x
                reduce(comparewithprec, s)
            compareprecdf(d,precision)
            return pd.DataFrame(newvalues,columns=['timestamp',s.name]).set_index('timestamp')[s.name]

    def compareStaticCompressionMethods(self,s,prec,show=False):
        res={}

        start = time.time()
        s1=self.staticCompressionTag(s=s,precision=prec,method='diff')
        res['diff ms']=computetimeshow('',start)
        res['diff len']=len(s1)

        start = time.time()
        s2=self.staticCompressionTag(s=s,precision=prec,method='dynamic')
        res['dynamic ms']=computetimeshow('',start)
        res['dynamic len']=len(s2)

        start = time.time()
        s3=self.staticCompressionTag(s=s,precision=prec,method='reduce')
        res['reduce ms']=computetimeshow('',start)
        res['reduce len']=len(s3)

        df=pd.concat([s,s1,s2,s3],axis=1)
        df.columns=['original','diff','dynamic','reduce']
        df=df.melt(ignore_index=False)
        d = {'original': 5, 'diff': 3, 'dynamic': 2, 'reduce': 0.5}
        df['sizes']=df['variable'].apply(lambda x:d[x])
        if show:
            fig=px.scatter(df,x=df.index,y='value',color='variable',symbol='variable',size='sizes')
            fig.update_traces(marker_line_width=0).show()
        df['precision']=prec
        return pd.Series(res),df

    def generateRampPlateau(self,br=0.1,nbpts=1000,valPlateau=100):
        m=np.linspace(0,valPlateau,nbpts)+br*np.random.randn(nbpts)
        p=valPlateau*np.ones(nbpts)+br*np.random.randn(nbpts)
        d=np.linspace(valPlateau,0,nbpts)+br*np.random.randn(nbpts)
        idx=pd.date_range('9:00',periods=nbpts*3,freq='S')
        return pd.Series(np.concatenate([m,p,d]),index=idx)

    def testCompareStaticCompression(self,s,precs,fcw=3):
        import plotly.express as px
        results=[self.compareStaticCompressionMethods(s=s,prec=p) for p in precs]
        timelens=pd.concat([k[0] for k in results],axis=1)
        timelens.columns=['prec:'+'{:.2f}'.format(p) for p in precs]
        df=pd.concat([k[1] for k in results],axis=0)
        fig=px.scatter(df,x=df.index,y='value',color='variable',symbol='variable',
            size='sizes',facet_col='precision',facet_col_wrap=fcw)
        fig.update_traces(marker_line_width=0)
        for t in fig.layout.annotations:
            t.text = '{:.2f}'.format(float(re.findall('\d+\.\d+',t.text)[0]))
        fig.show()
        return timelens

class Configurator():
    def __init__(self,folderPkl,dbParameters,devices,parkingTime):
        '''
        - parkedFolder : day or minute.
        - parkingTime : how often data are parked and db flushed in seconds
        - devices: dictionnary of devices where keys are device_names and values
        are devices instances generated from children classes of Device.
        '''
        Streamer.__init__(self)
        self.folderPkl = folderPkl##in seconds
        self.dbParameters = dbParameters
        self.dataTypes = {
          'REAL':'float',
          'BOOL':'bool',
          'WORD':'int',
          'DINT':'int',
          'INT':'int',
          'STRING(40)':'str'
        }
        self.streamer =  Streamer()
        self.parkingTime = parkingTime##seconds
        self.devices = devices
        #####################################
        self.dfplc = pd.concat([device.dfplc for device in self.devices.values()])
        self.dfplc = self.dfplc[self.dfplc.DATASCIENTISM==True]
        self.alltags    = list(self.dfplc.index)

        self.daysnotempty = self.getdaysnotempty()
        self.tmin,self.tmax = self.daysnotempty.min(),self.daysnotempty.max()
        self.listUnits = self.dfplc.UNITE.dropna().unique().tolist()
        self.to_folderminute=lambda x:self.folderPkl+x.strftime(self.format_folderminute)
        print('FINISH LOADING CONFIGURATOR')
        print('==============================')
        print()

    def getdaysnotempty(self):
        return self.fs.get_parked_days_not_empty(self.folderPkl)

    def connect2db(self):
        connReq = ''.join([k + "=" + v + " " for k,v in self.dbParameters.items()])
        return psycopg2.connect(connReq)

    def getUsefulTags(self,usefulTag):
        if usefulTag in self.usefulTags.index:
            category = self.usefulTags.loc[usefulTag,'Pattern']
            return self.getTagsTU(category)
        else:
            return []

    def createRandomInitalTagValues(self):
        return self.fs.createRandomInitalTagValues(self.alltags,self.dfplc)

    def getUnitofTag(self,tag):
        return self.fs.getUnitofTag(tag,self.dfplc)

    def getTagsTU(self,patTag,units=None,*args,**kwargs):
        if not units : units = self.listUnits
        return self.fs.getTagsTU(patTag,self.dfplc,units,*args,**kwargs)

class SuperDumper(Configurator):
    def __init__(self,*args,**kwargs):
        Configurator.__init__(self,*args,**kwargs)
        self.parkingTimes={}
        self.streamer = Streamer()
        self.fs = FileSystem()
        self.dumpInterval,self.reconnexionThread = {},{}
        self.parkInterval = SetInterval(self.parkingTime,self.park_database)
        ###### DOUBLE LOOP of setIntervals for devices/acquisition-frequencies
        for device_name,device in self.devices.items():
            self.reconnexionThread[device_name] = SetInterval(device.timeOUTreconnect,device.checkConnection)
            dfplc = device.dfplc[device.dfplc.DATASCIENTISM==True]
            freqs = dfplc['FREQUENCE_ECHANTILLONNAGE'].unique()
            device_dumps={}
            for freq in freqs:
                print(device_name,' : ',freq*1000,'ms')
                tags = list(dfplc[dfplc['FREQUENCE_ECHANTILLONNAGE']==freq].index)
                # print(tags)
                device_dumps[freq] = SetInterval(freq,device.insert_intodb,self.dbParameters,tags)

            self.dumpInterval[device_name] = device_dumps

    def flushdb(self,t,full=False):
        connReq = ''.join([k + "=" + v + " " for k,v in self.dbParameters.items()])
        dbconn = psycopg2.connect(connReq)
        cur  = dbconn.cursor()
        if full:
            cur.execute("DELETE from realtimedata;")
        else :
            cur.execute("DELETE from realtimedata where timestampz < '" + t + "';")
        cur.close()
        dbconn.commit()
        dbconn.close()

    def feed_db_random_data(self,*args,**kwargs):
        df = self.generateRandomParkedData(*args,**kwargs)
        dbconn = self.connect2db()
        cur  = dbconn.cursor()
        sqlreq = "insert into realtimedata (tag,value,timestampz) values "
        for k in range(len(df)):
            curval=df.iloc[k]
            sqlreq+="('" + curval.tag + "','"+ str(curval.value) +"','" + curval.name.isoformat()  + "'),"
        sqlreq =sqlreq[:-1]
        sqlreq+= ";"
        cur.execute(sqlreq)
        cur.close()
        dbconn.commit()
        dbconn.close()

    def exportdb2zip(self,dbParameters,t0,t1,folder,basename='-00-00-x-RealTimeData.csv'):
        '''
        Not fully working with zip file. Working with pkl for the moment

        '''
        from zipfile import ZipFile
        start=time.time()
        ### read database
        dbconn=psycopg2.connect(''.join([k + "=" + v + " " for k,v in dbParameters.items()]))
        sqlQ ="select * from realtimedata where timestampz < '" + t1.isoformat() +"'"
        sqlQ +="and timestampz > '" + t0.isoformat() +"'"
        print(sqlQ)
        df = pd.read_sql_query(sqlQ,dbconn,parse_dates=['timestampz'])
        df = df[['tag','value','timestampz']]
        df['timestampz'] = pd.to_datetime(df['timestampz'])
        df       = df.set_index('timestampz')
        df.index = df.index.tz_convert('UTC')
        df = df.sort_index()

        namefile=folder + (t0+pd.Timedelta(days=1)).strftime(self.format_dayFolder).split('/')[0] +basename
        # df.to_csv(namefile)
        # zipObj = ZipFile(namefile.replace('.csv','.zip'), 'w')
        # zipObj.write(namefile,namefile.replace('.csv','.zip'))
        computetimeshow(pd.Timestamp.now().strftime('%H:%M:%S,%f') + ' ===> database read',start)
        namefile = namefile.replace('.csv','.pkl')
        pickle.dump(df,open(namefile,'wb'))
        print(namefile,' saved')
        # close connection
        dbconn.close()

    def generateRandomParkedData(self,t0,t1,vol=1.5,listTags=None):
        valInits = self.createRandomInitalTagValues()
        if listTags==None:listTags=self.alltags
        valInits = {tag:valInits[tag] for tag in listTags}
        df = {}
        for tag,initval in valInits.items():
            tagvar = self.dfplc.loc[tag]
            precision  = self.dfplc.loc[tag,'PRECISION']
            timestampz = pd.date_range(t0,t1,freq=str(tagvar['FREQUENCE_ECHANTILLONNAGE'])+'S')

            if tagvar.DATATYPE=='STRING(40)':
                values  = [initval]* len(timestampz)
                df[tag] = pd.DataFrame({'value':values,'timestampz':timestampz})
            elif tagvar.DATATYPE=='BOOL':
                values  = initval + np.random.randint(0,2,len(timestampz))
                df[tag] = pd.DataFrame({'value':values,'timestampz':timestampz})
            else:
                values  = initval + precision*vol*np.random.randn(len(timestampz))
                stag = pd.Series(values,index=timestampz)
                # stag = self.streamer.staticCompressionTag(stag,precision,method='reduce')
                df[tag] = pd.DataFrame(stag).reset_index()
                df[tag].columns=['timestampz','value']
            df[tag]['tag'] = tag
            print(tag + ' generated')
        df=pd.concat(df.values(),axis=0)
        start = time.time()
        # df.timestampz = [t.isoformat() for t in df.timestampz]
        computetimeshow('timestampz to str',start)
        df=df.set_index('timestampz')
        return df

    def checkTimes(self,name_device):
        dict2pdf = lambda d:pd.DataFrame.from_dict(d,orient='index').squeeze().sort_values()
        device = self.devices.__dict__[name_device]
        s_collect = dict2pdf(device.collectingTimes)
        s_insert  = dict2pdf(device.insertingTimes)

        p = 1. * np.arange(len(s_collect))
        ## first x axis :
        tr1 = go.Scatter(x=p,y=df,name='collectingTime',col=1,row=1)
        ## second axis
        tr2 = go.Scatter(x=p,y=df,name='collectingTime',col=1,row=2)
        title1='cumulative probability density '
        title2='histogramm computing times '
        # fig.update_layout(titles=)
        return fig
    # ########################
    #       SCHEDULERS       #
    # ########################
    def start_dumping(self,parkedFolder):
        now = pd.Timestamp.now(tz='CET')
        ##### start the schedulers at H:M:S:00 petante! #####
        time.sleep(1-now.microsecond/1000000)

        ######## start dumping
        print(timenowstd(),': START DUMPING')
        for device,dictIntervals in self.dumpInterval.items():
            self.reconnexionThread[device].start()
            for freq in dictIntervals.keys():
                self.dumpInterval[device][freq].start()

        ######## start parking on time
        now = pd.Timestamp.now(tz='CET')
        # now = pd.Timestamp.now('2022-02-10 16:52:15',tz='CET')
        timer = 60-now.second
        print('parking should start at ',now +pd.Timedelta(seconds=timer))
        time.sleep(timer)
        print(timenowstd(),': START PARKING')
        self.parkInterval.start()

    def stop_dumping(self):
        for device,dictIntervals in self.dumpInterval.items():
            for freq in dictIntervals.keys():
                self.dumpInterval[device][freq].stop()
        self.parkInterval.stop()

class SuperDumper_daily(SuperDumper):
    def start_dumping(self):
        return SuperDumper.start_dumping(self,'day')

    def parktagfromdb(self,tag,dftag,folderday):
        df = dftag
        namefile = folderday + tag + '.pkl'
        if os.path.exists(namefile):
            df1 = pickle.load(open(namefile,'rb'))
            df  = pd.concat([df1,df])
        df.astype(self.dataTypes[self.dfplc.loc[tag,'DATATYPE']]).to_pickle(namefile)

    def park_database(self):
        listTags = self.alltags
        start = time.time()
        now = pd.Timestamp.now(tz=self.local_tzname)
        t_parking = now

        ### read database
        dbconn = self.connect2db()
        sqlQ ="select * from realtimedata where timestampz < '" + now.isoformat() +"'"
        # df = pd.read_sql_query(sqlQ,dbconn,parse_dates=['timestampz'],dtype={'value':'float'})
        df = pd.read_sql_query(sqlQ,dbconn,parse_dates=['timestampz'])
        computetimeshow('database for data <' + t_parking.isoformat() +' read',start)
        # check if database not empty
        if not len(df)>0:
            print('database ' + self.dbParameters['dbname'] + ' empty')
            return
        # close connection
        df = df.set_index('timestampz').sort_index()
        df.loc[df.value=='null','value']=np.nan
        dbconn.close()

        tmin,tmax = df.index.min().tz_convert('CET'),df.index.max().tz_convert('CET')
        listdays = list(np.unique([k.strftime(self.format_dayFolder)[:-1] for k in [tmin,tmax]]))
        #### in case they are 2 days around midnight
        for d in listdays:
            t0=pd.Timestamp(d + ' 00:00:00',tz='CET')
            t1=t0+pd.Timedelta(days=1)
            dfday=df[(df.index>=t0)&(df.index<t1)]
            folderday=self.folderPkl + d +'/'
            #### create folder if necessary
            if not os.path.exists(folderday):os.mkdir(folderday)
            #################################
            #           park now            #
            #################################
            start=time.time()
            # dftags=[dfday[dfday.tag==tag]['value'] for tag in listTags]
            # with Pool() as p:
            #     dfs=p.starmap(self.parktagfromdb,[(tag,dftag,folderday) for tag,dftag in zip(listTags,dftags)])
            dfs=[]
            for tag in listTags:
                dftag = dfday[dfday.tag==tag]['value'] #### dump a pd.series
                self.parktagfromdb(tag,dftag,folderday)

        computetimeshow('database parked',start)
        self.parkingTimes[now.isoformat()] = (time.time()-start)*1000
        # #FLUSH DATABASE
        self.flushdb(t_parking.isoformat())
        return

class SuperDumper_minutely(SuperDumper):
    def start_dumping(self):
        return SuperDumper.start_dumping(self,'minute')

    def parktagfromdb(self,t0,t1,df,tag,compression='reduce'):
        dftag = df[df.tag==tag].set_index('timestampz')
        # print(dftag)
        dftag.index=dftag.index.tz_convert(self.local_tzname)
        if dftag.empty:
            return dftag
        # print(tag + ' : ',self.dfplc.loc[tag,'DATATYPE'])
        if compression in ['reduce','diff','dynamic'] and not self.dfplc.loc[tag,'DATATYPE']=='STRING(40)':
            precision = self.dfplc.loc[tag,'PRECISION']
            dftag = dftag.replace('null',np.nan)
            dftag.value = dftag.value.astype(self.dataTypes[self.dfplc.loc[tag,'DATATYPE']])
            dftag.value = self.streamer.staticCompressionTag(dftag.value,precision,compression)
        return self.streamer.foldersaction(t0,t1,self.folderPkl,self.streamer.parktagminute,dftag=dftag)

    def park_database(self):
        listTags=self.alltags
        start = time.time()
        timenow = pd.Timestamp.now(tz=self.local_tzname)
        t1 = timenow

        ### read database
        dbconn = self.connect2db()
        sqlQ ="select * from realtimedata where timestampz < '" + t1.isoformat() +"'"
        # df = pd.read_sql_query(sqlQ,dbconn,parse_dates=['timestampz'],dtype={'value':'float'})
        df = pd.read_sql_query(sqlQ,dbconn,parse_dates=['timestampz'])
        computetimeshow(now.strftime('%H:%M:%S,%f') + ''' ===> database read''',start)
        print('for data <' + t1.isoformat())
        # close connection
        dbconn.close()

        # check if database not empty
        if not len(df)>0:
            print('database ' + self.dbParameters['dbname'] + ' empty')
            return []

        ##### determine minimum time for parking folders
        t0 = df.set_index('timestampz').sort_index().index[0].tz_convert(self.local_tzname)
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
        computetimeshow(now.strftime('%H:%M:%S,%f') + ''' ===> database parked''',start)
        self.parkingTimes[timenow.isoformat()] = (time.time()-start)*1000
        # #FLUSH DATABASE
        start=time.time()
        self.flushdb(t1.isoformat())
        return dfs

import plotly.graph_objects as go, plotly.express as px
class VisualisationMaster(Configurator):
    def __init__(self,*args,**kwargs):
        Configurator.__init__(self,*args,**kwargs)
        self.methods = self.streamer.methods
        self.methods_list = list(self.methods.keys())

    def _load_database_tags(self,t0,t1,tags,*args,pool=True,**kwargs):
        '''
        - tags : list of tags
        - t0,t1 : timestamps with timezone
        '''
        # for k in t0,t1,tags,args,kwargs:print(k)
        dbconn = self.connect2db()
        if not isinstance(tags,list) or len(tags)==0:
                print('no tags selected for database')
                return pd.DataFrame()

        sqlQ = "select * from realtimedata where tag in ('" + "','".join(tags) +"')"
        sqlQ += " and timestampz > '" + t0.isoformat() + "'"
        sqlQ += " and timestampz < '" + t1.isoformat() + "'"
        sqlQ +=";"
        # print(sqlQ)
        start=time.time()
        df = pd.read_sql_query(sqlQ,dbconn,parse_dates=['timestampz'])
        computetimeshow('database read ',start)
        dbconn.close()
        if len(df)==0:
            return df.set_index('timestampz')
        if df.duplicated().any():
            print("WARNING : duplicates in database")
            print(df[df.duplicated(keep=False)])
            df = df.drop_duplicates()
        df.loc[df.value=='null','value']=np.nan
        df = df.set_index('timestampz')

        def process_dbtag(df,tag,*args,**kwargs):
            dftag = df[df.tag==tag]['value']
            dftag = self.streamer.process_tag(dftag,*args,**kwargs)
            ## assign type
            dtype=self.dataTypes[self.dfplc.loc[tag,'DATATYPE']]
            dftag = dftag.astype(dtype)
            dftag['tag'] = tag
            return dftag
        dftags = [process_dbtag(df,tag,*args,**kwargs) for tag in tags]
        df = pd.concat(dftags,axis=0)
        df = df[df.index>=t0]
        df = df[df.index<=t1]
        return df

    def loadtags_period(self,t0,t1,tags,*args,checkTime=False,**kwargs):
        '''
        - t0,t1 : timestamps
        - *args,**kwargs of Streamer.processdf
        '''
        # for k in t0,t1,tags,args,kwargs:print(k)
        tags=list(np.unique(tags))
        ############ read parked data
        start=time.time()
        dfparked = self.streamer.load_parkedtags_daily(t0,t1,tags,self.folderPkl,pool=True,*args,**kwargs)
        if checkTime:computetimeshow('loading the parked data',start)
        start=time.time()
        # print(dfparked)
        df = dfparked.pivot(values='value',columns='tag').sort_index()
        if checkTime:computetimeshow('pivot data',start)
        ############ read database
        if t1>=pd.Timestamp.now(tz='CET')-pd.Timedelta(seconds=self.parkingTime):
            start = time.time()
            dfdb  = self._load_database_tags(t0,t1,tags,*args,**kwargs)
            dfdb  = dfdb.pivot(values='value',columns='tag').sort_index()
            if checkTime:computetimeshow('loading the database',start)
            df = pd.concat([df,dfdb])
        return df

    def toogle_tag_description(self,tagsOrDescriptions,toogleto='tag'):
        '''
        -tagsOrDescriptions:list of tags or description of tags
        -toogleto: you can force to toogleto description or tags ('tag','description')
        '''
        current_names = tagsOrDescriptions
        ### automatic detection if it is a tag --> so toogle to description
        areTags = True if current_names[0] in self.dfplc.index else False
        dictNames=dict(zip(current_names,current_names))
        if toogleto=='description'and areTags:
            newNames  = [self.dfplc.loc[k,'DESCRIPTION'] for k in current_names]
            dictNames = dict(zip(current_names,newNames))
        elif toogleto=='tag'and not areTags:
            newNames  = [self.dfplc.index[self.dfplc.DESCRIPTION==k][0] for k in current_names]
            dictNames = dict(zip(current_names,newNames))
        return dictNames

# #######################
# #  STANDARD GRAPHICS  #
# #######################
    def addTagEnveloppe(self,fig,tag_env,t0,t1,rs):
        hex2rgb = lambda h,a:'rgba('+','.join([str(int(h[i:i+2], 16)) for i in (0, 2, 4)])+','+str(a)+')'
        df     = self.loadtags_period(t0,t1,[tag_env],rsMethod='forwardfill',rs='100ms')
        dfmin  = df.resample(rs,label='right',closed='right').min()
        dfmax  = df.resample(rs,label='right',closed='right').max()
        hexcol = [trace.marker.color for trace in fig.data if trace.name==tag_env][0]
        col    = hex2rgb(hexcol.strip('#'),0.3)
        x = list(dfmin.index) + list(np.flip(dfmax.index))
        y = list(dfmin[tag_env])  + list(np.flip(dfmax[tag_env]))
        correctidx=[k for k in self.toogle_tag_description([k.name for k in fig.data],'tag').values()].index(tag_env)
        fig.add_trace(go.Scatter(x=x,y=y,fill='toself',fillcolor=col,mode='none',
                    name=tag_env + '_minmax',yaxis=fig.data[correctidx]['yaxis']))
        return fig

    def standardLayout(self,fig,ms=5,h=750):
        fig.update_yaxes(showgrid=False)
        fig.update_xaxes(title_text='')
        fig.update_traces(selector=dict(type='scatter'),marker=dict(size=ms))
        fig.update_layout(height=h)
        # fig.update_traces(hovertemplate='<b>%{y:.2f}')
        fig.update_traces(hovertemplate='     <b>%{y:.2f}<br>     %{x|%H:%M:%S,%f}')
        return fig

    def update_lineshape_fig(self,fig,style='default'):
        if style == 'default':
            style='lines+markers'
        if style in ['markers','lines','lines+markers']:
            fig.update_traces(line_shape="linear",mode=style)
        elif style =='stairs':
            fig.update_traces(line_shape="hv",mode='lines')
        return fig

    def plotTabSelectedData(self,df):
        start=time.time()
        fig = px.scatter(df)
        unit = self.getUnitofTag(df.columns[0])
        nameGrandeur = self.utils.detectUnit(unit)
        fig.update_layout(yaxis_title = nameGrandeur + ' in ' + unit)
        return fig

    def multiMultiUnitGraph(self,df,*listtags,axSP=0.05):
        hs=0.002
        dictdictGroups={'graph'+str(k):{t:self.getUnitofTag(t) for t in tags} for k,tags in enumerate(listtags)}
        fig = self.utils.multiUnitGraphSubPlots(df,dictdictGroups,axisSpace=axSP)
        nbGraphs=len(listtags)
        for k,g in enumerate(dictdictGroups.keys()):
            units = list(pd.Series(dictdictGroups[g].values()).unique())
            curDomaine = [1-1/nbGraphs*(k+1)+hs,1-1/nbGraphs*k-hs]
            for y in range(1,len(units)+1):
                fig.layout['yaxis'+str(k+1)+str(y)].domain = curDomaine
        fig.update_xaxes(showticklabels=False)
        # fig.update_yaxes(showticklabels=False)
        fig.update_yaxes(showgrid=False)
        fig.update_xaxes(matches='x')
        self.standardLayout(fig,h=None)
        return fig

    def graph_UnitsSubplots(self,df,facet_col_wrap=2):
        tagMapping = {t:self.getUnitofTag(t) for t in df.columns}
        allunits   = list(np.unique(list(tagMapping.values())))
        rows=len(allunits)
        df = df.melt(ignore_index=False)
        df['unit']=df.apply(lambda x:tagMapping[x['tag']],axis=1)
        fig=px.scatter(df,y='value',color='tag',
                        facet_col='unit',facet_col_wrap=facet_col_wrap,
                        color_discrete_sequence = self.utils.colors_mostdistincs)
        fig.update_traces(mode='lines+markers')
        fig.update_xaxes(matches='x')
        fig.update_yaxes(matches=None)
        return fig

class VisualisationMaster_daily(VisualisationMaster):
    def _load_parked_tags(self,t0,t1,tags,pool):
        '''
        - t0,t1 : timestamps
        - tags : list of tags
        - pool:if true pool on tags
        '''
        if not isinstance(tags,list) or len(tags)==0:
            print('tags is not a list or is empty')
            return pd.DataFrame(columns=['value','timestampz','tag']).set_index('timestampz')
        df = self.streamer.load_parkedtags_daily(t0,t1,tags,self.folderPkl,pool)
        # if df.duplicated().any():
        #     print("==========================================")
        #     print("WARNING : duplicates in parked data")
        #     print(df[df.duplicated(keep=False)])
        #     print("==========================================")
        #     df = df.drop_duplicates()
        return df

class VisualisationMaster_minutely(VisualisationMaster):
    def _loadparkedtag(self,t0,t1,tag):
        # print(tag)
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
                print('tags is not a list')
                return pd.DataFrame()
        if len(tags)==0:
            return pd.DataFrame()

        start=time.time()
        if poolTags:
            print('pooling the data...')
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
            print("==========================================")
            print("attention il y a des doublons dans les donnees parkes : ")
            print(df[df.duplicated(keep=False)])
            print("==========================================")
            df = df.drop_duplicates()
        return df

# #######################
# #  VERISON MANAGER    #
# #######################
import collections
sort_list=lambda x:list(pd.Series(x).sort_values())
class VersionManager():
    def __init__(self,folderData,plcDir,buildFiles=[False,False,False],pattern_plcFiles='*plc*.csv'):
        self.streamer     = Streamer()
        self.fs           = FileSystem()
        self.plcDir       = plcDir
        self.folderData   = folderData
        self.versionFiles = glob.glob(self.plcDir+pattern_plcFiles)
        self.dicVersions  = {f:re.findall('\d+\.\d+',f.split('/')[-1])[0] for f in self.versionFiles}
        self.versions     = sort_list(self.dicVersions.values())
        self.daysnotempty = pd.Series([pd.Timestamp(k) for k in self.fs.get_parked_days_not_empty(folderData)])
        self.tmin,self.tmax = self.daysnotempty.min(),self.daysnotempty.max()
        # self.transitionFile = self.plcDir + 'versionnageTags.xlsx'
        self.transitionFile = self.plcDir + 'versionnageTags.ods'
        self.transitions    = pd.ExcelFile(self.transitionFile).sheet_names
        self.file_df_plcs    = self.plcDir + 'alldfsPLC.pkl'
        self.file_df_nbTags  = self.plcDir + 'nbTags.pkl'
        self.file_map_missingTags  = self.plcDir + 'map_missingTags.pkl'
        self.file_map_presenceTags  = self.plcDir + 'map_presenceTags.pkl'
        self.load_confFiles(buildFiles)
        print('FINISH LOADING VERSION MANAGER ')
        print('==============================')
        print()

    def load_confFiles(self,buildFiles):
        loadconfFile = lambda x,y,b:self.fs.load_confFile(x,y,b)
        self.df_plcs,self.all_tags_history = loadconfFile(self.file_df_plcs,self.load_PLC_versions,buildFiles[0])
        self.df_nbTagsFolder = loadconfFile(self.file_df_nbTags,self.load_nbTags_folders,buildFiles[1])
        self.map_missingTags,self.map_missingTags_len = loadconfFile(self.file_map_missingTags,self.load_missingTags_versions,buildFiles[2])
        # self.map_presenceTags = loadconfFile(self.file_map_presenceTags,self.load_presenceTags)

    #######################
    #       UTILS         #
    #######################
    def totime(self,x):
        y=x.split('/')
        return pd.Timestamp(y[0]+' ' +y[1] + ':' + y[2])

    def is_tags_in_PLCs(self,tags,ds=True):
        df_plcs = self.df_plcs
        if not not ds:
            df_plcs = {k:v[v.DATASCIENTISM==ds] for k,v in self.df_plcs.items()}
        tagInplc={}
        for tag in tags:
            tagInplc[tag]=[True if tag in list(v.index) else False for k,v in df_plcs.items()]
        return pd.DataFrame.from_dict(tagInplc,orient='index',columns=df_plcs.keys()).T.sort_index()

    def get_patterntags_inPLCs(self,pattern,ds=True):
        df_plcs = self.df_plcs
        if not not ds:
            df_plcs = {k:v[v.DATASCIENTISM==ds] for k,v in self.df_plcs.items()}
        patterntags_plcs={}
        # print(df_plcs.keys())
        for v,dfplc in df_plcs.items():
            # return pd.DataFrame.from_dict(tagInplc,orient='index',columns=df_plcs.keys()).T.sort_index()
            patterntags_plcs[v]=list(dfplc.index[dfplc.index.str.contains(pattern)])
            patterntags_plcs = collections.OrderedDict(sorted(patterntags_plcs.items()))
        return patterntags_plcs

    def get_listTags_folder(self,folder):
        return self.fs.listfiles_folder(folder)

    def get_lentags(self,folder):
        return len(self.fs.listfiles_folder(folder))

    def get_presenceTags_folder(self,folder,tags=None):
        if tags is None : tags=self.all_tags_history
        # print(folder)
        listTags = [k.split('.pkl')[0] for k in self.fs.listfiles_folder(folder)]
        # print(listTags)
        return {t:True if t in listTags else False for t in tags}

    def get_missing_tags_versions(self,folder):
        # print(folder)
        listTags = [k.split('.pkl')[0] for k in self.get_listTags_folder(folder)]
        # keep only valid tags
        listTags = [k for k in listTags if k in self.all_tags_history]
        dfs, tagNotInVersion, tagNotInFolder={},{},{}
        dayCompatibleVersions = {}
        for version,dfplc in self.df_plcs.items():
            # keep only valid tags
            tagsVersion = list(dfplc.index[dfplc.DATASCIENTISM])
            tagNotInVersion[version] = [k for k in listTags if k not in tagsVersion]
            tagNotInFolder[version] = [k for k in tagsVersion if k not in listTags]
            dfs[version] = tagsVersion
            dayCompatibleVersions[version] = tagNotInFolder[version]
        return dayCompatibleVersions


    #######################
    # GENERATE DATAFRAMES #
    #######################
    def load_PLC_versions(self):
        print('Start reading plc files....')
        df_plcs = {}
        for f,v in self.dicVersions.items():
            print(f)
            df_plcs[v] = pd.read_csv(f,index_col=0)

        print('')
        print('concatenate tags of all dfplc verion')
        all_tags_history = list(pd.concat([pd.Series(dfplc.index[dfplc.DATASCIENTISM]) for dfplc in df_plcs.values()]).unique())
        return df_plcs,all_tags_history

    ######################
    # MAKE IT COMPATIBLE #
    ######################
    ##### load the right version to version correspondance
    def getCorrectVersionCorrespondanceSheet(self,transition):
        if transition not in self.transitions:
            return pd.DataFrame({'old tag':[],'new tag':[]})
        else:
            return pd.read_excel(self.transitionFile,sheet_name=transition)

    def get_renametagmap_transition(self,transition):
        patternsMap = self.getCorrectVersionCorrespondanceSheet(transition)
        if len(patternsMap)>0:
            dfRenameTagsMap = patternsMap.apply(lambda x:self._getReplaceTagPatternMap(x[0],x[1],transition),axis=1,result_type='expand')
            ## remove empty lists for old Tags
            dfRenameTagsMap = dfRenameTagsMap[dfRenameTagsMap[0].apply(len)>0]
            ## flatten lists
            dfRenameTagsMap = dfRenameTagsMap.apply(lambda x:self.flattenList(x))
        else:
            dfRenameTagsMap=pd.DataFrame([[],[]]).T
        dfRenameTagsMap.columns=['oldTags','newTags']

        vold,vnew=transition.split('_')
        plcold = self.df_plcs[vold]
        plcold = plcold[plcold.DATASCIENTISM==True]
        plcnew = self.df_plcs[vnew]
        plcnew = plcnew[plcnew.DATASCIENTISM==True]

        tagsAdded = [t for t in list(plcnew.TAG) if t not in list(plcold.TAG)]
        # tags that were renamed should not be added
        tagsAdded = [k for k in tagsAdded if k not in list(dfRenameTagsMap.newTags)]
        return dfRenameTagsMap,tagsAdded

    def get_renametagmap_transition_v2(self,transition):
        patternsMap = self.getCorrectVersionCorrespondanceSheet(transition)
        patternsMap = patternsMap.set_index('old tag').squeeze(axis=1).to_dict()
        vold,vnew=transition.split('_')
        plcold  = self.df_plcs[vold]
        oldtags = list(plcold[plcold.DATASCIENTISM==True].index)
        plcnew  = self.df_plcs[vnew]
        newtags = list(plcnew[plcnew.DATASCIENTISM==True].index)
        df_renametagsmap = {}
        for oldtag in oldtags:
            newtag = oldtag
            for oldpat,newpat in patternsMap.items():
                newtag= newtag.replace(oldpat,newpat)
            df_renametagsmap[oldtag] = newtag
        df_renametagsmap=pd.DataFrame({'oldtag':df_renametagsmap.keys(),'newtag':df_renametagsmap.values()})
        df_renametagsmap = df_renametagsmap[df_renametagsmap.apply(lambda x:not x['oldtag']==x['newtag'],axis=1)]

        # brand_newtags = [t for t in newtags if t not in list(df_renametagsmap['newtag'])]
        # brand_newtags = pd.DataFrame([(None,k) for k in brand_newtags],columns=['oldtag','newtag'])
        # df_renametagsmap = pd.concat([df_renametagsmap,brand_newtags])
        return df_renametagsmap

    def get_rename_tags_newpattern(self,oldPattern,newPattern,df_plc,debug=False):
        ''' replace only pattern occurence '''
        df_renametagsmap=pd.DataFrame(df_plc.index,columns=['oldtag'])
        df_renametagsmap['newtag']=df_renametagsmap.apply(lambda x : x.replace(oldPattern,newPattern))
        return df_renametagsmap

    def removeInvalidTags(self,folderminute):
        listTags = [k.split('.pkl')[0] for k in os.listdir(folderminute)]
        list_invalidTags = [k for k in listTags if k not in self.all_tags_history]
        try:
            [os.remove(folderminute + tag + '.pkl') for tag in list_invalidTags]
        except:
            print('not removed')
            # print('could not remove tags in',list_invalidTags)

    def get_replace_tags_folder(self,folder,tag2replace):
        # print(folder)
        result={}
        for oldtag,newtag in zip(tag2replace['oldtag'],tag2replace['newtag']):
            try:
                os.rename(folder + oldtag+'.pkl',folder+newtag+'.pkl')
                result[oldtag]='replace by ' + newtag
            except:
                result[oldtag]=' not in folder'
        return result

    def get_createnewtags_folder(self,folder,alltagsversion):
        # print(folder)
        df = pd.Series(name='value')
        df_tagAdded={}
        for tag in alltagsversion:
            tagpkl=folder + tag + '.pkl'
            if os.path.exists(tagpkl):
                df_tagAdded[tag] = False
            else:
                df.to_pickle(folder + tag + '.pkl')
                df_tagAdded[tag] = True
        return df_tagAdded

    ###################
    #       GRAPHS    #
    ###################
    def show_map_of_compatibility(self,binaire=False,zmax=None):
        testdf=self.map_missingTags_len.T
        if zmax is None:
            zmax = testdf.max().max()
        reverse_scale=True
        # testdf=testdf.applymap(lambda x:np.random.randint(0,zmax))
        if binaire:
            testdf=testdf.applymap(lambda x:1 if x==0 else 0)
            zmax=1
            reverse_scale=False

        fig=go.Figure(go.Heatmap(z=testdf,x=['v' + k for k in testdf.columns],
            y=testdf.index,colorscale='RdYlGn',reversescale=reverse_scale,
            zmin=0,zmax=zmax))
        fig.update_xaxes(side="top",tickfont_size=35)
        fig.update_layout(font_color="blue",font_size=15)
        fig.show()
        return fig

    def show_nbFolder(self):
        dfshow = self.df_nbTagsFolder
        dfshow.columns=['nombre tags']
        dfshow.index=[self.totime(x) for x in dfshow.index]
        fig = px.line(dfshow,x=dfshow.index,y='nombre tags')
        fig.show()
        return fig

    def show_map_presenceTags(self,tags):
        dfshow = self.map_presenceTags[tags]
        dfshow=dfshow.astype(int)
        fig=go.Figure(go.Heatmap(z=dfshow,x=dfshow.columns,
                        y=dfshow.index,colorscale='RdYlGn',reversescale=False,
                        zmin=0,zmax=1))
        fig.update_xaxes(side="top",tickfont_size=10)
        fig.update_layout(font_color="blue",font_size=15)
        fig.show()
        return fig
class VersionManager_minutely(VersionManager):
    #######################
    # GENERATE DATAFRAMES #
    #######################
    def load_nbTags_folders(self):
        # get_lentags=lambda x:len(self.fs.listfiles_folder(x))
        df_nbtags=self.streamer.actionMinutes_pooled(self.tmin,self.tmax,self.folderData,self.get_lentags)
        return pd.DataFrame.from_dict(df_nbtags,orient='index')

    def load_missingTags_versions(self,period=None,pool=True):
        '''-period : [tmin,tmax] timestamps'''
        map_missingTags = self._compute_all_minutefolders(self.get_missing_tags_versions,period=period)
        map_missingTags = pd.DataFrame(map_missingTags).T
        map_missingTags_len = map_missingTags.applymap(lambda x:len(x))
        return map_missingTags,map_missingTags_len

    def load_presenceTags(self,period=None,frequence='daily'):
        if frequence=='daily':
            return self._compute_all_minutefolders(self.get_presenceTags_folder,period=period)
        elif frequence=='minutely':
            return self._compute_all_minutefolders(self.get_presenceTags_folder,period=period)

    def _compute_all_minutefolders(self,function,*args,period=None,pool=True):
        '''-period : [tmin,tmax] timestamps'''
        if period is None:
            tmin = self.tmin
            tmax = self.tmax
        else :
            tmin,tmax=period
        if tmax - tmin -dt.timedelta(days=2)<pd.Timedelta(seconds=0):
            pool=False
        df = self.streamer.actionMinutes_pooled(tmin,tmax,self.folderData,function,*args,pool=pool)
        # print(df)
        df = pd.DataFrame(df).T
        df.index=[self.totime(x) for x in df.index]
        return df

    def make_it_compatible_with_renameMap(self,map_renametag,period):
        ## from one version to an adjacent version (next or last):
        ## get transition rules
        # self.getCorrectVersionCorrespondanceSheet(transition)
        ## get the corresponding map of tags that should be renamed
        ## rename tags that should be renamed
        '''map_renametag :
            - should be a dataframe with columns ['oldtag','newtag']
            - should have None values in oldtag column for brand newtags
            - should have None values in newtag column for deleted tags
            '''
        tag2replace = map_renametag[map_renametag.apply(lambda x:not x['oldtag']==x['newtag'] and not x['oldtag'] is None and not x['newtag'] is None,axis=1)]
        print()
        print('MAP OF TAGS TO REPLACE '.rjust(75))
        print(tag2replace)
        print()
        replacedmap=self._compute_all_minutefolders(self.get_replace_tags_folder,tag2replace,period=period)
        print()
        print('MAP OF REPLACED TAGS '.rjust(75))
        print(replacedmap)
        return replacedmap

class VersionManager_daily(VersionManager):
    def __init__(self,*args,**kwargs):
        VersionManager.__init__(self,*args,**kwargs)
        self.streamer.actiondays(self.tmin,self.tmax,self.folderData,self.streamer.create_dayfolder,pool=False)

    #######################
    # GENERATE DATAFRAMES #
    #######################
    def _compute_all_dayfolders(self,function,*args,period=None,pool=False):
        '''-period : [tmin,tmax] timestamps'''
        if period is None:
            tmin = self.tmin
            tmax = self.tmax
        else :
            tmin,tmax=period
        if tmax - tmin - dt.timedelta(days=20)<pd.Timedelta(seconds=0):
            pool=False
        df = self.streamer.actiondays(tmin,tmax,self.folderData,function,*args,pool=pool)
        # print(df)
        df = pd.DataFrame(df).T
        df.index=[pd.Timestamp(x,tz='CET') for x in df.index]
        return df

    def load_nbTags_folders(self):
        df_nbtags=self.streamer.actiondays(self.tmin,self.tmax,self.folderData,self.get_lentags,pool=False)
        return pd.DataFrame.from_dict(df_nbtags,orient='index')

    def load_missingTags_versions(self,period=None,pool=False):
        '''-period : [tmin,tmax] timestamps'''
        map_missingTags = self._compute_all_dayfolders(self.get_missing_tags_versions,period=period,pool=pool)
        map_missingTags = pd.DataFrame(map_missingTags).T.sort_index()
        map_missingTags_len = map_missingTags.applymap(lambda x:len(x))
        return map_missingTags,map_missingTags_len

    def load_presenceTags(self,period=None,pool=False):
        return self._compute_all_dayfolders(self.get_presenceTags_folder,period=period,pool=pool)

    ###########################
    # COMPATIBILITY FUNCTIONS #
    ###########################
    def make_it_compatible_with_renameMap(self,map_renametag,period):
        ## from one version to an adjacent version (next or last):
        ## get transition rules
        # self.getCorrectVersionCorrespondanceSheet(transition)
        ## get the corresponding map of tags that should be renamed
        ## rename tags that should be renamed
        '''map_renametag :
            - should be a dataframe with columns ['oldtag','newtag']
            - should have None values in oldtag column for brand newtags
            - should have None values in newtag column for deleted tags
            '''
        tag2replace = map_renametag[map_renametag.apply(lambda x:not x['oldtag']==x['newtag'] and not x['oldtag'] is None and not x['newtag'] is None,axis=1)]
        print()
        print('MAP OF TAGS TO REPLACE '.rjust(75))
        print(tag2replace)
        print()
        replacedmap=self._compute_all_dayfolders(self.get_replace_tags_folder,tag2replace,period=period)
        print()
        print('MAP OF REPLACED TAGS '.rjust(75))
        print(replacedmap)
        return replacedmap

    def create_emptytags_version(self,period,dfplc):
        ## add tags as emptydataframes in folder if they are missing
        print('---------------------------------------------------------------')
        print();print();print()
        alltags = list(dfplc[dfplc.DATASCIENTISM==True].index)
        map_createTags   = self._compute_all_dayfolders(self.get_createnewtags_folder,alltags,period=period)
        return map_createTags
