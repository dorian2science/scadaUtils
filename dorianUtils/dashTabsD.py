import datetime as dt, pickle, time
import os,re,sys
import pandas as pd,numpy as np
import dash, dash_core_components as dcc, dash_html_components as html, dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import plotly.express as px, plotly.graph_objects as go
from dorianUtils.dccExtendedD import DccExtended
from dorianUtils.utilsD import Utils

class TabMaster():
    '''
    - cfg: ConfigFiles object
    - loadData,plotgraph and updateLayoutGraph are functions
    '''

    def __init__(self,app,cfg,loadData,plotData,update_lineshapes,tabname,baseId='tab_'):
        self.utils = Utils()
        self.dccE = DccExtended()
        self.initialDateMethod = 'parkedData'
        self.app = app
        self.cfg = cfg
        self.loadData  = loadData
        self.plotData = plotData
        self.update_lineshapes=update_lineshapes
        self.tabname = tabname
        self.baseId = baseId
        self.modalError = self.dccE.addModalError(app,cfg,baseid=self.baseId)

    def _define_basicCallbacks(self,categories=[]):
        #update freeze button
        if 'ts_freeze' in categories:
            @self.app.callback(
                Output(self.baseId + 'ts_freeze', 'label'),
                Output(self.baseId + 'st_freeze', 'data'),
                Output(self.baseId + 'interval', 'disabled'),
                Input(self.baseId + 'ts_freeze','value'),
                Input(self.baseId + 'btn_freeze+','n_clicks'),
                Input(self.baseId + 'btn_freeze-','n_clicks'),
                State(self.baseId + 'in_addtime','value'),
                State(self.baseId + 'st_freeze','data'),
                State(self.baseId + 'graph','figure'),
                prevent_initial_call=True)
            def updateTimeRangeFrozen(valueFreeze,tp,tm,tadd,timeRange,fig):
                if valueFreeze:
                    mode_ts='mode : freeze'
                    freeze=True
                    ctx = dash.callback_context
                    trigId = ctx.triggered[0]['prop_id'].split('.')[0]
                    if trigId==self.baseId + 'ts_freeze':
                        fig = go.Figure(fig)
                        timeRange = [min([min(k['x']) for k in fig.data]),max([max(k['x']) for k in fig.data])]
                    elif trigId==self.baseId + 'btn_freeze+':
                        timeRange[1] = (pd.to_datetime(timeRange[1]) + dt.timedelta(seconds=tadd)).isoformat()
                    elif trigId==self.baseId + 'btn_freeze-':
                        timeRange[0] = (pd.to_datetime(timeRange[0]) - dt.timedelta(seconds=tadd)).isoformat()
                else:
                    mode_ts='mode : refresh'
                    freeze = False

                return mode_ts, timeRange, freeze

        #update freeze button
        if 'refreshWindow' in categories:
            @self.app.callback(Output(self.baseId + 'interval', 'interval'),
                                Input(self.baseId + 'in_refreshTime','value'))
            def updateRefreshTime(refreshTime):
                return refreshTime*1000

        #update legend toogle button
        if 'legendtoogle' in categories:
            @self.app.callback(Output(self.baseId + 'btn_legend', 'children'),
                                Input(self.baseId + 'btn_legend','n_clicks'))
            def updateLgdBtn(legendType):
                    if legendType%3==0 :
                        buttonMessage = 'tag'
                    elif legendType%3==1 :
                        buttonMessage = 'description'
                    elif legendType%3==2:
                        buttonMessage = 'unvisible'
                    return buttonMessage

        # call the export button
        if 'export' in categories:
            @self.app.callback(
                    Output(self.baseId + 'dl','data'),
                    Input(self.baseId + 'btn_export', 'n_clicks'),
                    State(self.baseId + 'graph','figure'),
                    prevent_initial_call=True
                    )
            def exportonclick(btn,fig):
                df,filename =  self.utils.exportDataOnClick(fig)
                return dcc.send_data_frame(df.to_csv, filename+'.csv')

        if 'datePickerRange' in categories:
            # initial visible month tuned to selection
            @self.app.callback(
            Output(self.baseId + 'pdr_timePdr','initial_visible_month'),
            Input(self.baseId + 'pdr_timePdr','start_date'),
            Input(self.baseId + 'pdr_timePdr','end_date'),
            )
            def updateInitialVisibleMonth(startdate,enddate):
                ctx = dash.callback_context
                trigId = ctx.triggered[0]['prop_id']
                if 'start_date' in trigId:
                    return startdate
                else :
                    return enddate

            # update inital datetime regularly
            @self.app.callback(
            Output(self.baseId + 'pdr_timePdr','start_date'),
            Output(self.baseId + 'pdr_timeStart','value'),
            Output(self.baseId + 'pdr_timePdr','end_date'),
            Output(self.baseId + 'pdr_timeEnd','value'),
            Input(self.baseId + 'pdr_timeInterval','n_intervals'),
            )
            def updateInitialDateTime(n):
                if self.initialDateMethod == 'time':
                    now = dt.datetime.now().astimezone()
                    t0 = now- dt.timedelta(hours=8)
                    return t0.strftime('%Y-%m-%d'),t0.strftime('%H:%M'),now.strftime('%Y-%m-%d'),now.strftime('%H:%M')
                if self.initialDateMethod == 'parkedData':
                    # dangerous => better use localtimezone
                    listDates = [pd.Timestamp(k,tz='CET') for k in self.cfg.parkedDays]
                    lastDate = max(listDates)
                    t0=t1=lastDate
                    # if hours/minute parked take the last 8 hours:
                    # folderLastDay = self.cfg.folderPkl+'parkedData/'+lastDate.strftime('%Y-%m-%d')+'/*'
                    # listHours=glob.glob(folderLastDay)
                    # lastHour = max([float(k) for k in listHours])
                    # t1 = lastDate+dt.timedelta(hours=lastHour)
                    # t0 = t1-dt.timedelta(hours=8)
                    # return t0,t0.strftime('%H:%M'),t1,t1.strftime('%H:%M')
                    return t0.strftime('%Y-%m-%d'),t0.strftime('9:00'),t1.strftime('%Y-%m-%d'),t1.strftime('18:00')
                    # return t0,t0.strftime('9:00'),t1,t1.strftime('18:00')

        if 'modalTagsTxt' in categories:
            @self.app.callback(
                Output(self.baseId + "modalListTags", "is_open"),
                [Input(self.baseId + "btn_omlt", "n_clicks"), Input(self.baseId + "close_omlt", "n_clicks")],
                [State(self.baseId + "modalListTags", "is_open")],
            )
            def popupModalListTags(n1,n2, is_open):
                if n1:
                    return not is_open
                return is_open

            @self.app.callback(
                Output(self.baseId + "dd_tag", "value"),
                [Input(self.baseId + "close_omlt", "n_clicks")],
                [State(self.baseId + "txtListTags", "value")],
                prevent_initial_call=True
            )
            def getListTagsModal(close,txt):
                listTags = [k.strip().upper() for k in txt.split('\n')]
                return listTags

    def _buildLayout(self,specialWidDic,realTime=False,widthG=85,*args):
        if not realTime:
            dicWidgets = {
                'pdr_time' : {'tmin':self.cfg.listFilesPkl[0],'tmax':self.cfg.listFilesPkl[-1]},
                'in_timeRes':'60s','dd_resampleMethod' : 'mean',
                'dd_style':'default',
                'btn_export':0,
                    }
        else :
            dicWidgets = {
                'block_refresh':{'val_window':30,'val_refresh':50,
                                    'min_refresh':1,'min_window':2},
                'btns_refresh':None,
                'block_resample':{'val_res':'60s','val_method' : 'mean'},
                'dd_style':'default',
                'btn_export':0,
                }

        basicWidgets = self.dccE.basicComponents(dicWidgets,self.baseId)

        config={
                'displaylogo': False,
                'modeBarButtonsToAdd':[
                    'drawline',
                    'drawopenpath',
                    'drawclosedpath',
                    'drawcircle',
                    'drawrect',
                    'eraseshape'
                ]
            }

        specialWidgets = self.addWidgets(specialWidDic)
        # add graph object
        fig = self.utils.addLogo(go.Figure())
        graphObj = dcc.Graph(id=self.baseId + 'graph',config = config,figure=fig)

        widgetLayout = html.Div(basicWidgets+specialWidgets,style={"width": str(100-widthG) + "%", "float": "left"})
        graphLayout = html.Div(graphObj, style={"width": str(widthG)+"%", "display": "inline-block"})
        self.tabLayout = [widgetLayout,graphLayout]

    def updateGraph(self,previousFig,listTrigs,style,argsLoad,argsPlot):
        ctx = dash.callback_context
        trigId = ctx.triggered[0]['prop_id'].split('.')[0]
        fig = go.Figure(previousFig)
        ## load data in that case
        if trigId in [self.baseId+k for k in listTrigs]:
            df_tuple = self.loadData(*argsLoad)
            if not isinstance(df_tuple,tuple):
                df_tuple = df_tuple,
            if isinstance(df_tuple[0],pd.DataFrame) and df_tuple[0].empty:
                ## get error code loading data ==> 1
                return go.Figure(),1
            else :
                fig = self.plotData(*df_tuple,*argsPlot)
        ## update style of graph
        if not not self.update_lineshapes:
            fig = self.cfg.updateLayoutStandard(fig)
            fig = self.update_lineshapes(fig,style)
        # keep traces visibility
        try :
            fig = self.utils.legendPersistant(previousFig,fig)
        except:
            print('problem to make traces visibility persistant.')
        return self.utils.addLogo(fig),0

    def addWidgets(self,dicWidgets):
        widgetLayout,dicLayouts = [],{}
        for wid_key,wid_val in dicWidgets.items():
            if 'dd_cmap'==wid_key:
                widgetObj = self.dccE.dropDownFromList(
                    self.baseId + wid_key, self.utils.cmapNames[0], 'colormap : ',value=wid_val)

            elif 'dd_listFiles' in wid_key:
                widgetObj = self.dccE.dropDownFromList(self.baseId+wid_key,self.cfg.listFilesPkl,
                    'Select your File : ',labelsPattern='\d{4}-\d{2}-\d{2}-\d{2}',defaultIdx=wid_val)


            elif 'dd_tag' in wid_key:
                widgetObj = self.dccE.dropDownFromList(self.baseId+wid_key,self.cfg.getTagsTU(''),
                    'Select the tags : ',value=wid_val,multi=True,optionHeight=20)

            elif 'dd_Units' in wid_key :
                widgetObj = self.dccE.dropDownFromList(self.baseId+wid_key,self.cfg.listUnits,'Select units graph : ',value=wid_val)

            elif 'dd_typeTags' in wid_key:
                widgetObj = self.dccE.dropDownFromList(self.baseId+wid_key,list(self.cfg.usefulTags.index),
                            'Select categorie : ',value=wid_val,optionHeight=20)

            elif 'btn_legend' in wid_key:
                widgetObj = [html.Button('tag',id=self.baseId+wid_key, n_clicks=wid_val)]

            elif 'in_patternTag' in wid_key  :
                widgetObj = [html.P('pattern with regexp on tag : '),
                dcc.Input(id=self.baseId+wid_key,type='text',value=wid_val)]

            elif 'in_step' in wid_key:
                widgetObj = [html.P('skip points : '),
                dcc.Input(id=self.baseId+wid_key,placeholder='skip points : ',type='number',
                            min=1,step=1,value=wid_val)]

            elif 'in_axisSp' in wid_key:
                widgetObj = [
                    html.P('select the space between axis : '),
                    dcc.Input(id=self.baseId+wid_key,type='number',value=wid_val,max=1,min=0,step=0.01)]

            elif wid_key == 'modalListTags':
                widgetObj = [
                    dbc.Button("enter your list of tags!", id=self.baseId + "btn_omlt", n_clicks=0),
                    dbc.Modal([
                            dbc.ModalHeader("list of tags to load"),
                            dbc.ModalBody([
                                html.P('please enter your list of tags. Tags are written as rows ==> a line for each tag:'),
                                dcc.Textarea(id=self.baseId + 'txtListTags',value='',
                                                style={
                                    'width':'50em',
                                    'min-height': '50vh'
                                    }),
                            ]),
                            dbc.ModalFooter(dbc.Button("Apply changes", id=self.baseId + "close_omlt", className="ml-auto", n_clicks=0)),
                        ],
                        id=self.baseId + "modalListTags",
                        is_open=False,
                        size='xl',
                    )
                ]
            else:
                print('component :' + wid_key +' not found')
                sys.exit()

            for widObj in widgetObj:widgetLayout.append(widObj)

        return widgetLayout

    def updateLegendBtnState(self,legendType):
        if legendType%3==0 :
            buttonMessage = 'tag'
        elif legendType%3==1 :
            buttonMessage = 'description'
        elif legendType%3==2:
            buttonMessage = 'unvisible'
        return buttonMessage

    def updateLegend(self,fig,lgd):
        fig.update_layout(showlegend=True)
        oldNames = [k['name'] for k in fig['data']]
        if lgd=='description': # get description name
            newNames = [self.cfg.getDescriptionFromTagname(k) for k in oldNames]
            dictNames   = dict(zip(oldNames,newNames))
            fig         = self.utils.customLegend(fig,dictNames)

        elif lgd=='unvisible': fig.update_layout(showlegend=False)

        elif lgd=='tag': # get tags
            if not oldNames[0] in list(self.cfg.dfPLC.index):# for initialization mainly
                newNames = [self.cfg.getTagnamefromDescription(k) for k in oldNames]
                dictNames   = dict(zip(oldNames,newNames))
                fig         = self.utils.customLegend(fig,dictNames)
        return fig

