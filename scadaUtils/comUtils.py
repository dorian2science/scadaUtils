# import importlib
import time, pytz,sys
from time import sleep
import sys,os,re,threading,struct, glob, pickle,struct,subprocess as sp
import numpy as np, pandas as pd
import psycopg2
from multiprocessing import Pool
import traceback
from .utils import Utils
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
DATATYPES={
    'REAL': 'float',
    'float32': 'float',
    'float': 'float',
    'bool': 'bool',
    'BOOL': 'bool',
    'WORD': 'int',
    'DINT': 'int',
    'INT' : 'int',
    'int16' : 'int',
    'uint16' : 'int',
    'int32' : 'int',
    'uint32' : 'int',
    'int64' : 'int',
    'uint64' : 'int',
    'STRING(40)': 'string',
    'IEEE754': 'float',
    'INT64': 'int'

     }
def create_folder_if_not(folder_path,*args,**kwargs):
    '''
    Checks if a folder exists and creates it if it does not exist

    :param str folder_path: path of the folder
    '''
    if not os.path.exists(folder_path):
        os.mkdir(folder_path)
        print_file('folder ' + folder_path + ' created!',*args,**kwargs)
def print_file(*args,filename=None,mode='a',with_infos=True,**kwargs):
    '''
    Prints with color code in a file with line number in code.

    :param str filename: file to print in, default None
    :param bool with_infos: default, True. If True, using line numbering and color code.
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
    print(Fore.RESET)
def print_error(tb,filename=None):
    exc_format=traceback.format_exception(*tb)
    ff=''
    for k in range(1,len(exc_format)-1):
        res=re.match('(.*.py")(.*line \d+)(.*)',exc_format[k]).groups()
        ff+=Fore.RED + res[0]+Fore.BLUE+res[1]+Fore.GREEN + res[2] + Fore.WHITE + '\n'
    print_file(ff,exc_format[-1],with_infos=False,filename=filename)
def html_table(df,title='table',useLinux=True):
    '''
    Render a DataFrame as an HTML table

    :param pd.Series or pd.DataFrame df: Serie or DataFrame
    :param str title: title of the table, default *table*
    :param bool useLinux:
    '''
    if useLinux:
        # path_linux='/tmp/table.html'
        path_linux=os.path.join(os.curdir,'table.html')
    else:
        path_linux=os.path.join(os.curdir,'table.html')
    f=open(path_linux,'w')
    f.write('<h1>'+title+'</h1>')
    if isinstance(df,pd.Series):df=df.to_frame()
    if isinstance(df,np.ndarray):df=pd.DataFrame(df   )
    df.to_html(f)
    f.close()
    sp.run('firefox '+path_linux,shell=True)
def read_db(db_parameters,db_table,t=None,tag=None,verbose=False,delete=False,regExp=True):
    '''
    Read the database.

    :param dict db_parameters: dict with localhost, port, dbnamme, user, and password keys
    :param str db_table: name of the table
    :param str t: timestamp with timezone under which data will be read (default None ==> read all)
    :param str tag: a regular expression or a tag (default None ==> read all)
    :param bool delete: if True, will just delete and not read
    :param bool regExp: if True, reg exp are used for tag
    '''
    connReq = ''.join([k + "=" + v + " " for k,v in db_parameters.items()])
    dbconn = psycopg2.connect(connReq)
    start="select * from " + db_table +" "
    if t is None : t=pd.Timestamp.now('CET').isoformat()
    sqlQ = start + "where timestampz < '" + t + "'"
    order_end=" order by timestampz asc;"
    if tag is None:
        sqlQ+=order_end
    else:
        symbol='='
        if regExp : symbol='~'
        tagPattern = " and tag " + symbol + "'" + tag + "'"
        sqlQ+=tagPattern+order_end
    if verbose:print_file(sqlQ)
    if delete:
        cur  = dbconn.cursor()
        sqlDel=sqlQ.replace('select *','DELETE')
        sqlDel=sqlDel.replace(order_end,';')
        # print_file(sqlDel)
        cur.execute(sqlDel)
        cur.close()
        dbconn.commit()
        if verbose:print_file('tag : ' + tag + ' flushed')
        dbconn.close()
        return
    try:
        ###########################################
        #    DANGEROUS WONT WORK WITH DST CHANGE  #
        ###########################################
        df = pd.read_sql_query(sqlQ,dbconn,parse_dates=['timestampz'])
    except:
        df = pd.read_sql_query(sqlQ,dbconn)
        df.timestampz=[pd.Timestamp(k).tz_convert('utc') for k in df.timestampz] #slower but will work with dst
    dbconn.close()
    return df
def dfplc_from_modbusmap(modbus_map):
    '''
    Returns a DataFrame *dfplc* from a modbus_map
    with columns description, unit, type and frequency

    :param pd.DataFrame modbus_map: a modbus map
    '''
    dfplc=modbus_map[['description','unit','type','frequency']]
    dfplc.columns=['DESCRIPTION','UNITE','DATATYPE','FREQUENCE_ECHANTILLONNAGE']
    return dfplc

to_folderday=lambda t:t.strftime(FORMAT_DAY_FOLDER)

class EmptyClass():pass

class FileSystem():
    ######################
    # FILE SYSTEMS  #
    ######################
    def load_confFile(self,filename,generate_func,generateAnyway=False):
        '''
        Load the configuration file

        :param str filename: name of the configuration file (format .pkl)
        :param generate_func: function to generate confFile if not exists
        :param bool generateAnyway: If True, will generate the confFile. Default False
        '''
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
        '''
        Flatten a given list of lists

        :param list list_of_lists: list of lists
        :return: a single list from a list of lists.
        :rtype: list
        '''
        if len(list_of_lists) == 0:
            return list_of_lists
        if isinstance(list_of_lists[0], list):
            return self.flatten(list_of_lists[0]) + self.flatten(list_of_lists[1:])
        return list_of_lists[:1] + self.flatten(list_of_lists[1:])

    def autoTimeRange(self,folderPkl,method='last'):
        '''
        Return a list of two strings representing a 8 hours time range
        determined based on the method specified.

        :param str folderPkl: folder path
        :param str method: 'last' or 'random'. 'last' will keep the most recent day of the folder, 'random' will choose above all days
        :rtype: list
        '''
        listDays = [pd.Timestamp(k.split('/')[-1]) for k in glob.glob(folderPkl+'*')]
        if method=='last':
            lastDay = max(listDays).strftime('%Y-%m-%d')
            hmax    = max([k.split('/')[-1] for k in glob.glob(folderPkl+lastDay+'/*')])
            t1      = lastDay + ' ' + hmax + ':00:00'
        elif method=='random':
            t1 = (pd.Series(listDays).sample(n=1).iloc[0]+dt.timedelta(hours=np.random.randint(8))).strftime('%Y-%m-%d')

        t0 = (pd.Timestamp(t1)-dt.timedelta(hours=8)).isoformat()
        return [t0,t1]

    def get_parked_days_not_empty(self,folderPkl,minSize=3,dict_size=3):
        '''
        Return a sorted pandas Series containing the dates of folders whose size is greater than *minSize*

        :param str folderPkl: folder path
        :param int minSize: minimum size in Mo of the folder to be taken in account, default 3
        :param int dict_size:
        :rtype: pd.Series
        '''

        '''dict_size:minimum size in Mo of the folder to be taken into account '''
        sizes={'G':1000,'K':0.001,'M':1}
        folders=[k.split('\t') for k in sp.check_output('du -h --max-depth=1 '+ folderPkl + ' | sort -h',shell=True).decode().split('\n')]
        '''liste la taille et noms de tous les répertoires et fichiers présents dans le répertoire folderPkl, triés par taille croissante.'''
        folders = [k for k in folders if len(k)==2]
        folders = [k for k in folders if len(re.findall('\d{4}-\d{2}-\d',k[1].split('/')[-1]))>0 ]
        folders={v.split('/')[-1]:float(k[:-1].replace(',','.'))*sizes[k[-1]] for k,v in folders}
        daysnotempty = pd.Series(folders)
        daysnotempty = [k for k in daysnotempty[daysnotempty>dict_size].index]
        daysnotempty = pd.Series([pd.Timestamp(k,tz='CET') for k in daysnotempty]).sort_values()
        return daysnotempty

    def createRandomInitalTagValues(self,listTags,dfplc):
        '''
        Return a dict valueInit containing initial randomized values for a list of tags

        :param list listTags: list of tags
        :param dataframe dfplc: dataframe with columns *DESCRIPTION*, *UNITE*, *DATAYPE*, *FREQUENCY* and tags as index.
        :rtype: dict
        '''
        valueInit={}
        for tag in listTags:
            tagvar=dfplc.loc[tag]
            if tagvar.DATATYPE=='STRING(40)':
                valueInit[tag] = 'STRINGTEST'
            else:
                valueInit[tag] = np.random.randint(tagvar.MIN,tagvar.MAX)
        return valueInit

    def listfiles_folder(self,folder):
        '''
        Return a list of files contained in the folder

        :param str folder: path of the folder to search in
        :rtype: list
        '''
        listFiles=[]
        if os.path.exists(folder):
            listFiles = os.listdir(folder)
        return listFiles

    def listfiles_pattern_folder(self,folder,pattern):
        '''
        Return a list of files contained in the folder whose name matches with pattern

        :param str folder: path of the folder to search in
        :param str pattern: pattern
        :rtype: list
        '''
        listFiles=[]
        if os.path.exists(folder):
            listFiles = [k.split('/')[-1] for k in glob.glob(folder+'/*'+pattern+'*')]
        return listFiles

    def getUnitofTag(self,tag,dfplc):
        '''
        Return the unit of the tag

        :param str tag: name of the tag
        :param dataframe dfplc: plc dataframe with tags in index
        :rtype: str
        '''
        unit=dfplc.loc[tag].UNITE
        # print_file(unit)
        if not isinstance(unit,str):
            unit='u.a'
        return unit

    def getTagsTU(self,patTag,dfplc,units=None,onCol='index',cols='tag'):
        '''
        Return a dataframe or a list containing tags matching with 'patTag' whose unit matches with 'units'

        :param str patTag: pattern, *insensitive to case*
        :param dataframe dfplc: plc dataframe with tags in index
        :param str or list[str] units: list of units, default None
        :param str onCol: name of the dataframe column to search in, default 'index'
        :param str cols: {'tag', 'tdu', None} default 'tag'
        :rtype: list if *cols* is 'tag', else pd.DataFrame
        '''
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
    '''
    Run the function *action* every *interval* seconds.
    Start on a multiple of *interval*
    Skip intermediate calls if the action takes longer for the interval to start stack.

    :param int interval: time interval
    :param str action: function to execute
    :param args: arguments for function *action*
    '''
    def __init__(self,interval,action,*args):
        self.argsAction=args
        self.interval  = interval
        self.action    = action
        self.stopEvent = threading.Event()
        self.thread    = threading.Thread(target=self.__SetInterval)

    def start(self):
        '''
        Start a new thread
        '''
        self.thread.start()

    def __SetInterval(self):
        nextTime=time.time()
        while not self.stopEvent.wait(nextTime-time.time()):
            self.action(*self.argsAction)
            nextTime+=self.interval
            while nextTime-time.time()<0:
                nextTime+=self.interval

    def stop(self):
        '''
        Stop the active thread
        '''
        self.stopEvent.set()
        self.thread.join()

# #######################
# #      DEVICES        #
# #######################
class Device():
    """
    Construtor: instanciate a device.

    :param str device_name: name of the device
    :param str ip: ip adress of the device
    :param int port: port of the connection of the device
    :param pd.DataFrame dfplc: plc dataframe with tags in index
    :param list[tuples] time_outs_reconnection: default None
    :param str log_file: path of the file where to log the infos. Default is None will return in the console.

    For inheritance :
        - a function **collectData** should be written  to collect data from the device.
        - a function **connectDevice** to connect to the device.
    """
    def __init__(self,device_name,ip,port,dfplc,time_outs_reconnection=None,log_file=None):
        STREAMER               = FileSystem()
        self._utils            = Utils()
        self._protocole        = 'undefined'
        self.device_name       = device_name
        self.ip                = ip
        self.port              = port
        self.log_file          = log_file
        self._isConnected      = False
        self._auto_connect     = threading.Event()
        self._auto_connect.set()
        if time_outs_reconnection is None:
            time_outs_reconnection=[(2,k) for k in [3,5,10,30,60,60*2,60*5,60*10,60*20,60*30,60*40,60*50]]
            # time_outs_reconnection=[(1,k) for k in [1]]
            time_outs_reconnection.append((100000,60*60))
        self._time_outs_reconnection = time_outs_reconnection
        self._timeOuts_counter  = 0
        self._current_trial     = 0
        self._current_timeOut   = self._time_outs_reconnection[0][1]

        self.dfplc = dfplc
        self.collectError_absolute      = 0
        self.collectError_consecutive   = 0
        self.clockLast                  = pd.Timestamp.now()

        if not self.dfplc is None:
            self.listUnits = self.dfplc.UNITE.dropna().unique().tolist()
            self._get_frequencies()

    def _update_log_file(self,log_file):
        '''
        Update *log_file* and create an attribute '_collect_file' which is the path of the .csv file where to collect logs

        :param str log_file: path of the file where to log the infos.
        '''
        self.log_file=log_file
        if self.log_file is None:
            self._collect_file = None
        else:
            self._collect_file  = os.path.join(os.path.dirname(self.log_file),
                self.device_name + '_collectTimes.csv')

    def _get_frequencies(self,):
        '''
        Return a dictionnary containing frequencies as keys and list of tags as values

        '''
        col_freq='FREQUENCE_ECHANTILLONNAGE'
        # self.tags_freqs = {freq: list(group.index) for freq, group in self.dfplc.groupby(col_freq)}
        self.tags_freqs = {freq: group.index for freq, group in self.dfplc.groupby(col_freq)}
        return self.tags_freqs

    # @abstract_method
    def connectDevice(self,state=None):
        '''
        **function description missing**

        :param bool state: status of connection, default None
        '''
        if state is None:self._isConnected=np.random.randint(0,2)==1
        else:self._isConnected=state
        return self._isConnected

    def start_auto_reconnect(self):
        '''
        **function description missing**
        '''
        if self._auto_connect.is_set():
            self.stop_auto_reconnect()
        self._auto_connect.clear()
        self.connectDevice()
        self._thread_reconnection = threading.Thread(target=self._checkConnection)
        self._thread_reconnection.start()

    def stop_auto_reconnect(self):
        '''
        **function description missing**
        '''
        if not self._auto_connect.is_set():
            self._auto_connect.set()
            self._thread_reconnection.join()

    def _checkConnection(self):
        '''
        Check connection
        '''
        while not self._auto_connect.wait(self._current_timeOut):
            # print_file('checking if device still connected')
            if not self._isConnected:
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
                    msg=timenowstd()+' : Connexion to '+self.device_name+' established again!!\n'
                else :
                    msg=timenowstd()+' : --> impossible to connect to device '+self.device_name
                    msg+='. Try new connection in ' + str(self._current_timeOut) + ' seconds\n'

                print_file(full_msg+msg+'-'*60+'\n',filename=self.log_file)

    def _generate_sql_insert_tag(self,tag,value,timestampz,dbTable):
        '''
        Generate a query to insert tag, value and timestamp into database *dbTable*

        :param str dbTable: name of table in database where to insert
        :rtype: str
        '''
        sqlreq = "insert into " + dbTable + " (tag,value,timestampz) values ('"
        if value==None:value = 'null'
        value = str(value)
        sqlreq+= tag +"','" + value + "','" + timestampz  + "');"
        return sqlreq.replace('nan','null')

    def insert_intodb(self,dbParameters,dbTable,*args,verbose=False,**kwargs):
        '''
        Insert into database datas that are collected with *self.collectData*.
        Function only works if there is a valid dfplc attribute.

        :param dict dbParameters: database parameters
        :param str dbTable: name of the database table
        :param \*args: arguments of *self.collectData*
        :param \**kwargs: arguments of *self.collectData*
        '''
        if self.dfplc is None:return 'pb dfplc'
        if not self._isConnected:
            return 'pb connection'
        ##### connect to database ########
        try :
            connReq = ''.join([k + "=" + v + " " for k,v in dbParameters.items()])
            dbconn = psycopg2.connect(connReq)
        except:
            print_file('problem connecting to database ',dbParameters,filename=self.log_file)
            return 'pb database'
        cur  = dbconn.cursor()
        start=pd.Timestamp.now().timestamp()


        ##### collect data ########
        data = self.collectData(*args,**kwargs)

        ###### JUST FOR DEBUG (REMOVE IT IN PRODUCTION)####
        # data = 'unkown error'
        ###### JUST FOR DEBUG (REMOVE IT IN PRODUCTION)####

        ##### handle exception ==> log ########
        if isinstance(data,str):
            msg=timenowstd() + ' : ' + self.device_name
            if data=='connection error':
                msg+=' --> connexion to device impossible.'
                self._isConnected = False
                print_file(msg,filename=self.log_file)
            else:
                self.collectError_absolute+= 1
                self.collectError_consecutive+= 1
                duration_failing_secs=start-self.clockLast.timestamp()
                if self.collectError_consecutive==1 or duration_failing_secs>59 or verbose:#### check every hour
                    msg+=' --> collectData was consecutively failing(consecutive:'
                    msg+=str(self.collectError_consecutive) + ', totally:'+str(self.collectError_absolute) +')'
                    msg+=' due to:' + data
                    print_file(msg,filename=self.log_file)
                    self.clockLast=pd.Timestamp.now()
            return 'pb collect'

        ##### if there it means it worked fine ########
        self.clockLast=pd.Timestamp.now()
        time_collect=[self.clockLast.strftime('%Y-%b-%d %H:%M:%S.%f')[:-3],str(round((pd.Timestamp.now().timestamp()-start)*1000))+' ms']
        self.collectError_consecutive = 0
        ##### insert the data in database ########
        for tag in data.keys():
            sqlreq=self._generate_sql_insert_tag(tag,data[tag]['value'],data[tag]['timestampz'],dbTable)
            cur.execute(sqlreq)
        dbconn.commit()
        cur.close()
        dbconn.close()
        ##### store collecting times  ########
        time_collect+=[str(round((pd.Timestamp.now().timestamp()-start)*1000))+' ms']
        if not self._collect_file is None:
            print_file(' ; '.join(time_collect),filename=self._collect_file)
        return 1

    def createRandomInitalTagValues(self):
        '''
        Return a dict valueInit containing initial randomized values for a list of tags.

        .. note:: See **FileSystem.createRandomInitalTagValues()**

        :rtype: dict
        '''
        return STREAMER.createRandomInitalTagValues(list(self.device.index),self.dfplc)

    def getUnitofTag(self,tag):
        '''
        Return the unit of the tag from dfplc.

        .. note:: See **FileSystem.getUnitofTag()**

        :param str tag:
        :rtype: str
        '''
        return STREAMER.getUnitofTag(tag,self.dfplc)

    def getTagsTU(self,patTag,units=None,*args,**kwargs):
        '''
        Return a dataframe or a list containing tags matching with *patTag* whose unit matches with *units*.

        .. note:: See **FileSystem.getTagsTU()**

        :param str patTag: pattern of tag, insensitive to case
        :param str or list[str] units: list of units, default None
        '''
        if self.dfplc is None:
            print_file('no dfplc. Function unavailable.')
            return
        if not units : units = self.listUnits
        return FileSystem().getTagsTU(patTag,self.dfplc,units,*args,**kwargs)

    def get_connection_status(self):
        '''
        Print connection status

        '''
        print('is connected'.ljust(50),self._isConnected)
        reconnecting=not self._auto_connect.is_set()
        print('is trying reconnection'.ljust(50),reconnecting)
        if reconnecting:
            print('next reconnection in :'.ljust(50),self._current_timeOut,'seconds')
            print('trial at that frequency :'.ljust(50),self._current_trial)
            print('for infos it will try to reconnect following this timeout :',self._time_outs_reconnection)

from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian
class ModbusDevice(Device):
    '''
    Instanciate a ModbusDevice, inherited of the class *Device*

    :param str ip: ip adress of the device
    :param int port: port of the connection of the device, default 502
    :param str device_name: name of the device
    :param pd.DataFrame modbus_map: map of the modbus, default None
    :param str bo: byte order, default big
    :param str wo: word order, default big

    '''
    def __init__(self,ip,port=502,device_name='',modbus_map=None,bo='big',wo='big',type_registers='',**kwargs):
        self.modbus_map = modbus_map
        self.byte_order,self.word_order = bo,wo
        self.type_registers=type_registers
        if not modbus_map is None:
            dfplc=dfplc_from_modbusmap(self.modbus_map)
        else:
            dfplc=None
        Device.__init__(self,device_name,ip,port,dfplc,**kwargs)
        self._protocole = 'modbus'

        if not self.modbus_map is None:
            self.slave_ids = list(self.modbus_map.slave_unit.unique())
        self._client = ModbusClient(host=self.ip,port=int(self.port))

    def connectDevice(self):
        '''
        Connect the Modbus Client

        :returns: connection status
        '''
        self._isConnected=False
        try:
            self._isConnected=self._client.connect()
        except:
            self._isConnected=False
        return self._isConnected

    def quick_decode_tag(self,tag,input=False):
        infos=self.modbus_map.loc[tag,['intaddress','type','slave_unit','scale']]
        print_file(infos)
        reg,dtype,unit,scale=infos
        nbs=int(4*int(re.findall('\d{2}',dtype)[0])/64)
        return self.quick_modbus_single_register_decoder(reg,nbs,dtype,unit=unit,input=input,scale=scale)

    def quick_modbus_single_register_decoder(self,reg,nbs,dtype,unit=1):
        '''
        Decode modbus single registers

        :param int reg: register address (0 to 65535)
        :param int nbs: **number of registers to decode (1 to 125)**
        :param str dtype: **data type ?**
        :rtype: dictionnary
        '''
        # self._client.connect()
        # print_file(locals())
        if input:
            result = self._client.read_input_registers(reg, nbs, unit=unit)
        else:
            result = self._client.read_holding_registers(reg, nbs, unit=unit)
        decoders={}
        decoders['bo=b,wo=b'] = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Big, wordorder=Endian.Big)
        decoders['bo=b,wo=l'] = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Big, wordorder=Endian.Little)
        decoders['bo=l,wo=b'] = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Little, wordorder=Endian.Big)
        decoders['bo=l,wo=l'] = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Little, wordorder=Endian.Little)
        values ={k:self._decode_register(d,dtype)*scale for k,d in decoders.items()}
        print('='*60+'\nvalues are \n',pd.Series(values))
        return values

    def decode_bloc_registers(self,bloc,*args,**kwargs):
        '''
        Return a dataframe

        :param pd.DataFrame bloc: should be continuous and contain:

            - type column with the datatypes
            - intaddress with the adress of the registers
            - scale with scales to apply
        :rtype: pd.DataFrame
        '''
        blocks=self._get_continuous_blocks(bloc)
        index_name=bloc.index.name
        if index_name is None:index_name='index'
        return pd.concat([self._decode_continuous_bloc(b,*args,**kwargs) for b in blocks],axis=0).set_index(index_name)

    def collectData(self,tz,tags=None):
        '''
        It will collect all the data if a dataframe modbus_map is present with columns
            - index : name of the registers or tags.
            - type  : datatype{uint16,int32,float...}
            - scale : the multiplication factor
            - intaddress :  for the adress in decimal format
            - slave_unit : the slave unit

        :param str tz: timezone
        :param list[str] tags: list of tags whose data you want to collect, default None. If None, collect all datas
        :rtype: pd.DataFrame
        '''
        try:
            if self.modbus_map is None:
                print_file('no modbus_map was selected. Collection not possible.')
                return
            d={}
            bbs=[]
            if tags is None:
                tags=self.modbus_map.index.to_list()
            local_modbus_map=self.modbus_map.loc[tags]
            for unit_id in local_modbus_map.slave_unit.unique():
                bloc=local_modbus_map[local_modbus_map.slave_unit==unit_id]
                bb=self.decode_bloc_registers(bloc,unit_id)
                # print_file(bb)
                bb['timestampz']=pd.Timestamp.now(tz=tz).isoformat()
                bbs+=[bb]
            d=pd.concat(bbs)[['value','timestampz']].T.to_dict()
            return d
        except Exception as e:
            self.err=e
            # if 'failed to connect' in e.string.lower().strip():
            msg_err=e.args[0].lower().strip()
            return 'connection error'
            if 'failed to connect' in msg_err:
                return 'connection error'
            else:
                return 'error:' + msg_err
    #####################
    # PRIVATE FUNCTIONS #
    #####################
    def _decode_continuous_bloc(self,bloc,unit_id=1):
        '''
        **function description missing**

        :param pd.DataFrame bloc: *bloc* should be continuous and contain:
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
            if self.type_registers=='input':
                result = self._client.read_input_registers(start, end-start, unit=unit_id)
            else:
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
        '''
        Return a copy of bloc with column 'size_words' referring to the size of the datatype

        :param pd.DataFrame bloc: *bloc* should be continuous and contain:
            - type column with the datatypes
            - intaddress with the adress of the registers
            - scale with scales to apply
        '''
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
        '''
        Return a list of blocks from intadress cut into 100 blocks

        :param pd.DataFrame bloc: should be continuous and contain:
            - type column with the datatypes
            - intaddress with the adress of the registers
            - scale with scales to apply
        '''
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
        '''

        Return a list of dataframes representing continuous blocks from initial dataframe

        :param pd.DataFrame bloc: should be continuous and contain:
            - type column with the datatypes
            - intaddress with the adress of the registers
            - scale with scales to apply
        :rtype: list

        '''
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
        '''
        **function description missing**

        :param pd.DataFrame bloc: should be continuous and contain:
            - type column with the datatypes
            - intaddress with the adress of the registers
            - scale with scales to apply
        '''
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
        '''
        Decode register

        :param decoder: **param missing**
        :param str dtype: datatype to decode

        '''
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
    '''
    Instanciate an Opcua_Client, inherited of the class *Device*

    :param str ip: ip adress of the device
    :param int port: port of the connection of the device, default 502
    :param str device_name: name of the device
    :param pd.DataFrame dfplc: plc dataframe with tags as index, default None
    :param str bo: byte order, default big
    :param str wo: word order, default big
    :param str nameSpace: nameSpace

    '''
    def __init__(self,*args,nameSpace,protocole='opc.tcp',**kwargs):
        Device.__init__(self,*args,**kwargs)
        self._protocole = 'opcua'

        self._nameSpace = nameSpace
        self._protocole = protocole
        self.ip = self.ip
        self.endpointurl = self._protocole + '://' +self.ip+":"+str(self.port)
        self._client     = opcua.Client(self.endpointurl)
        ####### load nodes
        self._nodesDict  = {t:self._client.get_node(self._nameSpace + t) for t in list(self.dfplc.index)}
        self._nodes      = list(self._nodesDict.values())

    def loadPLC_file(self):
        '''
        Load the configuration file of OPCUA Client and returns a pd.DataFrame 'dfplc'

        :return: configuration of plc
        :rtype: pd.DataFrame
        '''
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
        '''
        Connect the OPCUA Client

        '''
        try:
            self._client.connect()
            self._isConnected=True
        except:
            self._isConnected=False
        return self._isConnected

    def collectData(self,tz,tags):
        '''
        Collect the data and returns a dictionnary with tags as keys
        and values & timestamps as values

        :param str or timezone object tz: timezone to localize to
        :param list tags: list of tags
        :returns: a dictionnary with tags as keys and values & timestams as values
        :rtype: dictionnary

        '''
        nodes = {t:self._nodesDict[t] for t in tags}
        values = self._client.get_values(nodes.values())
        ts = pd.Timestamp.now(tz=tz).isoformat()
        data = {tag:{'value':val,'timestampz':ts} for tag,val in zip(nodes.keys(),values)}
        return data

    def _set_security(self,certif_path,key_path,password,user):
        '''
        **Function description missing**
        '''
        sslString = 'Basic256Sha256,Sign,' + certif_path + ',' + key_path
        if CONF.SIMULATOR:
            print_file('security check succedeed because working with SIMULATOR==>no need to enter credentials and rsa keys\n',filename=self.log_file,with_infos=False)
        else:
            try:
                self._client.set_security_string(sslString)
                self._client.set_user(user)
                self._client.set_password(password)
                print_file('beckhoff security check succeeded!',filename=self.log_file)
            except:
                print_file('beckhoff security check FAILED',filename=self.log_file)

