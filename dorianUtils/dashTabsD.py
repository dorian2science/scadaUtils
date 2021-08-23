import datetime as dt, pickle, time
import os,re,pandas as pd,numpy as np
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

# ==============================================================================
#                       format Tag,timestamp,value
# ==============================================================================
class TabDataTags(TabMaster):
    def __init__(self,folderPkl,cfg,app,baseId):
        super().__init__(app,baseId)
        self.cfg = cfg
        self.tabLayout = self._buildLayout()
        self.tabname = 'select tags'

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

    def drawGraph(self,df,typeGraph,**kwargs):
        unit = self.cfg.getUnitofTag(df.columns[0])
        nameGrandeur = self.utils.detectUnit(unit)
        fig.update_layout(yaxis_title = nameGrandeur + ' in ' + unit)
        return self.utils.plotGraphType(df,typeGraph,**kwargs)

class TabUnitSelector(TabDataTags):
    def __init__(self,folderPkl,cfg,app,baseId='tu0_'):
        TabDataTags.__init__(self,folderPkl,cfg,app,baseId)
        self.tabname = 'select units'

    def _buildLayout(self,widthG=85,unitInit=None,patTagInit=''):
        dicWidgets = {'pdr_time' : {'tmin':self.cfg.listFilesPkl[0],'tmax':self.cfg.listFilesPkl[-1]},
                        'in_timeRes':'auto','dd_resampleMethod' : 'mean',
                        'dd_style':'lines+markers','dd_typeGraph':'scatter',
                        'dd_cmap':'jet','btn_export':0}
        basicWidgets = self.dccE.basicComponents(dicWidgets,self.baseId)
        specialWidgets = self.addWidgets({'dd_Units':unitInit,'in_patternTag':patTagInit,'btn_legend':0},self.baseId)
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
        [Input(self.baseId + k,v) for k,v in listInputsGraph.items()],
        [State(self.baseId + k,v) for k,v in listStatesGraph.items()],
        State(self.baseId+'pdr_timePdr','end_date'))
        def updateGraph(unit,tagPat,timeBtn,rsMethod,typeGraph,cmap,lgd,style,previousFig,rs,date0,date1,t0,t1):
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
            else :fig = go.Figure(previousFig)
            fig = self.utils.updateStyleGraph(fig,style,cmap)
            try :
                fig = self.utils.legendPersistant(previousFig,fig)
            except:print('skip and update for next graph')
            fig = self.updateLegend(fig,lgd)
            return fig

        @self.app.callback(
                Output(self.baseId + 'dl','data'),
                Input(self.baseId + 'btn_export', 'n_clicks'),
                State(self.baseId + 'graph','figure'),
                prevent_initial_call=True
                )
        def exportClick(btn,fig):
            df,filename =  self.utils.exportDataOnClick(fig)
            return dcc.send_data_frame(df.to_csv, filename+'.csv')