class TabSelectedTags(TabMaster):
    def __init__(self,*args,defaultCat=[],baseId='ts0_',**kwargs):
        TabMaster.__init__(self,*args,**kwargs,tabname='pre-selected tags',baseId=baseId)
        dicSpecialWidgets = {'dd_typeTags':defaultCat,'dd_cmap':'jet','btn_legend':0}
        self._buildLayout(dicSpecialWidgets)
        self._define_callbacks()

    def _define_callbacks(self):
        self._define_basicCallbacks(['legendtoogle','export','datePickerRange'])
        @self.app.callback(
            Output(self.baseId + 'graph', 'figure'),
            Output(self.baseId + 'error_modal_store', 'data'),
            Input(self.baseId + 'dd_typeTags','value'),
            Input(self.baseId + 'pdr_timeBtn','n_clicks'),
            Input(self.baseId + 'dd_resampleMethod','value'),
            Input(self.baseId + 'btn_legend','children'),
            Input(self.baseId + 'dd_style','value'),
            Input(self.baseId + 'dd_cmap','value'),
            State(self.baseId + 'graph','figure'),
            State(self.baseId + 'in_timeRes','value'),
            State(self.baseId + 'pdr_timePdr','start_date'),
            State(self.baseId + 'pdr_timePdr','end_date'),
            State(self.baseId + 'pdr_timeStart','value'),
            State(self.baseId + 'pdr_timeEnd','value'),
            )
        def updatePSTGraph(tagCat,timeBtn,rsMethod,lgd,style,colmap,previousFig,rs,date0,date1,t0,t1):
            tags = self.cfg.getUsefulTags(tagCat)
            triggerList=['dd_tag','pdr_timeBtn','dd_resampleMethod']
            timeRange = [date0+' '+t0,date1+' '+t1]
            if len(tags)==0:
                return previousFig,2

            fig,errCode = self.updateGraph(previousFig,triggerList,style,
                [timeRange,tags,rs,rsMethod],[]
                )
            fig = self.utils.updateColorMap(fig,colmap)
            # fig = self.updateLegend(fig,lgd)
            return fig,errCode

