import pandas as pd, numpy as np, pickle, re, time, datetime as dt,glob
from datetime import timezone
import psycopg3 as psycopg
import subprocess as sp, os
from dateutil import parser
import plotly.graph_objects as go
from pylab import cm
import matplotlib.colors as mtpcl
import matplotlib.pyplot as plt
import scipy
from scipy.optimize import curve_fit

class Utils:
    def __init__(self):
        self.confDir=os.path.dirname(os.path.realpath(__file__)) + '/conf'
        self.phyQties = self.df2dict(pd.read_csv(self.confDir+ '/units.csv'))
        self.unitMag = ['u','m','c','d','','da','h','k','M']
        self.buildNewUnits()
        self.cmapNames = pickle.load(open(self.confDir+"/colormaps.pkl",'rb'))[::3]

    # ==========================================================================
    #                           DEBUG
    # ==========================================================================

    def printCTime(self,start,entete='time laps' ):
        print(entete + ' : {:.2f} seconds'.format(time.time()-start))

    # ==========================================================================
    #                           SYSTEM
    # ==========================================================================
    def read_csv_datetimeTZ(self,filename,**kwargs):
        start   = time.time()
        print("============================================")
        print('reading of file',filename)
        df      = pd.read_csv(filename,**kwargs,names=['tag','value','timestampUTC'])
        self.printCTime(start)
        start = time.time()
        print("============================================")
        print("parsing the dates : ",filename)
        df.timestampUTC=pd.to_datetime(df.timestampUTC,utc=True)# convert datetime to utc
        df['value'] = pd.to_numeric(df['value'],errors='coerce')
        self.printCTime(start)
        print("============================================")
        return df

    def convert_csv2pkl(self,folderCSV,folderPKL):
        for filename in self.get_listFilesPkl(folderCSV,'.csv'):
            df=self.read_csv_datetimeTZ(folderCSV + filename)
            with open(folderPKL + filename[:-4] + '.pkl' , 'wb') as handle:
                pickle.dump(df, handle, protocol=pickle.HIGHEST_PROTOCOL)

    def get_listFilesPkl(self,folderName=None,ext='.pkl'):
        if not folderName :folderName = os.getcwd()
        listFiles = sp.check_output('cd ' + '{:s}'.format(folderName) + ' && ls *' + ext,shell=True)
        listFiles=listFiles.decode().split('\n')[:-1]
        return listFiles

    def get_listFilesPklV2(self,folderName=None,pattern='*.pkl'):
        if not folderName :folderName = os.getcwd()
        listfiles = glob.glob(folderName+pattern)
        listfiles.sort()
        return listfiles

    def skipWithMean(self,df,windowPts,idxForMean=None,col=None):
        ''' compress a dataframe by computing the mean around idxForMean points'''
        if not col :
            col = [k for k in range(len(df.columns))]
        print(col)
        if not idxForMean :
            idxForMean = list(range(windowPts,len(df),windowPts))
        ll = [df.iloc[k-windowPts:k+windowPts+1,col].mean().to_frame().transpose()
                for k in idxForMean]
        dfR = pd.concat(ll)
        dfR.index = df.index[idxForMean]
        return dfR

    def datesBetween2Dates(self,dates,offset=0):
        times = [parser.parse(k) for k in dates]
        t0,t1 = [t-dt.timedelta(hours=t.hour,minutes=t.minute,seconds=t.second) for t in times]
        delta = t1 - t0       # as timedelta
        return [(t0 + dt.timedelta(days=i+offset)).strftime('%Y-%m-%d') for i in range(delta.days + 1)],times[1]-times[0]

    def slugify(self,value, allow_unicode=False):
        import unicodedata,re
        """
        Taken from https://github.com/django/django/blob/master/django/utils/text.py
        Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
        dashes to single dashes. Remove characters that aren't alphanumerics,
        underscores, or hyphens. Convert to lowercase. Also strip leading and
        trailing whitespace, dashes, and underscores.
        """
        value = str(value)
        if allow_unicode:value = unicodedata.normalize('NFKC', value)
        else:value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
        value = re.sub(r'[^\w\s-]', '', value.lower())
        return re.sub(r'[-\s]+', '-', value).strip('-_')

    def is_dst(self,t=None, timezone="UTC"):
        if t is None:t = dt.utcnow()
        timezone = pytz.timezone(timezone)
        timezone_aware_date = timezone.localize(t, is_dst=None)
        return timezone_aware_date.tzinfo._dst.seconds != 0

    def findDateInFilename(self,filename,formatDate='\d{4}-\d{2}-\d{2}'):
        if '/' in filename:filename = filename.split('/')[-1]
        print('filename:',filename)
        tmax = re.findall(formatDate,filename)[0].split('-')# read the date of the last file in the folder
        print('tmax:',tmax)
        tmax = dt.datetime(int(tmax[0]),int(tmax[1]),int(tmax[2]))
        return tmax

    def convertSecstodHHMM(self,lt,t0=None,formatTime='%d - %H:%M'):
        if not t0:t0=parser.parse('00:00')
        if isinstance(t0,str):t0=parser.parse(t0)
        if isinstance(lt[0],str):
            lt = [int(t) for t in lt]
        return [(t0 + dt.timedelta(seconds=k)).strftime(formatTime) for k in lt]

    def convertToSecs(self,lt,t0=None):
        if not t0:t0=parser.parse('00:00')
        if isinstance(t0,str):t0=parser.parse(t0)
        tmp = [parser.parse(k) for k in lt]
        return [(t-t0).total_seconds() for t in tmp]

    def regExpNot(self,regexp):
        if regexp[:2] == '--': regexp = '^((?!' + regexp[2:] + ').)*$'
        return regexp

