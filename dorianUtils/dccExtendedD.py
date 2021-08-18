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
        self.smallStyle = {'fontsize':'12 px','width':'120px','height': '40px','min-height': '1px',}
        self.verysmallStyle = {'fontsize':'12 px','width':'60px','height': '40px','min-height': '1px',}
        self.blockStyle1 = {"border":"4px green double"}
        self.blockStyle2 = {"border":"3px red solid"}
        self.blockStyle3 = {"border":"3px blue groove"}

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
            # print(valSel)
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

    def build_dbcBasicBlock(self,widgets,rows,cols,ws=None):
        dbc_rows,k = [],0
        if not ws : ws = [12/cols]*cols
        for r in range(rows):
            curRow=[]
            for c,w in zip(range(cols),ws) :
                # print(k,'******',widgets[k])
                curRow.append(dbc.Col(widgets[k],width=w))
                k+=1
            dbc_rows.append(curRow)
        return html.Div([dbc.Row(r) for r in dbc_rows])

    def buildModalLog(self,titleBtn,mdFile):
        f = open(mdFile)
        t = dcc.Markdown(f.readlines())
        f.close()
        logModal = html.Div([
                dbc.Button(titleBtn, id="btn_log", n_clicks=0),
                dbc.Modal([
                    dbc.ModalHeader("Log versionning"),
                    dbc.ModalBody(t),
                    dbc.ModalFooter(dbc.Button("Close", id="close", className="ml-auto", n_clicks=0)),
                    ],
                    id="log_modal",
                    is_open=False,
                    size='xl',
                ),
            ]
        )
        return logModal

    def basicComponents(self,dicWidgets,baseId):
        widgetLayout,dicLayouts = [],{}
        for wid_key,wid_val in dicWidgets.items():
            if 'dd_cmap' in wid_key:
                widgetObj = self.dropDownFromList(baseId+wid_key,self.utils.cmapNames[0],
                                                'colormap : ',value=wid_val)


            elif 'dd_resampleMethod' in wid_key:
                widgetObj = self.dropDownFromList(baseId+wid_key,['mean','max','min','median'],
                'resampling method: ',value=wid_val,multi=False)

            elif 'dd_style' in wid_key:
                widgetObj = self.dropDownFromList(baseId+wid_key,self.graphStyles,'style : ',value = wid_val)

            elif 'dd_typeGraph' in wid_key:
                widgetObj = self.dropDownFromList(baseId+wid_key,self.graphTypes,
                            'type graph : ',value=wid_val,
                            style=self.stdStyle,optionHeight=20)

            elif 'btn_export' in wid_key:
                widgetObj = [html.Button('export .csv',id=baseId+wid_key, n_clicks=wid_val),
                            dcc.Download(id=baseId + "dl")]

            elif 'btn_update' in wid_key:
                widgetObj = [html.Button('update',id=baseId+wid_key, n_clicks=wid_val)]

            elif 'check_button' in wid_key:
                widgetObj = [dcc.Checklist(id=baseId+wid_key,options=[{'label': wid_val, 'value': wid_val}])]

            elif 'in_timeRes' in wid_key:
                widgetObj = [html.P('time resolution : '),
                dcc.Input(id=baseId+wid_key,placeholder='time resolution : ',type='text',value=wid_val)]
                widgetObj = [self.build_dbcBasicBlock(widgetObj,2,1)]

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

            elif wid_key == 'interval' :
                widgetObj = [dcc.Interval(id=baseId + wid_key,interval=wid_val*1000,n_intervals=0)]

            elif 'pdr_time' in wid_key :
                if not wid_val :
                    wid_val={}
                    tmax = dt.datetime.now()
                    tmin = tmax-dt.timedelta(days=2*30)
                else :
                    tmax = self.utils.findDateInFilename(wid_val['tmax'])-dt.timedelta(seconds=1)
                    tmin = self.utils.findDateInFilename(wid_val['tmin'])
                t1 = tmax
                t0 = t1 - dt.timedelta(days=1)
                timeFormat='%Y-%m-%d'
                widgetObj = [
                html.Div([
                    dbc.Row([dbc.Col(html.P('select start and end time : ')),
                        dbc.Col(html.Button(id  = baseId + wid_key + 'Btn',children='update'))]),

                    dbc.Row([dbc.Col(dcc.DatePickerRange(id = baseId + wid_key + 'Pdr',
                                max_date_allowed = t1,
                                initial_visible_month = t0,
                                display_format = 'D-MMM-YY',minimum_nights=0,persistence=False,
                                start_date = t0, end_date = t1))]),

                    dbc.Row([dbc.Col(dcc.Input(id = baseId + wid_key + 'Start',type='text',value = '07:00',size='13',style={'font-size' : 13})),
                            dbc.Col(dcc.Input(id = baseId + wid_key + 'End',type='text',value = '21:00',size='13',style={'font-size' : 13}))])
                ])]

            elif 'block_refresh' in wid_key:
                interval = dcc.Interval(id=baseId + 'interval',interval=wid_val['val_refresh']*1000,n_intervals=0)

                timeWindow=[html.P('time window (in min): ',style=self.smallStyle),
                        dcc.Input(id=baseId+'in_timeWindow',placeholder='refresh Time in seconds: ',type='number',
                            max=24*60,min=wid_val['min_window'],step=1,value=wid_val['val_window'],style=self.smallStyle)]
                timeWindow = [self.build_dbcBasicBlock(timeWindow,1,2,ws=[6,6])]

                refreshTime = [html.P('refresh time (in s): ',style=self.smallStyle),
                        dcc.Input(id=baseId+'in_refreshTime',placeholder='refresh Time in seconds: ',type='number',
                            max=1500,min=wid_val['min_refresh'],step=1,value=wid_val['val_refresh'],style=self.smallStyle)]
                refreshTime = [self.build_dbcBasicBlock(refreshTime,1,2,ws=[6,6])]
                timeBlock = html.Div([
                                    html.H5(''),
                                    self.build_dbcBasicBlock([refreshTime,timeWindow],2,1)],
                                                style=self.blockStyle1)
                widgetObj = [interval,timeBlock]

            elif wid_key=='block_graphSettings':
                blockSettings = self.basicComponents({
                                            'dd_cmap':wid_val['colmap'],
                                            'dd_style':wid_val['style'],
                                            'dd_typeGraph':wid_val['type'],
                                            },baseId)
                widgetObj = [html.Div([self.build_dbcBasicBlock(blockSettings,3,2)],style=self.blockStyle2)]

            elif wid_key=='block_resample':
                timeRes = [html.P('time resolution: ',style=self.smallStyle),
                dcc.Input(id=baseId+'in_timeRes',placeholder='time resolution : ',type='text',value=wid_val['val_res'],style=self.smallStyle)]
                timeRes = [self.build_dbcBasicBlock(timeRes,1,2)]

                listdd=['mean','max','min','median']
                resampleMethod = [
                                html.P('resampling method: ',style=self.smallStyle),
                                dcc.Dropdown(id=baseId+'dd_resampleMethod',options=[{'value':t,'label':t} for t in listdd],
                                                value=wid_val['val_method'],clearable=False,style=self.smallStyle)]
                resampleMethod = [self.build_dbcBasicBlock(resampleMethod,1,2)]
                widgetObj = [html.Div(self.build_dbcBasicBlock([timeRes,resampleMethod],2,1),style=self.blockStyle3)]

            elif wid_key=='block_multiAxisSettings':
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
