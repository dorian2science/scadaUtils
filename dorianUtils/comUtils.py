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
# basic utilities for Streaming and DumpingClientMaster
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

class ComConfigMaster():
    def __init__(self,folderPkl,confFolder,dbParameters,
            dbTimeWindow = 60*10,parkingTime=60*1):
        '''
         - dbTimeWindow : how many minimum seconds before now are in the database
         - parkingTime : how often data are parked and db flushed in seconds
         '''
        self.folderPkl  = folderPkl
        self.confFolder = confFolder
        self.dbTimeWindow = dbTimeWindow##in seconds
        self.parkingTime = parkingTime##seconds
        self.dbParameters=dbParameters
        now = dt.datetime.now().astimezone()
        from dateutil.tz import tzlocal
        self.local_tzname = now.tzinfo.tzname(now)
        self.utils= Utils()
        self.loadPLC_file()
        self.allTags = list(self.dfPLC.index)
        self.listUnits = self.dfPLC.UNITE.dropna().unique().tolist()
        self.parkedDays = [k.split('/')[-1] for k in glob.glob(self.folderPkl+'/*')]
        self.parkedDays.sort()
        try :
            self.usefulTags = pd.read_csv(self.confFolder+'/predefinedCategories.csv',index_col=0)
            self.usefulTags.index = self.utils.uniformListStrings(list(self.usefulTags.index))
        except :
            self.usefulTags = pd.DataFrame()

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

class ModeBusConfigMaster(ComConfigMaster):
    import xml.etree.ElementTree as ET
    def __init__(self,folderPkl,confFolder,dbParameters,ipdevice,port,*args,**kwargs):
        ComConfigMaster.__init__(self,folderPkl,confFolder,dbParameters,*args,**kwargs)
        self.ip=ipdevice
        self.port=port
        self.allTags = dfInstr['id'].unique()
        self.fs = FileSystem()
        self.xmlfile = glob.glob(self.confFolder + '*dfInstr')[0]
        dfInstr = self._findInstruments(xmlfile)
        dfInstr = self._makeDfInstrUnique()
        pickle.dump(dfInstr,open(self.fs.getParentDir(xmlfile) + 'dfInstr.pkl','wb'))

    def loaddfInstr(self):
        try:
            if not os.path.exists(self.confFolder + 'dfInstr.pkl'):
                xmlfile = glob.glob(self.confFolder+'*ModbusTCP*.xml')[0]
                ModeBusXMLInstrument(xmlfile)
            self.dfInstr = pickle.load(open(self.confFolder+'dfInstr.pkl','rb'))
        except:
            print('no xml file found in ',self.confFolder)
            raise SystemExit

    def _makeDfInstrUnique(self):
        '''make build dfInstr from xmfile and make every tag unique. Then save.'''
        uniqueDfInstr = []
        for tag in self.allTags:
            dup=dfInstr[dfInstr['id']==tag]
            rowFloat = dup[dup['type']=='IEEE754']
            if len(rowFloat)==1:
                uniqueDfInstr.append(rowFloat)
            else :
                uniqueDfInstr.append(dup.iloc[[0]])
        uniqueDfInstr=pd.concat(uniqueDfInstr)
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
        df=df.set_index('adresse')
        # df=df[df['scale']==0.1]

        return df

class OpcuaConfigMaster(ComConfigMaster):
    def __init__(self,folderPkl,confFolder,dbParameters,
                    endpointUrl,port=4843,nameSpace="ns=4;s=GVL.",**kwargs):
        ComConfigMaster.__init__(self,folderPkl,confFolder,dbParameters,**kwargs)
        self.endpointUrl = endpointUrl
        self.ip = endpointUrl
        self.port = port
        self.nameSpace   = nameSpace
        self.client      = Client(endpointUrl)
        self.certif_path = self.confFolder + "my_cert.pem"
        self.key_path    = self.confFolder + "my_private_key.pem"
        ####### load nodes
        self.nodesDict  = {t:self.client.get_node(self.nameSpace + t) for t in self.allTags}
        self.nodes      = list(self.nodesDict.values())

    def loadPLC_file(self):
        self.dataTypes = {
          'REAL':'float',
          'BOOL':'bool',
          'WORD':'int',
          'DINT':'int',
          'INT':'int',
          'STRING(40)':'str'
        }
        listPLC = glob.glob(self.confFolder + '*Instrum*.pkl')
        if len(listPLC)<1:
            listPLC_xlsm = glob.glob(self.confFolder + '*Instrum*.xlsm')
            plcfile=listPLC_xlsm[0]
            print(plcfile,' is read and converted in .pkl')
            dfPLC = pd.read_excel(plcfile,sheet_name='FichierConf_Jules',index_col=0)
            dfPLC = dfPLC[dfPLC.DATASCIENTISM]
            pickle.dump(dfPLC,open(plcfile[:-5]+'.pkl','wb'))
            listPLC = glob.glob(self.confFolder + '*Instrum*.pkl')

        self.plcFile = listPLC[0]
        self.dfPLC = pickle.load(open(self.plcFile,'rb'))