import pyads
class ADS_Client(Device):
    '''
    Instanciate an ADS_Client, inherited of the class *Device*

    :param str device_name: name of the device
    :param str ip: ip adress of the device
    :param int port: port of the connection of the device, default 851
    :param pd.DataFrame dfplc: plc dataframe with tags in index
    :param str bo: byte order, default big
    :param str wo: word order, default big
    :param str nameSpace: nameSpace
    '''
    def __init__(self,*args,port=851,check_values=False,**kwargs):
        Device.__init__(self,*args,port=port,**kwargs)
        self._protocole = 'ads'
        self.ip        = self.ip
        self.TARGET_IP = self.ip + '.1.1'
        self.unknown_error = False
        self.plcs      = {f:pyads.Connection(self.TARGET_IP,int(self.port)) for f in self.tags_freqs.keys()}
        if check_values:
            tags=self.detect_tag_pb()
            if len(tags)>0:
                print_file('problem with those tags',tags,'\n','-'*60,'\n',
                    'THE PROGRAMM HAD TO KILL.',
                    filename=self.log_file)
                sys.exit()

    def drop_unreadable_tags(self,tags2Remove=None):
        '''
        Remove unreadable or problematic tags and return a dictionnary containing frequencies as keys and list of tags as values

        :param str tags2Remove: tags to remove, default None. If None, will detect problematic tags and remove them
        :returns: dictionnary containing frequencies as keys and list of tags as values
        :rtype: dictionnary
        '''
        if tags2Remove is None:
            tags2Remove=self.detect_tag_pb()
        self.dfplc=self.dfplc.drop(tags2Remove)
        self._get_frequencies()

    def detect_tag_pb(self,result='pb_tags',timeDebug=False):
        '''
        Detect problematic tags

        :param str result: 'vals', 'pbs' or 'pb_tags', default 'pb_tags'

            - 'vals' will return all valid values
            - 'pbs' all problematic tags with error messages
            - 'pb_tags' only problematic tags
        :param bool timeDebug: default False. If True, will print debug time
        '''
        pbs,vals={},{}
        tags=list(self.dfplc.index)
        start=time.time()
        self.connectDevice()
        for k,t in enumerate(tags):
            try:
                plc=list(self.plcs.values())[0]
                vals[t]=plc.read_by_name('GVL.'+t)
            except Exception as e:
                pbs[k]={'tag':t,'error':e}

        if timeDebug:print(time.time()-start)

        if result=='pb_tags':
            return [v['tag'] for k,v in pbs.items()]
        elif result=='vals':
            return vals
        elif result=='pbs':
            return pbs

    def _get_machine_ip(self):
        '''
        Return IP address
        '''
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_local=s.getsockname()[0]
        s.close()
        return ip_local

    def _initialize_route(self,username="Administrator",password="1"):
        '''
        **Function description missing**

        :param str username: name of the user. Default *'Administrator'*
        :param str password: password of the user. Default *"1"*
        '''
        import socket
        # create some constants for connection
        CLIENT_IP       = self._get_machine_ip()
        CLIENT_NETID    = CLIENT_IP +".1.1"
        HOST_IP         = self.ip
        TARGET_USERNAME = username
        TARGET_PASSWORD = password
        ROUTE_NAME      = 'route_to_'+socket.gethostname()
        pyads.open_port()
        pyads.set_local_address(CLIENT_NETID)
        pyads.add_route_to_plc(
            CLIENT_NETID, CLIENT_IP, HOST_IP, TARGET_USERNAME, TARGET_PASSWORD,
            route_name=ROUTE_NAME
        )
        pyads.close_port()
        # return locals()

    def connectDevice(self):
        '''
        Connect the ADS Client
        '''
        if self.unknown_error:
            for plc in self.plcs.values():
                plc.close()
                self._isConnected=False
                print_file('connection was closed here',self.log_file)
                self.unknown_error=False
        try:
            for plc in self.plcs.values():
                plc.open()
                plc.read_state()
            self._isConnected=True
        except:
        # except Exception as e:
            # print_file(e.string)
            self._isConnected=False
        return self._isConnected

    def close_connection(self):
        '''
        Close connection
        '''
        for plc in self.plcs.values():
            plc.close()

    def collectData(self,tz,tags,freq=None):
        '''
        Collect all the data from the device

        :param str or timezone object tz: timezone to use
        :param list[str] tags: list of tags
        :param float freq: if there are several connections to the device precise the unit.
        :returns: a dictionnary with tags as keys and values & timestamps as values
        :rtype: dictionnary
        '''
        listtags=['GVL.'+t for t in tags]
        ts = pd.Timestamp.now(tz=tz).isoformat()
        try:
            if freq is None:freq=list(self.plcs.keys())[0]
            values=self.plcs[freq].read_list_by_name(listtags)
            data = {tag.strip('GVL.'):{'value':val,'timestampz':ts} for tag,val in values.items()}

            ######## FOR DEBUGGING ONLY #######################
            ###### trigger the error intentionally and randomly
            # trigger_error=np.random.randint(0,20)
            # if trigger_error==1:
            #     e=Exception('unknown error')
            #     e.err_code=-1
            #     e.msg='unknown error'
            #     raise e
            ######## FOR DEBUGGING ONLY #######################

            return data
        except Exception as e:
            try:
                if e.err_code==1864:## port not opened
                    return 'connection error'
                elif 'unknown error' in e.msg.lower():
                ###### this is time to close the connections #######
                    self.unknown_error=True
                    self._isConnected=False
                return e.msg
            except:
                print_file(e)
                return 'internal error'