class TabMultiUnits(TabMaster):
    def __init__(self,*args,defaultTags=[],baseId='tmu0_',**kwargs):
        TabMaster.__init__(self,*args,**kwargs,tabname='multi Units',baseId=baseId)
        dicSpecialWidgets = {'dd_tag':defaultTags,'modalListTags':None,'btn_legend':0,'in_axisSp':0.05}
        self._buildLayout(dicSpecialWidgets)
        self._define_callbacks()

    def _define_callbacks(self):
        self._define_basicCallbacks(['legendtoogle','export','datePickerRange','modalTagsTxt'])
        @self.app.callback(
            Output(self.baseId + 'graph', 'figure'),
            Output(self.baseId + 'error_modal_store', 'data'),
            Input(self.baseId + 'dd_tag','value'),
            Input(self.baseId + 'pdr_timeBtn','n_clicks'),
            Input(self.baseId + 'dd_resampleMethod','value'),
            Input(self.baseId + 'btn_legend','children'),
            Input(self.baseId + 'dd_style','value'),
            Input(self.baseId + 'in_axisSp','value'),
            State(self.baseId + 'graph','figure'),
            State(self.baseId + 'in_timeRes','value'),
            State(self.baseId + 'pdr_timePdr','start_date'),
            State(self.baseId + 'pdr_timePdr','end_date'),
            State(self.baseId + 'pdr_timeStart','value'),
            State(self.baseId + 'pdr_timeEnd','value'),
            )
        def updateMUGGraph(tags,timeBtn,rsMethod,lgd,style,axSP,previousFig,rs,date0,date1,t0,t1):
            triggerList=['dd_tag','pdr_timeBtn','dd_resampleMethod']
            timeRange = [date0 + ' ' + t0, date1 + ' ' + t1]
            fig,errCode = self.updateGraph(previousFig,triggerList,style,
                [timeRange,tags,rs,rsMethod],[]
                # axSP=axSP
                )
            # fig = self.updateLegend(fig,lgd)
            return fig,errCode