# #######################
# #      SIMULATORS     #
# #######################
from pymodbus.server.sync import ModbusTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from random import uniform
from opcua import Client
import opcua

class Simulator():
    ''' for inheritance a simulator should have:
    - inheritance of a ComConfigMaster children class
    - a function "serve" that starts the serveer
    - a function "writeInRegisters" to feed the data.
    - a function "shutdown_server" to shutdown the server.
    '''
    def __init__(self,speedflowdata=50,volatilitySimu=5):
        '''
        - speedflowdata : single data trigger event in ms
        - volatilitySimu : how much random variation (absolute units)
        '''
        self.volatilitySimu = volatilitySimu
        self.speedflowdata = speedflowdata
        self.server_thread = threading.Thread(target=self.serve)
        self.server_thread.daemon = True
        self.feed = True
        self.stopfeed = threading.Event()
        self.feedingThread = threading.Thread(target=self.feedingLoop)

    def stop(self):
        self.stopfeed.set()
        self.shutdown_server()
        print("Server stopped")

    def start(self):
        print("Start server...")
        self.server_thread.start()
        print("Server is online")
        self.feedingThread.start()
        print("Server simulator is feeding")

    def stopFeeding(self):
        self.feed=False

    def startFeeding(self):
        self.feed=True

    def feedingLoop(self):
        while not self.stopfeed.isSet():
            if self.feed:
                start=time.time()
                self.writeInRegisters()
                print('fed in {:.2f} milliseconds'.format((time.time()-start)*1000))
                sleep(self.speedflowdata/1000 + uniform(0,1/1000))

    def is_serving(self):
        return self.server_thread.is_alive()