import urllib.request, json
class Meteo_Client(Device):
    '''
    Instanciate a new device Meteo_Client, inherited of the class *Device*

    :param int freq: acquisition time in seconds
    '''
    def __init__(self,freq=30,**kwargs):
        self.freq    = freq
        self.cities  = pd.DataFrame({'le_cheylas':{'lat' : '45.387','lon':'6.0000'}})
        self.baseurl = 'https://api.openweathermap.org/data/2.5/'
        dfplc = self.build_plcmeteo(self.freq)
        Device.__init__(self,'meteo',self.baseurl,None,dfplc)
        self.apitoken = '79e8bbe89ac67324c6a6cdbf76a450c0'
        # self.apitoken = '2baff0505c3177ad97ec1b648b504621'# Marc
        self.t0 = pd.Timestamp('1970-01-01 00:00',tz='UTC')

    def build_plcmeteo(self,freq):
        '''
        Build a weather dataframe from openweathermap.org with temp, pressure, humidity, clouds and wind_speed from the given city (currently, le cheylas).
        Columns are *MIN*, *MAX*, *UNITE*, *DESCRIPTION*, *DATATYPE*, *DATASCIENTISM*, *PRECISION*, *FREQUENCE_ECHANTILLONNAGE*, *VAL_DEF*

        :param int freq: acquisition time in seconds
        :rtype: pd.DataFrame
        '''
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
        '''
        Connect the objects to the meteo server
        '''
        try:
            request = urllib.request.urlopen('https://api.openweathermap.org/',timeout=2)
            print_file("Meteo : Connected to the meteo server.",filename=self.log_file)
            self._isConnected=True
        except:
            print_file("Meteo : No internet connection or server not available.",filename=self.log_file)
            self._isConnected=False
        return self._isConnected

    def collectData(self,tz='CET',tags=None):
        '''
        Collect weather data for the given city

        :param str or timezone object tz: timezone, default *CET*
        :param list[str] tags: default None
        :rtype: dictionnary
        '''
        df = pd.concat([self.get_dfMeteo(city,tz) for city in self.cities])
        return {tag:{'value':v,'timestampz':df.name} for tag,v in df.to_dict().items()}

    def get_dfMeteo(self,city,tz,ts_from_meteo=False):
        '''
        Return the weather (temperature, pressure, humidity, cloud cover and wind speed) for the given cities (currently, le cheylas).
        Can lead to duplicates in the data

        :param str city: city
        :param str or timezone object: timezone
        :param bool ts_from_meteo: default None. If True, the timestamp corresponds to the one given by the weather data server.
        :returns:
        :rtype: pd.DataFrame
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

    def dfMeteoForecast(self):
        '''
        Build a forecast weather dataframe
        '''
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
    '''
    Instanciate the object **Basic_streamer**
    Streamer enables to perform action on parked Day/Hour/Minute folders.
    It comes with basic functions like loaddata_minutefolder/create_minutefolder/parktagminute.

    :param str log_file: path of the file

    '''
    def __init__(self,log_file=None):
        self.methods=['ffill','nearest','mean','max','min','median','interpolate','rolling_mean','mean_mix']
        self._num_cpus = psutil.cpu_count(logical=False)
        STREAMER = FileSystem()
        self.log_file=log_file

    def _to_folderday(self,timestamp):
        '''
        Convert timestamp to standard day folder format

        :param str or timestamp object timestamp: timestamp
        '''
        return timestamp.strftime(self._format_dayFolder)

def to_type(x,dtype):
    try:
        if dtype=='string':
            return str(x)
        if dtype=='float':
            return float(x)
        elif dtype=='int':
            return int(x)
    except:
        return np.nan

class Streamer(Basic_streamer):
    '''
    Instanciate an object *Streamer*, inherited of the class **Basic_streamer**
    Streamer enables to perform action on parked Day/Hour/Minute folders.
    It comes with basic functions like loaddata_minutefolder/create_minutefolder/parktagminute.
    '''
    def __init__(self,*args,**kwargs):
        Basic_streamer.__init__(self,*args,**kwargs)
        self._format_dayFolder='%Y-%m-%d'

    def park_tags(self,df,tag,folder,dtype,showtag=False):
        '''
        Park all the values from a dataframe *df* for a given tag in a pickle file

        :param pd.DataFrame df: dataframe
        :param str tag: tag whose data to save
        :param str folder: path of the folder
        :param str dtype: data type
        :param bool showtag: default False. If True, applies the **print_file** function with *tag* as parameter
        '''
        if showtag:print_file(tag)
        dftag=df[df.tag==tag]['value'].astype(dtype)
        pickle.dump(dftag,open(folder + tag + '.pkl', "wb" ))

    # ########################
    #   MODIFY EXISTING DATA #
    # ########################
    def process_dbtag(self,s,dtype):
        '''
        Convert the values of a pd.Series in the given data type

        :param pd.Series s: pd.Series to convert
        :param str dtype: data type to convert *s*
        :returns: converted pd.Series
        :rtype: the given data type
        '''
        s=s.replace('null',np.nan)
        s=s.replace('False',False)
        s=s.replace('True',True)
        try:
            if dtype=='int':
                s = s.fillna(np.nan).replace('null',np.nan).astype(float)
                s = s.convert_dtypes()
            else:
                s = s.astype(dtype)
        except:
            # s = s.astype(dtype)
            s = s.apply(lambda x:to_type(x,dtype))
        return s

    # ########################
    #      DAY FUNCTIONS     #
    # ########################
    def _to_folderday(self,timestamp):
        '''
        Convert timestamp to standard day folder format *%Y-%m-%d*

        :param tr or timestamp object timestamp: timestamp
        :rtype: timestamp
        '''
        return timestamp.strftime(self._format_dayFolder)

    def create_dayfolder(self,folderday):
        '''
        Create a folder it not exists

        :param str folderday: name of the folder
        '''
        if not os.path.exists(folderday):
            os.mkdir(folderday)
            return folderday +' created '
        else :
            return folderday +' already exists '

    def park_DFday(self,dfday,folderpkl,pool=False,showtag=False):
        '''
        Apply the function **parkdaytag** to all the present tags in *dfday*

        :param pd.DataFrame dfday: pd.DataFrame with columns *tag*, *timestampz* and *value*
        :param str folderpkl: name of the pickle file to save datas
        :param bool pool: default False. If True, parallelizes the execution of the **parkdaytag** function with a Pool object
        :param bool showtag: default False. If True, applies the **print_file** function with *tag* as parameter
        '''
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
        folderday = os.path.join(folderpkl, dfday.index.mean().strftime(self._format_dayFolder))
        print_file(filename=self.log_file)
        if not os.path.exists(folderday): os.mkdir(folderday)
        #park tag-day
        if pool :
            with Pool() as p:dfs=p.starmap(self.parkdaytag,[(dfday,tag,folderday,showtag) for tag in listTags])
        else :
            for tag in listTags:self.parkdaytag(dfday,tag,folderday,showtag)

    def parkdaytag(self,dfday,tag,folderday,showtag=False):
        '''
        Park all the values from a dataframe *dfday* for a given tag in a pickle file

        :param pd.DataFrame dfday: dataframe of the day
        :param str tag: tag
        :param str folderday: path of the folder
        :param bool showtag: default False. If True, applies the **print_file** function with *tag* as parameter
        '''
        if showtag:print_file(tag,filename=self.log_file)
        dftag=dfday[dfday.tag==tag]['value']
        pickle.dump(dftag,open(folderday + tag + '.pkl', "wb" ))

    def actiondays(self,t0,t1,folderPkl,action,*args,pool=True):
        '''
        Run the function *action* for each day between *t0* and *t1*

        :param timestamp t0: timestamp
        :param timestamp t1: timestamp
        :param str folderPkl:
        :param str action: name of the function
        :param bool pool: default True.
        :returns: a dictionnary with days as keys and result of the function **action** as values
        :rtype: dictionnary
        '''
        print_file(t0,t1,filename=self.log_file)
        days=pd.date_range(t0,t1,freq='1D')
        dayfolders =[os.path.join(folderPkl,k.strftime(self._format_dayFolder)) for k in days]
        if pool:
            with Pool() as p:
                dfs = p.starmap(action,[(d,*args) for d in dayfolders])
        else:
            dfs = [action(d,*args) for d in dayfolders]
        return {d.strftime(self._format_dayFolder):df for d,df in zip(days,dfs)}

    def remove_tags_day(self,d,tags):
        '''
        Remove the pickle files for a given day and for a given tag

        :param str d: path of the folder
        :param list[str] tags: list of tags
        '''
        print_file(d,filename=self.log_file)
        for t in tags:
            tagpath=os.path.join(d,t+'.pkl')
            try:
                os.remove(tagpath)
            except:
                pass
                # print_file('no file :',tagpath)

    def dumy_day(self,day):
        '''
        **que dire...**
        '''
        return day

    def zip_day(self,folderday,basename,zipfolder):
        '''
        Create a unique dataframe with all tags for a given day and saves it as zip file

        :param str folderday: path of the folder
        :param str basename: basename of the zip file
        :param str zipfolder: path of the zip folder
        '''
        listtags=glob.glob(folderday+'/*')
        dfs=[]
        for tag in listtags:
            dftag = pickle.load(open(tag,'rb')).reset_index()
            dftag['tag'] = tag.split('/')[-1].replace('.pkl','')
            dfs.append(dftag)
        df = pd.concat(dfs)
        ### save as zip file
        filecsv = os.path.join(zipfolder, folderday.split('/')[-2] +'_'+ basename + '.csv')
        df.to_csv(filecsv)
        file_csv_local = filecsv.split('/')[-1]
        filezip        = file_csv_local.replace('.csv','.zip')
        # sp.Popen(['libreoffice','/tmp/test.xlsx'])
        sp.check_output('cd ' + zipfolder + ' && zip '+filezip + ' ' + file_csv_local,shell=True)
        os.remove(filecsv)

    def zip_day_v2(self,folderday,basename,zipfolder):
        '''
        **Same as zip_day ?**
        '''
        listtags=glob.glob(folderday+'/*')
        dfs=[]
        for tag in listtags:
            dftag = pickle.load(open(tag,'rb')).reset_index()
            dftag['tag'] = tag.split('/')[-1].replace('.pkl','')
            dfs.append(dftag)
        df = pd.concat(dfs)
        ### save as zip file
        filecsv = os.path.join(zipfolder, folderday.split('/')[-2] +'_'+ basename + '.csv')
        df.to_csv(filecsv)
        file_csv_local = filecsv.split('/')[-1]
        filezip        = file_csv_local.replace('.csv','.zip')
        # sp.Popen(['libreoffice','/tmp/test.xlsx'])
        sp.check_output('cd ' + zipfolder + ' && zip '+filezip + ' ' + file_csv_local,shell=True)
        os.remove(filecsv)

    def dummy_daily(self,days=[],nCores=4):
        '''
        **fonction utile ?**
        '''
        if len(days)==0:
            days=[k for k in pd.date_range(start='2021-10-02',end='2021-10-10',freq='1D')]
        with Pool(nCores) as p:
            dfs=p.map(self.dumy_day,days)
        return dfs

    def remove_tags_daily(self,tags,folderPkl,patPeriod='**',nCores=6):
        '''
        Remove the pickle files for a given day and for a given tag

        :param list[str] tags: list of tags
        :param str folderPkl: path of the folder
        :param str parPeriod: pattern of the period, default *'**'*
        :param int nCores: number of cores, default 6
        '''
        days=glob.glob(folderPkl + patPeriod)
        if len(days)==1:
            self.remove_tags_day(days[0])
        else :
            with Pool(nCores) as p:p.starmap(self.remove_tags_day,[(d,tags) for d in days])

    def process_tag(self,s,rsMethod='nearest',rs='auto',tz='CET',rmwindow='3000s',closed='left',checkTime=False,verbose=False):
        '''
        Resample a pd.Series with a given method

        :param pd.Series s: pd.Series with timestampz as index and name='value'
        :param str rsMethod: see Basic_streamer().methods, default *nearest*
        :param str rs: argument for pd.resample. See pandas.DataFrame.resample?
        :param str timezone: timezone, default CET
        :param str rmwindow: argument for method pandas.rollingmean, default *3000s*
        :param str closed: default *left*
        :param bool checkTime: if True, prints the compute time. Default False
        :param bool verbose: default False
        :returns: resampled pd.Series
        :rtype: pd.Series
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

    def _load_raw_day_tag(self,day,tag,folderpkl,rs,rsMethod,closed,showTag_day=True):
        '''

        :param str day: date in the format '%Y-%m-%d'
        '''
        filename = os.path.join(folderpkl,day,tag+'.pkl')
        if os.path.exists(filename):
            s= pd.read_pickle(filename)
        else :
            s=  pd.Series(dtype='float')
        if showTag_day:print_file(filename + ' read',filename=self.log_file)
        s = self.process_tag(s,rs=rs,rsMethod=rsMethod,closed=closed)
        return s

    def _pool_tag_daily(self,t0,t1,tag,folderpkl,rs='auto',rsMethod='nearest',closed='left',ncores=None,time_debug=False,verbose=False,**kwargs):
        '''
        **Function description missing**

        :param timestamp t0: timestamp
        :param timestamp t1: timestamp
        :param str tag: tag
        :param str folderpkl: path of the folder containing the pkl file
        :param str rsMethod: see Basic_streamer().methods, default *nearest*
        :param str rs: argument for pd.resample. See pandas.DataFrame.resample
        :param str closed: {‘right’, ‘left’}, default *left*. Which side of bin interval is closed
        :param int ncores: number of cores, default None
        :param bool time_debug: if True, prints the compute time. Default False
        :param bool verbose: default False
        '''
        start=time.time()

        listDays=[self._to_folderday(k) for k in pd.date_range(t0,t1,freq='D',ambiguous=True)]
        if ncores is None:
            ncores=min(len(listDays),self._num_cpus)
        with Pool(ncores) as p:
            dfs=p.starmap(self._load_raw_day_tag,[(d,tag,folderpkl,rs,rsMethod,closed,verbose) for d in listDays])
        if time_debug:print_file(computetimeshow('pooling ' + tag+' finished',start))
        s_tag = pd.concat(dfs)
        if time_debug:print_file(computetimeshow('concatenation ' + tag+' finished',start))
        s_tag = s_tag[(s_tag.index>=t0)&(s_tag.index<=t1)]
        s_tag.name=tag
        s_tag=s_tag[~s_tag.index.duplicated(keep='first')]
        if time_debug:print_file(computetimeshow(tag + ' finished',start))
        return s_tag

    def load_tag_daily(self,t0,t1,tag,folderpkl,showTag=False,time_debug=False,verbose=False,**kwargs):
        '''
        **Function description missing**

        :param timestamp t0: timestamp
        :param timestamp t1: timestamp
        :param str tag: tag
        :param str folderpkl: path of the folder containing the pkl file
        :param bool showTag: default False. If True,
        :param bool time_debug: default False
        :param bool verbose: default False
        '''
        if showTag:print_file(tag,filename=self.log_file)
        start=time.time()
        dfs={}
        t=t0 - pd.Timedelta(hours=t0.hour,minutes=t0.minute,seconds=t0.second)
        while t<t1:
            filename = os.path.join(folderpkl,t.strftime(self._format_dayFolder),tag+'.pkl')
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
        '''
        **function description missing**

        :param timestamp t0: timestamp
        :param timestamp t1: timestamp
        :param str tag: tag
        :param str folderpkl: path of the folder containing the pkl file
        :param args: arguments of the function *load_tag_daily*
        '''
        return self.load_tag_daily(t0,t1,tag,folderpkl,*args, **kwargs)

    def load_parkedtags_daily(self,t0,t1,tags,folderpkl,*args,verbose=False,pool='auto',**kwargs):
        '''
        **Function description missing**

        :param timestamp t0: timestamp
        :param timestamp t1: timestamp
        :param str tag: tag
        :param str folderpkl: path of the folder containing the pkl file
        :param str pool: {'tag','day','auto',False}, default 'auto'
            - 'auto': pool on days if more days to load than tags otherwise pool on tags
            - False or any other value will not pool the loading
        :param \**kwargs: Streamer._pool_tag_daily and Streamer.load_tag_daily
        '''
        if not len(tags)>0:return pd.DataFrame()
        loc_pool=pool
        if pool in ['tag','day','auto']:
            nbdays=len(pd.date_range(t0,t1,ambiguous=True))
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
                dftags={tag:self._pool_tag_daily(t0,t1,tag,folderpkl,ncores=n_cores,**kwargs) for tag in tags}
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
        '''
        **Function description missing**

        :param pd.DataFrame df:
        :param str folderpkl:
        param bool pool: default True
        '''
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
            minutes=pd.date_range(tm1,tm2,freq='1T',ambiguous=True)
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
        '''
        **Function description missing**

        :param str or timestamp object t0:
        :param str or timestamp object t1:
        :param str folderPkl: path of the folder
        :param str frequence: {'day', 'minute'}

        '''
        if frequence=='minute':
            return self.foldersaction(t0,t1,folderPkl,self.create_minutefolder)
        elif frequence=='day':
            createfolderday=lambda x:os.mkdir(folderday)
            listDays = pd.date_range(t0,t1,freq='1D',ambiguous=True)
            listfolderdays = [os.path.join(folderPkl ,d.strftime(self._format_dayFolder)) for d in listDays]
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
        '''
        **Function description missing**
        '''
        return self.actiondays(t0,t1,folderpkl,STREAMER.listfiles_pattern_folder,pattern,pool=pool)
    # ########################
    #   STATIC COMPRESSION   #
    # ########################
    def staticCompressionTag(self,s,precision,method='reduce'):
        '''
        **Function description missing**

        :param pd.Series s:
        :param precision:
        :param method: {'diff', 'dynamic', 'reduce'}, default 'reduce'
        '''
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
        '''
        **Function description missing**
        '''
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
        '''
        **Function description missing**
        '''
        m=np.linspace(0,valPlateau,nbpts)+br*np.random.randn(nbpts)
        p=valPlateau*np.ones(nbpts)+br*np.random.randn(nbpts)
        d=np.linspace(valPlateau,0,nbpts)+br*np.random.randn(nbpts)
        idx=pd.date_range('9:00',periods=nbpts*3,freq='S',ambiguous=True)
        return pd.Series(np.concatenate([m,p,d]),index=idx)

    def testCompareStaticCompression(self,s,precs,fcw=3):
        '''
        **Function description missing**
        '''
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

    process_tag.__doc__= process_tag.__doc__.replace('XXX',"'" + "',' ".join(Basic_streamer().methods)+"'")

