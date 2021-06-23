import datetime as dt, pickle, time
import os,re,pandas as pd
import dash, dash_core_components as dcc, dash_html_components as html, dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import plotly.express as px, plotly.graph_objects as go
import matplotlib.pyplot as plt, matplotlib.colors as mtpcl
from pylab import cm
from dorianUtils.dccExtendedD import DccExtended
from dorianUtils.utilsD import Utils
import dorianUtils.configFilesD as cfd

class TabMaster():
    ''' this tab can only be built with templateDashTagsUnit and ConfigDashTagUnitTimestamp instances
        from templateDashD and configFilesD '''
    def __init__(self,app,baseId):
        self.baseId=baseId
        self.app = app
        self.utils = Utils()
        self.dccE = DccExtended()

class TabDataTags(TabMaster):
    def __init__(self,folderPkl,cfg,app,baseId):
        super().__init__(app,baseId)
        self.cfg = cfg
        self.tabLayout = self._buildLayout()
        self.tabname = 'select tags'
        self._define_callbacks()

    def addWidgets(self,dicWidgets,baseId):
        widgetLayout,dicLayouts = [],{}
        for wid_key,wid_val in dicWidgets.items():
            if 'dd_listFiles' in wid_key:
                widgetObj = self.dccE.dropDownFromList(baseId+wid_key,self.cfg.listFilesPkl,
                    'Select your File : ',labelsPattern='\d{4}-\d{2}-\d{2}-\d{2}',defaultIdx=wid_val)


            elif 'dd_tag' in wid_key:
                widgetObj = self.dccE.dropDownFromList(baseId+wid_key,self.cfg.getTagsTU(''),
                    'Select the tags : ',value=wid_val,multi=True,optionHeight=20)

            elif 'dd_Units' in wid_key :
                widgetObj = self.dccE.dropDownFromList(baseId+wid_key,self.cfg.listUnits,'Select units graph : ',value=wid_val)

            elif 'dd_typeTags' in wid_key:
                widgetObj = self.dccE.dropDownFromList(baseId+wid_key,list(self.cfg.usefulTags.index),
                            'Select categorie : ',value=wid_val,optionHeight=20)

            elif 'btn_legend' in wid_key:
                widgetObj = [html.Button('tag',id=baseId+wid_key, n_clicks=wid_val)]

            elif 'in_patternTag' in wid_key  :
                widgetObj = [html.P('pattern with regexp on tag : '),
                dcc.Input(id=baseId+wid_key,type='text',value=wid_val)]

            elif 'in_step' in wid_key:
                widgetObj = [html.P('skip points : '),
                dcc.Input(id=baseId+wid_key,placeholder='skip points : ',type='number',
                            min=1,step=1,value=wid_val)]

            elif 'in_axisSp' in wid_key  :
                widgetObj = [html.P('select the space between axis : '),
                dcc.Input(id=baseId+wid_key,type='number',value=wid_val,max=1,min=0,step=0.01)]

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
            if not oldNames[0] in list(self.cfg.dfPLC[self.cfg.tagCol]):# for initialization mainly
                newNames = [self.cfg.getTagnamefromDescription(k) for k in oldNames]
                dictNames   = dict(zip(oldNames,newNames))
                fig         = self.utils.customLegend(fig,dictNames)
        return fig

    def drawGraph(self,typeGraph,**kwargs):
        unit = self.cfg.getUnitofTag(df.columns[0])
        nameGrandeur = self.utils.detectUnit(unit)
        fig.update_layout(yaxis_title = nameGrandeur + ' in ' + unit)
        # return fig
        return self.utils.plotGraphType(df,typeGraph,**kwargs)