class TabSelectedTags(TabDataTags):
    def __init__(self,folderPkl,cfg,app,baseId='ts0_'):
        super().__init__(folderPkl,cfg,app,baseId)
        self.tabname = 'select tags'

    def _buildLayout(self,widthG=80,tagCatDefault=None):
        dicWidgets = {'pdr_time' : {'tmin':self.cfg.listFilesPkl[0],'tmax':self.cfg.listFilesPkl[-1]},
                        'in_timeRes':'auto','dd_resampleMethod' : 'mean',
                        'dd_style':'lines+markers','dd_typeGraph':'scatter',
                        'dd_cmap':'jet','btn_export':0}
        basicWidgets = self.dccE.basicComponents(dicWidgets,self.baseId)
        specialWidgets = self.addWidgets({'dd_typeTags':tagCatDefault,'btn_legend':0},self.baseId)
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
        [Input(self.baseId + k,v) for k,v in listInputsGraph.items()],
        [State(self.baseId + k,v) for k,v in listStatesGraph.items()],
        State(self.baseId+'pdr_timePdr','end_date'),
        )
        def updateGraph(preSelGraph,timeBtn,rsMethod,typeGraph,colmap,lgd,style,previousFig,rs,date0,date1,t0,t1):
            ctx = dash.callback_context
            trigId = ctx.triggered[0]['prop_id'].split('.')[0]
            # to ensure that action on graphs only without computation do not
            # trigger computing the dataframe again
            listTrigs = ['dd_typeTags','pdr_timeBtn','dd_resampleMethod','dd_typeGraph']
            if not timeBtn or trigId in [self.baseId+k for k in listTrigs] :
                start       = time.time()
                timeRange   = [date0+' '+t0,date1+' '+t1]
                listTags    = self.cfg.getUsefulTags(preSelGraph)
                df          = self.cfg.DF_loadTimeRangeTags(timeRange,listTags,rs=rs,applyMethod=rsMethod)
                self.utils.printCTime(start)
                if not df.empty:
                    fig  = self.utils.plotGraphType(df,typeGraph)
                    unit = self.cfg.getUnitofTag(df.columns[0])
                    nameGrandeur = self.cfg.utils.detectUnit(unit)
                    fig.update_layout(yaxis_title = nameGrandeur + ' in ' + unit)
                    fig.update_layout(title = preSelGraph)
                else :
                    fig = go.Figure(previousFig)
                    fig.update_layout(title = 'NO DATA FOR THIS LIST OF TAGS AND DATE RANGE')
            else :fig = go.Figure(previousFig)
            fig = self.utils.updateStyleGraph(fig,style,colmap)
            try :
                fig = self.utils.legendPersistant(previousFig,fig)
            except:print('skip and update for next graph')
            fig = self.updateLegend(fig,lgd)
            return fig

        @self.app.callback(
                Output(self.baseId + 'dl','data'),
                Input(self.baseId + 'btn_export', 'n_clicks'),
                State(self.baseId + 'graph','figure'),
                prevent_initial_call=True
                )
        def exportClick(btn,fig):
            df,filename =  self.utils.exportDataOnClick(fig)
            return dcc.send_data_frame(df.to_csv, filename+'.csv')

class TabMultiUnits(TabDataTags):
    def __init__(self,folderPkl,cfg,app,baseId='tmu0_'):
        super().__init__(folderPkl,cfg,app,baseId)
        self.tabname = 'multi Units'

    def updateLayoutMultiUnitGraph(self,fig,sizeDots=10):
        fig.update_yaxes(showgrid=False)
        fig.update_traces(marker=dict(size=sizeDots))
        fig.update_layout(height=900)
        fig.update_traces(hovertemplate='<b>%{y:.1f}')
        return fig

    def _buildLayout(self,widthG=80,initialTags=None):
        dicWidgets = {'pdr_time' : {'tmin':self.cfg.listFilesPkl[0],'tmax':self.cfg.listFilesPkl[-1]},
                        'in_timeRes':'60s','dd_resampleMethod' : 'mean',
                        'dd_style':'lines+markers','dd_typeGraph':'scatter',
                        'dd_cmap':'jet','btn_export':0}
        basicWidgets = self.dccE.basicComponents(dicWidgets,self.baseId)
        specialWidgets = self.addWidgets({'dd_tag':initialTags,'btn_legend':0,'in_axisSp':0.05},self.baseId)
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
                        'dd_style':'value',
                        'in_axisSp':'value'}
        listStatesGraph = {
                            'graph':'figure',
                            'in_timeRes' : 'value',
                            'pdr_timeStart' : 'value',
                            'pdr_timeEnd':'value',
                            'pdr_timePdr':'start_date',
                            }

        @self.app.callback(
            Output(self.baseId + 'graph', 'figure'),
            [Input(self.baseId + k,v) for k,v in listInputsGraph.items()],
            [State(self.baseId + k,v) for k,v in listStatesGraph.items()],
            State(self.baseId+'pdr_timePdr','end_date'))
        def updateMUGGraph(tags,timeBtn,rsMethod,cmapName,lgd,style,axSP,previousFig,rs,date0,date1,t0,t1):
            ctx = dash.callback_context
            trigId = ctx.triggered[0]['prop_id'].split('.')[0]
            # to ensure that action on graphs only without computation do not
            # trigger computing the dataframe again
            triggerList=['dd_tag','pdr_timeBtn','dd_resampleMethod']
            if not timeBtn or trigId in [self.baseId+k for k in triggerList] :
                timeRange = [date0+' '+t0,date1+' '+t1]
                fig  = self.cfg.plotMultiUnitGraph(timeRange,listTags=tags,rs=rs,applyMethod=rsMethod)
            else :fig = go.Figure(previousFig)
            tagMapping = {t:self.cfg.getUnitofTag(t) for t in tags}
            fig.layout = self.utils.getLayoutMultiUnit(axisSpace=axSP,dictGroups=tagMapping)[0].layout
            fig = self.updateLayoutMultiUnitGraph(fig)
            try :
                fig = self.utils.legendPersistant(previousFig,fig)
            except:print('skip and update for next graph')
            fig = self.updateLegend(fig,lgd)
            return fig

        @self.app.callback(
                Output(self.baseId + 'dl','data'),
                Input(self.baseId + 'btn_export', 'n_clicks'),
                State(self.baseId + 'graph','figure'),
                prevent_initial_call=True
                )
        def exportClickMUG(btn,fig):
            df,filename =  self.utils.exportDataOnClick(fig)
            return dcc.send_data_frame(df.to_csv, filename+'.csv')