STREAMER = Streamer()
class Configurator():
    '''
    Instanciate an object *Configurator*

    :param conf: an instance of sylfenUtils.ConfGenerator

    ..note:: See **sylfenUtils.ConfGenerator**

    '''
    def __init__(self,conf):

        self.conf         = conf
        self.folderPkl    = conf.FOLDERPKL
        self.dbParameters = conf.DB_PARAMETERS
        self.dbTable      = conf.DB_TABLE
        self.dfplc        = conf.dfplc
        self._alltags     = list(conf.dfplc.index)
        self._dataTypes   = DATATYPES
        self.tz_record    = conf.TZ_RECORD
        self.parkingTime  = conf.PARKING_TIME##seconds
        self._format_dayFolder  = FORMAT_DAY_FOLDER##seconds
        #####################################
        # self.daysnotempty    = self.getdaysnotempty()
        # self.tmin,self.tmax  = self.daysnotempty.min(),self.daysnotempty.max()

    def getdaysnotempty(self):
        return self.conf.getdaysnotempty()

    def connect2db(self):
        return self.conf.connect2db()

    def getUsefulTags(self,usefulTag):
        return self.conf.getUsefulTags(usefulTag)

    def getUnitofTag(self,tag):
        return self.conf.getUnitofTag(tag)

    def getTagsTU(self,*args,**kwargs):
        return self.conf.getTagsTU(*args,**kwargs)

