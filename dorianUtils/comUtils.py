# import importlib
import datetime as dt, time, pytz
from time import sleep
import os,re,threading,struct, glob, pickle,struct
import numpy as np, pandas as pd
import psycopg2
import threading
from multiprocessing import Pool
import traceback
from dorianUtils.utilsD import Utils

# #######################
# #      BASIC Utils    #
# #######################
# basic utilities for Streamer and DumpingClientMaster
class EmptyClass():pass

class FileSystem():
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

class SetInterval:
    '''demarre sur un multiple de interval.
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
# basic utilities for Streamer and DumpingClientMaster
class Device():
    ''' for inheritance :
        - a function <loadPLC_file> should be written to load the data frame of info on tags.
        - a function <collectData> should be written  to collect data from the device.
        - a function <connectDevice> to connect to the device.
    '''
    def __init__(self,device_name):
        self.fs = FileSystem()
        self.device_name = device_name
        self.isConnected = True
        now = dt.datetime.now().astimezone()
        from dateutil.tz import tzlocal
        self.local_tzname = now.tzinfo.tzname(now)
        self.utils= Utils()
        self.dataTypes = {
          'REAL':'float',
          'BOOL':'bool',
          'WORD':'int',
          'DINT':'int',
          'INT':'int',
          'STRING(40)':'str'
        }
        self.loadPLC_file()
        self.allTags = list(self.dfPLC.index)
        self.listUnits = self.dfPLC.UNITE.dropna().unique().tolist()
        self.collectingTimes={}
        self.insertingTimes={}

    def checkConnection(self):
        if not self.isConnected:
            print('+++++++++++++++++++++++++++')
            print(dt.datetime.now(tz=pytz.timezone(self.local_tzname)))
            print('try new connection ...')
            try:
                self.connectDevice()
                print('connexion established again.')
                self.isConnected=True
            except Exception:
                print(dt.datetime.now().astimezone().isoformat() + '''--> problem connecting to
                                                device with endpointUrl''' + self.endpointUrl + '''
                                                on port ''' + str(self.port))
                print('sleep for ' + ' seconds')
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
            print('problem connecting to database ',self.dbParameters )
            return
        cur  = dbconn.cursor()
        start=time.time()
        ts = dt.datetime.now(tz=pytz.timezone(self.local_tzname))
        if self.isConnected:
            try :
                data = self.collectData(*args)
                # print(data)
            except:
                print('souci connexion at ' + ts.isoformat())
                self.isConnected = False
                print('waiting for the connexion to be re-established...')
            self.collectingTimes[dt.datetime.now(tz=pytz.timezone(self.local_tzname)).isoformat()] = (time.time()-start)*1000
            for tag in data.keys():
                sqlreq = "insert into realtimedata (tag,value,timestampz) values ('"
                value = data[tag][0]
                if value==None:
                    value = 'null'
                value=str(value)
                sqlreq+= tag +"','" + value + "','" + data[tag][1]  + "');"
                sqlreq=sqlreq.replace('nan','null')
                cur.execute(sqlreq)
            self.insertingTimes[dt.datetime.now(tz=pytz.timezone(self.local_tzname)).isoformat()]=(time.time()-start)*1000
            dbconn.commit()
        cur.close()
        dbconn.close()

    def getUsefulTags(self,usefulTag):
        category = self.usefulTags.loc[usefulTag]
        return self.getTagsTU(category.Pattern,category.Unit)

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

    def createRandomInitalTagValues(self):
        valueInit={}
        for tag in self.allTags:
            tagvar=self.dfPLC.loc[tag]
            if tagvar.DATATYPE=='STRING(40)':
                valueInit[tag] = 'STRINGTEST'
            else:
                valueInit[tag] = np.random.randint(tagvar.MIN,tagvar.MAX)
        return valueInit

from pymodbus.client.sync import ModbusTcpClient as ModbusClient
import xml.etree.ElementTree as ET
class ModeBusDevice(Device):
    '''dfInstr should be loaded with loaddfInstr before calling this constructor'''
    def __init__(self,device_name,ipdevice,port,confFolder,plc_dict=None):
        self.ip     = ipdevice
        self.port   = int(port)
        self.confFolder = confFolder
        self.device_name=device_name
        if not plc_dict is None:
            self.file_plc = self.confFolder + 'plc_' + device_name + plc_dict['version'] + '.csv'
            self.file_instr=self.confFolder + 'dfInstr_' + device_name + plc_dict['version']+'.pkl'
            self.build_plc_fromDevice(plc_dict)
        Device.__init__(self,device_name)
        self.loaddfInstr()
        self.allTCPid = list(self.dfInstr.addrTCP.unique())
        self.client = ModbusClient(host=self.ip,port=self.port)

    def build_plc_fromDevice(self,plc_dict):
        print('building PLC configuration file of ' + self.device_name  +' from dfInstr')
        dfInstr=self.loaddfInstr()
        units = {'kW':'JTW','kWh':'JTWH','kVA':'JTVA','kvar':'JTVar','kvarh':'JTVarH','kVAh':'JTVAH'}
        tags  = {}
        variables=plc_dict['variables']
        compteurs=plc_dict['compteurs']
        for t in dfInstr.index:
            currentTag = dfInstr.loc[t]
            variable = currentTag['description']
            fullCompteurName = compteurs.loc[currentTag['point de comptage']]
            if variable not in list(variables.index):
                print('variable ',variable, 'not describe in compteurs.ods/variables')
                # print('         exit        ')
                # print('=========================')
                print('')
                # sys.exit()
            else:
                unit = units[currentTag['unit']]
                description = fullCompteurName['description'] + ' - ' + variables.loc[variable,'description']
                tag     = fullCompteurName.fullname + '-' + currentTag['description'] + '-' + unit
                tags[tag] = {'DESCRIPTION' :description,'UNITE':unit}
                dfInstr.loc[t,'tag'] = tag
        dfplc = pd.DataFrame.from_dict(tags).T
        dfplc.index.name  = 'TAG'
        dfplc['MIN']      = -200000
        dfplc['MAX']      = 200000
        dfplc['DATATYPE'] = 'REAL'
        dfplc['DATASCIENTISM'] = True
        dfplc['PRECISION'] = 0.01
        dfplc['FREQUENCE_ECHANTILLONNAGE'] = 5
        dfplc['VAL_DEF'] = 0
        dfplc.to_csv(self.file_plc)
        print()
        print(self.file_plc +' saved.')
        dfInstr = dfInstr[~dfInstr['tag'].isna()].set_index('tag')
        pickle.dump(dfInstr,open(self.file_instr,'wb'))
        print(self.file_instr +' saved.')
        print('=======================================')
        print('')

    def loadPLC_file(self):
        patternPLC=self.confFolder + 'plc*' + self.device_name
        listPLC = glob.glob(patternPLC + '*.pkl')
        if len(listPLC)<1:
            listPLC_csv = glob.glob(patternPLC+'*.csv')
            plcfile = listPLC_csv[0]
            print(plcfile,' is read and converted into .pkl')
            dfPLC = pd.read_csv(plcfile,index_col=0)
            dfPLC = dfPLC[dfPLC.DATASCIENTISM]
            pickle.dump(dfPLC,open(plcfile[:-4]+'.pkl','wb'))
            listPLC = glob.glob(patternPLC + '*.pkl')
        self.file_plc = listPLC[0]
        self.dfPLC = pickle.load(open(self.file_plc,'rb'))

    def _makeDfInstrUnique(self,dfInstr):
        uniqueDfInstr = []
        for tag in dfInstr['id'].unique():
            dup=dfInstr[dfInstr['id']==tag]
            ### privilege on IEEE754 strcuture if duplicates
            rowFloat = dup[dup['type']=='IEEE754']
            if len(rowFloat)==1:
                uniqueDfInstr.append(rowFloat)
            else :
                uniqueDfInstr.append(dup.iloc[[0]])
        uniqueDfInstr=pd.concat(uniqueDfInstr).set_index('id')
        return uniqueDfInstr

    def getSizeOf(self,typeVar,f=1):
        if typeVar == 'IEEE754':return 2*f
        elif typeVar == 'INT64': return 4*f
        elif typeVar == 'INT32': return 2*f
        elif typeVar == 'INT16': return 1*f
        elif typeVar == 'INT8': return f/2

    def _findInstrument(self,meter):
        df=[]
        for var in meter.iter('var'):
            df.append([var.find('varaddr').text,
                        int(var.find('varaddr').text[:-1],16),
                        var.find('vartype').text,
                        self.getSizeOf(var.find('vartype').text,1),
                        self.getSizeOf(var.find('vartype').text,2),
                        var.find('vardesc').text,
                        var.find('scale').text,
                        var.find('unit').text])
        df = pd.DataFrame(df)
        df.columns=['adresse','intAddress','type','size(mots)','size(bytes)','description','scale','unit']
        df['addrTCP']=meter.find('addrTCP').text
        df['point de comptage']=meter.find('desc').text
        return df

    def _findInstruments(self,xmlpath):
        tree = ET.parse(xmlpath)
        root = tree.getroot()
        dfs=[]
        for meter in root.iter('meter'):
            dfs.append(self._findInstrument(meter))
        df=pd.concat(dfs)
        # tmp = df.loc[:,['point de comptage','description']].sum(axis=1)
        # df['id']=[re.sub('\s','_',k) for k in tmp]
        df['id']=[re.sub('[\( \)]','_',k) + '_' + l for k,l in zip(df['description'],df['point de comptage'])]
        # df=df[df['type']=='INT32']
        df['addrTCP'] = pd.to_numeric(df['addrTCP'],errors='coerce')
        df['scale'] = pd.to_numeric(df['scale'],errors='coerce')
        # df=df.set_index('adresse')
        # df=df[df['scale']==0.1]

        return df

    def decodeRegisters(self,regs,block,bo='='):
        d={}
        firstReg = block['intAddress'][0]
        for tag in block.index:
            row = block.loc[tag]
            #### in order to make it work even if block is not continuous.
            curReg = int(row['intAddress'])-firstReg
            if row.type == 'INT32':
                # print(curReg)
                valueShorts = [regs[curReg+k] for k in [0,1]]
                # conversion of 2 shorts(=DWORD=word) into long(=INT32)
                value = struct.unpack(bo + 'i',struct.pack(bo + "2H",*valueShorts))[0]
                # curReg+=2
            if row.type == 'IEEE754':
                valueShorts = [regs[curReg+k] for k in [0,1]]
                value = struct.unpack(bo + 'f',struct.pack(bo + "2H",*valueShorts))[0]
                # curReg+=2
            elif row.type == 'INT64':
                valueShorts = [regs[curReg+k] for k in [0,1,2,3]]
                value = struct.unpack(bo + 'q',struct.pack(bo + "4H",*valueShorts))[0]
                # curReg+=4
            d[tag]=[value*row.scale,dt.datetime.now().astimezone().isoformat()]
        return d

    def checkRegisterValueTag(self,tag,**kwargs):
        # self.connectDevice()
        tagid = self.dfInstr.loc[tag]
        regs  = self.client.read_holding_registers(tagid.intAddress,tagid['size(mots)'],unit=tagid.addrTCP).registers
        return self.decodeRegisters(regs,pd.DataFrame(tagid).T,**kwargs)

    def getPtComptageValues(self,unit_id,**kwargs):
        ptComptage = self.dfInstr[self.dfInstr['addrTCP']==unit_id].sort_values(by='intAddress')
        lastReg  = ptComptage['intAddress'][-1]
        firstReg = ptComptage['intAddress'][0]
        nbregs   = lastReg-firstReg + ptComptage['size(mots)'][-1]
        #read all registers in a single command for better performances
        regs = self.client.read_holding_registers(firstReg,nbregs,unit=unit_id).registers
        return self.decodeRegisters(regs,ptComptage,**kwargs)

    def connectDevice(self):
        return self.client.connect()

    def getModeBusRegistersValues(self,*args,**kwargs):
        d={}
        for idTCP in self.allTCPid:
            d.update(self.getPtComptageValues(unit_id=idTCP,*args,**kwargs))
        return d

    def quickmodebus2dbint32(self,conn,add):
        regs  = conn.read_holding_registers(add,2)
        return struct.unpack(bo + 'i',struct.pack(bo + "2H",*regs))[0]

    def collectData(self):
        data = self.getModeBusRegistersValues()
        return data

class ModeBusDeviceXML(ModeBusDevice):
    def loaddfInstr(self):
        self.file_xml  = glob.glob(self.confFolder+self.device_name + '*ModbusTCP*.xml')[0]
        patternDFinstr = self.confFolder + 'dfInstr*' + self.device_name+'*.pkl'
        listdfInstr    = glob.glob(patternDFinstr)
        if len(listdfInstr)==0:
            print('building dfInstr from '+ self.file_xml)
            try:
                dfInstr = self._findInstruments(self.file_xml)
                dfInstr = self._makeDfInstrUnique(dfInstr)
                self.dfInstr = dfInstr
            except:
                print('no xml file found in ',self.confFolder)
                raise SystemExit
        else :
            self.file_dfInstr = listdfInstr[0]
            self.dfInstr=pickle.load(open(self.file_dfInstr,'rb'))
        return self.dfInstr

        self.dfInstr = pickle.load(open(self.fileDfInstr,'rb'))


class ModeBusDeviceSingleRegisters(ModeBusDevice):
    def loaddfInstr(self):
        patternDFinstr=self.confFolder + 'dfInstr*' + self.device_name+'*.pkl'
        listdfInstr = glob.glob(patternDFinstr)
        if len(listdfInstr)==0:
            dfInstr=pd.DataFrame()
            dfInstr['adresse']     = [40525,40560]
            dfInstr['intAddress']  =[40525,40560]
            dfInstr['type']        = ['INT32']*2
            dfInstr['size(mots)']  = [2]*2
            dfInstr['size(bytes)'] = [4]*2
            dfInstr['description'] = ['kW','kWh']
            dfInstr['scale']       = [1/1000,1/10]
            dfInstr['unit']        = ['kW','kWh']
            dfInstr['addrTCP']     = [1]*2
            dfInstr['point de comptage'] = ['centrale SLS 80kWc']*2
            dfInstr.index = dfInstr['point de comptage']+'-'+dfInstr['description']
            self.dfInstr = dfInstr
        else :
            self.file_dfInstr = listdfInstr[0]
            self.dfInstr=pickle.load(open(self.file_dfInstr,'rb'))
        return self.dfInstr

    def getModeBusRegistersValues(self):
        data={}
        for tag in self.dfInstr.index:
            ptComptage = self.dfInstr.loc[[tag]]
            val = self.dfInstr.loc[tag]
            regs = self.client.read_holding_registers(val['intAddress'],val['size(mots)'],unit=val['addrTCP']).registers
            data.update(self.decodeRegisters(regs,ptComptage,bo='!'))
        return data


class Opcua(Device):
    def __init__(self,folderPkl,confFolder,dbParameters,
                    endpointUrl,port=4843,nameSpace="ns=4;s=GVL.",**kwargs):
        Device.__init__(self,folderPkl,confFolder,dbParameters,**kwargs)
        self.endpointUrl = endpointUrl
        self.ip   = endpointUrl
        self.port = port
        self.nameSpace   = nameSpace
        self.client      = opcua.Client(endpointUrl)
        self.certif_path = self.confFolder + 'my_cert.pem'
        self.key_path    = self.confFolder + 'my_private_key.pem'
        ####### load nodes
        self.nodesDict  = {t:self.client.get_node(self.nameSpace + t) for t in self.allTags}
        self.nodes      = list(self.nodesDict.values())

    def loadPLC_file(self):
        listPLC = glob.glob(self.confFolder + '*Instrum*.pkl')
        if len(listPLC)<1:
            listPLC_xlsm = glob.glob(self.confFolder + '*Instrum*.xlsm')
            plcfile=listPLC_xlsm[0]
            print(plcfile,' is read and converted in .pkl')
            dfPLC = pd.read_excel(plcfile,sheet_name='FichierConf_Jules',index_col=0)
            dfPLC = dfPLC[dfPLC.DATASCIENTISM]
            pickle.dump(dfPLC,open(plcfile[:-5]+'.pkl','wb'))
            listPLC = glob.glob(self.confFolder + '*Instrum*.pkl')

        self.file_plc = listPLC[0]
        self.dfPLC = pickle.load(open(self.file_plc,'rb'))

    def connectDevice(self):
        self.client.connect()

    def collectData(self,nodes):
        values = self.client.get_values(nodes.values())
        ts = dt.datetime.now().astimezone().isoformat()
        data = {tag:[val,ts] for tag,val in zip(nodes.keys(),values)}
        return data


class Meteo_Client():
    def __init__(self,city):
        self.cities = pd.DataFrame({'leCheylas':{'lat' : '45.387','lon':'6.0000'},
        'champet':{'lat':'45.466393','lon':'5.656045'},
        'stJoachim':{'lat':'47.382074','lon':'-2.196835'}})
        self.baseurl = 'https://api.openweathermap.org/data/2.5/'
        self.apitoken = '79e8bbe89ac67324c6a6cdbf76a450c0'
        # apitoken = '2baff0505c3177ad97ec1b648b504621'# Marc
        self.device_name='meteo'
        self.t0 = dt.datetime(1970,1,1,1,0).astimezone(tz = pytz.timezone('Etc/GMT-3'))
    # baseFolder = '/home/dorian/data/sylfenData/'

    def get_data(self):
        return pd.concat([self.get_dfMeteo(city) for city in self.cities],axis=1)

    def get_dfMeteo(self,city):
        url = self.baseurl + 'weather?lat='+self.gps.lat+'&lon=' + gps.lon + '&units=metric&appid=' + self.apitoken
        response = urllib.request.urlopen(url)
        data = json.loads(response.read())
        t0 = dt.datetime(1970,1,1,1,0).astimezone(tz = pytz.timezone('Etc/GMT-3'))
        dfmain=pd.DataFrame(data['main'],index=[t0 + dt.timedelta(seconds=data['dt'])])
        dfmain['clouds']=data['clouds']['all']
        dfmain['visibility']=data['visibility']
        dfmain['main']=data['weather'][0]['description']
        dfwind=pd.DataFrame(data['wind'],index=[t0 + dt.timedelta(seconds=data['dt'])])
        dfwind.columns = [self.city + '_wind_' + k  for k in dfwind.columns]
        dfmain.columns = [self.city + '_' + k  for k in dfmain.columns]
        return pd.concat([dfmain,dfwind],axis=1)

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
# #  DUMPING CLIENTS    #
# #######################
class Streamer():
    '''Streamer enables to perform action on parked Day/Hour/Minute folders.
    It comes with basic functions like loaddataminute/createminutefolder/parktagminute.'''
    def __init__(self):
        self.fs = FileSystem()
        self.dayFolderFormat='%Y-%m-%d'
        now = dt.datetime.now().astimezone()
        self.local_tzname = now.tzinfo.tzname(now)

    def createminutefolder(self,folderminute):
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

    def deleteminutefolder(self,folderminute):
        # print(folderminute)
        if os.path.exists(folderminute):
            os.rmdir(folderminute)
            return folderminute +' deleted '
        else :
            return folderminute +' does not exist '

    def loaddataminute(self,folderminute,tag):
        if os.path.exists(folderminute):
            # print(folderminute)
            return pickle.load(open(folderminute + tag + '.pkl', "rb" ))
        else :
            print('no folder : ',folderminute)
            return []

    def foldersaction(self,t0,t1,folderPkl,actionminute,pooldays=False,**kwargs):
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
        folderDay0 = folderPkl + t0.strftime(self.dayFolderFormat) + '/'
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
                days = [(t1-dt.timedelta(days=d)).strftime(self.dayFolderFormat) for d in daysBetween]
                dfs.append(actionDays(days,folderPkl,pooldays))
                #last day
                folderDayLast = folderPkl + t1.strftime(self.dayFolderFormat) + '/'
                #first hours of last day
                if not t1.hour==0:
                    dfs.append(actionHours(range(0,t1.hour),folderDayLast))
                #last hour
                folderHour11 = folderDayLast + '{:02d}'.format(t1.hour) + '/'
                dfs.append(actionMinutes(range(0,t1.minute),folderHour11))
        return self.fs.flatten(dfs)

    def parktagminute(self,folderminute,dftag):
        #get only the data for that minute
        tag = dftag.tag[0]
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
        res['diff ms']='{:.2f}'.format((time.time()-start)*1000)
        res['diff len']=len(s1)

        start = time.time()
        s2=self.staticCompressionTag(s=s,precision=prec,method='dynamic')
        res['dynamic ms']='{:.2f}'.format((time.time()-start)*1000)
        res['dynamic len']=len(s2)

        start = time.time()
        s3=self.staticCompressionTag(s=s,precision=prec,method='reduce')
        res['reduce ms']='{:.2f}'.format((time.time()-start)*1000)
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

class Configurator(Streamer):
    def __init__(self,folderPkl,confFolder,dbParameters,
                    dbTimeWindow = 60*10,parkingTime=60*1):
        '''
        - dbTimeWindow : how many minimum seconds before now are in the database
        - parkingTime : how often data are parked and db flushed in seconds
        '''
        Streamer.__init__(self)
        self.folderPkl = folderPkl##in seconds
        self.confFolder = confFolder##in seconds
        self.dbTimeWindow = dbTimeWindow##in seconds
        self.parkingTime = parkingTime##seconds
        listFiles = glob.glob(self.confFolder + '*compteurs*.ods')
        self.compteurFile=listFiles[0]
        self.v_compteur=re.findall('_v\d+',self.compteurFile)[0]
        self.df_devices = pd.read_excel(self.compteurFile,index_col=0,sheet_name='devices')
        self.variables = pd.read_excel(self.compteurFile,index_col=0,sheet_name='variables')
        self.compteurs = pd.read_excel(self.compteurFile,index_col=0,sheet_name='compteurs')
        dictCat = self.df_devices.category.to_dict()
        self.compteurs['fullname']=list(self.compteurs.reset_index().apply(lambda x:dictCat[x['device']]+'-'+ x['pointComptage']+'-',axis=1))
        for device in [d for  d in self.df_devices.index if not d=='meteo']:
            catCompteur = self.compteurs.loc[self.compteurs.device==device].reset_index()
            fullnames=dictCat[device] + catCompteur.index.to_series().apply(lambda x:'{:x}'.format(x+1).zfill(8))+'-'+catCompteur['pointComptage']
            self.compteurs.loc[self.compteurs.device==device,'fullname'] =list(fullnames)
        self.devices = EmptyClass()
        for device_name in self.df_devices.index[self.df_devices.statut=='actif']:
            device=self.df_devices.loc[device_name]
            # print(self.df_devices)
            plc_dict={
            'variables':self.variables[self.variables.device==device_name],
            'compteurs':self.compteurs[self.compteurs.device==device_name],
            'version':self.v_compteur
            }
            print(device_name)
            if device['protocole']=='modebus_xml':
                device=ModeBusDeviceXML(device_name,device['IP'],device['port'],self.confFolder,plc_dict=plc_dict)
            elif device['protocole']=='modebus_single':
                device=ModeBusDeviceSingleRegisters(device_name,device['IP'],device['port'],self.confFolder,plc_dict=plc_dict)
            elif device['protocole']=='Meteo_Client':
                device=Meteo_Client(device_name)
            elif device['protocole']=='opcua':
                device=Opcua()
            setattr(self.devices,device_name,device)
        self.dbParameters=dbParameters
        self.parkedDays = [k.split('/')[-1] for k in glob.glob(self.folderPkl+'/*')]
        self.parkedDays.sort()
        try :
            self.usefulTags = pd.read_csv(self.confFolder+'/predefinedCategories.csv',index_col=0)
            self.usefulTags.index = self.utils.uniformListStrings(list(self.usefulTags.index))
        except :
            self.usefulTags = pd.DataFrame()
        dfplcs=[]
        for device_name,device in self.devices.__dict__.items():
            # print(device)
            dfplc=device.dfPLC
            dfplc['device']=device
            dfplcs.append(dfplc)
        self.dfplc=pd.concat(dfplcs)

class SuperDumper(Configurator):
    def __init__(self,*args,**kwargs):
        Configurator.__init__(self,*args,**kwargs)
        self.streaming = Streamer()
        self.fs = FileSystem()
        self.logsFolder='/home/dorian/sylfen/exploreSmallPower/src/logs/'
        # self.timeOutReconnexion = 3
        # self.reconnectionThread = SetInterval(self.timeOutReconnexion,self.checkConnection)
        # self.reconnectionThread.start()
        self.connReq = ''.join([k + "=" + v + " " for k,v in self.dbParameters.items()])
        self.freq = 5
        self.dumpIntervalInit,self.dumpInterval = {},{}
        self.alltags=list(self.dfplc.index)

        for device_name,device in self.devices.__dict__.items():
            self.dumpIntervalInit[device_name] = SetInterval(self.freq,device.insert_intodb,self.dbParameters)
            self.dumpInterval[device_name] = SetInterval(self.freq,device.insert_intodb,self.dbParameters)
        self.parkInterval = SetInterval(self.parkingTime,self.parkallfromdb)
    # ########################
    #       WORKING WITH     #
    #    POSTGRES DATABASE   #
    # ########################
    def parkallfromdb(self):
        listTags=self.alltags
        start = time.time()
        timenow = pd.Timestamp.now(tz=self.local_tzname)
        t1 = timenow-dt.timedelta(seconds=self.dbTimeWindow)

        ### read database
        dbconn = self.connect2db()
        sqlQ ="select * from realtimedata where timestampz < '" + t1.isoformat() +"'"
        # df = pd.read_sql_query(sqlQ,dbconn,parse_dates=['timestampz'],dtype={'value':'float'})
        df = pd.read_sql_query(sqlQ,dbconn,parse_dates=['timestampz'])
        print(timenow.strftime('%H:%M:%S,%f') + ''' ===> database read in {:.2f} milliseconds'''.format((time.time()-start)*1000))
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
        self.createFolders(t0,t1)

        #################################
        #           park now            #
        #################################
        start=time.time()

        # with Pool() as p:
        #     dfs=p.starmap(self.parktagfromdb,[(t0,t1,df,tag) for tag in listTags])
        dfs=[]
        for tag in listTags:
            dfs.append(self.parktagfromdb(t0,t1,df,tag))
        print(timenow.strftime('%H:%M:%S,%f') + ''' ===> database parked in {:.2f} milliseconds'''.format((time.time()-start)*1000))
        self.parkingTimes[timenow.isoformat()] = (time.time()-start)*1000
        # #FLUSH DATABASE
        start=time.time()
        self.flushdb(t1.isoformat())
        return dfs

    def connect2db(self):
        return psycopg2.connect(self.connReq)

    def flushdb(self,t,full=False):
        dbconn = psycopg2.connect(self.connReq)
        cur  = dbconn.cursor()
        if full:
            cur.execute("DELETE from realtimedata;")
        else :
            # cur.execute("DELETE from realtimedata where timestampz < NOW() - interval '" + str(self.dbTimeWindow) + "' SECOND;")
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

    def createFolders(self,t0,t1):
        return self.streaming.foldersaction(t0,t1,self.folderPkl,self.streaming.createminutefolder)

    def parktagfromdb(self,t0,t1,df,tag,compression='reduce'):
        dftag = df[df.tag==tag].set_index('timestampz')
        dftag.index=dftag.index.tz_convert(self.local_tzname)
        if dftag.empty:
            return dftag
        # print(tag + ' : ',self.dfPLC.loc[tag,'DATATYPE'])
        if compression in ['reduce','diff','dynamic'] and not self.dfPLC.loc[tag,'DATATYPE']=='STRING(40)':
            precision = self.dfPLC.loc[tag,'PRECISION']
            dftag = dftag.replace('null',np.nan)
            dftag.value = dftag.value.astype(self.dataTypes[self.dfPLC.loc[tag,'DATATYPE']])
            dftag.value = self.streaming.staticCompressionTag(dftag.value,precision,compression)
        return self.streaming.foldersaction(t0,t1,self.folderPkl,self.streaming.parktagminute,dftag=dftag)

    def parkallfromdb(self):
        listTags = self.alltags
        start = time.time()
        timenow = pd.Timestamp.now(tz=self.local_tzname)
        t1 = timenow-dt.timedelta(seconds=self.dbTimeWindow)

        ### read database
        dbconn = self.connect2db()
        sqlQ ="select * from realtimedata where timestampz < '" + t1.isoformat() +"'"
        # df = pd.read_sql_query(sqlQ,dbconn,parse_dates=['timestampz'],dtype={'value':'float'})
        df = pd.read_sql_query(sqlQ,dbconn,parse_dates=['timestampz'])
        print(timenow.strftime('%H:%M:%S,%f') + ''' ===> database read in {:.2f} milliseconds'''.format((time.time()-start)*1000))
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
        self.createFolders(t0,t1)

        #################################
        #           park now            #
        #################################
        start=time.time()

        # with Pool() as p:
        #     dfs=p.starmap(self.parktagfromdb,[(t0,t1,df,tag) for tag in listTags])
        dfs=[]
        for tag in self.allTags:
            dfs.append(self.parktagfromdb(t0,t1,df,tag))
        print(timenow.strftime('%H:%M:%S,%f') + ''' ===> database parked in {:.2f} milliseconds'''.format((time.time()-start)*1000))
        self.parkingTimes[timenow.isoformat()] = (time.time()-start)*1000
        # #FLUSH DATABASE
        start=time.time()
        self.flushdb(t1.isoformat())
        return dfs

    def exportdb2csv(self,dbParameters,t0,t1,folder):
        start=time.time()
        ### read database
        dbconn=psycopg2.connect(''.join([k + "=" + v + " " for k,v in dbParameters.items()]))
        sqlQ ="select * from realtimedata where timestampz < '" + t1.isoformat() +"'"
        sqlQ +="and timestampz > '" + t0.isoformat() +"'"
        print(sqlQ)
        df = pd.read_sql_query(sqlQ,dbconn,parse_dates=['timestampz'])
        df=df[['tag','value','timestampz']]
        df['timestampz']=pd.to_datetime(df['timestampz'])
        df=df.set_index('timestampz')
        df.index=df.index.tz_convert('CET')
        df=df.sort_index()

        namefile=folder + 'realtimedata_'+t0.strftime('%Y-%m-%d')+'.pkl'
        # df.to_csv(namefile)
        pickle.dump(df,open(namefile,'wb'))
        print(pd.Timestamp.now().strftime('%H:%M:%S,%f') + ''' ===> database read in {:.2f} milliseconds'''.format((time.time()-start)*1000))
        # close connection
        dbconn.close()

    def parkalltagsDF(self,df,listTags=None,poolTags=True):
        if listTags is None : listTags = self.allTags
        #### create Folders
        t0 = df.index.min()
        t1 = df.index.max()
        self.createFolders(t0,t1)
        nbHours=int((t1-t0).total_seconds()//3600)
        for h in range(nbHours):
        # for h in range(1):
            tm1=t0+dt.timedelta(hours=h)
            tm2=tm1+dt.timedelta(hours=1)
            tm2=min(tm2,t1)
            dfloc=df[(df.index>tm1)&(df.index<tm2)]
            print('start for :', dfloc.index[-1])
            dfloc=dfloc.reset_index()
            start=time.time()
            if poolTags:
                with Pool() as p:
                    dfs=p.starmap(self.parktagfromdb,[(tm1,tm2,dfloc,tag) for tag in listTags])
            else:
                dfs=[]
                for tag in self.allTags:
                    dfs.append(self.parktagfromdb(tm1,tm2,dfloc,tag))
            print('done in {:.2f} s'.format((time.time()-start)))
    # ########################
    # GENERATE STATIC DATA
    # ########################
    def generateRandomParkedData(self,t0,t1,vol=1.5,listTags=None):
        valInits = self.createRandomInitalTagValues()
        if listTags==None:listTags=self.allTags
        valInits = {tag:valInits[tag] for tag in listTags}
        df = {}
        for tag,initval in valInits.items():
            tagvar = self.dfPLC.loc[tag]
            precision  = self.dfPLC.loc[tag,'PRECISION']
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
                # stag = self.streaming.staticCompressionTag(stag,precision,method='reduce')
                df[tag] = pd.DataFrame(stag).reset_index()
                df[tag].columns=['timestampz','value']
            df[tag]['tag'] = tag
            print(tag + ' generated')
        df=pd.concat(df.values(),axis=0)
        start = time.time()
        # df.timestampz = [t.isoformat() for t in df.timestampz]
        print('timestampz to str done in {:.2f} s'.format((time.time()-start)))
        df=df.set_index('timestampz')
        return df
    # ########################
    #   WORKING WITH BUFFER  #
    #       DICTIONNARY      #
    # ########################
    def dumpMonitoringBuffer(self):
        start=time.time()
        try :
            data = self.collectData()
            if not not self.dbParameters:
                dbconn = psycopg2.connect(self.connReq)
                cur  = dbconn.cursor()

            for tag in self.bufferData.keys():
                self.bufferData[tag].append(data[tag])
                ts = dt.datetime.now().isoformat()
                if not not self.dbParameters:
                    sqlreq = "insert into realtimedata (tag,value,timestampz) values ('" + tag + "',{:.2f},".format(data[tag][0]) +"'" + data[tag][1]  + "');"
                    cur.execute(sqlreq)
            if not not self.dbParameters:
                cur.close()
                dbconn.commit()
                dbconn.close()
        except :
            print('problem gathering data from device')

    def parkTag_buffer(self,tag,folderSave):
        df = pd.DataFrame()
        pklFile = folderSave + tag + '.pkl'
        df = pd.DataFrame(self.bufferData[tag],columns=['value','timestamp']).set_index('timestamp')
        with open(pklFile , 'wb') as f:
            pickle.dump(df, f)

    def park_all_buffer(self):
        start   = time.time()
        timenow = dt.datetime.now(tz=pytz.timezone(self.local_tzname))-dt.timedelta(minutes=1)
        folderDay = self.folderPkl + timenow.strftime(self.streaming.dayFolderFormat)+'/'
        if not os.path.exists(folderDay):os.mkdir(folderDay)
        folderHour = folderDay + timenow.strftime('%H/')
        if not os.path.exists(folderHour):os.mkdir(folderHour)
        folderMinute = folderHour + timenow.strftime('%M/')
        if not os.path.exists(folderMinute):os.mkdir(folderMinute)
        with Pool() as p:
            p.starmap(self.parkTag_buffer,[(tag,folderMinute) for tag in self.dfInstr['id']])

        #empty buffer
        self.bufferData={k:[] for k in self.dfInstr['id']}
        print(timenow.isoformat() + ' ===> data parked in {:.2f} milliseconds'.format((time.time()-start)*1000))

    # ########################
    #   CHECK ACQUISITION    #
    #       TIMES            #
    # ########################
    def checkTimes():
        dict2pdf = lambda d:pd.DataFrame.from_dict(d,orient='index').squeeze().sort_values()
        s_collect = dict2pdf(vmucDumpingClient.collectingTimes)
        s_insert  = dict2pdf(vmucDumpingClient.insertingTimes)

        p = 1. * np.arange(len(s_collect))
        ## first x axis :
        tr1 = go.Scatter(x=p,y=df,name='collectingTime',col=1,row=1)
        ## second axis
        tr2 = go.Scatter(x=p,y=df,name='collectingTime',col=1,row=2)
        title1='cumulative probability density '
        title2='histogramm computing times '
        # fig.update_layout(titles=)
    # ########################
    #   SCHEDULERS           #
    # ########################
    def start_dumping(self):
        ## start the schedulers at H:M:S:00 pétante while letting the database grows until it reaches timer size    ! #####
        now = dt.datetime.now().astimezone()
        # print(now)
        rab = 59-now.second
        time.sleep(1-now.microsecond/1000000)
        timer = rab
        print('start dumping at :')
        print(dt.datetime.now().astimezone())
        for device in self.dumpIntervalInit.keys():
            self.dumpIntervalInit[device].start()

        time.sleep(timer)
        print('start parking at :')
        print(dt.datetime.now().astimezone())
        ######## start parking first
        for device in self.dumpIntervalInit.keys():
            self.dumpIntervalInit[device].stop()
            self.dumpInterval[device].start()
        self.parkInterval.start()

    def stop_dumping():
        for device in devices.keys():
            dumpIntervalInit[device].stop()
            dumpInterval[device].stop()
            parkInterval[device].stop()
            vmucDumpingClient.reconnectionThread.stop()


# #######################
# #      VISU STREAMER  #
# #######################
import plotly.express as px
class StreamerVisualisationMaster():
    ''' can only be used with a children class inheritating from a class that has
    attributes and methods of Device.
    ex : class StreamVisuSpecial(ComConfigSpecial,StreamerVisualisationMaster)
    '''
    def __init__(self):
        self.streaming = Streamer()
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
        self.methods=methods

    def connect2db(self):
        return psycopg2.connect(''.join([k + "=" + v + " " for k,v in self.dbParameters.items()]))

    def loadparkedtag(self,t0,t1,tag):
        # print(tag)
        dfs = self.streaming.foldersaction(t0,t1,self.folderPkl,self.streaming.loaddataminute,tag=tag)
        if len(dfs)>0:
            return pd.concat(dfs)
        else:
            return pd.DataFrame()

    def processdf(self,df,rsMethod='forwardfill',rs='auto',timezone='CET',rmwindow='3000s'):
        if len(df)==0:
            return df
            #auto resample
        # remove duplicated index
        start=time.time()
        # return df
        df = df.dropna().pivot(values='value',columns='tag')
        print('pivot data in {:.2f} ms'.format((time.time()-start)*1000))
        if rs=='auto':
            totalPts = 10000
            ptCurve=totalPts/len(df.columns)
            deltat=(df.index[-1]-df.index[0]).total_seconds()//ptCurve+1
            rs = '{:.0f}'.format(deltat) + 's'
        # print(df)
        df.index = df.index.tz_convert(timezone)
        start=time.time()
        dtypes = self.dfPLC.loc[df.columns].DATATYPE.apply(lambda x:self.dataTypes[x]).to_dict()
        # df = df.dropna().astype(dtypes)
        df = df.astype(dtypes)
        if not rsMethod=='raw':
            df = eval(self.methods[rsMethod])
        print(rsMethod + ' data in {:.2f} ms'.format((time.time()-start)*1000))
        return df

    def _dfLoadparkedTags(self,listTags,timeRange,poolTags,*args,**kwargs):
        '''
        - timeRange:should be a vector of 2 datetimes
        '''
        if not isinstance(listTags,list):
            try:
                listTags=list(listTags)
            except:
                print('listTags is not a list')
                return pd.DataFrame()
        if len(listTags)==0:
            return pd.DataFrame()

        start=time.time()
        if poolTags:
            print('pooling the data...')
            with Pool() as p:
                dfs = p.starmap(self.loadparkedtag,[(timeRange[0],timeRange[1],tag) for tag in listTags])
        else:
            dfs = []
            for tag in listTags:
                dfs.append(self.loadparkedtag(timeRange[0],timeRange[1],tag))
        if len(dfs)==0:
            return pd.DataFrame()
        print('collecting parked tags done in {:.2f} ms'.format((time.time()-start)*1000))
        df = pd.concat(dfs).sort_index()
        print('finish loading the parked data in {:.2f} ms'.format((time.time()-start)*1000))
        start=time.time()
        df = self.processdf(df,*args,**kwargs)
        print('processing the data in {:.2f} ms'.format((time.time()-start)*1000))
        # if df.duplicated().any():
        #     print("==========================================")
        #     print("attention il y a des doublons dans les donnees parkes : ")
        #     print(df[df.duplicated(keep=False)])
        #     print("==========================================")
        #     df = df.drop_duplicates()
        return df

    def _dfLoadDataBaseTags(self,tags,timeRange,*args,**kwargs):
        '''
        - timeRange:should be a vector of 2 datetimes strings.
        '''
        dbconn = self.connect2db()
        if isinstance(tags,list):
            if len(tags)==0:
                print('no tags selected for database')
                return pd.DataFrame()

        sqlQ = "select * from realtimedata where tag in ('" + "','".join(tags) +"')"
        sqlQ += " and timestampz > '" + timeRange[0] + "'"
        sqlQ += " and timestampz < '" + timeRange[1] + "'"
        sqlQ +=";"
        # print(sqlQ)
        df = pd.read_sql_query(sqlQ,dbconn,parse_dates=['timestampz'])
        dbconn.close()
        if len(df)>0:
            if df.duplicated().any():
                print("attention il y a des doublons dans big brother : ")
                print(df[df.duplicated()])
                df = df.drop_duplicates()

            df.loc[df.value=='null','value']=np.nan
            df = df.set_index('timestampz')
            df = self.processdf(df,*args,**kwargs)
        return df

    def df_loadtagsrealtime(self,tags,timeRange,poolTags=False,*args,**kwargs):
        '''
        - timeRange:should be a vector of 2 datetimes strings.
        '''
        # print(tags,timeRange,poolTags,*args,**kwargs)
        start=time.time()
        df = self._dfLoadDataBaseTags(tags,timeRange,*args,**kwargs)
        print('finish loading and processing the database  in {:.2f} ms'.format((time.time()-start)*1000))
        # return df
        t0,t1 = [pd.Timestamp(t,tz=self.local_tzname) for t in timeRange]
        t1_max = pd.Timestamp.now(tz=self.local_tzname)- dt.timedelta(seconds=self.dbTimeWindow)

        t1=min(t1,t1_max)
        dfp = self._dfLoadparkedTags(tags,[t0,t1],poolTags,*args,**kwargs)
        # return dfp
        if len(df)>0:
            df = pd.concat([df,dfp])
        else:
            df = dfp
        return df.sort_index()

    def standardLayout(self,fig,ms=5,h=750):
        fig.update_yaxes(showgrid=False)
        fig.update_xaxes(title_text='')
        fig.update_traces(selector=dict(type='scatter'),marker=dict(size=ms))
        fig.update_layout(height=h)
        # fig.update_traces(hovertemplate='<b>%{y:.2f}')
        fig.update_traces(hovertemplate='     <b>%{y:.2f}<br>     %{x|%H:%M:%S,%f}')
        return fig

    def update_lineshape(self,fig,style='default'):
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

    def doubleMultiUnitGraph(self,df,*listtags,axSP=0.05):
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
        self.updatecolorAxes(fig)
        self.updatecolortraces(fig)
        self.standardLayout(fig,h=None)
        return fig