class SimulatorModeBus(Simulator):
    ''' can only be used with a children class inheritating from a class that has
    attributes and methods of ComConfigMaster.
    ex : class StreamVisuSpecial(ComConfigSpecial,SimulatorModeBus)
    with class ComConfigSpecial(ComConfigMaster)'''

    def __init__(self,bo='=',*args,**kwargs):
        '''
        - bo : byteorder : bigendian >, littleendian <, native =, network(big endian) !
        '''
        self.bo = bo
        Simulator.__init__(self,*args,**kwargs)
        # initialize server with random values
        self.dfInstr['value']=self.dfInstr['type'].apply(lambda x:uniform(0,100000))
        self.dfInstr['precision']=0.1
        self.dfInstr['FREQUENCE_ECHANTILLONNAGE']=1
        allTCPid = list(self.dfInstr['addrTCP'].unique())
        # Create an instance of ModbusServer
        slaves={}
        for k in allTCPid:
            slaves[k]  = ModbusSlaveContext(hr=ModbusSequentialDataBlock(0, [k]*128))
            self.context = ModbusServerContext(slaves=slaves, single=False)
        self.server = ModbusTcpServer(self.context, address=("", self.port))
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.feed = True
        self.stopfeed = threading.Event()
        self.feedingThread = threading.Thread(target=self.feedingLoop)

    def start(self):
        print("Start server...")
        self.server_thread.start()
        print("Server is online")
        self.feedingThread.start()
        print("Server simulator is feeding")

    def generateRandomData(self,ptComptage):
        byteflow=[]
        values=[]
        # te = ptComptage.iloc[[0]]
        for te in ptComptage.iterrows():
            te=te[1]
            # print(te)
            # address = te.index[0]
            typevar = te.type
            if typevar=='INT32':
                value = int(te.value + uniform(0,te.value*self.volatilitySimu/100))
                # conversion of long(=INT32) into 2 shorts(=DWORD=word)
                valueShorts = struct.unpack(self.bo + '2H',struct.pack(self.bo + "i",value))
            if typevar=='INT64':
                value = int(te.value + uniform(0,te.value*self.volatilitySimu/100))
                # conversion of long long(=INT64) to 4 short(=DWORD=word)
                valueShorts = struct.unpack(self.bo + '4H', struct.pack(self.bo + 'q', value))
            if typevar=='IEEE754':
                value = te.value + uniform(0,te.value*self.volatilitySimu/100)
                # value = 16.565
                # conversion of float(=IEEE7554O) to 2 shorts(=DWORD)
                valueShorts=struct.unpack(self.bo + '2H', struct.pack(self.bo+'f', value))
            byteflow.append(valueShorts)
            values.append(value)
        return [l for k in byteflow for l in k],values

    def writeInRegisters(self,idTCP):
        ptComptage = self.dfInstr[self.dfInstr['addrTCP']==idTCP]
        # #######
        #                   IMPORTANT CHECK HERE
        #           block should have continuous adresses with no gap!
        # #######
        # ptComptage = ptComptage[ptComptage.intAddress<10000]
        # try :
        feedingClient = ModbusClient(host='localhost',port=self.port)
        feedingClient.connect()
        byteflow,values = self.generateRandomData(ptComptage)
        feedingClient.write_registers(ptComptage.intAddress[0],byteflow,unit=idTCP)
        feedingClient.close()
        return byteflow,values
        # except:
            # print("Shutdown server ...")
            # self.stop()
            # print("Server is offline")

    def feedingLoop(self):
        while not self.stopfeed.isSet():
            if self.feed:
                idTCP = self.dfInstr.addrTCP.sample(n=1)[0]
                # print('idTCP ======> ',idTCP)
                start =time.time()
                byteflow,values=self.writeInRegisters(idTCP)
                # print('byteflow : ', byteflow)
                sleep(self.speedflowdata/1000 + uniform(0,1/1000))

    def serve(self):
        self.server.serve_forever()

    def shutdown_server(self):
        self.server.shutdown()

class SimulatorOPCUA(Simulator):
    ''' can only be used with a children class inheritating from a class that has
    attributes and methods of ComConfigMaster.
    ex : class StreamVisuSpecial(ComConfigSpecial,SimulatorOPCUA)
    with class ComConfigSpecial(ComConfigMaster)
    '''
    def __init__(self,*args,**kwargs):
        self.server=opcua.Server()
        self.server.set_endpoint(self.endpointUrl)
        self.nodeValues = {}
        self.nodeVariables = {}
        self.createNodes()
        Simulator.__init__(self,*args,**kwargs)

    def serve(self):
        print("start server")
        self.server.start()
        print("server Online")

    def shutdown_server(self):
        self.server.stop()

    def createNodes(self):
        objects=self.server.get_objects_node()
        self.beckhoff = objects.add_object(self.nameSpace,"Beckhoff")
        valueInits = self.createRandomInitalTagValues()
        for tag,val in valueInits.items():
            self.nodeValues[tag]    = val
            self.nodeVariables[tag] = self.beckhoff.add_variable(self.nameSpace+tag,tag,val)

    def writeInRegisters(self):
        for tag,var in self.nodeVariables.items():
            tagvar=self.dfPLC.loc[tag]
            if tagvar.DATATYPE=='REAL':
                newValue = self.nodeValues[tag] + self.volatilitySimu*np.random.randn()*tagvar.PRECISION
                self.nodeVariables[tag].set_value(newValue)
            if tagvar.DATATYPE=='BOOL':
                newValue = np.random.randint(0,2)
                self.nodeVariables[tag].set_value(newValue)
            self.nodeValues[tag] = newValue
        # tagTest = 'SEH1.STB_STK_03.HER_01_CL01.In.HR26'
        tagTest = 'SEH1.GWPBH_PMP_05.HO00'
        # tagTest = 'SEH1.STB_GFC_00_PT_01_HC21'
        # tagTest = 'SEH1.STB_STK_01.SN'
        # tagTest = 'SEH1.HPB_STG_01a_HER_03_JT_01.JTVAR_HC20'
        print(tagTest + ': ',self.nodeVariables[tagTest].get_value())

