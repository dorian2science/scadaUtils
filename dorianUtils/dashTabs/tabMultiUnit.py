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

class MultiUnitTab():
    ''' this tab can only be built with templateDashTagsUnit and ConfigDashTagUnitTimestamp instances
        from templateDashD and configFilesD '''

    def __init__(self,cfgtutu,dtu):
        self.dtu    = dtu
        self.cfgtu  = cfgtutu
        self.utils  = Utils()
        self.dccE   = DccExtended()

    def mut_pdr_cached(self,baseId,widthG=80,heightGraph=900):
        listWidgets = ['pdr_time','in_timeRes','dd_cmap','btn_legend',
                        'btn_export','btn_style','in_axisSp','dd_Tag']

        MUG_html = self.dtu.buildLayout(listWidgets,baseId,widthG=widthG,nbCaches=1,nbGraphs=1)
        listIds  = self.dtu.dccE.parseLayoutIds(MUG_html)
        dictOpts = self.dtu.autoDictOptions(listIds)

    # ==========================================================================
    #                           BUTTONS CALLBACKS
    # ==========================================================================

        @self.dtu.app.callback(Output(baseId + 'btn_legend', 'children'),Input(baseId + 'btn_legend','n_clicks'))
        def updateLgdBtn(legendType):return self.dtu.changeLegendBtnState(legendType)

        @self.dtu.app.callback(Output(baseId + 'btn_style', 'children'),Input(baseId + 'btn_style','n_clicks'))
        def updateStyleBtn(styleSel):return self.dtu.changeStyleBtnState(styleSel)

    # ==========================================================================
    #                           COMPUTE AND GRAPHICS CALLBACKS
    # ==========================================================================

        @self.dtu.app.callback(
            Output(baseId + 'fileInCache1','children'),
            Input(baseId + 'pdr_timeBtn','n_clicks'),
            State(baseId + 'dd_Tag','value'),State(baseId + 'in_timeRes','value'),
            State(baseId + 'pdr_timePdr','start_date'),State(baseId + 'pdr_timePdr','end_date'),
            State(baseId + 'pdr_timeStart','value'),State(baseId + 'pdr_timeEnd','value'))
        def computeDataFrame(btnUpdate,tags,step,date0,date1,t0,t1):
            startTime   = date0 + ' ' + t0
            endTime     = date1 + ' ' + t1
            df          = self.cfgtu.loadDFTimeRange([startTime,endTime],'',self.dtu.skipEveryHours)
            print('=======================================')
            print('dataframe reading finished')
            print('=======================================')
            df = self.dtu.preparePivotedData(df,tags,step)
            return df.to_json(date_format='iso', orient='split')

        listInputsGraph = [baseId+l for l in ['fileInCache1','dd_cmap','btn_legend',
                                            'btn_style','dd_cmap','in_axisSp']]
        @self.dtu.app.callback(
        Output(baseId + 'graph1', 'figure'),
        [Input(k,v) for k,v in {key: dictOpts[key] for key in listInputsGraph}.items()])
        def updateMUGGraph(dfjson,cmapName,legendType,styleSel,incSpace):
            df      = pd.read_json(dfjson, orient='split')
            names   = self.cfgtu.getUnitsOfpivotedDF(df,True)
            fig     = self.utils.multiYAxis(df,mapName=cmapName,inc=incSpace,names=names)
            fig     = self.dtu.updateLegend(df,fig,legendType,pivoted=True,breakLine=30,addUnit=True)
            fig     = self.dtu.updateStyleGraph(fig,styleSel)
            return fig

  # ==========================================================================
  #                           EXPORT CALLBACKS
  # ==========================================================================
        listStatesExport = [baseId+l for l in ['fileInCache1','graph1','dd_Tag']]
        @self.dtu.app.callback(Output(baseId + 'btn_export','children'),Input(baseId + 'btn_export', 'n_clicks'),
        [State(k,v) for k,v in {key: dictOpts[key] for key in listStatesExport}.items()])
        def exportClick(btn,dfjson,fig,tags):
          if btn>1:
              df = pd.read_json(dfjson, orient='split')
              xlims = fig['layout']['xaxis']['range']
              print('xlims : ',xlims)
              self.dtu.exportDFOnClick(xlims,tags,unit,fig,df=df)
          return 'export Data'

        return MUG_html

    def mut_pdr(self,baseId,widthG=80,heightGraph=900):
        listWidgets = ['pdr_time','in_timeRes','dd_cmap','btn_legend',
                        'btn_export','btn_style','in_axisSp','dd_Tag']

        MUG_html = self.dtu.buildLayout(listWidgets,baseId,widthG=widthG,nbCaches=1,nbGraphs=1)
        listIds  = self.dtu.dccE.parseLayoutIds(MUG_html)
        dictOpts = self.dtu.dccE.autoDictOptions(listIds)

    # ==========================================================================
    #                           BUTTONS CALLBACKS
    # ==========================================================================

        @self.dtu.app.callback(Output(baseId + 'btn_legend', 'children'),Input(baseId + 'btn_legend','n_clicks'))
        def updateLgdBtn(legendType):return self.dtu.changeLegendBtnState(legendType)

        @self.dtu.app.callback(Output(baseId + 'btn_style', 'children'),Input(baseId + 'btn_style','n_clicks'))
        def updateStyleBtn(styleSel):return self.dtu.changeStyleBtnState(styleSel)

    # ==========================================================================
    #                           COMPUTE AND GRAPHICS CALLBACKS
    # ==========================================================================
        listInputsGraph = [baseId+l for l in ['dd_Tag','in_timeRes','dd_cmap','btn_legend',
                                            'btn_style','in_axisSp']]
        @self.dtu.app.callback(
        Output(baseId + 'graph1', 'figure'),
        [Input(k,v) for k,v in {key: dictOpts[key] for key in listInputsGraph}.items()],
        Input(baseId + 'pdr_timeBtn','n_clicks'),
        State(baseId + 'pdr_timePdr','start_date'),State(baseId + 'pdr_timePdr','end_date'),
        State(baseId + 'pdr_timeStart','value'),State(baseId + 'pdr_timeEnd','value'))
        def updateMUGGraph(tags,step,cmapName,legendType,styleSel,incSpace,btnUpdate,date0,date1,t0,t1):
            df      = self.cfgtu.loadDFTimeRange([date0+' '+t0,date1+' '+t1],'',self.dtu.skipEveryHours)
            print([date0+' '+t0,date1+' '+t1])
            df      = self.dtu.preparePivotedData(df,tags,step)
            names   = self.cfgtu.getUnitsOfpivotedDF(df,True)
            fig     = self.utils.multiYAxis(df,mapName=cmapName,inc=incSpace,names=names)
            fig     = self.dtu.updateLegend(df,fig,legendType,pivoted=True,breakLine=30,addUnit=True)
            fig     = self.dtu.updateStyleGraph(fig,styleSel)
            return fig
  # ==========================================================================
  #                           EXPORT CALLBACKS
  # ==========================================================================
        listStatesExport = [baseId+l for l in ['graph1','dd_Tag','in_timeRes']]
        @self.dtu.app.callback(Output(baseId + 'btn_export','children'),
        Input(baseId + 'btn_export', 'n_clicks'),
        [State(k,v) for k,v in {key: dictOpts[key] for key in listStatesExport}.items()],
        State(baseId + 'pdr_timePdr','start_date'),State(baseId + 'pdr_timePdr','end_date'),
        State(baseId + 'pdr_timeStart','value'),State(baseId + 'pdr_timeEnd','value'))
        def exportClick(btn,fig,tags,step,date0,date1,t0,t1):
            if btn > 0:
                df    = self.cfgtu.loadDFTimeRange([date0+' '+t0,date1+' '+t1],'',self.dtu.skipEveryHours)
                df    = self.dtu.preparePivotedData(df,tags,step)
                xlims = fig['layout']['xaxis']['range']
                self.dtu.exportDFOnClick(df,xlims)
            return 'export Data'

        return MUG_html

    def mut_f(self,baseId,widthG=80,heightGraph=700):
        listWidgets = ['dd_listFiles','in_timeRes','dd_cmap','btn_legend',
                        'btn_export','btn_style','in_axisSp','dd_Tag']
        MUGlayout=self.dtu.buildLayout(listWidgets,baseId,widthG=widthG)

        dictOptsGraph = {k : 'value' for k in listWidgets}
        dictOptsGraph['btn_legend'] = 'n_clicks'
        dictOptsGraph['btn_style'] = 'n_clicks'
        del dictOptsGraph['btn_export']

        @self.dtu.app.callback(Output(baseId + 'btn_legend', 'children'),Input(baseId + 'btn_legend','n_clicks'))
        def updateLgdBtn(legendType):return self.dtu.changeLegendBtnState(legendType)

        @self.dtu.app.callback(Output(baseId + 'btn_style', 'children'),Input(baseId + 'btn_style','n_clicks'))
        def updateStyleBtn(styleSel):return self.dtu.changeStyleBtnState(styleSel)

        @self.dtu.app.callback(Output(baseId + 'btn_export','children'),Input(baseId + 'btn_export', 'n_clicks'),
            State(baseId + 'graph1','figure'),State(baseId + 'dd_listFiles','value'),State(baseId + 'dd_Tag','value'))
        def exportClick(btn,fig,filename,tags):
            changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
            if 'btn_export' in changed_id:
                df = self.dtu.preparePivotedData(filename,tags)
                self.dtu.exportDFOnClick(df,fig,folder=self.cfgtu.folderExport,baseName='smallPower')
            return 'export Data'

        @self.dtu.app.callback(
        Output(baseId + 'graph1', 'figure'),
        [Input(baseId+k,v) for k,v in dictOptsGraph.items()])
        def updateGraph(filename,step,cmapName,legendType,styleSel,incSpace,tags):
            df      = self.cfgtu.loadFile(filename)
            df      = self.dtu.preparePivotedData(df,tags,rs=step)
            names   = self.cfgtu.getUnitsOfpivotedDF(df,True)
            fig     = self.cfgtu.utils.multiYAxis(df,mapName=cmapName,inc=incSpace,names=names)
            fig     = self.dtu.updateLegend(df,fig,legendType,pivoted=True,breakLine=30,addUnit=True)
            fig     = self.dtu.updateStyleGraph(fig,styleSel)
            return fig
        return MUGlayout

    def mut_pdr_resample(self,baseId,defaultTag=[],widthG=80,heightGraph=900):
        dicWidgets = {'pdr_time' : None,'in_timeRes':str(60*10)+'s','dd_resampleMethod':'mean','dd_cmap':'jet','btn_legend':0,
                        'btn_export':0,'dd_style':'lines+markers','in_axisSp':0.1,'dd_Tag':defaultTag}

        MUG_htmlVdic = self.dtu.buildLayout(dicWidgets,baseId,widthG=widthG,nbCaches=1,nbGraphs=1)
        listIds  = self.dccE.parseLayoutIds(MUG_htmlVdic)
        dictOpts = self.dccE.autoDictOptions(listIds)

    # ==========================================================================
    #                           BUTTONS CALLBACKS
    # ==========================================================================

        @self.dtu.app.callback(Output(baseId + 'btn_legend', 'children'),Input(baseId + 'btn_legend','n_clicks'))
        def updateLgdBtn(legendType):return self.dtu.changeLegendBtnState(legendType)

    # ==========================================================================
    #                           COMPUTE AND GRAPHICS CALLBACKS
    # ==========================================================================
        listInputsGraph = {
                        'dd_Tag':'value',
                        'pdr_timeBtn':'n_clicks',
                        'dd_resampleMethod':'value',
                        'dd_cmap':'value',
                        'btn_legend':'children',
                        'dd_style':'value'
                        ,'in_axisSp':'value'}
        listStatesGraph = {
                            'graph1':'figure',
                            'in_timeRes' : 'value',
                            'pdr_timeStart' : 'value',
                            'pdr_timeEnd':'value',
                            'pdr_timePdr':'start_date',
                            }

        @self.dtu.app.callback(
            Output(baseId + 'graph1', 'figure'),
            Output(baseId + 'pdr_timeBtn', 'n_clicks'),
            [Input(baseId + k,v) for k,v in listInputsGraph.items()],
            [State(baseId + k,v) for k,v in listStatesGraph.items()],
            State(baseId+'pdr_timePdr','end_date'))
        def updateMUGGraph(tags,timeBtn,rsMethod,cmapName,lgd,style,axSP,fig,rs,date0,date1,t0,t1):
            ctx = dash.callback_context
            trigId = ctx.triggered[0]['prop_id'].split('.')[0]
            # to ensure that action on graphs only without computation do not
            # trigger computing the dataframe again
            if not timeBtn or trigId in [baseId+k for k in ['dd_Tag','pdr_timeBtn','dd_resampleMethod','in_axisSp']] :
                if not timeBtn : timeBtn=1 # to initialize the first graph
                timeRange = [date0+' '+t0,date1+' '+t1]
                start     = time.time()
                df      = self.cfgtu.DF_loadTimeRangeTags(timeRange,tags,rs=rs,applyMethod=rsMethod)
                names   = self.cfgtu.getUnitsOfpivotedDF(df,True)
                fig     = self.utils.multiYAxis(df,mapName=cmapName,inc=axSP,names=names)
                timeBtn = max(timeBtn,1) # to close the initialisation
                print(time.time()-start, 's')
            else :fig = go.Figure(fig)
            fig = self.dtu.updateStyleGraph(fig,style,cmapName)
            fig = self.dtu.updateLegend(fig,lgd)
            return fig,timeBtn
  # ==========================================================================
  #                           EXPORT CALLBACKS
  # ==========================================================================
        listStatesExport = [baseId+l for l in ['graph1','dd_Tag','in_timeRes']]
        @self.dtu.app.callback(Output(baseId + 'btn_export','children'),
        Input(baseId + 'btn_export', 'n_clicks'),
        [State(k,v) for k,v in {key: dictOpts[key] for key in listStatesExport}.items()],
        State(baseId + 'pdr_timePdr','start_date'),State(baseId + 'pdr_timePdr','end_date'),
        State(baseId + 'pdr_timeStart','value'),State(baseId + 'pdr_timeEnd','value'))
        def exportClick(btn,fig,tags,step,date0,date1,t0,t1):
            if btn > 0:
                df    = self.cfgtu.loadDFTimeRange([date0+' '+t0,date1+' '+t1],'',self.dtu.skipEveryHours)
                df    = self.dtu.preparePivotedData(df,tags,step)
                xlims = fig['layout']['xaxis']['range']
                self.dtu.exportDFOnClick(df,xlims)
            return 'export Data'

        return MUG_htmlVdic

    def mut_realTime(self,baseId,defaultTag=[],widthG=80,heightGraph=900):
        dicWidgets = {'pdr_time' : None,'in_timeRes':str(10)+'s','dd_resampleMethod':'mean','dd_cmap':'jet','btn_legend':0,
                        'btn_export':0,'dd_style':'lines+markers','in_axisSp':0.1,'dd_Tag':defaultTag}

        MUG_htmlVdic = self.dtu.buildLayout(dicWidgets,baseId,widthG=widthG,nbCaches=1,nbGraphs=1)
        listIds  = self.dccE.parseLayoutIds(MUG_htmlVdic)
        dictOpts = self.dccE.autoDictOptions(listIds)

    # ==========================================================================
    #                           BUTTONS CALLBACKS
    # ==========================================================================

        @self.dtu.app.callback(Output(baseId + 'btn_legend', 'children'),Input(baseId + 'btn_legend','n_clicks'))
        def updateLgdBtn(legendType):return self.dtu.changeLegendBtnState(legendType)

    # ==========================================================================
    #                           COMPUTE AND GRAPHICS CALLBACKS
    # ==========================================================================
        listInputsGraph = {
                        'dd_Tag':'value',
                        'pdr_timeBtn':'n_clicks',
                        'dd_resampleMethod':'value',
                        'dd_cmap':'value',
                        'btn_legend':'children',
                        'dd_style':'value'
                        ,'in_axisSp':'value'}
        listStatesGraph = {
                            'graph1':'figure',
                            'in_timeRes' : 'value',
                            'pdr_timeStart' : 'value',
                            'pdr_timeEnd':'value',
                            'pdr_timePdr':'start_date',
                            }

        @self.dtu.app.callback(
            Output(baseId + 'graph1', 'figure'),
            Output(baseId + 'pdr_timeBtn', 'n_clicks'),
            [Input(baseId + k,v) for k,v in listInputsGraph.items()],
            [State(baseId + k,v) for k,v in listStatesGraph.items()],
            State(baseId+'pdr_timePdr','end_date'))
        def updateMUGGraph(tags,timeBtn,rsMethod,cmapName,lgd,style,axSP,fig,rs,date0,date1,t0,t1):
            ctx = dash.callback_context
            trigId = ctx.triggered[0]['prop_id'].split('.')[0]
            # to ensure that action on graphs only without computation do not
            # trigger computing the dataframe again
            if not timeBtn or trigId in [baseId+k for k in ['dd_Tag','pdr_timeBtn','dd_resampleMethod','in_axisSp']] :
                if not timeBtn : timeBtn=1 # to initialize the first graph
                timeRange = [date0+' '+t0,date1+' '+t1]
                start     = time.time()
                df      = self.cfgtu.DF_loadTimeRangeTags(timeRange,tags,rs=rs,applyMethod=rsMethod)
                names   = self.cfgtu.getUnitsOfpivotedDF(df,True)
                fig     = self.utils.multiYAxis(df,mapName=cmapName,inc=axSP,names=names)
                timeBtn = max(timeBtn,1) # to close the initialisation
                print(time.time()-start, 's')
            else :fig = go.Figure(fig)
            fig = self.dtu.updateStyleGraph(fig,style,cmapName)
            fig = self.dtu.updateLegend(fig,lgd)
            return fig,timeBtn
    # ==========================================================================
    #                           EXPORT CALLBACKS
    # ==========================================================================
        listStatesExport = [baseId+l for l in ['graph1','dd_Tag','in_timeRes']]
        @self.dtu.app.callback(Output(baseId + 'btn_export','children'),
        Input(baseId + 'btn_export', 'n_clicks'),
        [State(k,v) for k,v in {key: dictOpts[key] for key in listStatesExport}.items()],
        State(baseId + 'pdr_timePdr','start_date'),State(baseId + 'pdr_timePdr','end_date'),
        State(baseId + 'pdr_timeStart','value'),State(baseId + 'pdr_timeEnd','value'))
        def exportClick(btn,fig,tags,step,date0,date1,t0,t1):
            if btn > 0:
                df    = self.cfgtu.loadDFTimeRange([date0+' '+t0,date1+' '+t1],'',self.dtu.skipEveryHours)
                df    = self.dtu.preparePivotedData(df,tags,step)
                xlims = fig['layout']['xaxis']['range']
                self.dtu.exportDFOnClick(df,xlims)
            return 'export Data'

        return MUG_htmlVdic