class SuperDumper(Configurator):
    '''
    Instanciate an object *SuperDumper*, inherited of the class **Configurator**

    :param dict devices: dictionnary of device_name : comUtils.Device instances
    :param sylfenUtils.ConfGenerator conf: ConfGenerator instance
    :param bool log_console: if True, the infos will be displayed in the CLI(console), otherwise in the log file in the folder of the project. Default, False
    '''
    def __init__(self,devices,conf,log_console=False):

        Configurator.__init__(self,conf)
        self.devices  = devices
        self.log_file = os.path.join(self.conf.LOG_FOLDER,self.conf.project_name+'_dumper.log')
        if log_console:
            self.log_file=None
        for dev in devices.values():
            dev._update_log_file(self.log_file)
        self.jobs = {}
        self.park_tag_pbs=[]
        self.possible_jobs=self._get_possible_jobs()
        # print_file(' '*20+'INSTANCIATION OF THE DUMPER'+'\n',filename=self.log_file)

    def _get_possible_jobs(self):
        '''
        Loop on devices and read all frequencies

        :returns: list of concatenations of devices and frequencies
        :rtype: list
        '''
        possible_jobs=[]
        for device_name,device in self.devices.items():#### loop on devices
            for freq in device.tags_freqs.keys():#### loop on frequencies
                job_name=device_name+'_'+str(freq)+'s'
                possible_jobs.append(job_name)
        return possible_jobs

    def _stop_auto_reconnect_all(self):
        for device_name,device in self.devices.items():
            device.stop_auto_reconnect()

    def start_job(self,device_name,freq):
        '''
        :param str device_name: name of the device
        :param int freq: frequency in seconds
        '''
        device=self.devices[device_name]
        job_name=device_name+'_' + str(freq) + 's'
        if job_name in list(self.jobs.keys()):
            self.stop_job(job_name)
        tags=device.tags_freqs[freq]
        ### collect special arguments in case prototype of collectData function
        # differs
        args_collect_special=[]
        if device._protocole=='ads': args_collect_special=[freq]
        self.jobs[job_name]=SetInterval(
            freq,
            device.insert_intodb,
            self.dbParameters,
            self.dbTable,
            self.tz_record,
            tags,
            *args_collect_special
            )
        ######## start dumping
        device.start_auto_reconnect()
        print_file(job_name,'is starting',filename=self.log_file)
        self.jobs[job_name].start()

    def stop_job(self,job_name,del_item=True):
        '''
        Stop the current job

        :param str job_name: job name (device_name + '_' + freq + 's'). See attribute self.possible_jobs
        :param bool del_item: if True, delete job. Default True
        '''
        if job_name in list(self.jobs.keys()):
            self.jobs[job_name].stop()
            if del_item:del self.jobs[job_name]
            print_file(job_name,'deleted',filename=self.log_file)

    def read_db(self,*args,**kwargs):
        '''
        Read database

        :param dict df_parameters: dictionnary with localhost, port, dbnamme, user and password keys
        :param str db_table: name of the table
        :param str timestamp: timestamp with timezone under which data will be read (default None ==> read all)
        :param str tag: a regular expression or a tag (default None ==> read all)
        :param bool delete: if True, will just delete and not read
        :param bool regExp: if True, reg exp are used for tag
        '''
        return read_db(self.dbParameters,self.dbTable,*args,**kwargs)

    def flushdb(self,t=None):
        '''
        Delete data from database

        :param str t:: timestamp. Everything before this timestamp will be deleted from the db. Default None
        '''
        connReq = ''.join([k + "=" + v + " " for k,v in self.dbParameters.items()])
        dbconn = psycopg2.connect(connReq)
        cur  = dbconn.cursor()
        if t is None:
            cur.execute("DELETE from " + self.dbTable + ";")
        else :
            cur.execute("DELETE from " + self.dbTable + " where timestampz < '" + t + "';")
        cur.close()
        dbconn.commit()
        dbconn.close()

    def feed_db_random_data(self,*args,**kwargs):
        '''
        Insert into database random data

        '''
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
        '''

        :param str t0: timestamp
        :param str t1: timestamp
        :param float vol: default *1.5*
        :param str listTags: default None
        '''
        valInits = self.createRandomInitalTagValues()
        if listTags==None:listTags=list(self.dfplc.index)
        valInits = {tag:valInits[tag] for tag in listTags}
        df = {}
        for tag,initval in valInits.items():
            tagvar = self.dfplc.loc[tag]
            precision  = self.dfplc.loc[tag,'PRECISION']
            timestampz = pd.date_range(t0,t1,freq=str(tagvar['FREQUENCE_ECHANTILLONNAGE'])+'S',ambiguous=True)

            if tagvar.DATATYPE=='STRING(40)':
                values  = [initval]* len(timestampz)
                df[tag] = pd.DataFrame({'value':values,'timestampz':timestampz})
            elif tagvar.DATATYPE=='BOOL':
                values  = initval + np.random.randint(0,2,len(timestampz))
                df[tag] = pd.DataFrame({'value':values,'timestampz':timestampz})
            else:
                values  = initval + precision*vol*np.random.randn(len(timestampz))
                stag = pd.Series(values,index=timestampz)
                # stag = STREAMER.staticCompressionTag(stag,precision,method='reduce')
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

    def _checkTimes(self,name_device):
        device = self.devices[name_device]
        df_collect = pd.read_csv(device.collect_file,index_col=0,)
        return df_collect
        p = 1. * np.arange(len(s_collect))
        fig = px.histogram(df_collect, x="value", color="group",hover_data=df.columns,nbins=20)
        return fig

    def stop_dumping(self):
        '''
        Stop dumping data
        '''
        for job_name in self.jobs.keys():
            self.stop_job(job_name,False)
        self.jobs={}
        if hasattr(self,'parkInterval'):
            self.parkInterval.stop()
        self._stop_auto_reconnect_all()

    def collectData(self,tags):
        ### determine to which device each tag belongs
        tags_devices=pd.Series({t:dev_name for dev_name,dev in self.devices.items() for t in tags if t in dev.dfplc.index},name='tags')
        ### make dictionnary out of it device_name:listTags
        tags_devices={dev:group.index.to_list() for dev,group in tags_devices.to_frame().groupby('tags')}
        ### call the different collectData
        df={}
        for dev_name,dev_tags in tags_devices.items():
            device=self.devices[dev_name]
            if not device.isConnected:
                device.connectDevice()
            df[dev_name]=device.collectData(self.tz_record,dev_tags)
        ### concatenate
        df=pd.concat([pd.DataFrame(s) for s in df.values()]).T
        return df

    def quick_analysis(self,tag):
        '''
        For the given tag, deliver a quick analysis (count, mean, std, min, max and some percentiles) of duration between 2 values.
        Return statistics and dataframe

        :param str tag: tag
        '''
        df=self.read_db(tag=tag,regExp=False).set_index('timestampz')
        df['ms']=pd.Series(df.index).diff().apply(lambda k:k.total_seconds()*1000).to_list()
        print(df.ms.describe(percentiles=[0.5,0.75,0.9,0.95]))
        return df

