import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from dateutil import parser
import re,datetime as dt, numpy as np
from dorianUtils.utilsD import Utils

class DccExtended:
    def __init__(self):
        self.utils=Utils()
        self.graphStyles = ['lines+markers','stairs','markers','lines']
        self.graphTypes = ['scatter','area','area %']
        self.stdStyle = {'fontsize':'12 px','width':'120px','height': '40px','min-height': '1px',}

    ''' dropdown with a list or dictionnary. Dictionnary doesn"t work for the moment '''
    def dropDownFromList(self,idName,listdd,pddPhrase = None,defaultIdx=None,labelsPattern=None,**kwargs):
        if not pddPhrase :
            pddPhrase = 'Select your ... : ' + idName
        p = html.P(pddPhrase)
        if labelsPattern :
            ddOpt= [{'label': re.findall(labelsPattern,t)[0], 'value': t} for t in listdd]
        else :
            ddOpt =[{'label': t, 'value': t} for t in listdd]

        if 'value' in list(kwargs.keys()):
            dd = dcc.Dropdown(id=idName,options=ddOpt,clearable=False,**kwargs)
        else :
            if not defaultIdx:
                defaultIdx = 0
            if 'value' in list(kwargs.keys()):
                del kwargs['value']
            dd = dcc.Dropdown(id=idName,options=ddOpt,value=listdd[defaultIdx],clearable=False,**kwargs)
        return [p,dd]

    def dropDownFromDict(self,idName,listdd,pddPhrase = None,valIdx=None,**kwargs):
        if not pddPhrase :
            pddPhrase = 'Select your ... : ' + idName
        p = html.P(pddPhrase)
        if isinstance(listdd,dict):
            keysDict= list(listdd.keys())
            valDict = list(listdd.values())
            ddOpt =[{'label': k, 'value': v} for k,v in listdd.items()]

        if 'value' in list(kwargs.keys()):
            dd = dcc.Dropdown(id=idName,options=ddOpt,clearable=False,**kwargs)
        elif valIdx:
            valSel = [list(listdd.values())[k] for k in valIdx]
            print(valSel)
            dd = dcc.Dropdown(id=idName,options=ddOpt,value=valSel,clearable=False,**kwargs)
        else :
            print('here')
            dd = dcc.Dropdown(id=idName,options=ddOpt,clearable=False,**kwargs)
        return [p,dd]

    def quickInput(self,idName,typeIn='text',pddPhrase = 'input',dftVal=0,**kwargs):
        p = html.P(pddPhrase),
        inp = dcc.Input(id=idName,placeholder=pddPhrase,type=typeIn,value=dftVal,**kwargs)
        return [p,inp]

    def timeRangeSlider(self,id,t0=None,t1=None,**kwargs):
        if not t0 :
            t0 = parser.parse('00:00')
        if not t1 :
            t1 = t0+dt.timedelta(seconds=3600*24)
        maxSecs=int((t1-t0).total_seconds())
        rs = dcc.RangeSlider(id=id,
        min=0,max=maxSecs,
        # step=None,
        marks = self.utils.buildTimeMarks(t0,t1,**kwargs)[0],
        value=[0,maxSecs]
        )
        return rs

    def dDoubleRangeSliderLayout(self,baseId='',t0=None,t1=None,formatTime = '%d - %H:%M',styleDBRS='small'):
        if styleDBRS=='large':
            style2 = {'padding-bottom' : 50,'padding-top' : 50,'border': '13px solid green'}
        elif styleDBRS=='small':
            style2 = {'padding-bottom' : 10,'padding-top' : 10,'border': '3px solid green'}
        elif styleDBRS=='centered':
            style2 = {'text-align': 'center','border': '3px solid green','font-size':'18'}

        if not t0:
            t0 = parser.parse('00:00')
        if not t1:
            t1 = t0 + dt.timedelta(seconds=3600*24*2-1)
        p0      = html.H5('fixe time t0')
        in_t0   = dcc.Input(id=baseId + 'in_t0',type='text',value=t0.strftime(formatTime),size='75')
        in_t1   = dcc.Input(id=baseId + 'in_t1',type='text',value=t1.strftime(formatTime),size='75')
        p       = html.H5('select the time window :',style={'font-size' : 40})
        ine     = dcc.Input(id=baseId + 'ine',type='text',value=t0.strftime(formatTime))
        rs      = self.timeRangeSlider(id=baseId + 'rs',t0=t0,t1=t1,nbMarks=5)
        ins     = dcc.Input(id=baseId + 'ins',type='text',value=t1.strftime(formatTime))
        pf      = html.H5('timeselect start and end time ', id = 'pf',style={'font-size' : 60})
        dbrsLayout = html.Div([
                            dbc.Row([dbc.Col(p0),
                                    dbc.Col(in_t0),
                                    dbc.Col(in_t1)],style=style2,no_gutters=True),
                            dbc.Row(dbc.Col(p),style=style2,no_gutters=True),
                            dbc.Row([dbc.Col(ine),
                                    dbc.Col(rs,width=9),
                                    dbc.Col(ins)],
                                    style=style2,
                                    no_gutters=True),
                            ])
        return dbrsLayout

    def parseLayoutIds(self,obj,debug=False):
        c = True
        ids,queueList,k = [],[],0
        while c:
            if debug : k=k+1;print(k)
            if isinstance(obj,list):
                if debug : print('listfound')
                if len(obj)>1 : queueList.append(obj[1:])
                obj = obj[0]
            elif hasattr(obj,'id'):
                if debug : print('id prop found')
                ids.append(obj.id)
                obj='idfound'
            elif hasattr(obj,'children'):
                if debug : print('children found')
                obj=obj.children
            elif not queueList:
                if debug : print('queue list empty')
                c=False
            else :
                if debug : print('iterate over queue list')
                obj = queueList.pop()
        return ids

    def autoDictOptions(self,listWidgets):
        dictOpts = {}
        d1 = {k : 'value' for k in listWidgets if bool(re.search('(in_)|(dd_)', k))}
        d2 = {k : 'n_clicks' for k in listWidgets if bool(re.search('btn_', k))}
        d3 = {k : 'figure' for k in listWidgets if bool(re.search('graph', k))}
        d4 = {k : 'children' for k in listWidgets if bool(re.search('fileInCache', k))}
        for d in [d1,d2,d3,d4] :
            if not not d : dictOpts.update(d)
        return dictOpts

    def build_dbcBasicBlock(self,widgets,rows,cols):
        dbc_rows,k = [],0
        for r in range(rows):
            curRow=[]
            for c in range(cols) :
                # print(k,'******',widgets[k])
                curRow.append(dbc.Col(widgets[k]))
                k+=1
            dbc_rows.append(curRow)
        return html.Div([dbc.Row(r) for r in dbc_rows])

    def basicComponents(self,dicWidgets,baseId):
        widgetLayout,dicLayouts = [],{}
        for wid_key,wid_val in dicWidgets.items():
            if 'dd_cmap' in wid_key:
                widgetObj = self.dropDownFromList(baseId+wid_key,self.utils.cmapNames[0],
                                                'select the colormap : ',value=wid_val)

            elif 'dd_resampleMethod' in wid_key:
                widgetObj = self.dropDownFromList(baseId+wid_key,['mean','max','min','median'],
                'Select the resampling method: ',value=wid_val,multi=False)

            elif 'dd_style' in wid_key:
                widgetObj = self.dropDownFromList(baseId+wid_key,self.graphStyles,'Select the style : ',value = wid_val)

            elif 'dd_typeGraph' in wid_key:
                widgetObj = self.dropDownFromList(baseId+wid_key,self.graphTypes,
                            'Select type graph : ',value=wid_val,
                            style=self.stdStyle,optionHeight=20)

            elif 'btn_export' in wid_key:
                widgetObj = [html.Button('export .txt',id=baseId+wid_key, n_clicks=wid_val)]

            elif 'btn_update' in wid_key:
                widgetObj = [html.Button('update',id=baseId+wid_key, n_clicks=wid_val)]

            elif 'check_button' in wid_key:
                widgetObj = [dcc.Checklist(id=baseId+wid_key,options=[{'label': wid_val, 'value': wid_val}])]

            elif 'in_timeRes' in wid_key:
                widgetObj = [html.P('time resolution : '),
                dcc.Input(id=baseId+wid_key,placeholder='time resolution : ',type='text',value=wid_val)]

            elif 'in_heightGraph' in wid_key:
                widgetObj = [html.P('heigth of graph: '),
                dcc.Input(id=baseId+wid_key,type='number',value=wid_val,max=3000,min=400,step=5,style=self.stdStyle)]
                widgetObj = [self.build_dbcBasicBlock(widgetObj,2,1)]

            elif 'in_axisSp' in wid_key :
                widgetObj = [html.P('space between axis: '),
                dcc.Input(id=baseId+wid_key,type='number',value=wid_val,max=1,min=0,step=0.01,style=self.stdStyle)]
                widgetObj = [self.build_dbcBasicBlock(widgetObj,2,1)]

            elif 'in_hspace' in wid_key :
                widgetObj = [html.P('horizontal space: '),
                dcc.Input(id=baseId+wid_key,type='number',value=wid_val,max=1,min=0,step=0.01,style=self.stdStyle)]
                widgetObj = [self.build_dbcBasicBlock(widgetObj,2,1)]

            elif 'in_vspace' in wid_key :
                widgetObj = [html.P('vertical space: '),
                dcc.Input(id=baseId+wid_key,type='number',value=wid_val,max=1,min=0,step=0.01,style=self.stdStyle)]
                widgetObj = [self.build_dbcBasicBlock(widgetObj,2,1)]

            elif 'interval' in wid_key:
                widgetObj = [dcc.Interval(id=baseId + wid_key,interval=wid_val*1000,n_intervals=0)]

            elif 'pdr_time' in wid_key :
                if not wid_val :
                    wid_val['tmax']=dt.datetime.now()
                    wid_val['tmin']=wid_val['tmax']-dt.timedelta(days=2*30)
                else :
                    tmax = self.utils.findDateInFilename(wid_val['tmax'])-dt.timedelta(days=1)
                    tmin = self.utils.findDateInFilename(wid_val['tmin'])
                t1= tmax
                t0 = t1 - dt.timedelta(days=2)
                widgetObj = [
                html.Div([
                    dbc.Row([dbc.Col(html.P('select start and end time : ')),
                        dbc.Col(html.Button(id  = baseId + wid_key + 'Btn',children='update Time'))]),

                    dbc.Row([dbc.Col(dcc.DatePickerRange( id = baseId + wid_key + 'Pdr',
                                max_date_allowed = tmax, initial_visible_month = t0.date(),
                                display_format = 'MMM D, YY',minimum_nights=0,
                                start_date = t0.date(), end_date   = t1.date()))]),

                    dbc.Row([dbc.Col(dcc.Input(id = baseId + wid_key + 'Start',type='text',value = '07:00',size='13',style={'font-size' : 13})),
                            dbc.Col(dcc.Input(id = baseId + wid_key + 'End',type='text',value = '21:00',size='13',style={'font-size' : 13}))])
                ])]

            elif 'block_multiAxisSettings' in wid_key:
                blockSettings = self.basicComponents({
                                            'in_heightGraph':900,
                                            'in_axisSp':0.02,
                                            'in_hspace':0.05,
                                            'in_vspace':0.05,
                                            },baseId)
                widgetObj = [self.build_dbcBasicBlock(blockSettings,2,2)]


            else :
                print('component ',wid_key,' is not available')
                return

            for widObj in widgetObj:widgetLayout.append(widObj)
        return widgetLayout

    def buildGraphLayout(self,widgetLayout,baseId,widthG=85):
        graphLayout=[html.Div([dcc.Graph(id=baseId+'graph',style={"width": str(widthG)+"%", "display": "inline-block"})])]
        return [html.Div(widgetLayout,style={"width": str(100-widthG) + "%", "float": "left"})]+graphLayout

    def createTabs(self,tabs):
        return [dbc.Tabs([dbc.Tab(t.tabLayout,label=t.tabname) for t in tabs])]