class TabUnitSelector(TabMaster):
    def __init__(self,*args,unitInit='mbarg',patTagInit='GFC',baseId='tu0_',**kwargs):
        TabMaster.__init__(self,*args,**kwargs,tabname='select Units',baseId=baseId)
        dicSpecialWidgets = {'dd_Units':unitInit,'in_patternTag':patTagInit,'dd_cmap':'jet','btn_legend':0}
        self._buildLayout(dicSpecialWidgets)
        self._define_callbacks()

    def _define_callbacks(self):
        self._define_basicCallbacks(['legendtoogle','export','datePickerRange'])
        @self.app.callback(
            Output(self.baseId + 'graph', 'figure'),
            Output(self.baseId + 'error_modal_store', 'data'),
            Input(self.baseId + 'dd_Units','value'),
            Input(self.baseId + 'in_patternTag','value'),
            Input(self.baseId + 'pdr_timeBtn','n_clicks'),
            Input(self.baseId + 'dd_resampleMethod','value'),
            Input(self.baseId + 'btn_legend','children'),
            Input(self.baseId + 'dd_style','value'),
            Input(self.baseId + 'dd_cmap','value'),
            State(self.baseId + 'graph','figure'),
            State(self.baseId + 'in_timeRes','value'),
            State(self.baseId + 'pdr_timePdr','start_date'),
            State(self.baseId + 'pdr_timePdr','end_date'),
            State(self.baseId + 'pdr_timeStart','value'),
            State(self.baseId + 'pdr_timeEnd','value'),
            )
        def updateMUGGraph(unit,patTag,timeBtn,rsMethod,lgd,style,colmap,previousFig,rs,date0,date1,t0,t1):
            triggerList=['dd_tag','pdr_timeBtn','dd_resampleMethod']
            tags  = self.cfg.getTagsTU(patTag,unit)
            timeRange = [date0+' '+t0,date1+' '+t1]
            fig,errCode = self.updateGraph(previousFig,triggerList,style,
                [timeRange,tags,rs,rsMethod],[]
                )
            fig = self.utils.updateColorMap(fig,colmap)
            # fig = self.updateLegend(fig,lgd)
            return fig,errCode