# ==============================================================================
#                              REAL TIME
# ==============================================================================
class RealTimeTagSelectorTab(TabSelectedTags):
    def __init__(self,app,connParameters,cfg,baseId='rts0_'):
        TabSelectedTags.__init__(self,None,cfg,app,baseId)
        self.tabname   = 'tag selector'
        self.cfg = cfg
        self.tabLayout = self._buildLayout()
        self._define_callbacks()

    def _buildLayout(self,widthG=85,defaultCat='',val_window=60*2,val_refresh=20,min_refresh=5,min_window=1):
        dicWidgets = {
                        'block_refresh':{'val_window':val_window,'val_refresh':val_refresh,
                                            'min_refresh':min_refresh,'min_window':min_window},
                        'btn_update':0,
                        'block_resample':{'val_res':'auto','val_method' : 'mean'},
                        'block_graphSettings':{'style':'lines+markers','type':'scatter','colmap':'jet'}
                        }
        basicWidgets = self.dccE.basicComponents(dicWidgets,self.baseId)
        specialWidgets = self.addWidgets({'dd_typeTags':defaultCat,'btn_legend':0},self.baseId)
        # reodrer widgets
        widgetLayout = basicWidgets + specialWidgets
        return self.dccE.buildGraphLayout(widgetLayout,self.baseId,widthG=widthG)

    def _define_callbacks(self):

        @self.app.callback(Output(self.baseId + 'interval', 'interval'),
                            Input(self.baseId + 'in_refreshTime','value'))
        def updateRefreshTime(refreshTime):return refreshTime*1000

        @self.app.callback(Output(self.baseId + 'btn_legend', 'children'),
                            Input(self.baseId + 'btn_legend','n_clicks'))
        def updateLgdBtn(legendType):return self.updateLegendBtnState(legendType)

        listInputsGraph = {
                        'interval':'n_intervals',
                        'btn_update':'n_clicks',
                        'dd_typeTags':'value',
                        'dd_resampleMethod':'value',
                        'dd_typeGraph':'value',
                        'dd_cmap':'value',
                        'btn_legend':'children',
                        'dd_style':'value',
                        }
        listStatesGraph = {
                            'graph':'figure',
                            'in_timeWindow':'value',
                            'in_timeRes':'value'
                            }
        @self.app.callback(
        Output(self.baseId + 'graph', 'figure'),
        [Input(self.baseId + k,v) for k,v in listInputsGraph.items()],
        [State(self.baseId + k,v) for k,v in listStatesGraph.items()],
        )
        def updateGraph(n,updateBtn,preSelGraph,rsMethod,typeGraph,colmap,lgd,style,previousFig,tw,rs):
            # self.utils.printListArgs(n,updateBtn,preSelGraph,rsMethod,typeGraph,colmap,lgd,style,rs)
            ctx = dash.callback_context
            trigId = ctx.triggered[0]['prop_id'].split('.')[0]
            # to ensure that action on graphs only without computation do not
            # trigger computing the dataframe again
            # ==============================================================
            #               CHANGE HERE YOUR CODE
            #           better to use decorators in the parent class
            # ==============================================================
            triggerList = [self.baseId+k for k in ['interval','dd_typeTags','btn_update','dd_resampleMethod','dd_typeGraph']]
            # print(trigId)
            if not updateBtn or trigId in triggerList :
                start = time.time()
                df    = self.cfg.realtimeDF(preSelGraph,timeWindow=tw*60,rs=rs,applyMethod=rsMethod)
                self.utils.printCTime(start)
                fig = self.utils.plotGraphType(df,typeGraph)
                unit = self.cfg.getUnitofTag(df.columns[0])
                nameGrandeur = self.cfg.utils.detectUnit(unit)
                fig.update_layout(yaxis_title = nameGrandeur + ' in ' + unit)
            else :fig = go.Figure(previousFig)
            fig = self.utils.updateStyleGraph(fig,style,colmap)
            try :
                fig = self.utils.legendPersistant(previousFig,fig)
            except:print('skip and update for next graph')
            fig = self.updateLegend(fig,lgd)
            return fig

