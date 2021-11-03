import pandas as pd, numpy as np, pickle, re, time, datetime as dt,glob,threading
from datetime import timezone
import pytz
import subprocess as sp, os
from dateutil import parser
from pyModbusTCP.client import ModbusClient
import xml.etree.ElementTree as ET, pandas as pd,re,struct,importlib,glob
from multiprocessing import Process, Queue, current_process,Pool

class Scheduler():
    def __init__(self,job,jobsArgs=None) :
        self.job=job
        self.jobsArgs=jobsArgs
        self.stopEvent=threading.Event()

class SetInterval :
    '''fait son maximum pour rattraper son retard, ne saute pas de données pour arriver à l'heure.
    Commence ponctuellement si en avance mais pas si en retard.'''
    def __init__(self,interval,action) :
        self.interval=interval
        self.action=action
        self.stopEvent=threading.Event()
        thread=threading.Thread(target=self.__SetInterval)
        thread.start()

    def __SetInterval(self) :
        nextTime=time.time()+self.interval
        while not self.stopEvent.wait(nextTime-time.time()) :
            nextTime+=self.interval
            self.action()

    def cancel(self) :
        self.stopEvent.set()

class SetIntervals :
    def __init__(self,interval,waitings,action) :
        self.interval=interval
        self.waitings=waitings
        self.action=action
        self.c=0
        self.stopEvent=threading.Event()
        thread=threading.Thread(target=self.__SetInterval)
        thread.start()
        self.nbactions = 0

    def __SetInterval(self) :
        nextTime=time.time()+self.interval
        print('start at : ',dt.datetime.now().isoformat())
        while (not self.stopEvent.wait(nextTime-time.time())) and self.c<len(self.waitings):
            nextTime+=self.interval # si il est en retard une fois alors il ne sera pas ponctuelle pour les autres
            self.action(self.waitings[self.c])
            finishedAt = dt.datetime.now().isoformat()
            self.nbactions+=1
            # print('actions done since begining : ',self.nbactions)
            # print('finished at',finishedAt)
            print('nextTime : ',nextTime)
            print('time',time.time())
            self.c+=1

    def cancel(self) :
        self.stopEvent.set()