class Physics():
    def __init__(self):
        self.confDir=os.path.dirname(os.path.realpath(__file__)) + '/conf'
        self.phyQties = self.df2dict(pd.read_csv(self.confDir+ '/units.csv'))
        self.unitMag = ['u','m','c','d','','da','h','k','M']
        self.buildNewUnits()
        self.cmapNames = pickle.load(open(self.confDir+"/colormaps.pkl",'rb'))[::3]

    def buildNewUnits(self):
        self.phyQties['speed'] = self.combineUnits(self.phyQties['distance'],self.phyQties['time'])
        self.phyQties['mass flow'] = self.combineUnits(self.phyQties['weight'],self.phyQties['time'])
        tmp = self.combineUnits(['','N'],self.phyQties['volume'],'')
        self.phyQties['volumetric flow'] = self.combineUnits(tmp,self.phyQties['time'])

    def combineUnits(self,units1,units2,oper='/'):
        return [x1 + oper + x2 for x2 in units2 for x1 in units1]

    def detectUnit(self,unit):
        phId = ''
        for phyQt in self.phyQties.keys():
            # listUnits = [x1+x2 for x2 in self.phyQts[phyQt] for x1 in self.unitMag]
            listUnits = self.combineUnits(self.unitMag,self.phyQties[phyQt],'')
            if unit in listUnits : phId = phyQt
        return phId

    def detectUnits(self,listUnits,check=0):
        tmp = [self.detectUnit(unit) for unit in listUnits]
        if check :
            listUnitsDf = pd.DataFrame()
            listUnitsDf['units'] = listUnits
            listUnitsDf['grandeur'] = tmp
            return listUnitsDf
        else :
            return tmp