class TabMultiUnitSelectedTags(TabMaster):
    def __init__(self,*args,defaultCat,defaultTags=[],baseId='tmus0_',**kwargs):
        TabMaster.__init__(self,*args,**kwargs,tabname='multi-units +',baseId=baseId)
        dicSpecialWidgets = {
            'dd_typeTags':defaultCat,
            'dd_tag':defaultTags,
            'btn_legend':0,'in_axisSp':0.05}
        self._buildLayout(dicSpecialWidgets)
        self._define_callbacks()

    def _define_callbacks(self):
        self._define_basicCallbacks(['legendtoogle','export','datePickerRange'])
        @self.app.callback(
            Output(self.baseId + 'graph', 'figure'),
            Output(self.baseId + 'error_modal_store', 'data'),
            Input(self.baseId + 'dd_tag','value'),
            Input(self.baseId + 'dd_typeTags','value'),
            Input(self.baseId + 'pdr_timeBtn','n_clicks'),
            Input(self.baseId + 'dd_resampleMethod','value'),
            Input(self.baseId + 'btn_legend','children'),
            Input(self.baseId + 'dd_style','value'),
            Input(self.baseId + 'in_axisSp','value'),
            State(self.baseId + 'graph','figure'),
            State(self.baseId + 'in_timeRes','value'),
            State(self.baseId + 'pdr_timePdr','start_date'),
            State(self.baseId + 'pdr_timePdr','end_date'),
            State(self.baseId + 'pdr_timeStart','value'),
            State(self.baseId + 'pdr_timeEnd','value'),
            )
        def updateMUGSGraph(tags,tagCat,timeBtn,rsMethod,lgd,style,axSP,previousFig,rs,date0,date1,t0,t1):
            tags = self.cfg.getUsefulTags(tagCat) + tags
            if len(tags)==0:
                return previousFig,2

            triggerList=['dd_tag','pdr_timeBtn','dd_resampleMethod']
            timeRange = [date0+' '+t0,date1+' '+t1]
            fig,errCode = self.updateGraph(previousFig,triggerList,style,
                [timeRange,tags,rs,rsMethod],[]
                # axSP=axSP
                )
            # fig = self.updateLegend(fig,lgd)
            return fig,errCode