class TabUnitSelector(TabDataTags):
    def __init__(self,folderPkl,cfg,app,baseId='tu0_'):
        TabDataTags.__init__(self,folderPkl,cfg,app,baseId)
        self.tabname = 'select units'

    def _buildLayout(self,widthG=85):
        dicWidgets = {'pdr_time' : {'tmin':self.cfg.listFilesPkl[0],'tmax':self.cfg.listFilesPkl[-1]},
                        'in_timeRes':'auto','dd_resampleMethod' : 'mean',
                        'dd_style':'lines+markers','dd_typeGraph':'scatter',
                        'dd_cmap':'jet','btn_export':0}
        basicWidgets = self.dccE.basicComponents(dicWidgets,self.baseId)
        specialWidgets = self.addWidgets({'dd_Units':'W AC','in_patternTag':'','btn_legend':0},self.baseId)
        # reodrer widgets
        widgetLayout = basicWidgets + specialWidgets
        return self.dccE.buildGraphLayout(widgetLayout,self.baseId,widthG=widthG)

    def _define_callbacks(self):

        @self.app.callback(Output(self.baseId + 'btn_legend', 'children'),
                            Input(self.baseId + 'btn_legend','n_clicks'))
        def updateLgdBtn(legendType):return self.updateLegendBtnState(legendType)

        listInputsGraph = {
                        'dd_Units':'value',
                        'in_patternTag':'value',
                        'pdr_timeBtn':'n_clicks',
                        'dd_resampleMethod':'value',
                        'dd_typeGraph':'value',
                        'dd_cmap':'value',
                        'btn_legend':'children',
                        'dd_style':'value'
                        }
        listStatesGraph = {
                            'graph':'figure',
                            'in_timeRes' : 'value',
                            'pdr_timeStart' : 'value',
                            'pdr_timeEnd':'value',
                            'pdr_timePdr':'start_date',
                            }
        @self.app.callback(
        Output(self.baseId + 'graph', 'figure'),
        Output(self.baseId + 'pdr_timeBtn', 'n_clicks'),
        [Input(self.baseId + k,v) for k,v in listInputsGraph.items()],
        [State(self.baseId + k,v) for k,v in listStatesGraph.items()],
        State(self.baseId+'pdr_timePdr','end_date'))
        def updateGraph(unit,tagPat,timeBtn,rsMethod,typeGraph,cmap,lgd,style,fig,rs,date0,date1,t0,t1):
            ctx = dash.callback_context
            trigId = ctx.triggered[0]['prop_id'].split('.')[0]
            # to ensure that action on graphs only without computation do not
            # trigger computing the dataframe again
            if not timeBtn or trigId in [self.baseId+k for k in ['pdr_timeBtn']] :
                timeRange = [date0+' '+t0,date1+' '+t1]
                listTags  = self.cfg.getTagsTU(tagPat,unit)
                df        = self.cfg.DF_loadTimeRangeTags(timeRange,listTags,rs=rs,applyMethod=rsMethod)
                # names     = self.cfg.getUnitsOfpivotedDF(df,True)
                fig     = self.utils.plotGraphType(df,typeGraph)
                nameGrandeur = self.utils.detectUnit(unit)
                fig.update_layout(yaxis_title = nameGrandeur + ' in ' + unit)
            else :fig = go.Figure(fig)
            fig = self.utils.updateStyleGraph(fig,style,cmap)
            fig = self.updateLegend(fig,lgd)
            return fig,timeBtn

        @self.app.callback(
                Output(self.baseId + 'btn_export','children'),
                Input(self.baseId + 'btn_export', 'n_clicks'),
                State(self.baseId + 'graph','figure')
                )
        def exportClick(btn,fig):
            if btn>1:
                self.utils.exportDataOnClick(fig)
            return 'export Data'

class TabSelectedTags(TabDataTags):
    def __init__(self,folderPkl,cfg,app,baseId='ts0_'):
        super().__init__(folderPkl,cfg,app,baseId)
        self.tabname = 'select tags'

    def _buildLayout(self,widthG=80):
        dicWidgets = {'pdr_time' : {'tmin':self.cfg.listFilesPkl[0],'tmax':self.cfg.listFilesPkl[-1]},
                        'in_timeRes':'auto','dd_resampleMethod' : 'mean',
                        'dd_style':'lines+markers','dd_typeGraph':'scatter',
                        'dd_cmap':'jet','btn_export':0}
        basicWidgets = self.dccE.basicComponents(dicWidgets,self.baseId)
        specialWidgets = self.addWidgets({'dd_typeTags':'Temperatures du gv1a','btn_legend':0},self.baseId)
        # reodrer widgets
        widgetLayout = basicWidgets + specialWidgets
        return self.dccE.buildGraphLayout(widgetLayout,self.baseId,widthG=widthG)

    def _define_callbacks(self):

        @self.app.callback(Output(self.baseId + 'btn_legend', 'children'),
                            Input(self.baseId + 'btn_legend','n_clicks'))
        def updateLgdBtn(legendType):return self.updateLegendBtnState(legendType)


        listInputsGraph = {
                        'dd_typeTags':'value',
                        'pdr_timeBtn':'n_clicks',
                        'dd_resampleMethod':'value',
                        'dd_typeGraph':'value',
                        'dd_cmap':'value',
                        'btn_legend':'children',
                        'dd_style':'value'}
        listStatesGraph = {
                            'graph':'figure',
                            'in_timeRes' : 'value',
                            'pdr_timeStart' : 'value',
                            'pdr_timeEnd':'value',
                            'pdr_timePdr':'start_date',
                            }
        @self.app.callback(
        Output(self.baseId + 'graph', 'figure'),
        Output(self.baseId + 'pdr_timeBtn', 'n_clicks'),
        [Input(self.baseId + k,v) for k,v in listInputsGraph.items()],
        [State(self.baseId + k,v) for k,v in listStatesGraph.items()],
        State(self.baseId+'pdr_timePdr','end_date'))
        def updateGraph(preSelGraph,timeBtn,rsMethod,typeGraph,colmap,lgd,style,fig,rs,date0,date1,t0,t1):
            ctx = dash.callback_context
            trigId = ctx.triggered[0]['prop_id'].split('.')[0]
            # to ensure that action on graphs only without computation do not
            # trigger computing the dataframe again
            if not timeBtn or trigId in [self.baseId+k for k in ['dd_typeTags','pdr_timeBtn','dd_resampleMethod','dd_typeGraph']] :
                start       = time.time()
                timeRange   = [date0+' '+t0,date1+' '+t1]
                listTags    = self.cfg.getUsefulTags(preSelGraph)
                df          = self.cfg.DF_loadTimeRangeTags(timeRange,listTags,rs=rs,applyMethod=rsMethod)
                names       = self.cfg.getUnitsOfpivotedDF(df,True)
                self.utils.printCTime(start)
                fig     = self.utils.plotGraphType(df,typeGraph)
                unit = self.cfg.getUnitofTag(df.columns[0])
                nameGrandeur = self.cfg.utils.detectUnit(unit)
                fig.update_layout(yaxis_title = nameGrandeur + ' in ' + unit)
            else :fig = go.Figure(fig)
            fig = self.utils.updateStyleGraph(fig,style,colmap)
            fig = self.updateLegend(fig,lgd)
            return fig,timeBtn


        @self.app.callback(
                Output(self.baseId + 'btn_export','children'),
                Input(self.baseId + 'btn_export', 'n_clicks'),
                State(self.baseId + 'graph','figure')
                )
        def exportClick(btn,fig):
            if btn>1:
                self.utils.exportDataOnClick(fig)
            return 'export Data'