class DataTypesUtils():

    def df2dict(self,df):
        return {df.columns[k] : list(df.iloc[:,k].dropna()) for k in range(len(df.columns))}

    def linspace(self,arr,numElems):
        idx = np.round(np.linspace(0, len(arr) - 1, numElems)).astype(int)
        return list([arr[k] for k in idx])

    def flattenList(self,l):
        return [item for sublist in l for item in sublist]

    def removeNaN(self,list2RmNan):
        tmp = pd.DataFrame(list2RmNan)
        return list(tmp[~tmp[0].isna()][0])

    def sortIgnoCase(self,lst):
        df = pd.DataFrame(lst)
        return list(df.iloc[df[0].str.lower().argsort()][0])

    def dfcolwithnbs(self,df):
        a = df.columns.to_list()
        coldict=dict(zip(range(0,len(a)),a))
        coldict
        return coldict

    def listWithNbs(self,l):
        return [str(i) + ' : '+ str(k) for i,k in zip(range(len(l)),l)]
        # return pd.DataFrame(l)

    def dspDict(self,dict,showRows=1):
        '''display dictionnary in a easy readable way :
        dict_disp(dict,showRows)
        showRows = 1 : all adjusted '''
        maxLen =max([len(v) for v in dict])
        for key, value in dict.items():
            valToShow = value
            if showRows == 0:
                rowTxt = key.ljust(maxLen)
            if showRows == 1:
                if len(key)>8:
                    rowTxt = (key[:8]+'..').ljust(10)
                else:
                    rowTxt = key.ljust(10)
            if showRows==-1:
                rowTxt      = key.ljust(maxLen)
                valToShow   = type(value)
            if showRows==-2:
                rowTxt      = key.ljust(maxLen)
                valToShow   = value.shape
            print(colored(rowTxt, 'red', attrs=['bold']), ' : ', valToShow)

    def combineFilter(self,df,columns,filters):
        cf  = [df[col]==f for col,f in zip(columns,filters)]
        dfF = [all([cfR[k] for cfR in cf]) for k in range(len(cf[0]))]
        return df[dfF]

    def pivotDataFrame(self,df,colPivot=None,colValue=None,colTimestamp=None,resampleRate='60s',applyMethod='nanmean'):
        if not colPivot : colPivot = df.columns[0]
        if not colValue : colValue = df.columns[1]
        if not colTimestamp : colTimestamp = df.columns[2]

        listTags = list(df[colPivot].unique())
        t0 = df[colTimestamp].min()
        dfOut = pd.DataFrame()
        for tagname in listTags:
            dftmp = df[df[colPivot]==tagname]
            dftmp = dftmp.set_index(colTimestamp)
            dftmp = eval('dftmp.resample(resampleRate,origin=t0).apply(np.' + applyMethod + ')')
            dfOut[tagname] = dftmp[colValue]

        dfOut=dfOut.fillna(method='ffill')
        return dfOut

class FitUtils():

    def expDown(self,x, a, b, c):
        return a * np.exp(-b * x) + c

    def expUp(self,x,a,b,c):
        return a *(1- np.exp(-b * x)) + c

    def poly2(self,x,a,b,c):
        return a*x**2 +b*x + c

    def expUpandDown(self,x,a1,b1,c1,a2,b2,c2):
        return self.expUp(x,a1,b1,c1) + self.expDown(x,a2,b2,c2)

    def generateSimuData(self,func='expDown'):
        x = np.linspace(0, 2, 150)
        y = eval(func)(x, 5.5, 10.3, 0.5)
        np.random.seed(1729)
        y_noise = 0.2 * np.random.normal(size=x.size)
        ydata = y + y_noise
        return x,ydata

    def fitSingle(self,dfx,func='expDown',plotYes=True,**kwargs):
        x = dfx.index
        y = dfx.iloc[:,0]
        if isinstance(dfx.index[0],pd._libs.tslibs.timestamps.Timestamp):
            xdata=np.arange(len(x))
        else :
            xdata=x
        popt, pcov = curve_fit(eval('self.'+func), xdata, y,**kwargs)
        if plotYes:
            plt.plot(x, y, 'bo', label='data')
            plt.plot(x, eval('self.'+func)(xdata, *popt), 'r-',
                label='fit: a=%.2f, b=%.2f, c=%.2f' % tuple(popt))
            plt.xlabel('x')
            plt.title(list(dfx.columns)[0])
            # plt.ylabel()
            plt.gcf().autofmt_xdate()
            plt.legend()
            plt.show()
        return popt