class RealTimeTagMultiUnit(TabMultiUnits):
    def __init__(self,app,connParameters,cfg,baseId='rtmu0_'):
        TabMultiUnits.__init__(self,None,cfg,app,baseId)
        self.tabname   = 'graphe multi-échelles'
        self.cfg = cfg
        self.tabLayout = self._buildLayout()
        self._define_callbacks()

    def _buildLayout(self,widthG=85,defaultTags='',val_window=60*2,val_refresh=20,min_refresh=5,min_window=1):
        dicWidgets = {
                        'block_refresh':{'val_window':val_window,'val_refresh':val_refresh,
                                            'min_refresh':min_refresh,'min_window':min_window},
                        'btn_update':0,
                        'block_resample':{'val_res':'auto','val_method' : 'mean'},
                        'block_graphSettings':{'style':'lines+markers','type':'scatter','colmap':'jet'}
                        }
        basicWidgets = self.dccE.basicComponents(dicWidgets,self.baseId)
        specialWidgets = self.addWidgets({'dd_tag':defaultTags,'btn_legend':0,'in_axisSp':0.05},self.baseId)
        # reodrer widgets
        widgetLayout = basicWidgets + specialWidgets
        return self.dccE.buildGraphLayout(widgetLayout,self.baseId,widthG=widthG)

    def _define_callbacks(self):

        @self.app.callback(Output(self.baseId + 'interval', 'interval'),
                            Input(self.baseId + 'in_refreshTime','value'))
        def updateRefreshTime(refreshTime):return refreshTime*1000

        @self.app.callback(Output(self.baseId + 'btn_legend', 'children'),
                            Input(self.baseId + 'btn_legend','n_clicks'))
        def updateLgdBtn(legendType):return self.updateLegendBtnState(legendType)

        listInputsGraph = {
                        'interval':'n_intervals',
                        'btn_update':'n_clicks',
                        'dd_tag':'value',
                        'dd_resampleMethod':'value',
                        'dd_typeGraph':'value',
                        'dd_cmap':'value',
                        'btn_legend':'children',
                        'dd_style':'value',
                        'in_axisSp':'value',
                        }
        listStatesGraph = {
                            'graph':'figure',
                            'in_timeWindow':'value',
                            'in_timeRes':'value'
                            }
        @self.app.callback(
        Output(self.baseId + 'graph', 'figure'),
        [Input(self.baseId + k,v) for k,v in listInputsGraph.items()],
        [State(self.baseId + k,v) for k,v in listStatesGraph.items()],
        )
        def updateGraphRT_MUG(n,updateBtn,tags,rsMethod,typeGraph,colmap,lgd,style,axSP,previousFig,tw,rs):
            # self.utils.printListArgs(n,updateBtn,tags,rsMethod,typeGraph,colmap,lgd,style,axSP,fig,tw,rs)
            ctx = dash.callback_context
            trigId = ctx.triggered[0]['prop_id'].split('.')[0]
            # ==============================================================
            triggerList = ['interval','dd_tag','btn_update','dd_resampleMethod','dd_typeGraph']
            if not updateBtn or trigId in [self.baseId+k for k in triggerList]:
                start = time.time()
                df    = self.cfg.realtimeTagsDF(tags,timeWindow=tw*60,rs=rs,applyMethod=rsMethod)
                self.utils.printCTime(start)
                tagMapping = {t:self.cfg.getUnitofTag(t) for t in tags}
                fig = self.utils.multiUnitGraph(df,tagMapping)
            else : fig = go.Figure(previousFig)
            fig.layout = self.utils.getLayoutMultiUnit(axisSpace=axSP,dictGroups=tagMapping)[0].layout
            fig = self.updateLayoutMultiUnitGraph(fig)
            try :
                fig = self.utils.legendPersistant(previousFig,fig)
            except:print('skip and update for next graph')
            fig = self.updateLegend(fig,lgd)
            return fig


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
            print(marks)
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