# ==============================================================================
#                              REAL TIME
# ==============================================================================
class RealTimeTabSelectedTags(TabMaster):
    def __init__(self,*args,defaultCat=[],baseId='ts0_',**kwargs):
        TabMaster.__init__(self,*args,**kwargs,tabname='pre-selected tags',baseId=baseId)
        dicSpecialWidgets = {'dd_typeTags':defaultCat,'dd_cmap':'jet','btn_legend':0}
        self._buildLayout(dicSpecialWidgets,realTime=True)
        self._define_callbacks()

    def _define_callbacks(self):
        self._define_basicCallbacks(['legendtoogle','export','ts_freeze','refreshWindow'])
        @self.app.callback(
            Output(self.baseId + 'graph', 'figure'),
            Output(self.baseId + 'error_modal_store', 'data'),
            Input(self.baseId + 'dd_typeTags','value'),
            Input(self.baseId + 'dd_resampleMethod','value'),
            Input(self.baseId + 'btn_legend','children'),
            Input(self.baseId + 'dd_style','value'),
            Input(self.baseId + 'dd_cmap','value'),
            Input(self.baseId + 'interval','n_intervals'),
            Input(self.baseId + 'btn_update','n_clicks'),
            Input(self.baseId + 'st_freeze','data'),
            State(self.baseId + 'graph','figure'),
            State(self.baseId + 'in_timeWindow','value'),
            State(self.baseId + 'in_timeRes','value'),
            State(self.baseId + 'ts_freeze','value'),
            )
        def updatePSTGraph(tagCat,rsMethod,lgd,style,colmap,n,updateBtn,timeRange,previousFig,tw,rs,freezeMode):
            tags = self.cfg.getUsefulTags(tagCat)
            triggerList = ['interval','btn_update','st_freeze','dd_typeTags','dd_resampleMethod']
            if len(tags)==0:
                return previousFig,2

            if freezeMode:
                fig,errCode = self.updateGraph(previousFig,triggerList,style,[tags,tw*60,rs,rsMethod,True,timeRange],[])
            else:
                fig,errCode = self.updateGraph(previousFig,triggerList,style,[tags,tw*60,rs,rsMethod,True],[])

            fig = self.utils.updateColorMap(fig,colmap)
            # fig = self.updateLegend(fig,lgd)
            return fig,errCode

class RealTimeTagMultiUnit(TabMaster):
    def __init__(self,*args,defaultTags=[],baseId='tmu0_',**kwargs):
        TabMaster.__init__(self,*args,**kwargs,tabname='multi unit',baseId=baseId)
        dicSpecialWidgets = {'dd_tag':defaultTags,'modalListTags':None,'btn_legend':0}
        self._buildLayout(dicSpecialWidgets,realTime=True)
        self._define_callbacks()

    def _define_callbacks(self):
        self._define_basicCallbacks(['legendtoogle','export','modalTagsTxt','refreshWindow','ts_freeze'])
        @self.app.callback(
            Output(self.baseId + 'graph', 'figure'),
            Output(self.baseId + 'error_modal_store', 'data'),
            Input(self.baseId + 'interval','n_intervals'),
            Input(self.baseId + 'dd_tag','value'),
            Input(self.baseId + 'btn_update','n_clicks'),
            Input(self.baseId + 'st_freeze','data'),
            Input(self.baseId + 'dd_resampleMethod','value'),
            Input(self.baseId + 'btn_legend','children'),
            Input(self.baseId + 'dd_style','value'),
            State(self.baseId + 'graph','figure'),
            State(self.baseId + 'in_timeWindow','value'),
            State(self.baseId + 'in_timeRes','value'),
            State(self.baseId + 'ts_freeze','value'),
            )
        def updatePSTGraph(n,tags,updateBtn,timeRange,rsMethod,lgd,style,previousFig,tw,rs,freezeMode):
            triggerList = ['interval','btn_update','st_freeze','dd_typeTags','dd_resampleMethod']
            if len(tags)==0:
                return previousFig,2

            if freezeMode:
                fig,errCode = self.updateGraph(previousFig,triggerList,style,
                            [tags,tw*60,rs,rsMethod,True,timeRange],[])
            else:
                fig,errCode = self.updateGraph(previousFig,triggerList,style,[tags,tw*60,rs,rsMethod,True],[])

            # fig = self.updateLegend(fig,lgd)
            return fig,errCode