class GraphUtils():
    def getColorHexSeq(self,N,colmap='jet'):
        cmap        = cm.get_cmap(colmap,N)
        colorList   = []
        for i in range(cmap.N):colorList.append(mtpcl.rgb2hex(cmap(i)))
        return colorList

    def updateColorMap(self,fig,colmap=None):
        listCols = self.getColorHexSeq(len(fig.data)+1,colmap=colmap)
        k,l=0,0
        listYaxis = [k for k in fig._layout.keys() if 'yax' in k]
        if len(listYaxis)>1:
            for yax in listYaxis :
                k+=1
                fig.layout[yax]['title']['font']['color'] = listCols[k]
                fig.layout[yax]['tickfont']['color'] = listCols[k]
        for d in fig._data :
            l+=1
            if 'marker' in d.keys():
                d['marker']['color']=listCols[l]
            if 'line' in d.keys():d['line']['color']=listCols[l]
        return fig

    def customLegend(self,fig, nameSwap,breakLine=None):
        if not isinstance(nameSwap,dict):
            print('not a dictionnary, there may be wrong assignment')
            namesOld = [k.name  for k in fig.data]
            nameSwap = dict(zip(namesOld,nameSwap))
        for i, dat in enumerate(fig.data):
            for elem in dat:
                if elem == 'name':
                    newName = nameSwap[fig.data[i].name]
                    if isinstance(breakLine,int):
                        newName = '<br>s'.join([newName[k:k+breakLine] for k in range(0,len(newName),breakLine)])
                    fig.data[i].name = newName
        return fig

    def makeFigureName(self,filename,patStop,toAdd):
        idx=filename.find(patStop)
        f=filename[:idx]
        f=re.sub('[\./]','_','_'.join([f]+toAdd))
        print(f)
        return f

    def buildTimeMarks(self,t0,t1,nbMarks=8,fontSize='12px'):
        maxSecs=int((t1-t0).total_seconds())
        listSeconds = [int(t) for t in np.linspace(0,maxSecs,nbMarks)]
        dictTimeMarks = {k : {'label':(t0+dt.timedelta(seconds=k)).strftime('%H:%M'),
                                'style' :{'font-size': fontSize}
                                } for k in listSeconds}
        return dictTimeMarks,maxSecs

    def getAutoAxes(self,N,inc=0.05):
        allSides =['left','right']*6
        allAnch = ['free']*12

        t=round((N-2)/2)+1
        graphLims = [0+t*inc,1-t*inc]
        tmp     = [[graphLims[0]-k,graphLims[1]+k] for k in np.arange(0,0.3,inc)]
        positions  = [it for sub in tmp for it in sub][:N]

        sides       = allSides[:N]
        anchors     = allAnch[:N]
        overlays    = [None] + ['y']*(N-1)
        return [graphLims,sides,anchors,positions,overlays]

    def multiYAxis(self,df,mapName='jet',names=None,inc=0.05):
        yList = df.columns
        cols = self.getColorHexSeq(len(yList),mapName)
        yNum=[str(k) for k in range(1,len(yList)+1)]
        graphLims,sides,anchors,positions,overlays = self.getAutoAxes(len(yList),inc=inc)
        fig = go.Figure()
        dictYaxis={}
        if not names :
            names = yList
        for y,name,side,anc,pos,col,k,overlay in zip(yList,names,sides,anchors,positions,cols,yNum,overlays):
            fig.add_trace(go.Scatter(x=df.index,y=df[y],name=y,yaxis='y'+k,
                                    marker=dict(color = col,size=10)))

            dictYaxis['yaxis'+k] = dict(
            title=name,
            titlefont=dict(color=col),
            tickfont=dict(color=col),
            anchor=anc,
            overlaying=overlay,
            side=side,
            position=pos
            )
        fig.update_layout(xaxis=dict(domain=graphLims))
        fig.update_layout(dictYaxis)
        return fig

    def printDFSpecial(self,df,allRows=True):
        # pd.describe_option('col',True)
        colWidthOri = pd.get_option('display.max_colwidth')
        rowNbOri = pd.get_option('display.max_rows')

        pd.set_option('display.max_colwidth',None)
        if allRows :
            pd.set_option('display.max_rows',None)
        pd.set_option('display.max_colwidth',colWidthOri)
        pd.set_option('display.max_rows',rowNbOri)

