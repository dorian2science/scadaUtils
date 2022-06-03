import pandas as pd, numpy as np, pickle, re, time, datetime as dt,glob
from datetime import timezone
import subprocess as sp, os
import plotly.graph_objects as go
import plotly.express as px
from plotly.validators.scatter.line import ShapeValidator
from plotly.validators.scatter.marker import SymbolValidator
from plotly.validators.scatter.line import DashValidator

def dimensions_pictures_screen(diag_inch=15,resolution=[1920,1080]):
    res={}
    res['a_ratio'] = 16/9
    res['resolution'] = resolution
    res['inch2cm'] = 2.54
    res['screen_w'] = np.cos(np.arctan(1/res['a_ratio']))*diag_inch
    res['screen_h'] = np.sin(np.arctan(1/res['a_ratio']))*diag_inch
    dpi_w=resolution[0]/res['screen_w']
    dpi_h=resolution[1]/res['screen_h']
    res['dpi']=np.mean([dpi_h,dpi_w])
    return res

class Utils:
    def __init__(self):
        self.confDir=os.path.dirname(os.path.realpath(__file__)) + '/conf'
        self.phyQties = self.df2dict(pd.read_csv(self.confDir+ '/units.csv'))
        self.unitMag = ['u','m','c','d','','da','h','k','M']
        self.buildNewUnits()
        raw_symbols = pd.Series(SymbolValidator().values[2::3])
        self.raw_symbols = list(pd.concat([raw_symbols[::4],raw_symbols[1::4],raw_symbols[2::4]]))
        self.listLines = 40*DashValidator().values[:-1]
        self.lineshapes = ShapeValidator().values
        allcolors=px.colors.qualitative.Plotly.copy()
        allcolors+=px.colors.qualitative.Dark24.copy()+px.colors.qualitative.Light24
        allcolors+=px.colors.qualitative.Alphabet
        allcolors+=px.colors.qualitative.Set1+px.colors.qualitative.Pastel1
        allcolors+=px.colors.qualitative.Antique
        self.colors_mostdistincs = allcolors
        self.styles = ['lines+markers','markers','stairs','lines']
        self.colorPalettes=pd.read_pickle(self.confDir + '/palettes.pkl')

        from PIL import Image # new import
        self.sylfenlogo  = Image.open(self.confDir +  '/logo_sylfen.png')

    # ==========================================================================
    #                               DEBUG
    # ==========================================================================

    def printCTime(self,start,entete='time laps' ):
        return entete + ' : {:.2f} seconds'.format(time.time()-start)

    def printListArgs(self,*args):
        for a in args :
            print(' ------- ')
            print(a)
        print('============ args finished =================')

    # ==========================================================================
    #                               SYSTEM
    # ==========================================================================
    def read_csv_datetimeTZ(self,filename,overwrite=False,**kwargs):
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

    def convert_csv2pkl(self,folderCSV,folderPKL,overwrite=False):
        try :
            listFiles=self.get_listFilesPkl(folderCSV,'.csv')
            if not overwrite:
                listFiles = [f for f in listFiles if not f[:-4]+'.pkl' in folderPKL]
                for filename in listFiles:
                    df=self.read_csv_datetimeTZ(folderCSV + filename)
                    with open(folderPKL + filename[:-4] + '.pkl' , 'wb') as handle:
                        pickle.dump(df, handle, protocol=pickle.HIGHEST_PROTOCOL)
        except:
            print('no csv files in directory : ',folderCSV)

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
        if not idxForMean :
            idxForMean = list(range(windowPts,len(df),windowPts))
        ll = [df.iloc[k-windowPts:k+windowPts+1,col].mean().to_frame().transpose()
                for k in idxForMean]
        dfR = pd.concat(ll)
        dfR.index = df.index[idxForMean]
        return dfR

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
        # print('filename:',filename)
        tmax = re.findall(formatDate,filename)[0].split('-')# read the date of the last file in the folder
        # print('tmax:',tmax)
        tmax = dt.datetime(int(tmax[0]),int(tmax[1]),int(tmax[2]))
        return tmax

    def writeLog(self,logFile,msg,newBlock=False):
        goLine = '================================================================'
        with open(logFile, 'a') as f:
            if newBlock:f.write(goLine + '\n')
            f.write(msg + '\n')
            if newBlock:f.write(goLine + '\n')

    def getSysConf(self, scriptFile):
        def toString(b):
            s = str(b).strip()
            if (s.startswith("b'")): s = s[2:].strip()
            if (s.endswith("'")): s = s[:-1].strip()
            return s
        conf = None
        with open(scriptFile) as f: s= ''.join(f.readlines())+'\nenv'
        process = sp.Popen(s,stdout=sp.PIPE,stderr=sp.PIPE,shell=True,
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
        else : print(stderr)

        return conf

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

    def lowpass(self,x,alpha=0.01):
        newx=x.copy()
        for k in range(1,len(x)):
            newx[k] = (1-alpha)*newx[k-1] + alpha*newx[k]
        return newx

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
    def loads_pickle(self,file_pkl):
        f = open(file_pkl,'rb')
        objs = []
        while 1:
            try:
                objs.append(pickle.load(f))
            except EOFError:
                break
        return objs

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

    def dictdict2df(self,dictdictGroups):
        dfGroups=pd.DataFrame.from_dict(dictdictGroups)
        dfGroups['tag']=dfGroups.index
        dfGroups=dfGroups.melt(id_vars='tag')
        dfGroups=dfGroups.dropna().set_index('tag')
        dfGroups.columns=['group','subgroup']
        return dfGroups

    def export2excel(df,filepath):
        if isinstance(df.index,pd.core.indexes.datetimes.DatetimeIndex):
            df.index=[k.isoformat() for k in df.index]
        df.to_excel(filepath)

    def popup_dfexcel(self,df):
        if isinstance(df.index,pd.core.indexes.datetimes.DatetimeIndex):
            df.index=[k.isoformat() for k in df.index]
        df.to_excel('/tmp/test.xlsx')
        sp.Popen(['libreoffice','/tmp/test.xlsx'])

    def showdf_as_table(self,df):
        fig = go.Figure(data=[go.Table(
        header=dict(values=list(df.columns),
        fill_color='paleturquoise',
        align='left'),
        cells=dict(values=[df[k] for k in df.columns],
        fill_color='lavender',
        align='left'))
        ])
        fig.show()
        return fig
    # ==========================================================================
    #                           GRAPHICS
    # ==========================================================================
    def sample_colorscale(self,N,colorscale='jet'):
        return px.colors.sample_colorscale(colorscale,np.linspace(0,1,N))

    def updateColorMap(self,fig,listCols=None):
        if listCols is None:
            listCols = self.colors_mostdistincs
        if isinstance(listCols,str):
            listCols = self.sample_colorscale(len(fig.data)+1,colorscale=listCols)
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
        return f

    def figureName(self,params,joinCara=',',egal='=',patAfterList=None):
        listParams=[]
        if not patAfterList : patAfterList=['']*len(params)
        for (k,v),u in zip(params.items(),patAfterList):
            tmp = ''
            if isinstance(v,int):tmp = k + egal + '{:d}'.format(v) + ' ' +u
            if isinstance(v,float):tmp=k + egal + '{:1f}'.format(v) + ' ' +u
            if isinstance(v,str):
                if len(v)>0 : tmp= k + egal + v + ' ' +u
            if not not tmp:listParams.append(tmp)
        return joinCara.join(listParams)

    def buildTimeMarks(self,t0,t1,nbMarks=8,fontSize='12px'):
        maxSecs=int((t1-t0).total_seconds())
        listSeconds = [int(t) for t in np.linspace(0,maxSecs,nbMarks)]
        dictTimeMarks = {k : {'label':(t0+dt.timedelta(seconds=k)).strftime('%H:%M'),
                                'style' :{'font-size': fontSize}
                                } for k in listSeconds}
        return dictTimeMarks,maxSecs

    def getAutoYAxes(self,N,xrange,inc):
        sides =['left','right']*6 # alterne
        # print(xrange)
        positions  = self.flattenList([[xrange[0]-k*inc,xrange[1]+k*inc] for k in range(6)])
        return sides[:N],positions[:N]

    def getLayoutMultiUnit(self,dictGroups,colormap='jet',axisSpace=0.05):
        dfGroups = pd.DataFrame.from_dict(dictGroups,orient='index',columns=['group'])
        groups=dfGroups.group.unique()

        yaxes=['yaxis'] + ['yaxis'+str(k) for k in range(2,len(groups)+1)]
        minx = (len(groups)-1)//2*axisSpace
        xdomain =[minx,1-minx]
        sides,positions = self.getAutoYAxes(len(groups),xdomain,inc=axisSpace)
        colors=self.sample_colorscale(len(groups),colormap)
        dfGroups['color']=colors[0]
        dfGroups['symbol'] = 'circle'
        dfGroups['line']   = 'solid'
        dictYaxis={}
        yscales=['y'] + ['y'+str(k) for k in range(2,len(groups)+1)]
        for g,c,s,p,y,ys in zip(groups,colors,sides,positions,yaxes,yscales):
            dfGroups.loc[dfGroups.group==g,'color'] = c
            dfGroups.loc[dfGroups.group==g,'yscale'] = ys
            lenGroup=len(dfGroups[dfGroups.group==g])
            dfGroups.loc[dfGroups.group==g,'line']=self.listLines[:lenGroup]
            dfGroups.loc[dfGroups.group==g,'symbol']=self.raw_symbols[:lenGroup]
            if ys=='y' : ov = None
            else : ov = 'y'
            dictYaxis[y] = dict(
                title=g,
                titlefont=dict(color=c),
                tickfont=dict(color=c),
                anchor='free',
                overlaying=ov,
                side=s,
                position=p,
                gridcolor=c
            )
        fig = go.Figure()
        fig.update_layout(dictYaxis)
        fig.update_layout(xaxis=dict(domain=xdomain))
        return fig,dfGroups

    def multiUnitGraph(self,df,dictGroups=None,sizeDots=3,dropna=False):
        if not dictGroups : dictGroups={t:t for t in df.columns}
        fig,dfGroups=self.getLayoutMultiUnit(dictGroups)
        if len(dfGroups.yscale.unique())>12:
            print('too many axes. Please reduce the number of axis')
            return
        for trace in df.columns:
            col=dfGroups.loc[trace,'color']
            y = df[trace]
            if dropna:y = y.dropna()
            fig.add_trace(go.Scatter(
                x=df.index,y=y,name=trace,
                mode="lines+markers",
                yaxis=dfGroups.loc[trace,'yscale'],
                marker=dict(color = col,size=sizeDots,symbol=dfGroups.loc[trace,'symbol']),
                line=dict(color = col,dash=dfGroups.loc[trace,'line'])
                ))
        fig.update_yaxes(showgrid=False)
        return fig

    def getAutoXYAxes(self,n,grid=None,hspace=0.05,minx=0.05,**kwargs):
        from plotly.subplots import make_subplots
        if not grid:grid=self.optimalGrid(n)
        fig = make_subplots(rows=grid[0], cols=grid[1],**kwargs)

        maxx = 1-minx
        if fig.layout['xaxis'].domain[0]==0:
            fig.layout['xaxis'].domain=[minx,fig.layout['xaxis'].domain[1]]
        if fig.layout['xaxis'].domain[1]==1:
            fig.layout['xaxis'].domain=[fig.layout['xaxis'].domain[0],maxx]
        for k in range(2,n+1):
            if fig.layout['xaxis' + str(k)].domain[0]==0:
                fig.layout['xaxis' + str(k)].domain=[minx,fig.layout['xaxis'+ str(k)].domain[1]]
            if fig.layout['xaxis' + str(k)].domain[1]==1:
                fig.layout['xaxis' + str(k)].domain=[fig.layout['xaxis'+ str(k)].domain[0],maxx]
        return fig

    def getLayoutMultiUnitSubPlots(self,dictdictGroups,colormap='jet',axisSpace=0.02,**kwargs):
        dfGroups = self.dictdict2df(dictdictGroups)
        groups = dfGroups.group.unique()
        maxgroups = max([len(dfGroups.groupby('group').get_group(g).subgroup.unique()) for g in groups])
        minx = (maxgroups-1)//2*axisSpace
        # print('minx : ',minx,'===========','maxgroups : ',maxgroups)
        fig=self.getAutoXYAxes(len(groups),minx=minx,**kwargs)

        dfGroups['xaxis']='x'
        dfGroups['yaxis']='y'
        dfGroups['color']='blue'
        dfGroups['symbol']='hexagon-dot'
        dfGroups['line']='solid'

        xaxisNames =['xaxis' + str(k) for k in range(1,len(groups)+1)]
        yaxisNames1 = ['yaxis' + str(k) for k in range(1,len(groups)+1)]
        xscales = ['x' + str(k) for k in range(1,len(groups)+1)]
        yscales1 =['y' + str(k) for k in range(1,len(groups)+1)]

        dictYaxis,dictXaxis = {},{}
        for g,ax,ay1,xs,ys1 in zip(groups,xaxisNames,yaxisNames1,xscales,yscales1):
            # print(ax,' ------ ',ay1,' ------ ',g)
            subgroups=dfGroups[dfGroups.group==g].subgroup.unique()
            colors=self.sample_colorscale(len(subgroups),colormap)
            yaxisNames = [ay1 + str(k) for k in range(1,len(subgroups)+1)]
            yscales = [ys1 + str(k) for k in range(1,len(subgroups)+1)]
            sides,positions = self.getAutoYAxes(len(subgroups),fig.layout[ax].domain,inc=axisSpace)

            dictXaxis[ax] = dict(anchor=ys1+str(1),domain=fig.layout[ax].domain)
            for sg,c,s,p,ys,ay in zip(subgroups,colors,sides,positions,yscales,yaxisNames):
                # print(sg,' ------ ',c,' ------ ',ys)
                # print(dfGroups[(dfGroups.group==g)&(dfGroups.subgroup==sg),'color'])
                filter=(dfGroups.group==g)&(dfGroups.subgroup==sg)
                dfGroups.loc[filter,'color'] = c
                dfGroups.loc[filter,'yaxis'] = ys
                dfGroups.loc[filter,'xaxis'] = xs
                # print(ax,' ------ ',ay1,' ------ ',g)
                lensubgroup=len(dfGroups[dfGroups.subgroup==sg])
                dfGroups.loc[dfGroups.subgroup==sg,'line']=self.listLines[:lensubgroup]
                dfGroups.loc[dfGroups.subgroup==sg,'symbol']=self.raw_symbols[:lensubgroup]
                if ys==ys1+'1' : ov = None
                else : ov = ys1+'1'
                dictYaxis[ay] = dict(
                    title=sg,
                    color=c,
                    anchor='free',
                    domain=fig.layout[ay1].domain,
                    overlaying=ov,
                    side=s,
                    position=p,
                )

        fig.update_layout(dictXaxis)
        fig.update_layout(dictYaxis)
        return fig,dfGroups

    def multiUnitGraphSubPlots(self,df,dictdictGroups,**kwargs):
        fig,dfGroups=self.getLayoutMultiUnitSubPlots(dictdictGroups,**kwargs)
        for trace,g in zip(dfGroups.index,dfGroups.group):
            curTrace =dfGroups[dfGroups.group==g].loc[trace,:]
            col,xa,ya,symbol,line = [curTrace[k] for k in ['color','xaxis','yaxis','symbol','line']]
            # print(col,'-----',xa,'-----',ya,'-----',symbol,'-----',line)
            fig.add_trace(go.Scatter(
                x=df.index,y=df[trace],name=trace,
                mode="lines+markers",xaxis=xa,yaxis=ya,
                marker=dict(color = col,size=10,symbol=symbol),
                line=dict(color = col,dash=line))
            )
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

    def updateStyleGraph(self,fig,style='lines+markers',colmap='jet',heightGraph=700):
        '''
        see self.styles
        '''

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
                height=800,width=1200
            )
        if not not xlab:fig.update_layout(yaxis_title = ylab)
        if not not ylab:fig.update_layout(xaxis_title = xlab)
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
                # print(rs)
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

    def plotGraphType(self,df,typeGraph='scatter',**kwargs):
        if 'tag' in df.columns:
            if typeGraph == 'scatter' :fig = px.scatter(df,x=df.index, y='value', color='tag',**kwargs)
            if typeGraph == 'area' :fig = px.area(df,x=df.index, y='value', color='tag',**kwargs)
            if typeGraph == 'area %' :fig = px.area(df,x=df.index, y='value', color='tag',groupnorm='percent',**kwargs)
        else :
            if typeGraph == 'scatter' :fig = px.scatter(df)
            if typeGraph == 'area' :fig = px.area(df)
            if typeGraph == 'area %' :fig = px.area(df,groupnorm='percent')
        return fig

    def legendPersistant(self,previousFig,newFig):
        if not not previousFig:
            visible_state = {}
            for trace in previousFig['data']:
                idxO = [k for k,v in enumerate(newFig['data']) if v['name']==trace['name']]
                if len(idxO)==1:
                    visible = trace['visible'] if 'visible' in trace.keys() else True
                    newFig['data'][idxO[0]]['visible'] = visible
        return newFig

    def addLogo(self,fig):
        fig.add_layout_image(
            dict(
                source=self.sylfenlogo,
                xref="paper", yref="paper",
                x=0., y=1.02,
                sizex=0.12, sizey=0.12,
                xanchor="left", yanchor="bottom"
            ))
        return fig

    def add_drawShapeToolbar(self,fig):
        fig.update_layout(
            dragmode='drawopenpath',
            newshape_line_color='cyan',
            title_text='Draw a path to separate versicolor and virginica',
            modebar_add=['drawline',
                'drawopenpath',
                'drawclosedpath',
                'drawcircle',
                'drawrect',
                'eraseshape'
               ])

    def showPalettes(self,color):
        colorPalettes = self.colorPalettes
        cols = colorPalettes[color]['hex']
        # cols = cols.loc['Red','Salmon Pink','Cordovan','Tomato','Rosy brown','Scarlet','Bittersweet','Blood red']
        data=[[k,k] for k,c in enumerate(cols)]
        df = pd.DataFrame(data)
        df.index = colorPalettes[color].index
        fig=px.scatter(df.transpose(),color_discrete_sequence=cols)
        fig.update_traces(line_width=20,mode='lines').show()