SuperDumper.read_db.__doc__=read_db.__doc__

class SuperDumper_daily(SuperDumper):
    '''
    Instanciate an object *SuperDumper_daily*, inherited of the class **SuperDumper**
    '''
    def start_dumping(self,park_on_time=True):
        '''
        Start dumping data

        :param bool park_on_time: if True, it will wait for the parking to start at a round time.

        For example, if it is 11:17 and parkingTime is 10 minutes, it will wait until 11:20 to start parking the data.
        '''
        import time
        print_file(timenowstd(),': START DUMPING',filename=self.log_file,with_infos=False)
        self.jobs = {}
        for device_name,device in self.devices.items():#### loop on devices
            min_freq=min(device.tags_freqs.keys())
            for freq in device.tags_freqs.keys():#### loop on frequencies
                job_name=device_name+'_'+str(freq)+'s'
                self.start_job(device_name,freq)

        ######## start parking on time
        if park_on_time:
            now = pd.Timestamp.now(tz=self.tz_record)
            next_round_minute_on_clock=now.ceil(str(self.parkingTime)+'s')
            time.sleep((next_round_minute_on_clock-now).total_seconds())
        print_file(timenowstd(),': START PARKING',filename=self.log_file,with_infos=False)
        self.parkInterval = SetInterval(self.parkingTime,self.park_database)
        self.parkInterval.start()

    def format_tag(self):
        df=df.set_index('timestampz').tz_convert(self.tz_record)
        tmin,tmax = df.index.min().strftime('%Y-%m-%d'),df.index.max().strftime('%Y-%m-%d')
        listdays=[k.strftime(self._format_dayFolder) for k in pd.date_range(tmin,tmax,ambiguous=True)]
        #### in case they are several days
        for d in listdays:
            t0 = pd.Timestamp(d + ' 00:00:00',tz=self.tz_record)
            t1 = t0 + pd.Timedelta(days=1)
            dfday=df[(df.index>=t0)&(df.index<t1)]
            folderday=os.path.join(self.folderPkl,d)
            #### create folder if necessary
            if not os.path.exists(folderday):os.mkdir(folderday)
            #################################
            #           park now            #
            #################################
            start=time.time()
            dftag = dfday[dfday.tag==tag]['value'] #### dump a pd.series
            self.parktagfromdb(tag,dftag,folderday)

    def _park_singletag_DB(self,tag,t_park=None,deleteFromDb=False,verbose=False):
        '''

        :param str tag: tag
        :param str t_park: timestamp before which data should be parked. Default, None. If None, t_park is now.
        :param bool deleteFromDb: if True, tag will be flushed individually from the database after having been parked.
        '''
        if verbose:print_file(tag)
        start = time.time()
        ######### rekad database
        if t_park is None:t_park=pd.Timestamp.now(tz=self.tz_record).isoformat()
        df=self.read_db(t=t_park,tag=tag,regExp=False,verbose=verbose).set_index('timestampz')
        if verbose:print_file(computetimeshow('tag : '+tag+ ' read in '+self.dbTable + ' in '+ self.dbParameters['dbname'],start),filename=self.log_file)
        ####### check if database not empty
        if not len(df)>0:
            if verbose : print_file('tag :'+tag+' not in table '+ self.dbTable + ' in ' + self.dbParameters['dbname'],filename=self.log_file)
            return
        ####### determine the folder days to store the data
        tmin,tmax =[t.strftime(self._format_dayFolder) for t in [df.index.min(),df.index.max()] ]
        listdays=[k.strftime(self._format_dayFolder) for k in pd.date_range(tmin,tmax,ambiguous=True)]
        # print_file(listdays)
        #### in case they are several days
        for d in listdays:
            t0 = pd.Timestamp(d + ' 00:00:00',tz=self.tz_record)
            t1 = t0 + pd.Timedelta(days=1)
            dfday=df[(df.index>=t0)&(df.index<t1)]
            folderday=os.path.join(self.folderPkl,d)
            #### create folder if necessary
            if not os.path.exists(folderday):os.mkdir(folderday)
            #################################
            #           park now            #
            #################################
            start=time.time()
            dftag = dfday[dfday.tag==tag]['value'] #### dump a pd.series
            self.parktagfromdb(tag,dftag,folderday)

        if verbose:print_file(computetimeshow('tag : '+tag+ ' parked',start),filename=self.log_file)
        if deleteFromDb:
            self.read_db(tag=tag,verbose=verbose,delete=True,regExp=False)

    def parktagfromdb(self,tag,s_tag,folderday,verbose=False):
        '''
        Park the data for the given tag in a pickle file in the *folderday*

        :param str tag: tag
        :param pd.Series s_tag: pd.Series to park
        :param str folderday: path of the folder
        '''
        namefile = os.path.join(folderday,tag + '.pkl')
        if verbose:print_file(namefile)
        if os.path.exists(namefile):
            s1 = pd.read_pickle(namefile)
            s_tag  = pd.concat([s1,s_tag])
        STREAMER.process_dbtag(s_tag,self._dataTypes[self.dfplc.loc[tag,'DATATYPE']]).to_pickle(namefile)

    def park_database(self,flush_tag=False,verbose=False):
        '''
        :param bool flush_tag: if True, all tag will be flushed from the database separately, otherwise the database will be flushed all together.
        '''
        start = time.time()
        now = pd.Timestamp.now(tz=self.tz_record)
        t_parking = now.isoformat()
        if len(self.park_tag_pbs)>0:
            flush_tag=True
            self.park_tag_pbs=[]
        for tag in self.dfplc.index.to_list():
            try:
                self._park_singletag_DB(tag,t_park=t_parking,deleteFromDb=flush_tag,verbose=verbose)
            except:
                self.park_tag_pbs.append(tag)
                if verbose:print_file('problem with tag : ',tag)

        if len(self.park_tag_pbs)==0:
            msg=' successfully'
            self.flushdb(t_parking)
        else:
            msg='with problems for tags:'+';'.join(self.park_tag_pbs)
        msg=computetimeshow('database parked'+msg,start)
        print_file(msg,filename=self.log_file)
        return msg

    def fix_timestamp(self,t0,tag,folder_save=None):
        t=t0 - pd.Timedelta(hours=t0.hour,minutes=t0.minute,seconds=t0.second)
        if folder_save is None:folder_save=self.folderPkl
        while t<pd.Timestamp.now(self.tz_record):
            filename = os.path.join(self.folderPkl,t.strftime(self._format_dayFolder),tag+'.pkl')
            if os.path.exists(filename):
                s=pd.read_pickle(filename)
                ####### FIX TIMESTAMP PROBLEM
                s.index=[k.tz_convert(tz=self.tz_record) for k in s.index]
                folder_day_save=os.path.join(folder_save,t.strftime(self._format_dayFolder))
                ####### fix dupplicated index
                if not os.path.exists(folder_day_save):os.mkdir(folder_day_save)
                new_filename = folder_day_save + tag+'.pkl'
                s.to_pickle(new_filename)
            t = t + pd.Timedelta(days=1)