# #######################
# #  DUMPING CLIENTS    #
# #######################
class Streaming():
    '''Streaming enables to perform action on parked Day/Hour/Minute folders.
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
        if dfminute.empty:
            print(tag,t1,t2)
            print(dfminute)
            time.sleep(1)
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

class DumpingClientMaster():
    ''' DumpingClientMaster is the master client that connects to buffer database and devices.
    It has functions to store data in database while parking the data and
    flushing the database with a dbwindow parameters that determines how big
    the buffer data base can be and how often data should be parked.
    For inheritance children classes should have :
    - a function connect2device to connect to the device
    - a function collectData to collect data from the device.
    - a function connectDevice to connect to the device.
    '''
    def __init__(self):
        # self.configCom = configCom
        self.streaming = Streaming()
        self.fs = FileSystem()
        self.connReq = ''.join([k + "=" + v + " " for k,v in self.dbParameters.items()])
        self.logsFolder='/home/dorian/sylfen/exploreSmallPower/src/logs/'
        self.insertingTimes = {}
        self.collectingTimes = {}
        self.parkingTimes = {}
        self.isConnected = True
        self.timeOutReconnexion = 3
        self.reconnectionThread = SetInterval(self.timeOutReconnexion,self.checkConnection)
        self.reconnectionThread.start()

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

    # ########################
    #       WORKING WITH     #
    #    POSTGRES DATABASE   #
    # ########################
    def connect2db(self):
        return psycopg2.connect(self.connReq)

    def insert_intodb(self,*args):
        ''' should have a function that gather data and returns them
        in form of a dictionnary tag:value.
        '''
        data={}
        try :
            dbconn = self.connect2db()
        except :
            print('problem connecting to database ',self.dbParameters )
            return
        cur  = dbconn.cursor()
        start=time.time()
        ts = dt.datetime.now(tz=pytz.timezone(self.local_tzname))
        if self.isConnected:
            try :
                data = self.collectData(*args)
            except:
                print('souci connexion at ' + ts)
                self.isConnected = False
                print('waiting for the connexion to be re-established...')

            self.collectingTimes[ts] = (time.time()-start)*1000
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
        if compression in ['reduce','diff','dynamic'] and not self.dfPLC.loc[tag,'DATATYPE']=='STRING(40)':
            precision = self.dfPLC.loc[tag,'PRECISION']
            dftag = dftag.replace('null',np.nan)
            dftag.value = dftag.value.astype(self.dataTypes[self.dfPLC.loc[tag,'DATATYPE']])
            dftag.value = self.streaming.staticCompressionTag(dftag.value,precision,compression)
        return self.streaming.foldersaction(t0,t1,self.folderPkl,self.streaming.parktagminute,dftag=dftag)

    def parkallfromdb(self):
        start=time.time()
        timenow=pd.Timestamp.now(tz=self.local_tzname)
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
        listTags = self.allTags

        # with Pool() as p:
        #     dfs=p.starmap(self.parktagfromdb,[(t0,t1,df,tag) for tag in listTags])
        dfs=[]
        for tag in self.allTags:
            dfs.append(self.parktagfromdb(t0,t1,df,tag))

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

    def parkalltagsDF(self,df,poolTags=True):
        listTags = self.allTags
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

class DumpingModeBusClient(DumpingClientMaster):
    ''' can only be used with a children class inheritating from a class that has
    attributes and methods of ComConfigMaster.
    ex : class StreamVisuSpecial(ComConfigSpecial,DumpingModeBusClient)
    with class ComConfigSpecial(ComConfigMaster)
    '''
    def __init__(self):
        DumpingClientMaster.__init__(self)
        self.allTCPid = self.dfInstr['addrTCP'].unique()

    def decodeRegisters(self,regs,block,bo='='):
        firstReg = min(block['intAddress'])
        curReg   = firstReg
        d={}
        for row in block.iterrows():
            row=row[1]
            if row.type == 'INT32':
                valueShorts = [regs[curReg+k] for k in [0,1]]
                # conversion of 2 shorts(=DWORD=word) into long(=INT32)
                value = struct.unpack(bo + 'i',struct.pack(bo + "2H",*valueShorts))[0]
                curReg+=2
            if row.type == 'IEEE754':
                valueShorts = [regs[curReg+k] for k in [0,1]]
                value = struct.unpack(bo + 'f',struct.pack(bo + "2H",*valueShorts))[0]
                curReg+=2
            elif row.type == 'INT64':
                valueShorts = [regs[curReg+k] for k in [0,1,2,3]]
                value = struct.unpack(bo + 'q',struct.pack(bo + "4H",*valueShorts))[0]
                curReg+=4
            d[row.id]=[value*row.scale,dt.datetime.now().astimezone().isoformat()]
        return d

    def checkRegisterValueTag(self,tag,**kwargs):
        checkClient = self.connect2device()
        checkClient.connect()
        tagid    = self.dfInstr[self.dfInstr['id']==tag]
        regs     = checkClient.read_holding_registers(tagid.intAddress[0],tagid['size(mots)'][0],unit=tagid.addrTCP[0]).registers
        checkClient.close()
        return self.decodeRegisters(regs,tagid,**kwargs)

    def getPtComptageValues(self,conn,unit_id,**kwargs):
        '''ptComptage must be a continuous block.'''
        ptComptage = self.dfInstr[self.dfInstr['addrTCP']==unit_id]
        firstReg = min(ptComptage['intAddress'])
        lastReg  = max(ptComptage['intAddress'])
        unit_id  = ptComptage['addrTCP'][0]
        #read all registers in a single command for better performances
        regs = conn.read_holding_registers(firstReg,ptComptage['size(mots)'].sum(),unit=unit_id).registers
        return self.decodeRegisters(regs,ptComptage,**kwargs)

    def connect2device(self):
        return ModbusClient(host=self.ip,port=self.port)

    def getModeBusRegistersValues(self,**kwargs):
        d={}
        conn = self.connect2device()
        for idTCP in self.allTCPid:
            d.update(self.getPtComptageValues(conn,unit_id=idTCP,**kwargs))
        conn.close()
        return d

    def quickmodebus2dbint32(self,conn,add):
        regs  = conn.read_holding_registers(add,2)
        return struct.unpack(bo + 'i',struct.pack(bo + "2H",*regs))[0]

    def collectData(self):
        data={}
        try:
            data = self.getModeBusRegistersValues()
        except Exception:
            print(dt.datetime.now().astimezone().isoformat() + '''--> problem gathering data from mode bus device
                with ip adress : ''' + self.ip + ' on port ' + str(self.port))
            # print(traceback.format_exc())
        return data

class DumpingOPCUAClient(DumpingClientMaster):
    ''' can only be used with a children class inheritating from a class that has
    attributes and methods of ComConfigMaster.
    ex : class StreamVisuSpecial(ComConfigSpecial,DumpingOPCUAClient)
    with class ComConfigSpecial(ComConfigMaster)
    '''
    def __init__(self):
        DumpingClientMaster.__init__(self)
        self.isOPCUAconnected=True

    def connectDevice(self):
        self.client.connect()

    def collectData(self,nodes):
        values = self.client.get_values(nodes.values())
        ts = dt.datetime.now().astimezone().isoformat()
        data = {tag:[val,ts] for tag,val in zip(nodes.keys(),values)}
        return data

# #######################
# #      VISU           #
# #######################
import plotly.express as px
class StreamingVisualisationMaster():
    ''' can only be used with a children class inheritating from a class that has
    attributes and methods of ComConfigMaster.
    ex : class StreamVisuSpecial(ComConfigSpecial,StreamingVisualisationMaster)
    '''
    def __init__(self):
        self.streaming = Streaming()
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
            dtypes = self.dfPLC.loc[tags].DATATYPE.apply(lambda x:self.dataTypes[x]).to_dict()
            df = df.dropna().astype(dtypes)
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

    def updateLayoutStandard(self,fig,sizeDots=5):
        fig.update_yaxes(showgrid=False)
        fig.update_traces(selector=dict(type='scatter'),marker=dict(size=sizeDots))
        fig.update_layout(height=750)
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
        fig.update_yaxes(showticklabels=False)
        fig.update_yaxes(showgrid=False)
        fig.update_xaxes(matches='x')
        self.updatecolorAxes(fig)
        self.updatecolortraces(fig)
        self.standardLayout(fig,h=None)
        return fig
