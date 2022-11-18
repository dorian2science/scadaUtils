# import importlib
import time, pytz,sys
from time import sleep
import sys,os,re,threading,struct, glob, pickle,struct,subprocess as sp
import numpy as np, pandas as pd
import psycopg2
from multiprocessing import Pool
import traceback
from sylfenUtils.utils import Utils
from dateutil.tz import tzlocal
from zipfile import ZipFile
import psutil

# #######################
# #      BASIC Utils    #
# #######################
# basic utilities for Streamer and DumpingClientMaster
timenowstd=lambda :pd.Timestamp.now().strftime('%d %b %H:%M:%S')
computetimeshow=lambda x,y:timenowstd() + ' : ' + x + ' in {:.2f} ms'.format((time.time()-y)*1000)
from inspect import currentframe, getframeinfo
from colorama import Fore
FORMAT_DAY_FOLDER='%Y-%m-%d'

def print_file(*args,filename=None,mode='a',with_infos=True,**kwargs):
    '''
    Print with color code in a file with line number in code.
    Parameters :
    -----------------
        - filename:file to print in.
        - with_infos:using line numbering and color code.
    '''
    entete=''
    if with_infos:
        frameinfo = currentframe().f_back
        frameinfo = getframeinfo(frameinfo)
        entete=Fore.BLUE + frameinfo.filename + ','+ Fore.GREEN + str(frameinfo.lineno) + '\n'+Fore.WHITE
    if filename is None:
        print(entete,*args,**kwargs)
    else:
        print(entete,*args,file=open(filename,mode),**kwargs)
def print_error(tb,filename=None):
    exc_format=traceback.format_exception(*tb)
    ff=''
    for k in range(1,len(exc_format)-1):
        res=re.match('(.*.py")(.*line \d+)(.*)',exc_format[k]).groups()
        ff+=Fore.RED + res[0]+Fore.BLUE+res[1]+Fore.GREEN + res[2] + Fore.WHITE + '\n'
    print_file(ff,exc_format[-1],with_infos=False,filename=filename)
def html_table(df,title='table'):
    f=open('/tmp/table.html','w')
    f.write('<h1>'+title+'</h1>')
    if isinstance(df,pd.Series):df=df.to_frame()
    df.to_html(f)
    f.close()
    sp.run('firefox /tmp/table.html',shell=True)
def read_db(db_parameters,db_table,t=None,tagPat=None,debug=False):
    '''
    read the database.
    Parameters :
    -----------
        - db_parameters:dictionnary with localhost,port,dbnamme,user, and password keys
        - db_table:name of the table
        - t : timestamp with timezone(default None ==> read all)
        - tagPat : regular expression pattern for tags(default None ==> read all)
    '''
    connReq = ''.join([k + "=" + v + " " for k,v in db_parameters.items()])
    dbconn = psycopg2.connect(connReq)
    start="select * from " + db_table +" "
    order_end=" order by timestampz asc;"
    if not t is None : ts=" timestampz < '" + t + "'"
    if tagPat is None:
        if t is None:
            sqlQ =start + order_end
        else:
            sqlQ = start + "where "+ ts + order_end
    else:
        tagPattern = " tag~'"+tagPat + "'"
        sqlQ =start + "where " + tagPattern
        if t is None:
            sqlQ = sqlQ + order_end
        else:
            sqlQ = sqlQ + "and " + ts + order_end
    if debug:print(sqlQ)
    try:
        ###########################################
        #    DANGEROUS WONT WORK WITH DST CHANGE  #
        ###########################################
        df = pd.read_sql_query(sqlQ,dbconn,parse_dates=['timestampz'])
    except:
        df = pd.read_sql_query(sqlQ,dbconn)
        df.timestampz=[pd.Timestamp(k).tz_convert('utc') for k in df.timestampz] #slower but will work with dst
    return df

class EmptyClass():pass

class FileSystem():
    ######################
    # FILE SYSTEMS  #
    ######################
    def load_confFile(self,filename,generate_func,generateAnyway=False):
        start    = time.time()
        if not os.path.exists(filename) or generateAnyway:
            print_file('Start generating the file '+filename+' with function : ')
            print_file(' '.ljust(20)+'\n',generate_func)
            # try:
            plcObj = generate_func()
            pickle.dump(plcObj,open(filename,'wb'))
            print_file('\n'+filename + ' saved\n')
            # except:
            #     print_file('failed to build plc file with filename :',filename)
            #     raise SystemExit
        # sys.exit()
        plcObj = pickle.load(open(filename,'rb'))
        print_file(computetimeshow(filename.split('/')[-1] + ' loaded',start),'\n---------------------------------------\n')
        return plcObj

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
        # print_file(unit)
        if not isinstance(unit,str):
            unit='u.a'
        return unit

    def getTagsTU(self,patTag,dfplc,units=None,onCol='index',cols='tag'):
        if onCol=='index':
            df = dfplc[dfplc.index.str.contains(patTag,case=False)]
        else:
            df = dfplc[dfplc[onCol].str.contains(patTag,case=False)]

        if units is None:units=list(dfplc['UNITE'].unique())
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
    def __init__(self,device_name,ip,port,dfplc,time_outs_reconnection=None,log_file=None):
        self._fs               = FileSystem()
        self._utils            = Utils()
        self.device_name       = device_name
        self.ip                = ip
        self.port              = port
        self.log_file          = log_file
        self.isConnected       = False
        self._auto_connect     = False
        self._kill_auto_connect= threading.Event()
        if time_outs_reconnection is None:
            time_outs_reconnection=[(2,k) for k in [3,5,10,30,60,60*2,60*5,60*10,60*20,60*30,60*40,60*50]]
            # time_outs_reconnection=[(1,k) for k in [1]]
            time_outs_reconnection.append((100000,60*60))
        self._time_outs_reconnection = time_outs_reconnection
        self._timeOuts_counter  = 0
        self._current_trial     = 0
        self._current_timeOut   = self._time_outs_reconnection[0][1]
        self._thread_reconnection = threading.Thread(target=self.__auto_reconnect)

        self.dfplc = dfplc
        self._collectingTimes,self._insertingTimes  = {},{}
        if not self.dfplc is None:
            self.listUnits = self.dfplc.UNITE.dropna().unique().tolist()
            self.alltags   = list(self.dfplc.index)

    def __auto_reconnect(self):
        while not self._kill_auto_connect.is_set():
            while self._auto_connect:
                self._checkConnection()
                self._kill_auto_connect.wait(self._current_timeOut)

    def connectDevice(self,state=None):
        if state is None:self.isConnected=np.random.randint(0,2)==1
        else:self.isConnected=state
        return self.isConnected

    def start_auto_reconnect(self):
        self.connectDevice()
        self._auto_connect=True
        self._thread_reconnection.start()

    def stop_auto_reconnect(self):
        self._auto_connect=False

    def kill_auto_reconnect(self):
        self._auto_connect=False
        self._kill_auto_connect.set()
        self._thread_reconnection.join()

    def _checkConnection(self):
        # print_file('checking if device still connected')
        if not self.isConnected:
            self._current_trial+=1
            nb_trials,self._current_timeOut = self._time_outs_reconnection[self._timeOuts_counter]
            if self._current_trial>nb_trials:
                self._timeOuts_counter+=1
                self._current_trial=0
                self._checkConnection()
                return

            full_msg='-'*60+'\n'
            if self.connectDevice():
                self._timeOuts_counter  = 0
                self._current_timeOut   = self._time_outs_reconnection[0][1]
                self._current_trial     = 0
                msg=timenowstd()+' : Connexion to '+self.device_name+' established again!!'
            else :
                msg=timenowstd()+' : --> impossible to connect to device '+self.device_name
                msg+='. Try new connection in ' + str(self._current_timeOut) + ' seconds'

            print_file(full_msg+msg+'-'*60+'\n',filename=self.log_file)

    def _generate_sql_insert_tag(self,tag,value,timestampz,dbTable):
        '''
        - dbTable : name of table in database where to insert
        '''
        sqlreq = "insert into " + dbTable + " (tag,value,timestampz) values ('"
        if value==None:value = 'null'
        value = str(value)
        sqlreq+= tag +"','" + value + "','" + timestampz  + "');"
        return sqlreq.replace('nan','null')

    def insert_intodb(self,dbParameters,dbTable,*args,**kwargs):
        '''
        insert into database data that are collected with self.collectData.
        dfplc attribute should not be None.
        *args : arguments of self.collectData
        '''
        if self.dfplc is None:return
        ##### connect to database ########
        try :
            connReq = ''.join([k + "=" + v + " " for k,v in dbParameters.items()])
            dbconn = psycopg2.connect(connReq)
        except:
            print_file('problem connecting to database ',dbParameters,filename=self.log_file)
            return
        cur  = dbconn.cursor()
        start=time.time()
        ##### check that device is connected ########
        if not self.isConnected:
            return
        ##### collect data ########
        try:
            data = self.collectData(*args,**kwargs)
        except:
            print_file(timenowstd(),' : ',self.device_name,' --> connexion to device impossible.',filename=self.log_file)
            self.isConnected = False
            return
        self._collectingTimes[timenowstd()] = (time.time()-start)*1000
        ##### generate sql insertion and insert ########
        for tag in data.keys():
            sqlreq=self._generate_sql_insert_tag(tag,data[tag]['value'],data[tag]['timestampz'],dbTable)
            cur.execute(sqlreq)
        self._insertingTimes[timenowstd()]= (time.time()-start)*1000
        dbconn.commit()
        cur.close()
        dbconn.close()

    def createRandomInitalTagValues(self):
        return self._fs.createRandomInitalTagValues(self.alltags,self.dfplc)

    def getUnitofTag(self,tag):
        return self._fs.getUnitofTag(tag,self.dfplc)

    def getTagsTU(self,patTag,units=None,*args,**kwargs):
        if self.dfplc is None:
            print_file('no dfplc. Function unavailable.')
            return
        if not units : units = self.listUnits
        return self._fs.getTagsTU(patTag,self.dfplc,units,*args,**kwargs)