class TabMultiUnits(TabDataTags):
    def __init__(self,folderPkl,cfg,app,baseId='tmu0_'):
        super().__init__(folderPkl,cfg,app,baseId)
        self.tabname = 'multi Units'

    def _buildLayout(self,widthG=80):
        dicWidgets = {'pdr_time' : {'tmin':self.cfg.listFilesPkl[0],'tmax':self.cfg.listFilesPkl[-1]},
                        'in_timeRes':str(60*10)+'s','dd_resampleMethod' : 'mean',
                        'dd_style':'lines+markers','dd_typeGraph':'scatter',
                        'dd_cmap':'jet','btn_export':0}
        basicWidgets = self.dccE.basicComponents(dicWidgets,self.baseId)
        specialWidgets = self.addWidgets({'dd_tag':None,'btn_legend':0,'in_axisSp':0.05},self.baseId)
        # reodrer widgets
        widgetLayout = basicWidgets + specialWidgets
        return self.dccE.buildGraphLayout(widgetLayout,self.baseId,widthG=widthG)

    def _define_callbacks(self):
        @self.app.callback(Output(self.baseId + 'btn_legend', 'children'),
                            Input(self.baseId + 'btn_legend','n_clicks'))
        def updateLgdBtn(legendType):return self.updateLegendBtnState(legendType)

        listInputsGraph = {
                        'dd_tag':'value',
                        'pdr_timeBtn':'n_clicks',
                        'dd_resampleMethod':'value',
                        'dd_cmap':'value',
                        'btn_legend':'children',
                        'dd_style':'value'
                        ,'in_axisSp':'value'}
        listStatesGraph = {
                            'graph':'figure',
                            'in_timeRes' : 'value',
                            'pdr_timeStart' : 'value',
                            'pdr_timeEnd':'value',
                            'pdr_timePdr':'start_date',
                            }

        @self.app.callback(
            Output(self.baseId + 'graph', 'figure'),
            Output(self.baseId + 'pdr_timeBtn', 'n_clicks'),
            [Input(self.baseId + k,v) for k,v in listInputsGraph.items()],
            [State(self.baseId + k,v) for k,v in listStatesGraph.items()],
            State(self.baseId+'pdr_timePdr','end_date'))
        def updateMUGGraph(tags,timeBtn,rsMethod,cmapName,lgd,style,axSP,fig,rs,date0,date1,t0,t1):
            ctx = dash.callback_context
            trigId = ctx.triggered[0]['prop_id'].split('.')[0]
            # to ensure that action on graphs only without computation do not
            # trigger computing the dataframe again
            triggerList=['dd_tag','pdr_timeBtn','dd_resampleMethod']
            if not timeBtn or trigId in [self.baseId+k for k in triggerList] :
                timeRange = [date0+' '+t0,date1+' '+t1]
                print('================== here ==========================')
                fig  = self.cfg.plotMultiUnitGraph(timeRange,listTags=tags,rs=rs,applyMethod=rsMethod)
            else :fig = go.Figure(fig)
            tagMapping = {t:self.cfg.getUnitofTag(t) for t in tags}
            fig.layout = self.utils.getLayoutMultiUnit(axisSpace=axSP,dictGroups=tagMapping)[0].layout
            fig = self.cfg.updateLayoutMultiUnitGraph(fig)
            fig = self.updateLegend(fig,lgd)
            return fig,timeBtn

        @self.app.callback(
                Output(self.baseId + 'btn_export','children'),
                Input(self.baseId + 'btn_export', 'n_clicks'),
                State(self.baseId + 'graph','figure')
                )
        def exportClick(btn,fig):
            if btn>1:
                self.utils.exportDataOnClick(fig)
            return 'export Data'