class StartEverySeconds(Scheduler):
    '''demarre a l'heure mais saute des données si en retard. Ne démarre pas si les actions prennent toujours plus de temps
    que le scheduler'''
    def __init__(self,seconds,job) :
        self.seconds=seconds
        self.job=job
        self.stopEvent=threading.Event()
        thread=threading.Thread(target=self.__schedulerAction)
        thread.start()

    def __schedulerAction(self):
        self.startTime=time.time()
        nextTime=(time.time()//self.seconds+1)*self.seconds
        while not self.stopEvent.wait(nextTime-time.time()):
            self.job()
            nextTime=(time.time()//self.seconds+1)*self.seconds
            print(nextTime)
            print(time.time())

class StartEveryDayAt(Scheduler):
    def __init__(self,timeOfDay,job,jobArgs=None):
        Scheduler.__init__(self,job)
        self.timeOfDay=timeOfDay
        thread=threading.Thread(target=self.__schedulerAction)
        thread.start()

    def __schedulerAction(self):
        deltat=(pd.to_datetime(self.timeOfDay)-dt.datetime.now()).total_seconds()
        if deltat<0:
            deltat=(pd.to_datetime(self.timeOfDay)+dt.timedelta(days=1)-dt.datetime.now()).total_seconds()
        print(deltat)
        while not self.stopEvent.wait(deltat):
            deltat=3600*24
            self.job()

class ComUtils:
    def datesBetween2Dates(self,dates,offset=0):
        times = [parser.parse(k) for k in dates]
        t0,t1 = [t-dt.timedelta(hours=t.hour,minutes=t.minute,seconds=t.second) for t in times]
        delta = t1 - t0       # as timedelta
        return [(t0 + dt.timedelta(days=i+offset)).strftime('%Y-%m-%d') for i in range(delta.days + 1)],times[1]-times[0]

    def readTag_csv(self,tag,folderDayRT,rs,applyMethod='mean',old=True,locProd='Europe/Paris'):
        df = pd.DataFrame()
        try :
            filename = folderDayRT + tag + '.csv'
            if not rs=='raw':
                df = pd.read_csv(filename,parse_dates=[0],index_col=0,)
                df.index = df.index.tz_localize('Europe/Paris')
                df = eval("df.resample('1s').ffill().ffill().resample(rs).apply(np." + applyMethod + ")")
            if old :
                df = pd.read_csv(filename,parse_dates=[0],header=None)
                df.columns=['timestampUTC','value']
                df = df.set_index('timestampUTC')
                df.index = df.index.tz_convert('UTC')
                df['tag']=tag
                df=df.reset_index()
            else :
                df.columns=[tag]
        except:
            print('problem for reading :',filename)
        return df

    def readTagsRealTime(self,folderRT,tags,timeWindow=30*60,rs='5s',applyMethod='mean'):
        today = dt.datetime.now()
        timeMin =  pd.to_datetime(dt.datetime.now() - dt.timedelta(seconds=timeWindow))
        listDays = self.datesBetween2Dates([t.strftime('%Y-%m-%d') for t in [timeMin,today]])[0]
        dfdays = []
        for day in listDays:
            folderDay = folderRT + day + '/'
            with Pool() as p:
                dfs=p.starmap(self.readTag_csv,[(tag,folderDay,rs,applyMethod) for tag in tags])
            dfs = [k for k in dfs if not k.empty]
            if len(dfs)>0:
                dfdays.append(pd.concat(dfs,axis=1))
        df = pd.concat(dfdays)
        return df[df.index>timeMin.tz_localize('Europe/Paris')]

    def parkTag_csv(self,tag,folderDayPkl,folderDayRT):
        df = self.readTag_csv(tag,folderDayRT,rs='raw')
        with open(folderDayPkl + tag + '.pkl' , 'wb') as handle:
            pickle.dump(df, handle, protocol=pickle.HIGHEST_PROTOCOL)

    def park_today(self,folderPkl,folderRT,offSetDay=0):
        today = dt.datetime.now()-dt.timedelta(days=offSetDay)
        folderDayPkl = folderPkl + today.strftime('%Y-%m-%d') + '/'
        folderDayRT = folderRT + today.strftime('%Y-%m-%d') + '/'
        listTags = [k[:-4] for k in os.listdir(folderDayRT)]
        if not os.path.exists(folderDayPkl):os.mkdir(folderDayPkl)
        with Pool() as p:
            df=p.starmap(self.parkTag_csv,[(tag,folderDayPkl,folderDayRT) for tag in listTags])

class OPCUA_utils(ComUtils):
    def __init__(self):
        self.confDir=os.path.dirname(os.path.realpath(__file__)) + '/conf'

class Modebus_utils(ComUtils):
    ## parse XMLReader
    # https://docs.python.org/3/library/xml.etree.elementtree.html

    def __init__(self):
        ComUtils.__init__(self,)
        self.confDir=os.path.dirname(os.path.realpath(__file__)) + '/conf'

    def getSizeOf(self,typeVar,f=1):
        if typeVar == 'IEEE754':return 2*f
        elif typeVar == 'INT64': return 4*f
        elif typeVar == 'INT32': return 2*f
        elif typeVar == 'INT16': return 1*f
        elif typeVar == 'INT8': return f/2

    def demoBytesInt(self):
    # https://docs.python.org/fr/3/library/stdtypes.html

        #convert an int to bytes
        (1000).to_bytes(2, byteorder='little')
        #convert bytes to int
        int.from_bytes(b'\xfc\x00', byteorder='big', signed=False)
        int.from_bytes([255, 0], byteorder='big')

        float.hex(3740.0)
        float.fromhex('0x3.a7p10')

    def wordTofloat(self,t = (123, 456)):
        import struct,binascii
        packed_string = struct.pack("HH", *t)
        print(binascii.hexlify(packed_string))
        unpacked_float = struct.unpack("f", packed_string)[0]
        return unpacked_float

    def ieee_754_conversion(self,n, sgn_len=1, exp_len=8, mant_len=23):
        """
        Converts an arbitrary precision Floating Point number.
        Note: Since the calculations made by python inherently use floats, the accuracy is poor at high precision.
        :param n: An unsigned integer of length `sgn_len` + `exp_len` + `mant_len` to be decoded as a float
        :param sgn_len: number of sign bits
        :param exp_len: number of exponent bits
        :param mant_len: number of mantissa bits
        :return: IEEE 754 Floating Point representation of the number `n`
        """
        if n >= 2 ** (sgn_len + exp_len + mant_len):
            raise ValueError("Number n is longer than prescribed parameters allows")

        sign = (n & (2 ** sgn_len - 1) * (2 ** (exp_len + mant_len))) >> (exp_len + mant_len)
        exponent_raw = (n & ((2 ** exp_len - 1) * (2 ** mant_len))) >> mant_len
        mantissa = n & (2 ** mant_len - 1)

        sign_mult = 1
        if sign == 1:
            sign_mult = -1

        if exponent_raw == 2 ** exp_len - 1:  # Could be Inf or NaN
            if mantissa == 2 ** mant_len - 1:
                return float('nan')  # NaN

            return sign_mult * float('inf')  # Inf

        exponent = exponent_raw - (2 ** (exp_len - 1) - 1)

        if exponent_raw == 0:
            mant_mult = 0  # Gradual Underflowsion 	2 	24 	7
        else:
            mant_mult = 1

        for b in range(mant_len - 1, -1, -1):
            if mantissa & (2 ** b):
                mant_mult += 1 / (2 ** (mant_len - b))

        return sign_mult * (2 ** exponent) * mant_mult
        '''conversion of a byte flow in ieee54 numbers'''

    def findInstrument(self,meter):
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

    def findInstruments(self,xmlpath):
        tree = ET.parse(xmlpath)
        root = tree.getroot()
        dfs=[]
        for meter in root.iter('meter'):
            dfs.append(self.findInstrument(meter))
        df=pd.concat(dfs)
        tmp = df.loc[:,['point de comptage','description']].sum(axis=1)
        df['id']=[re.sub('\s','_',k) for k in tmp]
        # df=df[df['type']=='INT32']
        df['addrTCP'] = pd.to_numeric(df['addrTCP'],errors='coerce')
        df['scale'] = pd.to_numeric(df['scale'],errors='coerce')
        df=df.set_index('adresse')
        # df=df[df['scale']==0.1]
        return df

    def decodeModeBusIEEE754(self,a,b,endianness='big',signed=False):
        a = '{0:04x}'.format(a)# from decimal to hexadecimal representation of a word
        b = '{0:04x}'.format(b)
        # a = a.to_bytes(2, byteorder=endianness,signed=signed)
        # b = b.to_bytes(2, byteorder=endianness,signed=signed)
        # xx = a+b
        xx = b+a
        # try:return struct.unpack('!f', xx)[0]
        try:return struct.unpack('!f', bytes.fromhex(xx))[0]
        except : return 'error'

    def decodeModeBusINT32(self,a,b,endianness='big',signed=False):
        # a = '{0:04x}'.format(a)
        # b = '{0:04x}'.format(b)
        # a = a.to_bytes(2, byteorder=endianness,signed=signed)
        # b = b.to_bytes(2, byteorder=endianness,signed=signed)
        # xx = a+b
        # xx = b+a
        # try:return struct.unpack('!f', bytes.fromhex(xx))[0]
        # except : return 'error'
        return a + 256**2*b

    def decodeModeBusINT64(self,a,b,c,d):
        return a + 256**2*b + 256**4*c + 256**6*d

    def checkPtComptage(self,idTCP,client,dfInstr,sizeReg=10):
        ptComptage = dfInstr[dfInstr['addrTCP']==idTCP]
        wordNbs = ptComptage.sum()['size(mots)']
        bytesNb = ptComptage.sum()['size(bytes)']
        print('point de comptage \n: ',ptComptage)
        print('idTCP : ',idTCP)
        print('nb vars : ',len(ptComptage))
        print('wordNbs : ',wordNbs)
        print('bytesNb : ',bytesNb)
        regs = client.read_holding_registers(0,sizeReg)
        regs = pd.DataFrame(regs)
        print(regs)
        return regs

    def showRegisterValue(self,c,dfInstr,id,showCom=True):
        idinit=id

        if isinstance(id,int): id = dfInstr.iloc[id,:]
        else :
            id = dfInstr[dfInstr['id']==id]
            if len(id)>1: id=id.iloc[0,:]
            else : id = id.squeeze()
        # print(id)
        intadd,typedata   = id['intAddress'],id['type']
        sizeType = self.getSizeOf(typedata,1)
        regs     = c.read_holding_registers(intadd,sizeType)

        if typedata == 'INT32':value = self.decodeModeBusINT32(regs[0],regs[1])
        if typedata == 'IEEE754':value = self.decodeModeBusIEEE754(regs[0],regs[1])
        elif typedata == 'INT64':value = self.decodeModeBusINT64(regs[0],regs[1],regs[2],regs[3])
        value=value*id.scale
        if showCom:
            print(typedata,intadd,id['point de comptage'],id['description'],regs,'======>',value)

        return id['description'],value

    def tryDecoding(self,regs,formatOut=None,endianness='!'):
        import itertools,numpy as np
        if len(regs)==2 :
            if not formatOut :formatOut = endianness+'f'
            permutRep = list(itertools.permutations(['a ','b ']))
            permutRep = list(itertools.permutations(['a ','b ','c ','d ']))
            hexList   = ['{0:04x}'.format(k) for k in regs]
        elif len(regs)==4 :
            if not formatOut :formatOut = endianness+'d'
            permutRep = list(itertools.permutations(['a ','b ','c ','d ']))
            permutRep = list(itertools.permutations(['a ','b ','c ','d ','e','f','g','h']))
            hexList     = ['{0:04x}'.format(k) for k in regs]
        hexList   = [[k[:2],k[2:]] for k in hexList]
        hexList = [item for sublist in hexList for item in sublist] #flatten list
        allPerms    = list(itertools.permutations(hexList))
        permHexList = [''.join(k) for k in allPerms]
        # print(permutRep)
        for xx,p in zip(permHexList,permutRep):
            # print(p)
            try:
                res = struct.unpack(formatOut, bytes.fromhex(xx))[0]
                if abs(np.log(abs(res)))<5 :
                    print('p=',p,';hexCode:',xx,';endianness:',endianness,';out:',
                                formatOut,'====>',res)
                # else : print(';hexCode:',xx,'extrem value')
            except : print('p=',p,',hexCode:',xx,',endianness:',endianness,';out:',formatOut,'===>','error')

    def getContinuBlocks(self,ptComptage):
        nextAddContigu=(ptComptage['intAddress']+ptComptage['size(mots)'])[:-1]
        nextAddContigu.index=ptComptage.index[1:]
        ptComptage['nextAdd']=nextAddContigu
        a = ptComptage['intAddress']==ptComptage['nextAdd']
        a[-1]=False
        addStops = ptComptage[~a]['intAddress']
        regContinuBlocs =[ptComptage.loc[k:l] for k,l in zip(addStops.index[:-1],addStops.index[1:])]
        return regContinuBlocs

    def getRegisterValues(self,hostIP,dfInstr,allTCPid=None,exclude='INT32'):
        if not allTCPid : allTCPid = dfInstr['addrTCP'].unique()
        d,timestamps = {},{}
        for idTCP in allTCPid:
            c = ModbusClient(host=hostIP, unit_id=idTCP,auto_open=True, auto_close=True)
            ptComptage = dfInstr[dfInstr['addrTCP']==idTCP]
            compteur = ptComptage['point de comptage'].unique()[0]

            regContinuBlocs = self.getContinuBlocks(ptComptage)
            for blocCon in regContinuBlocs:
                firstReg = blocCon.iloc[0]['intAddress']
                regs     = c.read_holding_registers(0,blocCon['size(mots)'].sum())
                curReg = 0
                for row in blocCon.iterrows():
                    row=row[1]
                    if row.type == 'INT32':
                        localRegs = [regs[curReg+k] for k in [1,0]]
                        value = self.decodeModeBusINT32(*localRegs)
                    if row.type == 'IEEE754':
                        localRegs = [regs[curReg+k] for k in [0,1]]
                        value = self.decodeModeBusIEEE754(*localRegs)
                    elif row.type == 'INT64':
                        localRegs = [regs[curReg+k] for k in [0,1,2,3]]
                        value = self.decodeModeBusINT64(*localRegs)
                    value=value*row.scale
                    curReg+=row['size(mots)']

                    if not row.type == exclude:
                        timestamps[row['point de comptage'] + '---'+ row['description']] = dt.datetime.now(tz=pytz.timezone('Europe/Paris')).isoformat()
                        d[row['point de comptage'] + '---'+ row['description']]=value
                        # print(row['point de comptage'] + '---'+ row['description'],' : ',value)
        return d,timestamps

    def dumpData(self,d,timestamps,folderSave,validTags):
        for k,v,t in zip(d.keys(),d.values(),timestamps.values()):
            findTag = k.replace('---','.*')+'-'
            tagName = [l for l in validTags if re.findall(findTag.replace('(-)','\(-\)'),l)]
            if len(tagName)==1:
                with open(folderSave + tagName[0] + '.csv' , 'a') as f:f.write(t+','+str(v)+'\n')