import plotly.graph_objects as go, plotly.express as px
class VisualisationMaster(Configurator):
    '''
    Instanciate an object *VisualisationMaster*, inherited of the class **Configurator**

    :param conf: an instance of sylfenUtils.ConfGenerator

    ..note:: See sylfenUtils.Configurator
    '''
    def __init__(self,*args,**kwargs):
        Configurator.__init__(self,*args,**kwargs)
        self.methods = STREAMER.methods
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
            s = STREAMER.process_dbtag(s,dtype)
            s = STREAMER.process_tag(s,*args,**kwargs)
            return s

        dftags = {tag:process_dbtag(df,tag,*args,**kwargs) for tag in tags}
        df = pd.concat(dftags,axis=1)
        df = df[df.index>=t0]
        df = df[df.index<=t1]
        return df

    def loadtags_period(self,t0,t1,tags,*args,pool='auto',verbose=False,**kwargs):
        '''
        Load tags between times t0 and t1.

        :param pd.Timestamp t0: timestamp. t0 start
        :param pd.Timestamp t1: timestamp. t1 end
        :param list[str] tags: list of tags available from self.dfplc.listtags
        :rtype: pd.DataFrame
        :return: pd.DataFrame with ntags columns

        ..note:: See also args of **VisualisationMaster.Streamer.process_tag**
        '''

        # for k in t0,t1,tags,args,kwargs:print_file(k)
        tags=list(np.unique(tags))
        ############ read parked data
        df = STREAMER.load_parkedtags_daily(t0,t1,tags,self.folderPkl,*args,pool=pool,verbose=verbose,**kwargs)
        ############ read database
        if t1<pd.Timestamp.now(self.tz_record)-pd.Timedelta(seconds=self.parkingTime) or not self.conf._realtime:
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

        :param list[str] tagsOrDescriptions: list of tags or description of tags
        :param str toogleto: {'tag', 'description'} you can force to toogleto description or tags. Default 'tag'
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

    def multiUnitGraph(self,df,tagMapping=None,**kwargs):
        '''
        :param pd.DataFrame df: pd.DataFrame pivoted
        :param dict tagMapping: same as dictGroups
        '''
        if not tagMapping:tagMapping = {t:self.getUnitofTag(t) for t in df.columns}
        # print(tagMapping)
        fig = self.utils.multiUnitGraph(df,tagMapping,**kwargs)
        return fig

    multiUnitGraph.__doc__+=Utils.multiUnitGraph.__doc__
    loadtags_period.__doc__+=Streamer.process_tag.__doc__