from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian
class ModbusDevice(Device):
    def __init__(self,ip,port=502,device_name='',dfplc=None,modbus_map=None,freq=30,bo='big',wo='big',**kwargs):
        '''freq: how often to fetch the data in seconds/'''
        Device.__init__(self,device_name,ip,port,dfplc,**kwargs)
        self.modbus_map = modbus_map
        self.freq = freq
        self.byte_order,self.word_order = bo,wo
        if not self.modbus_map is None:
            self.slave_ids = list(self.modbus_map.slave_unit.unique())
        self._client = ModbusClient(host=self.ip,port=int(self.port))
        if not self.dfplc is None:dfplc['FREQUENCE_ECHANTILLONNAGE'] = self.freq

    def connectDevice(self):
        self.isConnected=False
        try:
            self.isConnected=self._client.connect()
        except:
            self.isConnected=False
        return self.isConnected

    def quick_modbus_single_register_decoder(self,reg,nbs,dtype,unit=1):
        self._client.connect()
        result = self._client.read_holding_registers(reg, nbs, unit=unit)
        decoders={}
        decoders['bo=b,wo=b'] = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Big, wordorder=Endian.Big)
        decoders['bo=b,wo=l'] = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Big, wordorder=Endian.Little)
        decoders['bo=l,wo=b'] = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Little, wordorder=Endian.Big)
        decoders['bo=l,wo=l'] = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Little, wordorder=Endian.Little)
        values ={k:self._decode_register(d,dtype) for k,d in decoders.items()}
        print('='*60+'\nvalues are \n',pd.Series(values))
        return values

    def decode_bloc_registers(self,bloc,*args,**kwargs):
        blocks=self._get_continuous_blocks(bloc)
        index_name=bloc.index.name
        if index_name is None:index_name='index'
        return pd.concat([self._decode_continuous_bloc(b,*args,**kwargs) for b in blocks],axis=0).set_index(index_name)

    def collectData(self,tz,*args):
        '''It will collect all the data if a dataframe modbus_map is present with columns
        - index : name of the registers or tags.
        - type  : datatype{uint16,int32,float...}
        - scale : the multiplication factor
        - intaddress :  for the adress in decimal format
        - slave_unit : the slave unit
        '''
        if self.modbus_map is None:
            print_file('no modbus_map was selected. Collection not possible.')
            return
        d={}
        bbs=[]
        for unit_id in self.modbus_map.slave_unit.unique():
            bloc=self.modbus_map[self.modbus_map.slave_unit==unit_id]
            bb=self.decode_bloc_registers(bloc,unit_id)
            bb['timestampz']=pd.Timestamp.now(tz=tz).isoformat()
            bbs+=[bb]
        d=pd.concat(bbs)[['value','timestampz']].T.to_dict()
        return d
    #####################
    # PRIVATE FUNCTIONS #
    #####################
    def _decode_continuous_bloc(self,bloc,unit_id=1):
        '''
        - bloc[pd.DataFrame] should be continuous and contain:
            - type column with the datatypes
            - intaddress with the adress of the registers
            - scale with scales to apply
        '''

        def sizeof(dtype):
            if dtype.lower()=='float32' or dtype.lower()=='ieee754':
                return 2
            elif dtype.lower()=='int32' or dtype.lower()=='uint32':
                return 2
            elif dtype.lower()=='int16' or dtype.lower()=='uint16':
                return 1
            elif dtype.lower()=='int64' or dtype.lower()=='uint64':
                return 4

        ### determine range to read
        blocks=[]
        for block_100 in self._cut_into_100_blocks(bloc):
            start=block_100['intaddress'].min()
            end=block_100['intaddress'].max()+sizeof(block_100['type'].iloc[-1])
            self._client.connect()
            result = self._client.read_holding_registers(start, end-start, unit=unit_id)
            ### decode values
            if self.byte_order.lower()=='little' and self.word_order.lower()=='big':
                decoder = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Little, wordorder=Endian.Big)
            elif self.byte_order.lower()=='big' and self.word_order.lower()=='big':
                decoder = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Big, wordorder=Endian.Big)
            elif self.byte_order.lower()=='little' and self.word_order.lower()=='little':
                decoder = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Little, wordorder=Endian.Little)
            elif self.byte_order.lower()=='big' and self.word_order.lower()=='little':
                decoder = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Big, wordorder=Endian.Little)
            block_100['value'] = [self._decode_register(decoder,dtype) for dtype in block_100['type']]
            blocks+=[block_100]
        bloc=pd.concat(blocks)
        ### apply scales
        bloc['value']*=bloc['scale']
        return bloc

    def _get_size_words_block(self,bloc):
        bs=pd.Series(1,index=bloc.index)
        bs=bs.mask(bloc['type']=='IEEE754',2)
        bs=bs.mask(bloc['type']=='INT64',4)
        bs=bs.mask(bloc['type']=='UINT64',4)
        bs=bs.mask(bloc['type']=='INT32',2)
        bs=bs.mask(bloc['type']=='UINT32',2)

        bs=bs.mask(bloc['type']=='float32',2)
        bs=bs.mask(bloc['type']=='int64',4)
        bs=bs.mask(bloc['type']=='uint64',4)
        bs=bs.mask(bloc['type']=='int32',2)
        bs=bs.mask(bloc['type']=='uint32',2)
        bloc2=bloc.copy()
        bloc2['size_words']=bs
        return bloc2

    def _cut_into_100_blocks(self,bloc):
        bbs=[]
        bint=bloc['intaddress']
        mini=bint.min()
        range_width=bint.max()-mini
        for k in range(range_width//100+1):
            bb=bloc[(bint>=mini+k*100) & (bint<=mini+(k+1)*100)]
            if not bb.empty:
                bbs+=[bb]
        return bbs

    def _get_continuous_blocks(self,bloc):
        bloc=self._get_size_words_block(bloc)
        index_name=bloc.index.name
        if index_name is None:index_name='index'
        c=(bloc['intaddress']+bloc['size_words']).reset_index()[:-1]
        b=bloc['intaddress'][1:].reset_index()
        idxs_break=b[~(b['intaddress']==c[0])][index_name].to_list()
        bb=bloc.reset_index()
        idxs_break=[bb[bb[index_name]==i].index[0] for i in idxs_break]

        idxs_break=[0]+idxs_break+[len(bb)]
        blocks=[bb.iloc[idxs_break[i]:idxs_break[i+1],:] for i in range(len(idxs_break)-1)]
        return blocks

    def _fill_gaps_bloc(self,bloc):
        bloc=bloc.copy().sort_values('intaddress')[['intaddress','type']]
        bloc=self._get_size_words_block(bloc)
        k=0
        while k<len(bloc)-1:
            cur_loc=bloc.iloc[k]
            next_loc=cur_loc[['intaddress','size_words']].sum()
            next_loc_real=bloc.iloc[k+1]['intaddress']
            if not next_loc_real==next_loc:
                rowAdd=pd.DataFrame([next_loc,'int16',1],index=bloc.columns,columns=['unassigned']).T
                bloc=pd.concat([bloc,rowAdd],axis=0)
                bloc=bloc.sort_values('intaddress')
            k+=1
        return bloc

    def _decode_register(self,decoder,dtype):
        if dtype.lower()=='float32' or dtype.lower()=='ieee754':
            value=decoder.decode_32bit_float()
        elif dtype.lower()=='int32':
            value=decoder.decode_32bit_int()
        elif dtype.lower()=='uint32':
            value=decoder.decode_32bit_uint()
        elif dtype.lower()=='int16':
            value=decoder.decode_16bit_int()
        elif dtype.lower()=='uint16':
            value=decoder.decode_16bit_uint()
        elif dtype.lower()=='int64':
            value=decoder.decode_64bit_int()
        elif dtype.lower()=='uint64':
            value=decoder.decode_64bit_uint()
        else:
            value=dtype+' not available'
        return value

import opcua
class Opcua_Client(Device):
    def __init__(self,*args,nameSpace,protocole='opc.tcp',**kwargs):
        Device.__init__(self,*args,**kwargs)

        self._nameSpace = nameSpace
        self._protocole = protocole
        self.ip = self.ip
        self.endpointurl = self._protocole + '://' +self.ip+":"+str(self.port)
        self._client     = opcua.Client(self.endpointurl)
        ####### load nodes
        self._nodesDict  = {t:self._client.get_node(self._nameSpace + t) for t in self.alltags}
        self._nodes      = list(self._nodesDict.values())

    def loadPLC_file(self):
        listPLC = glob.glob(self.confFolder + '*Instrum*.pkl')
        if len(listPLC)<1:
            listPLC_xlsm = glob.glob(self.confFolder + '*Instrum*.xlsm')
            plcfile=listPLC_xlsm[0]
            print_file(plcfile,' is read and converted in .pkl')
            dfplc = pd.read_excel(plcfile,sheet_name='FichierConf_Jules',index_col=0)
            pickle.dump(dfplc,open(plcfile[:-5]+'.pkl','wb'))
            listPLC = glob.glob(self.confFolder + '*Instrum*.pkl')

        self.file_plc = listPLC[0]
        dfplc = pickle.load(open(self.file_plc,'rb'))
        return dfplc

    def connectDevice(self):
        try:
            self._client.connect()
            self.isConnected=True
        except:
            self.isConnected=False
        return self.isConnected

    def collectData(self,tz,tags):
        nodes = {t:self._nodesDict[t] for t in tags}
        values = self._client.get_values(nodes.values())
        ts = pd.Timestamp.now(tz=tz).isoformat()
        data = {tag:{'value':val,'timestampz':ts} for tag,val in zip(nodes.keys(),values)}
        return data

import urllib.request, json
class Meteo(Device):
    def __init__(self,cities,service='openweather',apitoken='',freq=30,**kwargs):
        '''-freq: acquisition time in seconds '''
        self.cities = cities
        self.freq=freq
        self.service=service
        if service=='openweather':
            self.baseurl = 'https://api.openweathermap.org/data/2.5/'
        dfplc = self.build_plcmeteo(self.freq)
        Device.__init__(self,'meteo',self.baseurl,None,dfplc)
        self.apitoken = apitoken
        # self.apitoken = '2baff0505c3177ad97ec1b648b504621'# Marc
        self.t0 = pd.Timestamp('1970-01-01 00:00',tz='UTC')

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
            request = urllib.request.urlopen('https://api.openweathermap.org/',timeout=2)
            print_file("Meteo : Connected to the meteo server.",filename=self.log_file)
            self.isConnected=True
        except:
            print_file("Meteo : No internet connection or server not available.",filename=self.log_file)
            self.isConnected=False
        return self.isConnected

    def collectData(self,tz='CET',tags=None):
        df = pd.concat([self.get_dfMeteo(city,tz) for city in self.cities])
        return {tag:{'value':v,'timestampz':df.name} for tag,v in df.to_dict().items()}

    def get_dfMeteo(self,city,tz,ts_from_meteo=False):
        '''
        ts_from_meteo : if True the timestamp corresponds to the one given by the weather data server.
        Can lead to dupplicates in the data.
        '''
        gps = self.cities[city]
        url = self.baseurl + 'weather?lat='+gps.lat+'&lon=' + gps.lon + '&units=metric&appid=' + self.apitoken
        response = urllib.request.urlopen(url)
        data     = json.loads(response.read())
        if ts_from_meteo:
            timeCur  = (self.t0 + pd.Timedelta(seconds=data['dt'])).tz_convert(tz)
        else:
            timeCur  = pd.Timestamp.now(tz=tz)
        dfmain   = pd.DataFrame(data['main'],index=[timeCur.isoformat()])
        dfmain['clouds']     = data['clouds']['all']
        dfmain['visibility'] = data['visibility']
        dfmain['main']       = data['weather'][0]['description']
        dfmain['seconds']       = data['dt']
        dfwind = pd.DataFrame(data['wind'],index=[timeCur.isoformat()])
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

class Meteo_Client(Device):
    def __init__(self,freq=30,**kwargs):
        '''-freq: acquisition time in seconds '''
        self.freq=freq
        self.cities = pd.DataFrame({'le_cheylas':{'lat' : '45.387','lon':'6.0000'}})
        self.baseurl = 'https://api.openweathermap.org/data/2.5/'
        dfplc = self.build_plcmeteo(self.freq)
        Device.__init__(self,'meteo',self.baseurl,None,dfplc)
        self.apitoken = '79e8bbe89ac67324c6a6cdbf76a450c0'
        # self.apitoken = '2baff0505c3177ad97ec1b648b504621'# Marc
        self.t0 = pd.Timestamp('1970-01-01 00:00',tz='UTC')

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
            request = urllib.request.urlopen('https://api.openweathermap.org/',timeout=2)
            print_file("Meteo : Connected to the meteo server.",filename=self.log_file)
            self.isConnected=True
        except:
            print_file("Meteo : No internet connection or server not available.",filename=self.log_file)
            self.isConnected=False
        return self.isConnected

    def collectData(self,tz='CET',tags=None):
        df = pd.concat([self.get_dfMeteo(city,tz) for city in self.cities])
        return {tag:{'value':v,'timestampz':df.name} for tag,v in df.to_dict().items()}

    def get_dfMeteo(self,city,tz,ts_from_meteo=False):
        '''
        ts_from_meteo : if True the timestamp corresponds to the one given by the weather data server.
        Can lead to dupplicates in the data.
        '''
        gps = self.cities[city]
        url = self.baseurl + 'weather?lat='+gps.lat+'&lon=' + gps.lon + '&units=metric&appid=' + self.apitoken
        response = urllib.request.urlopen(url)
        data     = json.loads(response.read())
        if ts_from_meteo:
            timeCur  = (self.t0 + pd.Timedelta(seconds=data['dt'])).tz_convert(tz)
        else:
            timeCur  = pd.Timestamp.now(tz=tz)
        dfmain   = pd.DataFrame(data['main'],index=[timeCur.isoformat()])
        dfmain['clouds']     = data['clouds']['all']
        dfmain['visibility'] = data['visibility']
        dfmain['main']       = data['weather'][0]['description']
        dfmain['seconds']       = data['dt']
        dfwind = pd.DataFrame(data['wind'],index=[timeCur.isoformat()])
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
class Basic_streamer():
    '''Streamer enables to perform action on parked Day/Hour/Minute folders.
    It comes with basic functions like loaddata_minutefolder/create_minutefolder/parktagminute.'''
    def __init__(self,log_file=None):
        self.methods=['ffill','nearest','mean','max','min','median','interpolate','rolling_mean','mean_mix']
        self._num_cpus = psutil.cpu_count(logical=False)
        self._fs = FileSystem()
        self.log_file=log_file

class Streamer(Basic_streamer):
    '''Streamer enables to perform action on parked Day/Hour/Minute folders.
    It comes with basic functions like loaddata_minutefolder/create_minutefolder/parktagminute.'''
    def __init__(self,*args,**kwargs):
        Basic_streamer.__init__(self,*args,**kwargs)
        self._format_dayFolder='%Y-%m-%d/'


    def park_tags(self,df,tag,folder,dtype,showtag=False):
        if showtag:print_file(tag)
        dftag=df[df.tag==tag]['value'].astype(dtype)
        pickle.dump(dftag,open(folder + tag + '.pkl', "wb" ))

    # ########################
    #   MODIFY EXISTING DATA #
    # ########################
    def process_dbtag(self,s,dtype):
        s=s.replace('null',np.nan)
        s=s.replace('False',False)
        s=s.replace('True',True)
        if dtype=='int':
            s = s.fillna(np.nan).replace('null',np.nan).astype(float)
            s = s.convert_dtypes()
        else:
            s = s.astype(dtype)
        return s

    def applyCorrectFormat_tag(self,tagpath,dtype,newtz='CET',print_fileag=False,debug=False):
        '''
        Formats as pd.Series with name values and timestamp as index, remove duplicates, convert timestamp with timezone
        and apply the correct datatype

        :Parameters:
            tagpath:str absolute path of the parked tag
        '''
        if print_fileag:print_file(tagpath,filename=self.log_file)
        ##### --- load pkl----
        try:df=pd.read_pickle(tagpath)
        except:df=pd.DataFrame();print_file('pb loading',tagpath,filename=self.log_file)
        if df.empty:print_file('dataframe empty for ',tagpath,filename=self.log_file);return

        ##### --- make them format pd.Series with name values and timestamp as index----
        if not isinstance(df,pd.core.series.Series):
            col_timestamp=[k for k in df.columns if 'timestamp' in k]
            df.set_index(col_timestamp)['value'].to_pickle(tagpath)
        ##### --- remove index duplicates ----
        df = df[~df.index.duplicated(keep='first')]
        ##### --- convert tz----
        if isinstance(df.index.dtype,pd.DatetimeTZDtype):
            df.index = df.index.tz_convert(newtz)
        else:### for cases with changing DST at 31.10 or if it is a string
            df.index = [pd.Timestamp(k).astimezone(newtz) for k in df.index]
        #####----- apply correct datatype ------
        df = df.astype(dtype)
        df.to_pickle(tagpath)

    def applyCorrectFormat_day(self,folder_day,dtypes,*args,**kwargs):
        # list of dtypes of all tags in folder
        print_file(folder_day,filename=self.log_file)
        tags = os.listdir(folder_day)
        for tag in tags:
            tag=tag.strip('.pkl')
            if tag in dtypes.keys():
                self.applyCorrectFormat_tag(folder_day+'/'+tag+'.pkl',dtypes[tag],*args,**kwargs)
            else: print_file('dtypes does not contain tag : ', tag,filename=self.log_file)

    # ########################
    #      DAY FUNCTIONS     #
    # ########################
    def to_folderday(self,timestamp):
        '''convert timestamp to standard day folder format'''
        return timestamp.strftime(self._format_dayFolder)+'/'

    def create_dayfolder(self,folderday):
        if not os.path.exists(folderday):
            os.mkdir(folderday)
            return folderday +' created '
        else :
            return folderday +' already exists '

    def park_DFday(self,dfday,folderpkl,pool=False,showtag=False):
        correctColumns=['tag','timestampz','value']
        if not list(dfday.columns.sort_values())==correctColumns:
            print_file('PROBLEM: the df dataframe should have the following columns : ',correctColumns,'''
            instead your columns are ''',list(dfday.columns.sort_values()),filename=self.log_file)
            return

        dfday = dfday.set_index('timestampz')
        if isinstance(dfday.index.dtype,pd.DatetimeTZDtype):
            dfday.index = dfday.index.tz_convert('UTC')
        else:### for cases with changing DST 31.10 for example
            dfday = [pd.Timestamp(k).astimezone('UTC') for k in dfday.index]
        listTags = dfday.tag.unique()
        folderday = folderpkl +'/'+ dfday.index.mean().strftime(self._format_dayFolder)+'/'
        print_file(filename=self.log_file)
        if not os.path.exists(folderday): os.mkdir(folderday)
        #park tag-day
        if pool :
            with Pool() as p:dfs=p.starmap(self.parkdaytag,[(dfday,tag,folderday,showtag) for tag in listTags])
        else :
            for tag in listTags:self.parkdaytag(dfday,tag,folderday,showtag)

    def parkdaytag(self,dfday,tag,folderday,showtag=False):
        if showtag:print_file(tag,filename=self.log_file)
        dftag=dfday[dfday.tag==tag]['value']
        pickle.dump(dftag,open(folderday + tag + '.pkl', "wb" ))

    def actiondays(self,t0,t1,folderPkl,action,*args,pool=True):
        '''
        -t0,t1:timestamps
        '''
        print_file(t0,t1,filename=self.log_file)
        days=pd.date_range(t0,t1,freq='1D')
        dayfolders =[folderPkl + k.strftime(self._format_dayFolder)+'/' for k in days]
        if pool:
            with Pool() as p:
                dfs = p.starmap(action,[(d,*args) for d in dayfolders])
        else:
            dfs = [action(d,*args) for d in dayfolders]
        return {d.strftime(self._format_dayFolder):df for d,df in zip(days,dfs)}

    def remove_tags_day(self,d,tags):
        print_file(d,filename=self.log_file)
        for t in tags:
            tagpath=d+'/'+t+'.pkl'
            try:
                os.remove(tagpath)
            except:
                pass
                # print_file('no file :',tagpath)

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

    def zip_day_v2(self,folderday,basename,zipfolder):
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

    def process_tag(self,s,rsMethod='nearest',rs='auto',tz='CET',rmwindow='3000s',closed='left',checkTime=False,verbose=False):
        '''
            - s : pd.series with timestampz index and name=value
            - rsMethod : see self.methods
            - rs : argument for pandas.resample
            - rmwindow : argument for method rollingmean
        '''
        if s.empty:
            if verbose:print_file('processing : series is empty')
            s.index=pd.DatetimeIndex([],tz=tz)
            return s

        start=time.time()
        # remove duplicated index
        s=s[~s.index.duplicated(keep='last')].sort_index()
        if checkTime:computetimeshow('drop duplicates ',start)

        # timezone conversion
        s.index = s.index.tz_convert(tz)

        ##### auto resample
        if rs=='auto' and not rsMethod=='raw':
            ptsCurve = 500
            deltat = (s.index.max()-s.index.min()).seconds//ptsCurve+1
            rs = str(deltat) + 's'
        start  = time.time()
        ############ compute resample
        # return s
        if not rsMethod=='raw':
            if pd.api.types.is_string_dtype(s):
                s=s.resample(rs,label=closed,closed=closed).nearest()
            else:
                if rsMethod=='ffill':
                    s = s.resample(rs,label=closed,closed=closed).ffill()
                if rsMethod=='nearest':
                    s = s.resample(rs,label=closed,closed=closed).nearest()
                elif rsMethod=='mean':
                    s = s.resample('100ms').nearest().resample(rs,label=closed,closed=closed).mean()
                elif rsMethod=='max':
                    s = s.resample(rs,label=closed,closed=closed).max()
                elif rsMethod=='min':
                    s = s.resample(rs,label=closed,closed=closed).min()
                elif rsMethod=='median':
                    s = s.resample(rs,label=closed,closed=closed).median()

                elif rsMethod=='interpolate':
                    s = pd.concat([s.resample(rs).asfreq(),s]).sort_index().interpolate('time')
                    s = s[~s.index.duplicated(keep='first')]

                elif rsMethod=='rolling_mean':
                    s=s.nearest().resample(rs).ffill().rolling(rmwindow).mean()

                elif rsMethod=='mean_mix':
                    if pd.api.types.is_float_dtype(s) :
                        s = s.resample('100ms').nearest().resample(rs,label=closed,closed=closed).mean()
                    else:
                        s = s.resample(rs,label=closed,closed=closed).nearest()

        if checkTime:computetimeshow(rsMethod + ' data',start)
        return s

    def load_raw_day_tag(self,day,tag,folderpkl,rs,rsMethod,closed,showTag_day=True):
        # print(folderpkl, day,'/',tag,'.pkl')

        filename = folderpkl +'/'+ day+'/'+tag+'.pkl'
        if os.path.exists(filename):
            s= pd.read_pickle(filename)
        else :
            s=  pd.Series(dtype='float')
        if showTag_day:print_file(filename + ' read',filename=self.log_file)
        s = self.process_tag(s,rs=rs,rsMethod=rsMethod,closed=closed)
        return s

    def pool_tag_daily(self,t0,t1,tag,folderpkl,rs='auto',rsMethod='nearest',closed='left',ncores=None,time_debug=False,verbose=False,**kwargs):
        start=time.time()

        listDays=[self.to_folderday(k)[:-1] for k in pd.date_range(t0,t1,freq='D')]
        if ncores is None:
            ncores=min(len(listDays),self._num_cpus)

        with Pool(ncores) as p:
            dfs=p.starmap(self.load_raw_day_tag,[(d,tag,folderpkl,rs,rsMethod,closed,verbose) for d in listDays])
        if time_debug:print_file(computetimeshow('pooling ' + tag+' finished',start))
        s_tag = pd.concat(dfs)
        if time_debug:print_file(computetimeshow('concatenation ' + tag+' finished',start))
        s_tag = s_tag[(s_tag.index>=t0)&(s_tag.index<=t1)]
        s_tag.name=tag
        s_tag=s_tag[~s_tag.index.duplicated(keep='first')]
        if time_debug:print_file(computetimeshow(tag + ' finished',start))
        return s_tag

    def load_tag_daily(self,t0,t1,tag,folderpkl,showTag=False,time_debug=False,verbose=False,**kwargs):
        if showTag:print_file(tag,filename=self.log_file)
        start=time.time()
        dfs={}
        t=t0 - pd.Timedelta(hours=t0.hour,minutes=t0.minute,seconds=t0.second)
        while t<t1:
            filename = folderpkl +'/'+ t.strftime(self._format_dayFolder)+'/'+tag+'.pkl'
            if os.path.exists(filename):
                if time_debug: print_file(filename,t.isoformat(),filename=self.log_file)
                dfs[filename]=pd.read_pickle(filename)
            else :
                if verbose:print_file('no file : ',filename,filename=self.log_file)
                dfs[filename] = pd.Series(dtype='float',name='value')
            t = t + pd.Timedelta(days=1)
        if time_debug:computetimeshow('raw pkl loaded in ',start)
        start=time.time()
        s_tag = pd.DataFrame(pd.concat(dfs.values()))
        if time_debug:computetimeshow('contatenation done in ',start)
        s_tag.index.name='timestampz'
        start = time.time()
        s_tag = s_tag[(s_tag.index>=t0)&(s_tag.index<=t1)]
        s_tag = self.process_tag(s_tag['value'],**kwargs)
        s_tag.name=tag
        if time_debug:computetimeshow('processing done in ',start)
        return s_tag

    def load_tag_daily_kwargs(self,t0,t1,tag,folderpkl,args, kwargs):
        return self.load_tag_daily(t0,t1,tag,folderpkl,*args, **kwargs)

    def load_parkedtags_daily(self,t0,t1,tags,folderpkl,*args,verbose=False,pool='auto',**kwargs):
        '''
        :Parameters:
            pool : {'tag','day','auto',False}, default 'auto'
                'auto': pool on days if more days to load than tags otherwise pool on tags
                False or any other value will not pool the loading
            **kwargs Streamer.pool_tag_daily and Streamer.load_tag_daily
        '''
        if not len(tags)>0:return pd.DataFrame()
        loc_pool=pool
        if pool in ['tag','day','auto']:
            nbdays=len(pd.date_range(t0,t1))
            if pool=='auto':
                if nbdays>len(tags):
                    loc_pool='day'
                    if verbose:print_file('pool on days because we have',nbdays,'days >',len(tags),'tags')
                else:
                    loc_pool='tag'
                    if verbose:print_file('pool on tags because we have',len(tags),'tags >',nbdays,'days')

            if loc_pool=='day':
                n_cores=min(self._num_cpus,nbdays)
                if verbose:print_file('pool on days with',n_cores,'cores for',nbdays,'days')
                dftags={tag:self.pool_tag_daily(t0,t1,tag,folderpkl,ncores=n_cores,**kwargs) for tag in tags}
            elif loc_pool=='tag':
                n_cores=min(self._num_cpus,len(tags))
                if verbose:print_file('pool on tags with',n_cores,'cores for',len(tags),'tags')
                with Pool(n_cores) as p:
                    dftags=p.starmap(self.load_tag_daily_kwargs,[(t0,t1,tag,folderpkl,args,kwargs) for tag in tags])
                dftags={k.name:k for k in dftags}

        else:
            dftags = {}
            for tag in tags:
                if verbose:print(tag)
                dftags[tag]=self.load_tag_daily(t0,t1,tag,folderpkl,*args,**kwargs)

        empty_tags=[t for t,v in dftags.items() if v.empty]
        dftags = {tag:v for tag,v in dftags.items() if not v.empty}
        if len(dftags)==0:
            return pd.DataFrame(columns=dftags.keys())
        df = pd.concat(dftags,axis=1)
        for t in empty_tags:df[t]=np.nan
        df = df[df.index>=t0]
        df = df[df.index<=t1]
        return df
    # ########################
    #   HIGH LEVEL FUNCTIONS #
    # ########################
    def park_alltagsDF_minutely(self,df,folderpkl,pool=True):
        # check if the format of the file is correct
        correctColumns=['tag','timestampz','value']
        if not list(df.columns.sort_values())==correctColumns:
            print_file('PROBLEM: the df dataframe should have the following columns : ',correctColumns,'''
            or your columns are ''',list(df.columns.sort_values()),filename=self.log_file)
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
            # print_file(tm1,tm2)
            dfhour=df[(df.index>tm1)&(df.index<tm2)]
            print_file('start for :', dfhour.index[-1],filename=self.log_file)
            start=time.time()
            minutes=pd.date_range(tm1,tm2,freq='1T')
            df_minutes=[dfhour[(dfhour.index>a)&(dfhour.index<a+dt.timedelta(minutes=1))] for a in minutes]
            minutefolders =[folderpkl + k.strftime(self.format_folderminute) for k in minutes]
            # print_file(minutefolders)
            # sys.exit()
            if pool:
                with Pool() as p:
                    dfs = p.starmap(self.park_df_minute,[(fm,dfm,listTags) for fm,dfm in zip(minutefolders,df_minutes)])
            else:
                dfs = [self.park_df_minute(fm,dfm,listTags) for fm,dfm in zip(minutefolders,df_minutes)]
            print_file(computetimeshow('',start),filename=self.log_file)

    def createFolders_period(self,t0,t1,folderPkl,frequence='day'):
        if frequence=='minute':
            return self.foldersaction(t0,t1,folderPkl,self.create_minutefolder)
        elif frequence=='day':
            createfolderday=lambda x:os.mkdir(folderday)
            listDays = pd.date_range(t0,t1,freq='1D')
            listfolderdays = [folderPkl +'/'+ d.strftime(self._format_dayFolder) for d in listDays]
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
        return self.actiondays(t0,t1,folderpkl,self._fs.listfiles_pattern_folder,pattern,pool=pool)
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
    def __init__(self,folderPkl,dbParameters,parkingTime,tz_record='CET',dbTable='realtimedata',log_file=None):
        '''
        - parkedFolder : day or minute.
        - parkingTime : how often data are parked and db flushed in seconds
        '''
        Streamer.__init__(self,log_file=log_file)
        self.folderPkl = folderPkl
        self.dbParameters = dbParameters
        self.dbTable = dbTable
        self._dataTypes={
            'REAL': 'float',
            'float32': 'float',
            'BOOL': 'bool',
            'WORD': 'int',
            'DINT': 'int',
            'INT' : 'int',
            'int16' : 'int',
            'int32' : 'int',
            'STRING(40)': 'string'
             }
        self.streamer  = Streamer()
        self.tz_record = tz_record
        self.parkingTime = parkingTime##seconds
        #####################################
        # self.daysnotempty    = self.getdaysnotempty()
        # self.tmin,self.tmax  = self.daysnotempty.min(),self.daysnotempty.max()

    def getdaysnotempty(self):
        return self._fs.get_parked_days_not_empty(self.folderPkl)

    def connect2db(self):
        connReq = ''.join([k + "=" + v + " " for k,v in self.dbParameters.items()])
        return psycopg2.connect(connReq)

    def getUsefulTags(self,usefulTag):
        if usefulTag in self.usefulTags.index:
            category = self.usefulTags.loc[usefulTag,'Pattern']
            return self.getTagsTU(category)
        else:
            return []

    def getUnitofTag(self,tag):
        return self._fs.getUnitofTag(tag,self.dfplc)

    def getTagsTU(self,patTag,units=None,*args,**kwargs):
        if not units : units = self.listUnits
        return self._fs.getTagsTU(patTag,self.dfplc,units,*args,**kwargs)

class SuperDumper(Configurator):
    def __init__(self,devices,*args,log_file=None,**kwargs):
        Configurator.__init__(self,*args,**kwargs,log_file=log_file)
        self.parkingTimes = {}
        self.streamer     = Streamer()
        self.devices      = devices
        self._fs          = FileSystem()
        self.dfplc        = pd.concat([v.dfplc for k,v in self.devices.items()])
        self.alltags      = list(self.dfplc.index)

        self.dumpInterval = {}
        self.parkInterval = SetInterval(self.parkingTime,self.park_database)
        ###### DOUBLE LOOP of setIntervals for devices/acquisition-frequencies

        print_file(' '*20+'INSTANCIATION OF THE DUMPER'+'\n',filename=self.log_file,with_infos=False)
        for device_name,device in self.devices.items():
            freqs = device.dfplc['FREQUENCE_ECHANTILLONNAGE'].unique()
            device_dumps={}
            for freq in freqs:
                print_file(device_name,' : ',freq*1000,'ms',filename=self.log_file,with_infos=False)
                tags = list(device.dfplc[device.dfplc['FREQUENCE_ECHANTILLONNAGE']==freq].index)
                # print_file(tags)
                device_dumps[freq] = SetInterval(freq,device.insert_intodb,self.dbParameters,self.dbTable,self.tz_record,tags)

            self.dumpInterval[device_name] = device_dumps

    def read_db(self,*args,**kwargs):
        return read_db(self.dbParameters,self.dbTable,*args,**kwargs)

    def flushdb(self,t,full=False):
        connReq = ''.join([k + "=" + v + " " for k,v in self.dbParameters.items()])
        dbconn = psycopg2.connect(connReq)
        cur  = dbconn.cursor()
        if full:
            cur.execute("DELETE from " + self.dbTable + ";")
        else :
            cur.execute("DELETE from " + self.dbTable + " where timestampz < '" + t + "';")
        cur.close()
        dbconn.commit()
        dbconn.close()

    def feed_db_random_data(self,*args,**kwargs):
        df = self.generateRandomParkedData(*args,**kwargs)
        dbconn = self.connect2db()
        cur  = dbconn.cursor()
        sqlreq = "insert into " + self.dbTable + " (tag,value,timestampz) values "
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
        sqlQ ="select * from " + self.dbTable + " where timestampz < '" + t1.isoformat() +"'"
        sqlQ +="and timestampz > '" + t0.isoformat() +"'"
        print_file(sqlQ,filename=self.log_file)
        df = pd.read_sql_query(sqlQ,dbconn,parse_dates=['timestampz'])
        df = df[['tag','value','timestampz']]
        df['timestampz'] = pd.to_datetime(df['timestampz'])
        df       = df.set_index('timestampz')
        df.index = df.index.tz_convert('UTC')
        df = df.sort_index()

        namefile=folder + (t0+pd.Timedelta(days=1)).strftime(self._format_dayFolder).split('/')[0] +basename
        # df.to_csv(namefile)
        # zipObj = ZipFile(namefile.replace('.csv','.zip'), 'w')
        # zipObj.write(namefile,namefile.replace('.csv','.zip'))
        print_file(computetimeshow('database read',start),filename=self.log_file)
        namefile = namefile.replace('.csv','.pkl')
        df.to_pickle(namefile)
        print_file(namefile,' saved',filename=self.log_file)
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
            print_file(tag + ' generated')
        df=pd.concat(df.values(),axis=0)
        start = time.time()
        # df.timestampz = [t.isoformat() for t in df.timestampz]
        print_file(computetimeshow('timestampz to str',start),filename=self.log_file)
        df=df.set_index('timestampz')
        return df

    def checkTimes(self,name_device):
        def dict2df(d,name):
            df=pd.Series(d,name='value').sort_values().to_frame()
            df['group']=name
            return df
        device = self.devices[name_device]
        s_collect = dict2df(device._collectingTimes,'collection')
        s_insert  = dict2df(device._insertingTimes,'insertion')
        df=pd.concat([s_collect,s_insert])

        p = 1. * np.arange(len(s_collect))
        fig = px.histogram(df, x="value", color="group",hover_data=df.columns,nbins=20)
        return fig
    # ########################
    #       SCHEDULERS       #
    # ########################

    def stop_dumping(self):
        for device,dictIntervals in self.dumpInterval.items():
            for freq in dictIntervals.keys():
                self.dumpInterval[device][freq].stop()
        self.parkInterval.stop()

class SuperDumper_daily(SuperDumper):
    def start_dumping(self):
        now = pd.Timestamp.now(tz='CET')
        ##### start the schedulers at H:M:S:00 petante! #####
        time.sleep(1-now.microsecond/1000000)

        ######## start dumping
        print_file(timenowstd(),': START DUMPING',filename=self.log_file,with_infos=False)
        for device,dictIntervals in self.dumpInterval.items():
            self.devices[device].start_auto_reconnect()
            for freq in dictIntervals.keys():
                self.dumpInterval[device][freq].start()

        ######## start parking on time
        now = pd.Timestamp.now(tz='CET')
        # now = pd.Timestamp.now('2022-02-10 16:52:15',tz='CET')
        timer = 60-now.second
        print_file('parking should start at ',now +pd.Timedelta(seconds=timer),filename=self.log_file,with_infos=False)
        # time.sleep(timer)
        print_file(timenowstd(),': START PARKING',filename=self.log_file,with_infos=False)
        self.parkInterval.start()

    def park_single_tag_DB_URGENT(self,tag,deleteFromDb=False):
        print_file(tag)
        start = time.time()
        now = pd.Timestamp.now(tz=self.tz_record)
        ### read database
        dbconn = self.connect2db()
        sqlQ ="select * from " + self.dbTable + " where tag='"+tag+"' and timestampz<'"+now.isoformat()+"';"
        # print(sqlQ)
        df = pd.read_sql_query(sqlQ,dbconn,parse_dates=['timestampz'])
        print_file(computetimeshow('tag : '+tag+ ' read in '+self.dbTable + ' in '+ self.dbParameters['dbname'],start),filename=self.log_file)
        # check if database not empty
        if not len(df)>0:
            print_file('tag :'+tag+' not in table '+ self.dbTable + ' in ' + self.dbParameters['dbname'],filename=self.log_file)
            return
        # return df
        df=df.set_index('timestampz').tz_convert(self.tz_record)
        tmin,tmax = df.index.min().strftime('%Y-%m-%d'),df.index.max().strftime('%Y-%m-%d')
        listdays=[k.strftime(self._format_dayFolder) for k in pd.date_range(tmin,tmax)]
        #### in case they are several days
        for d in listdays:
            t0 = pd.Timestamp(d + ' 00:00:00',tz=self.tz_record)
            t1 = t0 + pd.Timedelta(days=1)
            dfday=df[(df.index>=t0)&(df.index<t1)]
            folderday=self.folderPkl + d +'/'
            #### create folder if necessary
            if not os.path.exists(folderday):os.mkdir(folderday)
            #################################
            #           park now            #
            #################################
            start=time.time()
            dftag = dfday[dfday.tag==tag]['value'] #### dump a pd.series
            self.parktagfromdb(tag,dftag,folderday)

        print_file(computetimeshow('tag : '+tag+ ' parked',start),filename=self.log_file)
        if deleteFromDb:
            # #delete the tag
            cur  = dbconn.cursor()
            sqlDel=sqlQ.replace('select *','DELETE')
            # print(sqlDel)
            cur.execute(sqlDel)
            cur.close()
            dbconn.commit()
            print_file(computetimeshow('tag : '+tag+ ' flushed',start),filename=self.log_file)

        dbconn.close()
        return dftag

    def parktagfromdb(self,tag,s_tag,folderday,verbose=False):
        namefile = folderday + tag + '.pkl'
        if verbose:print_file(namefile)
        if os.path.exists(namefile):
            s1 = pd.read_pickle(namefile)
            s_tag  = pd.concat([s1,s_tag])
        self.streamer.process_dbtag(s_tag,self._dataTypes[self.dfplc.loc[tag,'DATATYPE']]).to_pickle(namefile)

    def park_database(self,verbose=False):
        start = time.time()
        now = pd.Timestamp.now(tz=self.tz_record)
        t_parking = now

        ### read database
        dbconn = self.connect2db()
        sqlQ ="select * from " + self.dbTable + " where timestampz < '" + now.isoformat() +"'"
        try:
            ###########################################
            #    DANGEROUS WONT WORK WITH DST CHANGE  #
            ###########################################
            df = pd.read_sql_query(sqlQ,dbconn,parse_dates=['timestampz'])
        except:
            df = pd.read_sql_query(sqlQ,dbconn)
            df.timestampz=[pd.Timestamp(k).tz_convert('utc') for k in df.timestampz] #slower but will work with dst

        print_file(computetimeshow(self.dbTable + ' in '+ self.dbParameters['dbname'] +' for data <' + now.isoformat() +' read',start),
            filename=self.log_file,with_infos=False)
        # check if database not empty
        if not len(df)>0:
            print_file('table '+ self.dbTable + ' in ' + self.dbParameters['dbname'] + ' empty',filename=self.log_file)
            return
        dbconn.close()
        df=df.set_index('timestampz').tz_convert(self.tz_record)
        tmin,tmax = df.index.min().strftime('%Y-%m-%d'),df.index.max().strftime('%Y-%m-%d')
        listdays=[k.strftime(self._format_dayFolder) for k in pd.date_range(tmin,tmax)]
        #### in case they are several days(for example at midnight)
        for d in listdays:
            t0 = pd.Timestamp(d + ' 00:00:00',tz=self.tz_record)
            t1 = t0 + pd.Timedelta(days=1)
            dfday=df[(df.index>=t0)&(df.index<t1)]
            folderday=self.folderPkl+'/' + d +'/'
            #### create folder if necessary
            if not os.path.exists(folderday):os.mkdir(folderday)
            for tag in self.alltags:
                dftag = dfday[dfday.tag==tag]['value'] #### dump a pd.series
                self.parktagfromdb(tag,dftag,folderday,verbose=verbose)

        print_file(computetimeshow('database parked',start),filename=self.log_file)
        self.parkingTimes[now.isoformat()] = (time.time()-start)*1000
        # #FLUSH DATABASE
        self.flushdb(t_parking.isoformat())
        return

    def fix_timestamp(self,t0,tag,folder_save=None):
        t=t0 - pd.Timedelta(hours=t0.hour,minutes=t0.minute,seconds=t0.second)
        if folder_save is None:folder_save=self.folderPkl
        while t<pd.Timestamp.now(self.tz_record):
            filename = self.folderPkl +'/'+ t.strftime(self._format_dayFolder)+'/'+tag+'.pkl'
            if os.path.exists(filename):
                s=pd.read_pickle(filename)
                ####### FIX TIMESTAMP PROBLEM
                s.index=[k.tz_convert(tz=self.tz_record) for k in s.index]
                folder_day_save=folder_save +'/'+ t.strftime(self._format_dayFolder)+'/'
                ####### fix dupplicated index
                if not os.path.exists(folder_day_save):os.mkdir(folder_day_save)
                new_filename = folder_day_save + tag+'.pkl'
                s.to_pickle(new_filename)
            t = t + pd.Timedelta(days=1)

import plotly.graph_objects as go, plotly.express as px
class VisualisationMaster(Configurator):
    def __init__(self,*args,**kwargs):
        Configurator.__init__(self,*args,**kwargs)
        self.methods = self.streamer.methods
        self.utils=Utils()
        self.usefulTags=pd.DataFrame()


    def _load_database_tags(self,t0,t1,tags,*args,**kwargs):
        '''
        - t0,t1 : timestamps with tz
        - tags : list of tags
        '''
        # for k in t0,t1,tags,args,kwargs:print_file(k)
        dbconn = self.connect2db()
        if not isinstance(tags,list) or len(tags)==0:
                print_file('no tags selected for database',filename=self.log_file)
                return pd.DataFrame()

        sqlQ = "select * from " + self.dbTable + " where tag in ('" + "','".join(tags) +"')"
        sqlQ += " and timestampz > '" + t0.isoformat() + "'"
        sqlQ += " and timestampz < '" + t1.isoformat() + "'"
        sqlQ +=";"
        # print_file(sqlQ)
        start=time.time()
        df = pd.read_sql_query(sqlQ,dbconn,parse_dates=['timestampz'])
        dbconn.close()

        if len(df)==0:return df.set_index('timestampz')

        df.loc[df.value=='null','value']=np.nan
        df = df.set_index('timestampz')

        def process_dbtag(df,tag,*args,**kwargs):
            s = df[df.tag==tag]['value']
            dtype = self._dataTypes[self.dfplc.loc[tag,'DATATYPE']]
            s = self.streamer.process_dbtag(s,dtype)
            s = self.streamer.process_tag(s,*args,**kwargs)
            return s

        dftags = {tag:process_dbtag(df,tag,*args,**kwargs) for tag in tags}
        df = pd.concat(dftags,axis=1)
        df = df[df.index>=t0]
        df = df[df.index<=t1]
        return df

    def loadtags_period(self,t0,t1,tags,*args,pool='auto',verbose=False,**kwargs):
        """
        Loads tags between times t0  and t1.

        :Parameters:
            t0,t1 : [pd.Timestamp]
                Timestamps, t0 start and t1 end.
            tags : [list]
                List of tags available from self.dfplc.listtags

        :return:
            pd.DataFrame with ntags columns

        :see also:
            *args,**kwargs of VisualisationMaster.Streamer.process_tag
        """
        # for k in t0,t1,tags,args,kwargs:print_file(k)
        tags=list(np.unique(tags))
        ############ read parked data
        df = self.streamer.load_parkedtags_daily(t0,t1,tags,self.folderPkl,*args,pool=pool,verbose=verbose,**kwargs)
        ############ read database
        if t1<pd.Timestamp.now(self.tz_record)-pd.Timedelta(seconds=self.parkingTime):
            if verbose:print_file('no need to read in the database')
        else:
            df_db = self._load_database_tags(t0,t1,tags,*args,**kwargs)
            if not df_db.empty:
                if verbose:print_file('concatenated')
                df = pd.concat([df,df_db])
            if verbose:print_file('database read')
        return df.sort_index()

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
        def hex2rgb(h,a):
            return 'rgba('+','.join([str(int(h[i:i+2], 16)) for i in (0, 2, 4)])+','+str(a)+')'
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

    def multiMultiUnitGraph(self,df,*listtags,axSP=0.05):
        hs=0.002
        dictdictGroups={'graph'+str(k):{t:self.getUnitofTag(t) for t in tags} for k,tags in enumerate(listtags)}
        fig = self._utils.multiUnitGraphSubPlots(df,dictdictGroups,axisSpace=axSP)
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
        df.columns=['tag','value']
        df['unit']=df.apply(lambda x:tagMapping[x['tag']],axis=1)
        fig=px.scatter(df,y='value',color='tag',
                        facet_col='unit',facet_col_wrap=facet_col_wrap,
                        color_discrete_sequence = Utils().colors_mostdistincs)
        fig.update_traces(mode='lines+markers')
        fig.update_xaxes(matches='x')
        fig.update_yaxes(matches=None)
        return fig

class VisualisationMaster_daily(VisualisationMaster):
    def __init__(self,*args,**kwargs):
        VisualisationMaster.__init__(self,*args,**kwargs)
        self.folder_coarse=self.folderPkl.rstrip('/')+'_coarse/'
        if not os.path.exists(self.folder_coarse):os.mkdir(self.folder_coarse)
        if not os.path.exists(self.folder_coarse+'mean'):os.mkdir(self.folder_coarse+'mean')
        if not os.path.exists(self.folder_coarse+'max'):os.mkdir(self.folder_coarse+'max')
        if not os.path.exists(self.folder_coarse+'min'):os.mkdir(self.folder_coarse+'min')

    def _load_parked_tags(self,t0,t1,tags,pool):
        '''
        - t0,t1 : timestamps
        - tags : list of tags
        - pool:if true pool on tags
        '''
        if not isinstance(tags,list) or len(tags)==0:
            print_file('tags is not a list or is empty',filename=self.log_file)
            return pd.DataFrame(columns=['value','timestampz','tag']).set_index('timestampz')
        df = self.streamer.load_parkedtags_daily(t0,t1,tags,self.folderPkl,pool)
        # if df.duplicated().any():
        #     print_file("==========================================")
        #     print_file("WARNING : duplicates in parked data")
        #     print_file(df[df.duplicated(keep=False)])
        #     print_file("==========================================")
        #     df = df.drop_duplicates()
        return df

    def load_coarse_data(self,t0,t1,tags,rs,rsMethod='mean',verbose=False):
        #### load the data
        dfs={}
        empty_tags=[]
        for t in tags:
            filename=os.path.join(self.folder_coarse,rsMethod,t+'.pkl')
            if verbose:print(filename)
            if os.path.exists(filename):
                s=pd.read_pickle(filename)
                dfs[t]=s[~s.index.duplicated(keep='first')]
            else:
                empty_tags+=[t]

        if len(dfs)==0:
            return pd.DataFrame(columns=dfs.keys())
        df=pd.concat(dfs,axis=1)
        df=df[(df.index>=t0)&(df.index<=t1)]
        for t in empty_tags:df[t]=np.nan

        #### resample again according to the right method
        if rsMethod=='min':
            df=df.resample(rs).min()
        elif rsMethod=='max':
            df=df.resample(rs).max()
        else:
            if rsMethod=='mean':
                df=df.resample(rs).mean()
            elif rsMethod=='median':
                df=df.resample(rs).median()
            elif rsMethod=='forwardfill':
                df=df.resample(rs).ffill()
            elif rsMethod=='nearest':
                df=df.resample(rs).nearest()
        return df

    def park_coarse_data(self,tags=None,*args,**kwargs):
        if tags is None : tags=self.alltags
        for tag in tags:
            try:
                self._park_coarse_tag(tag,*args,**kwargs)
            except:
                print(timenowstd(),tag,' not possible to coarse-compute')

    def _get_t0(self,file_tag):
        t0=self.t0
        if os.path.exists(file_tag):
            s_tag=pd.read_pickle(file_tag)
            t1=s_tag.index.max()
            if s_tag.empty:t1=t0
            t0=max(t1,t0)
        return t0

    def _park_coarse_tag(self,tag,rs='60s',verbose=False,from_start=False):
        # self.t0=pd.Timestamp(pd.Series(os.listdir(self.folderPkl)).min()+' 00:00',tz=self.tz_record)
        self.t0=pd.Timestamp('2022-01-01 00:00',tz=self.tz_record)
        methods=['mean','min','max']
        start=time.time()
        ########### determine t0
        t0=min([self._get_t0(os.path.join(self.folder_coarse,m,tag + '.pkl') ) for m in methods])
        if from_start:
            t0=self.t0
        ######### load the raw data
        if verbose:print(tag,t0)
        s=self.streamer.load_tag_daily(t0,pd.Timestamp.now(self.tz_record),tag,self.folderPkl,rsMethod='raw',verbose=False)
        ######### build the new data
        s_new = {}
        if 'string' in self.dfplc.loc[tag,'DATATYPE'].lower():
            tmp = s.resample(rs,closed='right',label='right').ffill()
            s_new['mean'] = tmp
            s_new['min']  = tmp
            s_new['max']  = tmp
        else:
            s_new['mean'] = s.resample(rs,closed='right',label='right').mean()
            s_new['min']  = s.resample(rs,closed='right',label='right').min()
            s_new['max']  = s.resample(rs,closed='right',label='right').max()
        for m in methods:
            filename=os.path.join(self.folder_coarse, m,tag + '.pkl')
            if os.path.exists(filename) and not from_start:
                tmp=pd.concat([pd.read_pickle(filename),s_new[m]],axis=0).sort_index()
                s_new[m]=tmp[~tmp.index.duplicated(keep='first')]
            s_new[m].to_pickle(filename)
        if verbose:print(tag,'done in ',time.time()-start)

class Fix_daily_data():
    def __init__(self,conf):
        '''
        Parameters:
        ------------
        - conf:should be a sylfenUtils.ConfGenerator object
        '''
        self.conf=conf
        self.checkFolder=os.path.join(os.path.abspath(os.path.join(conf.FOLDERPKL,os.pardir)),conf.project_name+'_fix')
        create_folder_if_not(self.checkFolder)

    ########### PRIVATE
    def _load_raw_tag_day(self,tag,day,showTag_day=True,checkFolder=False):
        if checkFolder:
            filename = os.path.join(self.checkFolder,day,tag+'.pkl')
        else:
            filename = os.path.join(self.conf.FOLDERPKL,day,tag+'.pkl')
        if os.path.exists(filename):
            s= pd.read_pickle(filename)
        else :
            print(filename,'does not exist.')
            return
        if showTag_day:print(filename + ' read')
        return s

    def _to_folderday(self,timestamp):
        '''convert timestamp to standard day folder format'''
        return Streamer()._to_folderday(timestamp)

    def applyCorrectFormat_daytag(self,tag,day,newtz='CET',print_fileag=False,debug=False,checkFolder=False):
        '''
        Formats as pd.Series with name values and timestamp as index, remove duplicates, convert timestamp with timezone
        and apply the correct datatype

        :Parameters:
        ----------------
            - tag:str ==> the tag
            - day:str ==> the day
        '''
        tagpath=os.path.join(self.conf.FOLDERPKL,day,tag+'.pkl')
        if print_fileag:print(tagpath)
        ##### --- load pkl----
        if not os.path.exists(tagpath):print(tagpath,'does not exist');return
        try:s=pd.read_pickle(tagpath)
        except:print('pb loading',tagpath);return
        if s.empty:print('series empty for ',tagpath);return

        ##### --- make them format pd.Series with name values and timestamp as index----
        if isinstance(s,pd.DataFrame):
            df=s.copy()
            ### to put the timestamp as index
            col_timestamp=[k for k in df.columns if 'timestamp' in k]
            if len(col_timestamp)==1:
                df=df.set_index(col_timestamp)
            if len(df)>1:
                print('pb with',tagpath,'several columns where only one expected.')
                return
            s=df.iloc[:,0]
        ### make sure the name of the series is value.
        s.name='value'
        ##### --- remove index duplicates ----
        s = s[~s.index.duplicated(keep='first')]
        ##### --- convert tz ----
        if isinstance(s.index.dtype,pd.DatetimeTZDtype):
            s.index = s.index.tz_convert(newtz)
        else:### for cases with changing DST at 31.10 or if it is a string
            s.index = [pd.Timestamp(k).astimezone(newtz) for k in s.index]
        #####----- apply correct datatype ------
        try:dtype=DATATYPES[self.conf.dfplc.loc[tag,'DATATYPE']]
        except:print('impossible to find a valid DATATYPE of ',tag,'in conf.dfplc.')
        s=Streamer().process_dbtag(s,dtype)
        #####----- save the new pkl ------
        if checkFolder:
            folderday=os.path.join(self.checkFolder,day)
            create_folder_if_not(folderday)
            tagpath=os.path.join(folderday,tag+'.pkl')
        s.to_pickle(tagpath)

    ########### PUBLIC

    def load_raw_tag_period(self,tag,t0,t1,*args,**kwargs):
        t=t0
        dfs=[]
        while t<=t1:
            dfs.append(self._load_raw_tag_day(tag,self._to_folderday(t),*args,**kwargs))
            t=t+pd.Timedelta(days=1)
        return dfs

    def load_raw_tags_day(self,tags,day,*args,**kwargs):
        return {tag:self._load_raw_tag_day(tag,day,*args,**kwargs) for tag in tags}

    def applyCorrectFormat_day(self,day,dtypes,*args,**kwargs):
        tags = self.conf.dfplc.index.to_list()
        for tag in tags:
            self.applyCorrectFormat_daytag(tag,day,*args,**kwargs)

    def applyCorrectFormat_tag(self,tag,*args,**kwargs):
        print(tag)
        for day in os.listdir(self.conf.FOLDERPKL):
            self.applyCorrectFormat_daytag(tag,day,*args,**kwargs)