class DataBase:
    def __init__(self):
        try :
            import psycopg3 as psycopg
        except:
            import psycopg2 as psycopg
        self.psycopg=psycopg

    def connectToPSQLsDataBase(self,connParameters):
        connReq = ''.join([k + "=" + v + " " for k,v in connParameters.items()])
        conn = self.psycopg.connect(connReq)
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
        timeSQL = tsCol + " BETWEEN '" + t0 +"' AND '" + t1 +"'"
        # tagSQL = tagCol + " like '" + patSql + "'"
        tagSQL = tagCol + " ~ '" + patSql + "'"
        sqlQ = "select * from realtimedata where " + timeSQL + " and  " + tagSQL + ";"
        df = pd.read_sql_query(sqlQ,conn,parse_dates=[tsCol])
        return df

    def readSeveralTagsSQL(self,conn,tags,secs=60*2,tagCol="tag",tsCol="timestampz",timeRange=None):
        if not timeRange:
            t0,t1 = self.gettimeSQL(secs=secs)
        else :
            t0,t1 = timeRange
        timeSQL = tsCol + " BETWEEN '" + t0 +"' AND '" + t1 +"'"
        tagSQL = tagCol + " in ('" + "','".join(tags) + "')"
        sqlQ = "select * from realtimedata where " + timeSQL + " and  " + tagSQL + ";"
        df = pd.read_sql_query(sqlQ,conn,parse_dates=[tsCol])
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

class Callback():
    import base64
    import io

    def __init__(self,):
        self.utils = Utils()

    def parse_contents(self,contents, filename):
        content_type, content_string = contents.split(',')
        decoded = self.base64.b64decode(content_string)
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            return pd.read_csv(
                self.io.StringIO(decoded.decode('utf-8')),index_col=0)
        elif 'xls' in filename:
            # Assume that the user uploaded an excel file
            return pd.read_excel(self.io.BytesIO(decoded))

    def df_toTable(self,df):
        rows = df.to_dict('records')
        cols=[{"name": i, "id": i,'renamable': True, 'deletable': True}
                            for i in df.columns]
        return rows,cols

    def exportDataOnClick(self,fig,baseName=None):
        dfs = []
        gofig=go.Figure(fig)
        for trace in gofig.data :
            tmp = pd.DataFrame([trace['x'],trace['y']])
            tmp = tmp.transpose()
            tmp = tmp.set_index(0)
            tmp.columns=[trace.name]
            dfs.append(tmp)
        df = pd.concat(dfs,axis=1)
        filename = 'exportedData'
        return df,filename