class VisualisationMaster_daily(VisualisationMaster):
    '''
    Instanciates an object *VisualisationMaster_daily*, inherited of the class **VisualisationMaster**
    '''
    def __init__(self,*args,**kwargs):
        VisualisationMaster.__init__(self,*args,**kwargs)
        self.folder_coarse=self.folderPkl.rstrip('/')+'_coarse/'
        if not os.path.exists(self.folder_coarse):os.mkdir(self.folder_coarse)
        if not os.path.exists(self.folder_coarse+'mean'):os.mkdir(self.folder_coarse+'mean')
        if not os.path.exists(self.folder_coarse+'max'):os.mkdir(self.folder_coarse+'max')
        if not os.path.exists(self.folder_coarse+'min'):os.mkdir(self.folder_coarse+'min')

    def _load_parked_tags(self,t0,t1,tags,pool):
        '''

        :param str t0: timestamp
        :param str t1: timestamp
        :param list[str] tags: list of tags
        :param bool pool: if True, pool on tags
        :rtype: pd.DataFrame
        '''
        if not isinstance(tags,list) or len(tags)==0:
            print_file('tags is not a list or is empty',filename=self.log_file)
            return pd.DataFrame(columns=['value','timestampz','tag']).set_index('timestampz')
        df = STREAMER.load_parkedtags_daily(t0,t1,tags,self.folderPkl,pool)
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
            if verbose:print_file(filename)
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
        '''

        :param list[str] tags: list of tags
        '''
        if tags is None : tags=list(self.dfplc.index)
        pb_tags=[]
        for tag in tags:
            try:
                self._park_coarse_tag(tag,*args,**kwargs)
            except:
                pb_tags.append(tag)
                print(timenowstd(),tag,' not possible to coarse-compute')
        return pb_tags

    def _get_t0(self,file_tag,from_start=False):
        t0 = pd.Timestamp(min(os.listdir(self.folderPkl)),tz=self.tz_record)
        if from_start:return t0
        if os.path.exists(file_tag):
            s_tag=pd.read_pickle(file_tag)
            t1=s_tag.index.max()
            if s_tag.empty:t1=t0
            t0=max(t1,t0)
        return t0

    def _park_coarse_tag(self,tag,rs='60s',verbose=False,from_start=False):
        '''
        Will park coarse data by pre-calculating the mean/max/min of the period from the raw data.
        Only missing coarse data will be computed unless from_start is set to True

        :param str tag: tag
        :param str rs: default 60s
        :param bool from_start: if set to True, will recalculate all from the begining(older day folder)
        '''

        methods=['mean','min','max']
        start=time.time()
        ########### determine t0
        t0=min([self._get_t0(os.path.join(self.folder_coarse,m,tag + '.pkl'),from_start=from_start) for m in methods])
        ######### load the raw data
        if verbose:print(tag,t0)
        s=STREAMER.load_tag_daily(t0,pd.Timestamp.now(self.tz_record),tag,self.folderPkl,rsMethod='raw',verbose=False)
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
    park_coarse_data.__doc__+=_park_coarse_tag.__doc__

class Fix_daily_data():
    '''
    param conf: should be a sylfenUtils.ConfGenerator object
    '''
    def __init__(self,conf):

        self.conf=conf
        self._format_day_folder=FORMAT_DAY_FOLDER
        self.checkFolder=os.path.join(os.path.abspath(os.path.join(conf.FOLDERPKL,os.pardir)),conf.project_name+'_fix')
        create_folder_if_not(self.checkFolder)

    ########### PRIVATE
    def _load_raw_tag_day(self,tag,day,verbose=True,checkFolder=False):
        """
        Load the raw data from self.conf.FOLDERPKL

        :param str tag: tag
        :param str day: day at the format '%Y-%m-%d'
        :param bool verbose:
        :param bool checkFolder: if True, the data will be loaded from self.checkFolder
        """
        if checkFolder:
            filename = os.path.join(self.checkFolder,day,tag+'.pkl')
        else:
            filename = os.path.join(self.conf.FOLDERPKL,day,tag+'.pkl')
        if os.path.exists(filename):
            s= pd.read_pickle(filename)
        else :
            print(filename,'does not exist.')
            return
        if verbose:print(filename + ' read')
        return s

    def _to_folderday(self,timestamp):
        '''
        Convert timestamp to standard day folder format

        :param str or timestamp object timestamp: timestamp
        '''
        return Streamer()._to_folderday(timestamp)

    def applyCorrectFormat_daytag(self,tag,day,newtz='CET',verbose=True,checkFolder=False):
        '''
        Format as pd.Series with name values and timestamp as index, remove duplicates, convert timestamp with timezone
        and apply the correct datatype

        :param str tag: tag
        :param str day: day at the format '%Y-%m-%d'
        :param str newtz: timezone
        :param bool checkFolder: if True, it will save the correct formatted data in self.checkFolder
        '''
        tagpath=os.path.join(self.conf.FOLDERPKL,day,tag+'.pkl')
        if verbose:print(tagpath)
        ##### --- load pkl----
        if not os.path.exists(tagpath):
            print(tagpath,'does not exist');
            return
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
        '''
        .. note:: For *args,**kwargs : see _load_raw_tag_day
        '''
        t=t0
        dfs=[]
        while t<=t1:
            dfs.append(self._load_raw_tag_day(tag,self._to_folderday(t),*args,**kwargs))
            t=t+pd.Timedelta(days=1)
        return dfs

    def load_raw_tags_day(self,tags,day,*args,**kwargs):
        '''
        :param list[str] tags: list of tags
        :param str day: day at the format '%Y-%m-%d'
        .. note:: For *args,**kwargs : see _load_raw_tag_day
        '''
        return {tag:self._load_raw_tag_day(tag,day,*args,**kwargs) for tag in tags}

    def applyCorrectFormat_day(self,day,dtypes,*args,**kwargs):
        '''
        :param str day: day at the format %Y-%m-%d'
        :param str dtypes: see self.DATATYPES for valid datatypes
        .. note:: See doc of Fix_daily_data.applyCorrectFormat_daytag()
        '''
        tags = self.conf.dfplc.index.to_list()
        for tag in tags:
            self.applyCorrectFormat_daytag(tag,day,*args,**kwargs)

    def applyCorrectFormat_tag(self,tag,*args,**kwargs):
        '''
        :param str tag: tag
        .. note:: See doc of Fix_daily_data.applyCorrectFormat_daytag()
        '''
        print(tag)
        for day in os.listdir(self.conf.FOLDERPKL):
            self.applyCorrectFormat_daytag(tag,day,*args,**kwargs)

    load_raw_tag_period.__doc__+=_load_raw_tag_day.__doc__
    load_raw_tags_day.__doc__+=_load_raw_tag_day.__doc__

    applyCorrectFormat_day.__doc__+=applyCorrectFormat_daytag.__doc__
    applyCorrectFormat_tag.__doc__+=applyCorrectFormat_daytag.__doc__

class VisualisatorStatic(VisualisationMaster):
    '''
    Visualiser data of folderpkl
    Instanciate an object *VisualisatorStatic*, inherited of the class **VisualisationMaster**

    :param str folderPkl: path of the data
    :param pd.DataFrame dfplc : pd.DataFrame with columns DESCRIPTION, UNITE, DATATYPE and tags as index.
    '''
    def __init__(self,folderPkl,dfplc):

        self.methods = STREAMER.methods
        self.dfplc = dfplc
        self.folderPkl = folderPkl
        self.log_file=None

    def loadtags_period(self,t0,t1,tags,*args,pool='auto',verbose=False,**kwargs):
        '''
        Load tags between times t0  and t1.

        :param pd.Timestamp t0: timestamp, t0 start
        :param pd.Timestamp t1: timestamp, t1 end
        :param list[str] tags: list of tags available from self.dfplc.listtags
        :return: pd.DataFrame with ntags columns

        .. note:: See also: *args,**kwargs of VisualisationMaster.Streamer.process_tag()
        '''
        # for k in t0,t1,tags,args,kwargs:print_file(k)
        tags=list(np.unique(tags))
        ############ read parked data
        df = STREAMER.load_parkedtags_daily(t0,t1,tags,self.folderPkl,*args,pool=pool,verbose=verbose,**kwargs)
        return df.sort_index()