class RealTimeMultiUnitSelectedTags(TabMaster):
    def __init__(self,*args,defaultCat,defaultTags=[],baseId='tmus0_',**kwargs):
        TabMaster.__init__(self,*args,**kwargs,tabname='multi unit +',baseId=baseId)
        dicSpecialWidgets = {
            'dd_typeTags':defaultCat,
            'dd_tag':defaultTags,
            'btn_legend':0,'in_axisSp':0.05}
        self._buildLayout(dicSpecialWidgets,realTime=True)
        self._define_callbacks()

    def _define_callbacks(self):
        self._define_basicCallbacks(['legendtoogle','export','ts_freeze','refreshWindow'])
        @self.app.callback(
            Output(self.baseId + 'graph', 'figure'),
            Output(self.baseId + 'error_modal_store', 'data'),
            Input(self.baseId + 'dd_tag','value'),
            Input(self.baseId + 'dd_typeTags','value'),
            Input(self.baseId + 'dd_resampleMethod','value'),
            Input(self.baseId + 'btn_legend','children'),
            Input(self.baseId + 'dd_style','value'),
            Input(self.baseId + 'interval','n_intervals'),
            Input(self.baseId + 'btn_update','n_clicks'),
            Input(self.baseId + 'st_freeze','data'),
            State(self.baseId + 'graph','figure'),
            State(self.baseId + 'in_timeWindow','value'),
            State(self.baseId + 'in_timeRes','value'),
            State(self.baseId + 'ts_freeze','value'),
            )
        def updatePSTGraph(tags,tagCat,rsMethod,lgd,style,n,updateBtn,timeRange,previousFig,tw,rs,freezeMode):
            triggerList = ['interval','btn_update','st_freeze','dd_typeTags','dd_resampleMethod']
            tags = self.cfg.getUsefulTags(tagCat) + tags
            if len(tags)==0:
                return previousFig,2

            if freezeMode:
                fig,errCode = self.updateGraph(previousFig,triggerList,style,
                                        [tags,tw*60,rs,rsMethod,True,timeRange],[])
            else:
                fig,errCode = self.updateGraph(previousFig,triggerList,style,
                                [tags,tw*60,rs,rsMethod,True],[])

            # fig = self.updateLegend(fig,lgd)
            return fig,errCode

class RealTimeDoubleMultiUnits(TabMaster):
    def __init__(self,*args,defaultTags1=[],defaultTags2=[],baseId='rtdmu0_',**kwargs):
        TabMaster.__init__(self,*args,**kwargs,tabname='double multi units',baseId=baseId)
        dicSpecialWidgets = {
            'dd_tag1':defaultTags1,
            'dd_tag2':defaultTags2,
            'btn_legend':0,'in_axisSp':0.05}

        self._buildLayout(dicSpecialWidgets,realTime=True)
        self._define_callbacks()

    def _define_callbacks(self):
        self._define_basicCallbacks(['legendtoogle','export','ts_freeze','refreshWindow'])
        @self.app.callback(
            Output(self.baseId + 'graph', 'figure'),
            Output(self.baseId + 'error_modal_store', 'data'),
            Input(self.baseId + 'dd_tag1','value'),
            Input(self.baseId + 'dd_tag2','value'),
            Input(self.baseId + 'dd_resampleMethod','value'),
            Input(self.baseId + 'btn_legend','children'),
            Input(self.baseId + 'dd_style','value'),
            Input(self.baseId + 'interval','n_intervals'),
            Input(self.baseId + 'btn_update','n_clicks'),
            Input(self.baseId + 'st_freeze','data'),
            State(self.baseId + 'graph','figure'),
            State(self.baseId + 'in_timeWindow','value'),
            State(self.baseId + 'in_timeRes','value'),
            State(self.baseId + 'ts_freeze','value'),
            )
        def updateDMUGraph(tags1,tags2,rsMethod,lgd,style,n,updateBtn,timeRange,previousFig,tw,rs,freezeMode):
            triggerList = ['interval','btn_update','st_freeze','dd_typeTags','dd_resampleMethod']
            tags = tags1+tags2
            if len(tags)==0:
                return previousFig,2

            if freezeMode:
                fig,errCode = self.updateGraph(previousFig,triggerList,style,
                    [tags,tw*60,rs,rsMethod,True,timeRange],
                    [tags1,tags2])
            else:
                fig,errCode = self.updateGraph(previousFig,triggerList,style,
                [tags,tw*60,rs,rsMethod,True],
                    [tags1,tags2])

            # fig = self.updateLegend(fig,lgd)
            return fig,errCode


