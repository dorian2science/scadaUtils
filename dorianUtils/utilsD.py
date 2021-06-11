import pandas as pd, numpy as np, pickle, re, time, datetime as dt,glob
from datetime import timezone
import subprocess as sp, os
from dateutil import parser
import plotly.graph_objects as go
import plotly.express as px
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
        self.listPatterns = ['.*',
        '[A-Z0-9]+',
        '[A-Z0-9]+_[A-Z0-9]+',
        '[A-Z0-9]+_[A-Z0-9]+_[A-Z0-9]+',
        '[A-Z0-9]+_[A-Z0-9]+_[A-Z0-9]+_[A-Z0-9]+',
        '[\w_]+[A-Z]+',
        '[A-Za-z]+',]
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

    def dateOffset(self,datum,offset=0):
        datum = parser.parse(datum)
        return (datum + dt.timedelta(days=i+offset)).strftime('%Y-%m-%d')

    def timeBetween2Dates(self,dates,N=10):
        t0,t1 = [parser.parse(k) for k in dates]
        listSecs = np.linspace(0,(t1-t0).total_seconds(),N)
        return [(t0 + dt.timedelta(seconds=k)).strftime('%Y-%m-%d %H:%M') for k in listSecs]

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

    # ==========================================================================
    #                           PHYSICS
    # ==========================================================================
    def buildNewUnits(self):
        self.phyQties['vitesse'] = self.combineUnits(self.phyQties['distance'],self.phyQties['temps'])
        self.phyQties['mass flow'] = self.combineUnits(self.phyQties['masse'],self.phyQties['temps'])
        tmp = self.combineUnits(['','N'],self.phyQties['volume'],'')
        self.phyQties['volumetric flow'] = self.combineUnits(tmp,self.phyQties['temps'])
        self.phyQties['conducitivité'] = self.combineUnits(self.phyQties['conductance'],self.combineUnits(self.unitMag,self.phyQties['distance'],''))

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

    # ==========================================================================
    #                       lIST AND DICTIONNARIES
    # ==========================================================================
    def df2dict(self,df):
        return {df.columns[k] : list(df.iloc[:,k].dropna()) for k in range(len(df.columns))}

    def linspace(self,arr,numElems):
        idx = np.round(np.linspace(0, len(arr) - 1, numElems)).astype(int)
        return list([arr[k] for k in idx])

    def flattenList(self,l):
        return [item for sublist in l for item in sublist]

    def flattenDict(self,ld):
        finalMap = {}
        for d in ld:finalMap.update(d)
        return finalMap

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

    def listWithNbs(self,l,withDF=False):
        if withDF:return pd.DataFrame(l)
        else : return [str(i) + ' : '+ str(k) for i,k in zip(range(len(l)),l)]

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

    def uniformListStrings(self,l):
        newList=[]
        for k in l:
            li=[m.start(0) for m in re.finditer('\w',k)]
            newList.append(k[li[0]:li[-1]+1].capitalize())
        return newList

    # ==========================================================================
    #                                   DATAFRAMES
    # ==========================================================================
    def combineFilter(self,df,columns,filters):
        cf  = [df[col]==f for col,f in zip(columns,filters)]
        dfF = [all([cfR[k] for cfR in cf]) for k in range(len(cf[0]))]
        return df[dfF]

    def pivotDataFrame(self,df,colTagValTS=None,resampleRate='60s',applyMethod='nanmean'):
        if not colTagValTS : colTagValTS = [0,1,2]
        colTagValTS = df.columns[colTagValTS]
        listTags = list(df[colTagValTS[0]].unique())
        t0 = df[colTagValTS[2]].min()
        dfOut = pd.DataFrame()
        for tagname in listTags:
            dftmp = df[df[colTagValTS[0]]==tagname]
            dftmp = dftmp.set_index(colTagValTS[2])
            dftmp = eval('dftmp.resample(resampleRate,origin=t0).apply(np.' + applyMethod + ')')
            dfOut[tagname] = dftmp[colTagValTS[1]]

        # dfOut=dfOut.fillna(method='ffill')
        return dfOut

    # ==========================================================================
    #                           FITTING FUNCTIONS
    # ==========================================================================

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

    # ==========================================================================
    #                           GRAPHICS
    # ==========================================================================
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

    def optimalGrid(self,n):
        if n==1:return [1,1]
        elif n==2:return [2,1]
        elif n==3:return [3,1]
        elif n==4:return [2,2]
        elif n==5:return [3,2]
        elif n==6:return [3,2]
        elif n==7:return [4,2]
        elif n==8:return [4,2]
        elif n==9:return [3,3]
        elif n==10:return [5,2]

    def rowsColsFromGrid(self,n,grid):
        i,rows,cols=0,[],[]
        idxMin=grid.index(min(grid))
        while i<n+1:
            rows.append(i%min(grid)+1)
            cols.append(i//min(grid)+1)
            # print(i,rows[i],cols[i])
            i+=1
        if idxMin==0:return rows,cols
        else:return cols,rows

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

    def figureName(self,params,joinCara=',',egal='='):
        listParams=[]
        for k,v in params.items():
            tmp = ''
            if isinstance(v,int):tmp = k + egal + '{:d}'.format(v)
            if isinstance(v,float):tmp=k + egal + '{:1f}'.format(v)
            if isinstance(v,str):
                if len(v)>0 : tmp= k + egal +v
            if not not tmp:listParams.append(tmp)
        return joinCara.join(listParams)


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

    def exportDataOnClick(self,fig,folder=None,baseName=None):
        dfs = []
        for trace in fig.data :
            tmp = pd.DataFrame([trace['x'],trace['y']])
            tmp = tmp.transpose()
            tmp = tmp.set_index(0)
            tmp.columns=[trace.name]
            dfs.append(tmp)
        df = pd.concat(dfs,axis=1)

        xlims=fig['layout']['xaxis']['range']
        trange=[parser.parse(k) for k in xlims]
        df.index = [parser.parse(k) for k in df.index]
        df = df[(df.index>xlims[0]) & (df.index<xlims[1])]

        dateF=[k.strftime('%Y-%m-%d %H_%M') for k in trange]

        if not baseName :baseName = ''
        filename = baseName +  '_' + dateF[0]+ '_' + dateF[1]
        if not folder:folder=os.getenv('HOME')+'/Pictures/'
        filename = self.slugify(filename)
        df.to_csv(folder + filename + '.csv')
        return df

    def updateStyleGraph(self,fig,style='lines+markers',colmap='jet',heightGraph=700):
        '''style = {'lines+markers','markers','stairs','lines'}'''
        if style=='lines+markers':
            fig.update_traces(mode='lines+markers',line_shape='linear', marker_line_width=0.2, marker_size=6,line=dict(width=3))
        elif style=='markers':
            fig.update_traces(mode='markers', marker_line_width=0.2, marker_size=4)
        elif style=='stairs':
            fig.update_traces(mode='lines+markers',line_shape='hv', marker_line_width=0.2, marker_size=6,line=dict(width=3))
        elif style=='lines':
            fig.update_traces(mode='lines',line=dict(width=1),line_shape='linear')
        self.updateColorMap(fig,colmap)
        fig.update_layout(height=heightGraph)
        return fig

    def quickLayout(self,fig,title='',xlab='',ylab='',style='std'):
        if style=='std':
            fig.update_layout(
                title={'text': title,'x':0.5,'xanchor': 'center','yanchor': 'top'},
                title_font_color="RebeccaPurple",title_font_size=18),

        if style=='latex':
            fig.update_layout(
                font=dict(family="Times New Roman",size=18,color="black"),
                title={'text': title,'x':0.5,'xanchor': 'center','yanchor': 'top'},
                title_font_color="RebeccaPurple",title_font_size=22,
            )
        fig.update_layout(yaxis_title = ylab,xaxis_title = xlab)
        # fig.show(config=dict({'scrollZoom': True}))
        return fig

    def legendStyle(self,fig,style='big'):
        if style=='plotlySetup':
            return fig.update_layout(
                legend=dict(x=0,y=1,traceorder="reversed",
                font=dict(family="Courier",size=12,color="black"),
                    title_font_family="Times New Roman",
                    bgcolor="LightSteelBlue",bordercolor="Black",borderwidth=2
                    )
                )
        elif style=='big':
            return fig.update_layout(
                font=dict(family="Courier",size=16,color="black"),
                legend=dict(
                            title_font_family="Times New Roman",
                            title_font_size=22,
                            font=dict(family="Courier",size=18,color="black")
                    )
                )
        elif style=='big2':
            fig.update_layout(
                title="Plot Title",
                xaxis_title="X Axis Title",
                yaxis_title="Y Axis Title",
                font=dict(family="Courier New, monospace",size=18,color="black")
    )


    def prepareDFsforComparison(self,dfs,groups,group1='group1',group2='group2',regexpVar='',rs=None,):
        'dfs:list of pivoted dataframes with a timestamp as index'
        dfsOut=[]
        for df,groupy in zip(dfs,groups):
            if not not rs:
                print(rs)
                df=df.resample(rs).apply(np.mean)
            df['timestamp']= df.index
            df[group1]  = groupy
            df = df.melt(id_vars = ['timestamp',group1])
            if not regexpVar:df[group2] = df.variable
            else:df[group2] = df.variable.apply(lambda x:re.findall(regexpVar,x)[0])
            dfsOut.append(df)
        return pd.concat(dfsOut,axis=0)

    def graphComparaison(self,df,title,ylab,line=True):
        if line : fig=px.line(df,x='timestamp',y='value',color=group2,line_dash=group1)
        else : px.scatter(df,x='timestamp',y='value',color=group2,symbol=group1)
        fig.update_traces(mode='lines+markers',line=dict(width=2))
        fig = self.addTiYXlabs(fig,title='comparaison of ' + title,ylab=ylab,style=1)
        return fig
    # ==========================================================================
    #                           SQL
    # ==========================================================================

    def connectToPSQLsDataBase(self,connParameters=None):
        if not connParameters :
            connParameters ={
                'host'     : "192.168.1.222",
                'port'     : "5434",
                'dbname'   : "Jules",
                'user'     : "postgres",
                'password' : "SylfenBDD"
            }
        connReq = ''.join([k + "=" + v + " " for k,v in connParameters.items()])
        conn = psycopg.connect(connReq)
        # conn = psycopg.connect(connReq,autocommit=True)
        return conn

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

    def executeSQLRequest(self,conn,sqlR):
        cur  = conn.cursor()
        cur.execute(sqlR)
        data = cur.fetchall()
        for row in data :
            print(row)

    def showAllTables(self,conn):
        sqlR = 'select * from information_schema.tables'
        self.executeSQLRequest(sqlR)

class EmailSmtp:

    import os
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email.mime.text import MIMEText
    from email.utils import COMMASPACE
    from email import encoders

    host = None
    port = 25
    user = None
    password = None
    isTls = False

    # Constructor
    def __init__(self, host='127.0.0.1', port=25, user=None, password=None, isTls=False):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.isTls = isTls

    # Send a email with the possibility to attach one or several  files
    def sendMessage(self, fromAddr, toAddrs, subject, content, files=None):
        '''
        Send an email with attachments.

        - Configuring:
            smtp = EmailSmtp()
            smtp.host = 'smtp.office365.com'
            smtp.port = 587
            smtp.user = "datalab@akka.eu"
            smtp.password = "xxxxx"
            smtp.isTls = True

        - Examples of contents:
            # A pure text content
            content1 = "An alert level 3 has been created from the system"
            # Another pure text content
            content2 = [["An alert level 3 has been created from the system", "text"]]
            # A pure html content
            content3 = [["An alert level 3 has been created <br>from the system.<br>", "html"]]
            # A list of text and html contents
            content4 = [
                ["ALERT LEVEL 3!\n", "text"],
                ["An alert level 3 has been created <br>from the system.<br><br>", "html"],
                ["ALERT LEVEL 2!\n", "text"],
                ["An alert level 2 has been also created <br>from the system.<br>", "html"]
            ]

        - Example of attaching file(s):
            # Specifying only one file
            files1 = "./testdata/bank.xlsx"
            # Specifying several files
            files2 = ["./testdata/bank.xlsx", "./testdata/OpenWeather.json"]

        - Example of sending a message:
            # Choose your message and send it
            smtp.sendMessage(
                     fromAddr = "ALERTING <data.intelligence@akka.eu>",
                     toAddrs = ["PhilAtHome <prossblad@gmail.com>", "PhilAtCompany <philippe.rossignol@akka.eu>"],
                     subject = "WARNING: System issue",
                     content = content4,
                     files = files2
            )
        '''

        # Prepare the message
        message = self.MIMEMultipart()
        message["From"] = fromAddr
        message["To"] = self.COMMASPACE.join(toAddrs)
        from email.utils import formatdate
        message["Date"] = formatdate(localtime=True)
        message["Subject"] = subject

        # Create the content (text, html or a combination)
        if (type(content) is not str and type(content) is not list): content = str(content)
        if (type(content) is str): content = [[content, "plain"]]
        for msg in content:
            if (msg[1].strip().lower() != "html"): msg[1] = "plain"
            message.attach(self.MIMEText(msg[0], msg[1]))

        # Attach the files
        if (files != None):
            if (type(files) is str): files = [files]
            for path in files:
                part = self.MIMEBase("application", "octet-stream")
                with open(path, "rb") as file: part.set_payload(file.read())
                self.encoders.encode_base64(part)
                part.add_header("Content-Disposition", 'attachment; filename="{}"'.format(self.os.path.basename(path)))
                message.attach(part)

        # Send the message
        if (fromAddr == None): fromAddr = user
        con = self.smtplib.SMTP(self.host, self.port)
        if (self.isTls): con.starttls()
        if (self.user != None and self.password != None): con.login(self.user, self.password)
        con.sendmail(fromAddr, toAddrs, message.as_string())
        con.quit()
