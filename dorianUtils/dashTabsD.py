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
    - cfg: ConfigFiles object generated from configFilesD class
    - loadData : function with at least following arguments :
        - t0,t1 : timestamps for period to be showed
        - tags : tags to be plot
        - rsMethod : resampling method ('raw','forwardfill'....)
        - rs : resampling time for pd.resample
    - plotgraph  function to plot the data
    - updateLayoutGraph function to update the graph
    '''
    def __init__(self,app,cfg,loadData,plotData,tabname,update_fig=None,baseId='tab_'):
        self.utils = Utils()
        self.dccE = DccExtended()
        self.app = app
        self.cfg = cfg
        self.loadData   = loadData
        self.plotData   = plotData
        if not update_fig==None:self.update_fig = update_fig
        self.tabname    = tabname
        self.baseId     = baseId
        self.modalError = self.dccE.addModalError(app,cfg,baseid=self.baseId)

    def _define_basicCallbacks(self,categories=[]):
        # update freeze button
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

        # update freeze button
        if 'refreshWindow' in categories:
            @self.app.callback(Output(self.baseId + 'interval', 'interval'),
                                Input(self.baseId + 'in_refreshTime','value'))
            def updateRefreshTime(refreshTime):
                return refreshTime*1000

        # update legend toogle button
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

        # update datetime picker
        if 'datePickerRange' in categories:
            # initial visible month tuned to selection
            @self.app.callback(
            Output(self.baseId + 'pdr_date','initial_visible_month'),
            Input(self.baseId + 'pdr_date','start_date'),
            Input(self.baseId + 'pdr_date','end_date'),
            )
            def updateInitialVisibleMonth(startdate,enddate):
                ctx = dash.callback_context
                trigId = ctx.triggered[0]['prop_id']
                if 'start_date' in trigId:
                    return startdate
                else :
                    return enddate

            # update datetimepickerrange options
            @self.app.callback(
                Output(self.baseId + 'pdr_date','min_date_allowed'),
                Output(self.baseId + 'pdr_date','max_date_allowed'),
                Output(self.baseId + 'pdr_date','end_date'),
                Output(self.baseId + 'pdr_timeEnd','value'),
                Output(self.baseId + 'pdr_date','start_date'),
                Output(self.baseId + 'pdr_timeStart','value'),
                Input(self.baseId + 'pdr_timeInterval','n_intervals'),
            )
            def updateDatePickerRange(n):
                listdays  = self.cfg.getdaysnotempty()
                min_date  = listdays.min().strftime('%Y-%m-%d')
                max_date  = listdays.max().strftime('%Y-%m-%d')
                end_date  = max_date
                startdate = end_date
                starttime ='00:00'
                endtime   = '23:59'
                return min_date,max_date,end_date,endtime,startdate,starttime

        # pop up modal list tags
        if 'modalTagsTxt' in categories:
            @self.app.callback(
                Output(self.baseId + "modalListTags", "is_open"),
                Output(self.baseId + "txtListTags", "value"),
                [Input(self.baseId + "btn_omlt", "n_clicks"), Input(self.baseId + "close_omlt", "n_clicks")],
                [State(self.baseId + "modalListTags", "is_open"),State(self.baseId + "dd_tag", "value")]
            )
            def popupModalListTags(n1,n2, is_open,listTags):
                listTags='\n'.join(listTags)
                if n1:
                    return not is_open,listTags
                return is_open,listTags

            @self.app.callback(
                Output(self.baseId + "dd_tag", "value"),
                [Input(self.baseId + "close_omlt", "n_clicks")],
                [State(self.baseId + "txtListTags", "value")],
                prevent_initial_call=True
            )
            def getListTagsModal(close,txt):
                listTags = [k.strip().upper() for k in txt.split('\n')]
                return listTags

        # update enveloppe dropdown menu
        if 'mini_maxi_enveloppe' in categories:
            @self.app.callback(
                Output(self.baseId + "dd_enveloppe", "options"),
                Output(self.baseId + "dd_enveloppe", "value"),
                [Input(self.baseId + "dd_typeTags", "value"),Input(self.baseId + "dd_tag", "value")],
                State(self.baseId + "dd_enveloppe", "value")
            )
            def update_dd_enveloppe(typeTags,tags,curTagEnv):
                listTags = self.cfg.getUsefulTags(typeTags)+tags
                if curTagEnv not in listTags: curTagEnv=''
                return [{'label':t,'value':t} for t in listTags],curTagEnv

    def _buildLayout(self,specialWidDic,realTime=False,widthG=85,timeres=None):
        methodsList=[k for k in self.cfg.methods_list if not k=='raw']
        if not realTime:
            if timeres is None:timeres='300s'
            dicWidgets = {
                'pdr_time' : {'tmin':self.cfg.tmin,'tmax':self.cfg.tmax,'interval':2*60*60*1000},#update every 2 hours
                'in_timeRes':timeres,
                'dd_resampleMethod' : {'value':'meanright','methods':methodsList},
                'dd_style':'default',
                'btn_export':0,
                    }
        else :
            if timeres is None:timeres='5s'
            dicWidgets = {
                'block_refresh':{'val_window':120,'val_refresh':50,
                                    'min_refresh':1,'min_window':2},
                'btns_refresh':None,
                'block_resample':{'val_res':'5s','val_method' : 'meanright','methods':list(self.cfg.methods.keys())},
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
                            'Select categorie : ',value=wid_val,optionHeight=20,clearable=True)

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
                # print()
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

            elif wid_key=='dd_enveloppe':
                widgetObj = self.dccE.dropDownFromList(self.baseId+wid_key,[''],
                            'add mini maxi enveloppe : ',optionHeight=20,clearable=True,multi=False)
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
        if lgd=='unvisible':
            fig.update_layout(showlegend=False)
        else:
            fig.update_layout(showlegend=True)
            current_names = [k['name'] for k in fig['data']]
            td  = self.cfg.toogle_tag_description(current_names,lgd)
            fig = self.cfg.utils.customLegend(fig,td)
        return fig

    def buildGraph(self,previousFig,listTrigs,argsLoad,args_plot,args_updatefig):
        '''
        - listTrigs : list of components ids that should trigger the building of the graph
            (otherwise the figure will just be updated).
        - argsLoad,args_plot,args_updatefig : list of arguments for the function self.loadData,self.plotData,self.update_fig
        '''
        ctx = dash.callback_context
        trigId = ctx.triggered[0]['prop_id'].split('.')[0]
        fig = go.Figure(previousFig)
        ####### load data in that case
        if trigId in [self.baseId+k for k in listTrigs]:
            # print(*argsLoad)
            start=time.time()
            df_tuple = self.loadData(*argsLoad)
            print()
            print('full loading of  data in {:.2f} ms'.format((time.time()-start)*1000))
            if not isinstance(df_tuple,tuple):
                df_tuple = df_tuple,
            start=time.time()
            if isinstance(df_tuple[0],pd.DataFrame) and df_tuple[0].empty:
                ## get error code loading data ==> 1
                return go.Figure(),1
            else :
                fig = self.plotData(*df_tuple,*args_plot)
        ###### update style of graph
        start=time.time()
        print('here'.rjust(50))

        self.update_fig(fig,*args_updatefig)
        print('figure generated in {:.2f} ms'.format((time.time()-start)*1000))
        print("====================================")

        ######### keep traces visibility
        try :
            fig = self.utils.legendPersistant(previousFig,fig)
        except:
            print('problem to make traces visibility persistant.')
        return self.utils.addLogo(fig),0

    def _defineCallbackGraph(self,realTime,t_inputs,getTags,t_getTags,t_states,t_outputs,t_updateFig,t_plotdata):
        '''
        this function will define the callback to update the graph which will ultimately
        call the funtion self.buildGraph to generate the figure.In order for inheritance
        to work the arguements argsload,args_plot,argsUpdate should be generated automatically.
        *** ALL PROPERTIES OF WIDGETS WILL BE STORED IN A DICTIONNARY

                                    d_args

        where keys are:
        <widget_id>_<widget_property>. where <widget_id> contains only the extension(not the baseId)

        - realTime    : bool for realtime or not
        - t_inputs    : list of tuples (widget_id,widget_property) inputs to add to standard inputs
                            for the callback updateGraph.
        - getTags     : function to get the list of tags
        - t_getTags   : list of tuples (widget_id,widget_property) that are used for the function getTags
        - t_states    : list of tuples (widget_id,widget_property) ststes to add to standard states
                            for the callback updateGraph.
        - t_outputs   : list of tuples (widget_id,widget_property) outputs to add to the standard outputs
                            for the callback updateGraph.
        - t_plotdata  : list of tuples (widget_id,widget_property) that are used for the function self.plotData
        - t_updatefig : list of tuples (widget_id,widget_property) that are used for the function self.update_fig
        '''
        ###################################
        #  DEFINE INPUTS/STATES/OUTPUTS   #
        ###################################
        d_outputs = [
            ('graph','figure'),
            ('error_modal_store','data')
        ]
        d_outputs+=t_outputs

        if realTime:
            d_inputs = [
                ('interval','n_intervals'),
                ('btn_update','n_clicks'),
                ('st_freeze','data'),
                ('dd_resampleMethod','value'),
                ('dd_style','value')
            ]
            d_states = [
                ('graph','figure'),
                ('in_timeWindow','value'),
                ('in_timeRes','value'),
                ('ts_freeze','value'),
            ]
        else:
            d_inputs = [
                ('pdr_timeBtn','n_clicks'),
                ('dd_resampleMethod','value'),
                ('dd_style','value')
            ]
            d_states = [
                ('graph','figure'),
                ('in_timeRes','value'),
                ('pdr_date','start_date'),
                ('pdr_date','end_date'),
                ('pdr_timeStart','value'),
                ('pdr_timeEnd','value'),
            ]
        d_inputs+=t_inputs
        d_states+=t_states

        # print(d_inputs)
        listArgsInputs = [id + '_' + prop for id,prop in d_inputs]
        listArgsStates = [id + '_' + prop for id,prop in d_states]
        allArgsName = listArgsInputs + listArgsStates
        ######################
        #  DEFINE CALLBACK   #
        ######################
        def get_t0_t1_fromWidgets(realTime,d_args):
            if realTime:
                t1 = pd.Timestamp.now(tz='CET')
                t0 = t1 - dt.timedelta(seconds=d_args['in_timeWindow_value']*60)
                if d_args['ts_freeze_value']:
                    t0,t1 = d_args['st_freeze_data']
            else:
                t0 = d_args['pdr_date_start_date'] + ' ' + d_args['pdr_timeStart_value']
                t1 = d_args['pdr_date_end_date'] + ' ' + d_args['pdr_timeEnd_value']
                t0,t1 = [pd.Timestamp(k,tz='CET') for k in [t0,t1]]
            return [t0,t1]
        # print(allArgsName)
        @self.app.callback(
            [Output(self.baseId + k,v) for k,v in d_outputs],
            [Input(self.baseId + k,v) for k,v in d_inputs],
            [State(self.baseId + k,v) for k,v in d_states])
        def updateGraph(*argsCallback):
            ###############################
            #   BUILD THE DICTIONNARY OF  #
            #   WIDGET PROPERTY VALUES    #
            ###############################
            d_args = {k : v for k,v in zip(allArgsName,argsCallback)}
            # for k in d_args.keys():print(k)

            previousFig = d_args['graph_figure']
            ###############################
            #   BUILD THE DICTIONNARY OF  #
            #   WIDGET PROPERTY VALUES    #
            ###############################
            args_getTags=[d_args[wid_id + '_' + prop] for wid_id,prop in t_getTags]
            tags = getTags(*args_getTags)

            if len(tags)==0:
                return previousFig,2
            ##################################
            #   get list of arguments        #
            #   for self.buildGraph function #
            ##################################
            if realTime:triggerloadData_ids = ['interval','btn_update','st_freeze','dd_resampleMethod'] + [widid for widid,prop  in t_getTags]
            else:triggerloadData_ids=['dd_tag','pdr_timeBtn','dd_resampleMethod'] + [widid for widid,prop  in t_getTags]
            d_args['pdr_'] = get_t0_t1_fromWidgets(realTime,d_args)
            argsLoad       = [*d_args['pdr_'],tags,d_args['dd_resampleMethod_value'],d_args['in_timeRes_value']]
            args_plot      = [d_args[wid_id + '_' + prop] for wid_id,prop in t_plotdata]
            args_updatefig = [d_args[wid_id + '_' + prop] for wid_id,prop in t_updateFig]
            fig,errCode = self.buildGraph(previousFig,triggerloadData_ids,argsLoad,args_plot,args_updatefig)
            return fig,errCode

    def update_fig(self,fig,style,colmap=None,lgd=None):
        self.cfg.update_lineshape_fig(fig,style)
        self.cfg.standardLayout(fig)
        if not colmap==None:
            fig = self.utils.updateColorMap(fig,colmap)
        if not lgd==None:
            # print(lgd)
            # try:
            fig = self.updateLegend(fig,lgd)
            # except:
            #     print('impossible to toogle legend')
        return fig

# ==============================================================================
#                              TEMPLATE TABS
# ==============================================================================
class TabSelectedTags(TabMaster):
    def __init__(self,*args,realtime=False,defaultCat=[],tabname='pre-selected tags',baseId='ts0_',**kwargs):
        TabMaster.__init__(self,*args,**kwargs,tabname=tabname,baseId=baseId)
        dicSpecialWidgets = {'dd_typeTags':defaultCat,'dd_cmap':'jet','btn_legend':0}

        self._buildLayout(dicSpecialWidgets,realTime=realtime)
        if realtime:
            self._define_basicCallbacks(['export','ts_freeze','refreshWindow'])
        else:
            self._define_basicCallbacks(['legendtoogle','export','datePickerRange'])
        t_inputs = [
            ('dd_typeTags','value'),
            ('dd_cmap','value')
            #('btn_legend','children')
            ]
        def getTags(tagCat):return self.cfg.getUsefulTags(tagCat)
        self._defineCallbackGraph(realtime,t_inputs,getTags,['dd_typeTags'],[],['dd_style','dd_cmap'])

class TabMultiUnits(TabMaster):
    def __init__(self,*args,realtime=False,defaultTags=[],baseId='tmu0_',tabname='multi-unit',**kwargs):
        # for k in args:print(k)
        TabMaster.__init__(self,*args,**kwargs,tabname=tabname,baseId=baseId)
        dicSpecialWidgets = {'dd_tag':defaultTags,'modalListTags':None,'btn_legend':0}
        self._buildLayout(dicSpecialWidgets,realTime=realtime)
        self.wids=self.dccE.parseLayoutIds(self.tabLayout)
        if realtime:
            self._define_basicCallbacks(['legendtoogle','export','modalTagsTxt','refreshWindow','ts_freeze'])
        else:
            self.wids[self.baseId + 'pdr_timeInterval'].interval=1*60*60*1000 #update every hour
            self._define_basicCallbacks(['legendtoogle','export','datePickerRange','modalTagsTxt'])
            # self._define_basicCallbacks(['legendtoogle','export','modalTagsTxt'])
        t_inputs = [
            ('dd_tag','value'),
            ('btn_legend','children'),
        ]
        def getTags(tags):return tags
        self._defineCallbackGraph(realtime,t_inputs,getTags,['dd_tag'],[],['dd_style'])

class TabMultiUnitSelectedTags(TabMaster):
    def __init__(self,*args,realtime=False,defaultCat=[],ddtag=[],tabname='multi-unit +',baseId='muts0_',**kwargs):
        TabMaster.__init__(self,*args,**kwargs,
                    update_fig = self.update_figure,
                    tabname=tabname,baseId=baseId)
        dicSpecialWidgets = {'dd_typeTags':defaultCat,'dd_tag':ddtag,'btn_legend':0,'modalListTags':None,'dd_enveloppe':''}
        self._buildLayout(dicSpecialWidgets,realTime=realtime)
        listCallbacks = ['legendtoogle','export','modalTagsTxt','mini_maxi_enveloppe']
        if realtime:
            listCallbacks+=['ts_freeze','refreshWindow']
        else:
            listCallbacks+=['datePickerRange']
        self._define_basicCallbacks(listCallbacks)

        t_inputs = [
            ('dd_typeTags','value'),
            ('dd_tag','value'),
            ('dd_enveloppe','value'),
            ('btn_legend','children')
        ]
        def getTags(tagCat,tags):
            return list(pd.Series(self.cfg.getUsefulTags(tagCat) + tags).unique())
        t_getTags = [('dd_typeTags','value'),('dd_tag','value')]
        t_plotdata,t_states,t_outputs = [[]]*3
        # t_updatefig  = [('graph','figure'),('dd_style','value'),('dd_enveloppe','value'),('pdr',''),('in_timeRes','value')]
        # t_updatefig  = [('dd_style','value'),('dd_enveloppe','value'),('pdr',''),('in_timeRes','value')]
        t_updatefig  = [('dd_style','value'),('dd_enveloppe','value'),('pdr',''),('in_timeRes','value'),('btn_legend','children')]

        self._defineCallbackGraph(realtime,t_inputs,getTags,t_getTags,t_states,t_outputs,t_updatefig,t_plotdata)

        # def update_fig(self,fig,style,lgd,tag_env='',t0=None,t1=None,rs=None):

    def update_figure(self,fig,style,tag_env,timerange,rs,lgd):
        '''timerange : [t0,t1]'''
        # print('here'.rjust(50))
        #### remove the previous minmax curve
        idxs=[]
        # print('--------------------')
        # print('try to update figure')
        for k,trace in enumerate(fig.data):
            if '_minmax' in trace.name:
                # print('remove : ',trace.name)
                idxs.append(k)

        fig.data=[fig.data[k] for k in range(len(fig.data)) if k not in idxs]

        #### update style regular curves
        ### (it is here because minmax should not be present to standard update fig)
        fig = TabMaster.update_fig(self,fig,style,lgd=lgd)
        # print(fig.data)
        #### add the new minmax curve
        if tag_env in self.cfg.alltags:
            # print('add minmax:' ,tag_env)
            fig = self.cfg.addTagEnveloppe(fig,tag_env,*timerange,rs)
        # print('--------------------')
        return fig

class TabDoubleMultiUnits(TabMaster):
    def __init__(self,*args,realtime=False,defaultTags1=[],defaultTags2=[],baseId='rtdmu0_',tabname='double multi units',**kwargs):
        TabMaster.__init__(self,*args,**kwargs,tabname=tabname,baseId=baseId)
        dicSpecialWidgets = {
            'dd_tag1':defaultTags1,
            'dd_tag2':defaultTags2,
            # 'dd_cmap':'jet',
            'btn_legend':0,'in_axisSp':0.05}
        if realtime:
            self._define_basicCallbacks(['legendtoogle','export','modalTagsTxt','refreshWindow','ts_freeze'])
        else:
            self._define_basicCallbacks(['legendtoogle','export','datePickerRange','modalTagsTxt'])

        self._buildLayout(dicSpecialWidgets,realTime=realtime)
        t_inputs = [
            ('dd_tag1','value'),
            ('dd_tag2','value')
            # 'dd_cmap','value'
        ]
        def getTags(tags1,tags2):
            return tags1 + tags2
        self._defineCallbackGraph(realtime,t_inputs,getTags,
                    ['dd_tag1','dd_tag2'],
                    ['dd_tag1','dd_tag2'],
                    ['dd_style'])

class TabUnitSelector(TabMaster):
    def __init__(self,*args,realtime=False,unitInit='mbarg',patTagInit='GFC',baseId='tu0_',**kwargs):
        TabMaster.__init__(self,*args,**kwargs,tabname='select Units',baseId=baseId)

        dicSpecialWidgets = {'dd_Units':unitInit,'in_patternTag':patTagInit,'dd_cmap':'jet','btn_legend':0}
        t_inputs = [
            ('dd_Units','value'),
            ('in_patternTag','value'),
        ]
        self._buildLayout(dicSpecialWidgets,realTime=realtime)
        if realtime:
            self._define_basicCallbacks(['legendtoogle','export','ts_freeze','refreshWindow'])
        else:
            self._define_basicCallbacks(['legendtoogle','export','datePickerRange'])
        def getTags(patTag,unit):
            tags=self.cfg.getTagsTU(patTag,unit)
            return tags
        self._defineCallbackGraph(realtime,t_inputs,getTags,['in_patternTag','dd_Units'],[],['dd_style'])

class AnalysisTab(TabMaster):
    def __init__(self,app,cfg):
        TabMaster.__init__(self,app,cfg,
                    self.loadDF,self.plotdf,cfg.update_lineshape,
                    baseId='formu_',tabname = 'Analysis'
                    )
        self.df = px.data.stocks()
        dicSpecialWidgets = {}
        self._buildLayout(dicSpecialWidgets)
        xwid  = self.dccE.DropdownFromList(self.cfg.getTagsTU('')+['timestamp'],
                    id=self.baseId+'dd_x',value='timestamp',clearable=False)
        ywid  = self.dccE.DropdownFromList(self.cfg.getTagsTU(''),
                    id=self.baseId+'dd_y',value=self.cfg.getTagsTU('GFC')[0],multi=True)
        self.tabLayout[0].children+=[html.P('   x variable :'),xwid,html.P('   y variables :'),ywid]
        self.tabLayout.append(html.Div(self.newWidgets()))
        self.tabLayout.append(dcc.Store(id=self.baseId + '_newListTags',data={}))
        self._define_callbacks()

    def computeNewTag(self,timeRange,formulas,**kwargs):
        if len(formulas)==0:
            return pd.DataFrame()
        listTags = [re.findall('[a-zA-Z][a-zA-Z\._\d]*',f) for f in formulas]
        listTags = list(pd.Series(self.cfg.utils.flattenList(listTags)).unique())

        df = self.cfg.DF_loadTimeRangeTags(timeRange,listTags,**kwargs)
        newdf=pd.DataFrame()
        for formula in formulas:
            realFormula = formula
            for t in listTags:realFormula = realFormula.replace(t,"df['"+t+"']")
            newdf[realFormula] = eval(realFormula)
        return newdf

    def loadDF(self,timeRange,x,ys,rs,rsMethod):
        if not isinstance(ys,list):ys=[ys]
        #search and compute formulas
        formulas = [t for t in ys + [x] if re.search('[-\*\+\/]',t)]
        dfFormulas = self.computeNewTag(timeRange,formulas,rs=rs,applyMethod=rsMethod)
        #search and compute not formulas
        tags = [t for t in ys+[x] if t not in formulas]
        if not x=='timestamp':
            df = self.cfg.DF_loadTimeRangeTags(timeRange,tags,rs=rs,applyMethod=rsMethod)
            dft = pd.concat([dfFormulas,df],axis=1)
            dft = dft.set_index(x)
        else :
            tags = [t for t in tags if not t=='timestamp']
            df = self.cfg.DF_loadTimeRangeTags(timeRange,tags,rs=rs,applyMethod=rsMethod)
            dft = pd.concat([dfFormulas,df],axis=1)
        return dft

    def plotdf(self,df):
        return px.scatter(df)

    def newWidgets(self):
        self.egalstyle = {'fontsize':'20 px','width':'10px','height': '40px','min-height': '1px',}
        self.newtagstyle = {'fontsize':'15 px','width':'300px','height': '40px','min-height': '1px',}
        self.tagstyle = {'fontsize':'15 px','width':'400px','height': '40px','min-height': '1px',}
        self.formulastyle = {'fontsize':'15 px','width':'800px','height': '40px','min-height': '1px',}
        self.buttonstyle = {'fontsize':'15 px','width':'90px','height': '40px','min-height': '1px',}

        tagwid = self.dccE.DropdownFromList(self.cfg.getTagsTU(''),
                        id=self.baseId+'dd_tag',placeholder='liste tags:',style=self.tagstyle)
        newTagIn = dcc.Input(id=self.baseId+'in_newtag',placeholder='tagname:',
                        type='text',style=self.newtagstyle)
        egalwid     = html.P(id=self.baseId+'egal',children=' : ',style=self.egalstyle)
        formulawid  = dcc.Input(id=self.baseId+'in_formula',placeholder='formula : ',
                        type='text',style=self.formulastyle,value='')
        btn_create  = html.Button(id=self.baseId+'btn_create',children='create',
                        style=self.buttonstyle)

        createFormulaWidget = [
                dbc.Row([
                    dbc.Col(tagwid),
                    dbc.Col(newTagIn),
                    dbc.Col(egalwid),
                    dbc.Col(formulawid),
                    dbc.Col(btn_create)
                ]),
                ]
        return createFormulaWidget

    def _define_callbacks(self):
        @self.app.callback(
            Output(self.baseId + 'in_formula', 'value'),
            Output(self.baseId + 'in_newtag', 'value'),
            Output(self.baseId + 'dd_tag', 'value'),
            Output(self.baseId + 'dd_x', 'options'),
            Output(self.baseId + 'dd_y', 'options'),

            Input(self.baseId + 'btn_create', 'n_clicks'),
            Input(self.baseId + 'dd_tag', 'value'),
            State(self.baseId + 'in_newtag','value'),
            State(self.baseId + 'in_formula','value'),
            State(self.baseId + 'dd_x','options'),
            State(self.baseId + 'dd_y','options'),
            prevent_initial_call=True
        )
        def addNewTag(n,tag,newtag,formula,ddx,ddy):
            ctx = dash.callback_context
            trigId = ctx.triggered[0]['prop_id'].split('.')[0]
            # print(trigId)
            if trigId==self.baseId + 'dd_tag':
                return formula + tag,newtag,'',ddx,ddy

            if trigId==self.baseId + 'btn_create':
                ## check if formula is correct
                ## add the new formula
                newentry = [{'label':newtag,'value':formula}]
                newddx = ddx + newentry
                newddy = ddy + newentry
                return '','','',newddx,newddy

        self._define_basicCallbacks(['export','datePickerRange'])
        @self.app.callback(
            Output(self.baseId + 'graph', 'figure'),
            Output(self.baseId + 'error_modal_store', 'data'),
            Input(self.baseId + 'pdr_timeBtn','n_clicks'),
            Input(self.baseId + 'dd_resampleMethod','value'),
            Input(self.baseId + 'dd_style','value'),
            Input(self.baseId + 'dd_x','value'),
            Input(self.baseId + 'dd_y','value'),
            State(self.baseId + 'graph','figure'),
            State(self.baseId + 'in_timeRes','value'),
            State(self.baseId + 'pdr_date','start_date'),
            State(self.baseId + 'pdr_date','end_date'),
            State(self.baseId + 'pdr_timeStart','value'),
            State(self.baseId + 'pdr_timeEnd','value'),
            )
        def buildGraph(timeBtn,rsMethod,style,x,y,previousFig,rs,date0,date1,t0,t1):
            triggerList=['pdr_timeBtn','dd_resampleMethod','dd_x','dd_y']
            timeRange = [date0+' '+t0,date1+' '+t1]

            fig,errCode = self.buildGraph(previousFig,triggerList,style,
                [timeRange,x,y,rs,rsMethod],[]
                )
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
        def buildGraph(x,y,upBtn,rsMethod,typeGraph,cmap,style,fig,pts,rsx):
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