# ==============================================================================
#                               template tabs
# ==============================================================================
class TabExploreDF(TabMaster):
    def __init__(self,app,df,baseId='ted0_'):
        TabMaster.__init__(self,app,baseId)
        self.tabname = 'explore df'
        self.df = df
        self.tabLayout = self._buildLayout()
        self._define_callbacks()

    def _buildLayout(self,widthG=85):
        dicWidgets = {  'btn_update':0,
                        'dd_resampleMethod' : 'mean',
                        'dd_style':'lines+markers','dd_typeGraph':'scatter',
                        'dd_cmap':'jet'}
        basicWidgets = self.dccE.basicComponents(dicWidgets,self.baseId)
        listCols = list(self.df.columns)
        specialWidgets = self.dccE.dropDownFromList(self.baseId + 'dd_x',listCols,'x : ',defaultIdx=0)
        specialWidgets = specialWidgets + self.dccE.dropDownFromList(self.baseId + 'dd_y',listCols,'y : ',defaultIdx=1,multi=True)
        specialWidgets = specialWidgets + [html.P('nb pts :'),dcc.Input(self.baseId + 'in_pts',type='number',step=1,min=0,value=1000)]
        specialWidgets = specialWidgets + [html.P('slider x :'),dcc.RangeSlider(self.baseId + 'rs_x')]
        # reodrer widgets
        widgetLayout = specialWidgets + basicWidgets
        return self.dccE.buildGraphLayout(widgetLayout,self.baseId,widthG=widthG)

    def _define_callbacks(self):
        @self.app.callback(
        Output(self.baseId + 'rs_x', 'marks'),
        Output(self.baseId + 'rs_x', 'value'),
        Output(self.baseId + 'rs_x', 'max'),
        Output(self.baseId + 'rs_x', 'min'),
        Input(self.baseId +'dd_x','value'))
        def update_slider(x):
            x = self.df[x].sort_values()
            min,max = x.iloc[0],x.iloc[-1]
            listx = [int(np.floor(k)) for k in np.linspace(0,len(x)-1,5)]
            marks = {k:{'label':str(k),'style': {'color': '#77b0b1'}} for k in x[listx]}
            return marks,[min,max],max,min

        listInputsGraph = {
                        'dd_x':'value',
                        'dd_y':'value',
                        'btn_update':'n_clicks',
                        'dd_resampleMethod':'value',
                        'dd_typeGraph':'value',
                        'dd_cmap':'value',
                        'dd_style':'value'
                        }
        listStatesGraph = {
                            'graph':'figure',
                            'in_pts':'value',
                            'rs_x': 'value',
                            }
        @self.app.callback(
        Output(self.baseId + 'graph', 'figure'),
        [Input(self.baseId + k,v) for k,v in listInputsGraph.items()],
        [State(self.baseId + k,v) for k,v in listStatesGraph.items()],
        )
        def updateGraph(x,y,upBtn,rsMethod,typeGraph,cmap,style,fig,pts,rsx):
            ctx = dash.callback_context
            trigId = ctx.triggered[0]['prop_id'].split('.')[0]
            if not upBtn or trigId in [self.baseId+k for k in ['btn_update','dd_x','dd_y']]:
                df = self.df.set_index(x)
                if not isinstance(y,list):y=[y]
                if x in y : df[x]=df.index
                # print(df)
                df = df[df.index>rsx[0]]
                df = df[df.index<rsx[1]]
                if pts==0 : inc=1
                else :
                    l = np.linspace(0,len(df),pts)
                    inc = np.median(np.diff(l))
                df = df[::int(np.ceil(inc))]
                df  = df.loc[:,y]
                fig = self.utils.multiUnitGraph(df)
            else :fig = go.Figure(fig)
            fig.update_yaxes(showgrid=False)
            fig.update_xaxes(title=x)
            fig = self.utils.quickLayout(fig,title='',xlab='',ylab='',style='latex')
            fig = self.utils.updateStyleGraph(fig,style,cmap)
            return fig