class SqlUtils():

    def connectToDataBase(self,h,p,d,u,w):
        connReq = "host=" + h + " port=" + p + " dbname="+ d +" user="+ u + " password=" + w
        conn    = psycopg.connect(connReq,autocommit=True)
        return conn

    def gettimeSQL(self,secs=10*60):
        t1 = dt.datetime.now()
        # t1 = dt.datetime.now(tz=timezone.utc)
        t0 = t1 - dt.timedelta(seconds=secs)
        timeRange = [t.strftime('%Y-%m-%d %H:%M:%S').replace('T',' ') for t in [t0,t1]]
        return timeRange[0], timeRange[1]

    def readSQLdataBase(self,conn,patSql,secs=60*2,tagCol="tag",tsCol="timestampz"):
        t0,t1 = self.gettimeSQL(secs=secs)
        start = time.time()
        timeSQL = tsCol + " BETWEEN '" + t0 +"' AND '" + t1 +"'"
        # tagSQL = tagCol + " like '" + patSql + "'"
        tagSQL = tagCol + " ~ '" + patSql + "'"
        sqlQ = "select * from realtimedata where " + timeSQL + " and  " + tagSQL + ";"
        print(sqlQ)
        df = pd.read_sql_query(sqlQ,conn,parse_dates=[tsCol])
        self.printCTime(start)
        return df

class ConnectUtils():
    import pandas as pd, numpy as np, pickle, re, time, datetime as dt,glob
    import subprocess as sp, os
    from datetime import timezone
    from dateutil import parser
    import xml.etree.ElementTree as ET, pandas as pd,re,struct,importlib
    def getSizeOf(typeVar,f=1):
        if typeVar == 'IEEE754':return 2*f
        elif typeVar == 'INT64': return 4*f
        elif typeVar == 'INT32': return 2*f
        elif typeVar == 'INT16': return 1*f
        elif typeVar == 'INT8': return f/2

    def demoBytesInt():
    # https://docs.python.org/fr/3/library/stdtypes.html

        #convert an int to bytes
        (1000).to_bytes(2, byteorder='little')
        #convert bytes to int
        int.from_bytes(b'\xfc\x00', byteorder='big', signed=False)
        int.from_bytes([255, 0], byteorder='big')

        float.hex(3740.0)
        float.fromhex('0x3.a7p10')

    def wordTofloat(t = (123, 456)):
        import struct,binascii
        packed_string = struct.pack("HH", *t)
        print(binascii.hexlify(packed_string))
        unpacked_float = struct.unpack("f", packed_string)[0]
        return unpacked_float

    def ieee_754_conversion(n, sgn_len=1, exp_len=8, mant_len=23):
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

    def decodeModeBusIEEE754(a,b,endianness='big',signed=False):
        a = '{0:04x}'.format(a)# from decimal to hexadecimal representation of a word
        b = '{0:04x}'.format(b)
        # a = a.to_bytes(2, byteorder=endianness,signed=signed)
        # b = b.to_bytes(2, byteorder=endianness,signed=signed)
        # xx = a+b
        xx = b+a
        # try:return struct.unpack('!f', xx)[0]
        try:return struct.unpack('!f', bytes.fromhex(xx))[0]
        except : return 'error'

    def decodeModeBusINT32(a,b,endianness='big',signed=False):
        # a = '{0:04x}'.format(a)
        # b = '{0:04x}'.format(b)
        # a = a.to_bytes(2, byteorder=endianness,signed=signed)
        # b = b.to_bytes(2, byteorder=endianness,signed=signed)
        # xx = a+b
        # xx = b+a
        # try:return struct.unpack('!f', bytes.fromhex(xx))[0]
        # except : return 'error'
        return a + 256**2*b

    def decodeModeBusINT64(a,b,c,d):
        return a + 256**2*b + 256**4*c + 256**6*d

    def showRegisterValue(c,dfInstr,id):
        idinit=id
        if isinstance(id,int): id = dfInstr.iloc[id,:]
        else :
            id = dfInstr[dfInstr['id']==id]
            if len(id)>1: id=id.iloc[0,:]
            else : id = id.squeeze()
        # print(id)
        intadd,typedata   = id['intAddress'],id['type']
        sizeType = getSizeOf(typedata,1)
        regs     = c.read_holding_registers(intadd,sizeType)
        if typedata == 'INT32':value = decodeModeBusINT32(regs[0],regs[1])
        if typedata == 'IEEE754':value = decodeModeBusIEEE754(regs[0],regs[1])
        elif typedata == 'INT64':value = decodeModeBusINT64(regs[0],regs[1],regs[2],regs[3])
        value=value*id.scale
        print(typedata,intadd,id['id'],regs,'======>',value)
        return value

    def tryDecoding(regs,formatOut=None,endianness='!'):
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
        hexList   = utils.flattenList([[k[:2],k[2:]] for k in hexList])
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
