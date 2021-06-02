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

class UnitSelectorTab():
    ''' this tab can only be built with templateDashTagsUnit and ConfigDashTagUnitTimestamp instances
        from templateDashD and configFilesD '''
    def __init__(self,cfgtu,dtu):
        self.dtu = dtu
        self.cfgtu = cfgtu
        self.utils = Utils()
        self.dccE = DccExtended()
    # ==========================================================================
    #                           SHARED FUNCTIONS CALLBACKS
    # ==========================================================================
    def updateTUGraph(self,df,tagPat,unit,step,cmapName,legendType,figname=None,breakLine=None):
        ## FILTER the dataframe
        df = self.cfgtu.getDFTagsTU(df,tagPat,unit).iloc[::step]
        ## build/PLOT the graph
        fig = self.dtu.drawGraph(df,cmapName=cmapName)
        ## build the LEGEND with the toogle button
        fig = self.dtu.updateLegend(df,fig,legendType,pivoted=False)
        ## build the TITLE
        nameGrandeur = self.cfgtu.utils.detectUnit(unit)
        # if not isinstance(figname,str):figname = self.cfgtu.utils.makeFigureName(filename,'Small',[unit,tagPat])
        ## build the Y-AXIS name
        # fig.update_layout(yaxis_title = nameGrandeur + ' in ' + unit,title=figname)
        fig.update_layout(yaxis_title = nameGrandeur + ' in ' + unit)
        return fig

    def updateTUGraph_rs(self,df,unit,cmapName,legendType,figname=None,breakLine=None):
        fig = self.dtu.drawGraph(df,cmapName=cmapName)
        fig = self.dtu.updateLegend(df,fig,legendType,pivoted=False)
        nameGrandeur = self.cfgtu.utils.detectUnit(unit)
        fig.update_layout(yaxis_title = nameGrandeur + ' in ' + unit)
        # if not isinstance(figname,str):figname = self.cfgtu.utils.makeFigureName(filename,'Small',[unit,tagPat])
        ## build the Y-AXIS name
        # fig.update_layout(yaxis_title = nameGrandeur + ' in ' + unit,title=figname)
        return fig

    def computeDataFrame(self,timeRange,tagPat,unit,rs,rsMethod):
        start     = time.time()
        listTags  = self.cfgtu.getTagsTU(tagPat,unit)
        if not rsMethod :
            df = self.cfgtu.DF_loadTimeRangeTags(timeRange,listTags,rs='raw')
            df=df.iloc[::rs,:]
            names=list(df.tag.unique())
        else:
            df = self.cfgtu.DF_loadTimeRangeTags(timeRange,listTags,rs=rs,applyMethod=rsMethod)
            names     = self.cfgtu.getUnitsOfpivotedDF(df,True)
        print(time.time()-start, 's')
        return df,names
    # ==========================================================================
    #                           with unit and tag INPUT  FUNCTIONS
    # ==========================================================================
    def tagUnit_in_pdr_cached(self,baseId,widthG=80,heightGraph=900):
        listWidgets = ['pdr_time','in_step','dd_Units','in_patternTag','btn_legend',
                        'btn_style','btn_export','dd_cmap']
        TUinPDR_html = self.dtu.buildLayout(listWidgets,baseId,widthG=widthG,nbCaches=1,nbGraphs=1)
        listIds = self.dccE.parseLayoutIds(TUinPDR_html)
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
            State(baseId + 'pdr_timePdr','start_date'),State(baseId + 'pdr_timePdr','end_date'),
            State(baseId + 'pdr_timeStart','value'),State(baseId + 'pdr_timeEnd','value'))
        def computeDataFrame(btnUpdate,date0,date1,t0,t1):
            return self.dtu.computeDataFrame(date0,date1,t0,t1)

        listInputsGraph = [baseId+l for l in ['fileInCache1','dd_Units','in_patternTag','dd_cmap','btn_legend','btn_style','in_step']]
        @self.dtu.app.callback(Output(baseId + 'graph1', 'figure'),
        [Input(k,v) for k,v in {key: dictOpts[key] for key in listInputsGraph}.items()])
        def updateGraphIn(dfjson,unit,tagPat,cmapName,legendType,styleSel,step):
            df = pd.read_json(dfjson, orient='split')
            fig = self.updateTUGraph(df,tagPat,unit,step,cmapName,legendType,breakLine=None)
            fig = self.dtu.updateStyleGraph(fig,styleSel)
            return fig

        # ==========================================================================
        #                           EXPORT CALLBACKS
        # ==========================================================================
        listStatesExport = [baseId+l for l in ['fileInCache1','graph1','in_patternTag','dd_Units']]
        @self.dtu.app.callback(Output(baseId + 'btn_export','children'),Input(baseId + 'btn_export', 'n_clicks'),
        [State(k,v) for k,v in {key: dictOpts[key] for key in listStatesExport}.items()])
        def exportClick(btn,dfjson,fig,tagPattern,unit):
            if btn>1:
                df = pd.read_json(dfjson, orient='split')
                xlims = fig['layout']['xaxis']['range']
                print('xlims : ',xlims)
                self.dtu.exportDFOnClick(xlims,tagPattern,unit,fig,df=df)
            return 'export Data'

        return TUinPDR_html

    def tagUnit_in_pdr(self,baseId,unitDefault='W',patternDefault='',widthG=80,heightGraph=900):
        dicWidgets = {'pdr_time':None,'in_step':300,'dd_Units':unitDefault,'in_patternTag':patternDefault,
                        'dd_typeGraph':0,'dd_style':'lines+markers',
                        'btn_legend':0,'btn_export':0,'dd_cmap':'jet'}
        TUinPDR_html = self.dtu.buildLayout(dicWidgets,baseId,widthG=widthG,nbCaches=1,nbGraphs=1)
        listIds = self.dccE.parseLayoutIds(TUinPDR_html)
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
                        'pdr_timeBtn':'n_clicks',
                        'dd_typeGraph':'value',
                        'dd_cmap':'value',
                        'btn_legend':'children',
                        'dd_style':'value'
                        }
        listStatesGraph = {
                            'dd_Units':'value',
                            'in_patternTag':'value',
                            'in_step' : 'value',
                            'graph1':'figure',
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
        def updateGraph(timeBtn,typeGraph,cmap,lgd,style,unit,tagPat,skip,fig,date0,date1,t0,t1):
            ctx = dash.callback_context
            trigId = ctx.triggered[0]['prop_id'].split('.')[0]
            # to ensure that action on graphs only without computation do not
            # trigger computing the dataframe again
            if not timeBtn or trigId in [baseId+k for k in ['pdr_timeBtn']] :
                if not timeBtn : timeBtn=1 # to initialize the first graph
                timeRange = [date0+' '+t0,date1+' '+t1]
                df,names  = self.computeDataFrame(timeRange,tagPat,unit,skip,rsMethod=None)
                fig       = self.dtu.drawGraph(df,typeGraph)
                nameGrandeur = self.cfgtu.utils.detectUnit(unit)
                fig.update_layout(yaxis_title = nameGrandeur + ' in ' + unit)
                timeBtn = max(timeBtn,1) # to close the initialisation
            else :fig = go.Figure(fig)
            fig = self.dtu.updateStyleGraph(fig,style,cmap)
            fig = self.dtu.updateLegend(fig,lgd)
            return fig,timeBtn

        # ==========================================================================
        #                           EXPORT CALLBACKS
        # ==========================================================================
        listStatesExport = [baseId+l for l in ['graph1','in_patternTag','dd_Units']]
        @self.dtu.app.callback(Output(baseId + 'btn_export','children'),
        Input(baseId + 'btn_export', 'n_clicks'),
        [State(k,v) for k,v in {key: dictOpts[key] for key in listStatesExport}.items()],
        State(baseId + 'pdr_timePdr','start_date'),State(baseId + 'pdr_timePdr','end_date'),
        State(baseId + 'pdr_timeStart','value'),State(baseId + 'pdr_timeEnd','value'))
        def exportClick(btn,fig,tagPattern,unit,date0,date1,t0,t1):
            if btn>1:
                df = self.dtu.computeDataFrame(date0,date1,t0,t1,toJson=False)
                xlims = fig['layout']['xaxis']['range']
                print('xlims : ',xlims)
                self.dtu.exportDFOnClick(xlims,tagPattern,unit,fig,df=df)
            return 'export Data'

        return TUinPDR_html

    def tagUnit_in_f(self,baseId,widthG=80,heightGraph=900):
        listWidgets = ['dd_listFiles','dd_Units','in_patternTag','btn_legend',
                        'btn_style','btn_export','in_step','dd_cmap']

        dictOptsGraph = {k : 'value' for k in listWidgets}
        dictOptsGraph['btn_legend'] = 'n_clicks'
        dictOptsGraph['btn_style'] = 'n_clicks'
        del dictOptsGraph['btn_export']

        TUinGhtml=self.dtu.buildLayout(listWidgets,baseId,widthG=widthG)

        @self.dtu.app.callback(Output(baseId + 'btn_legend', 'children'),Input(baseId + 'btn_legend','n_clicks'))
        def updateLgdBtn(legendType):return self.dtu.changeLegendBtnState(legendType)

        @self.dtu.app.callback(Output(baseId + 'btn_style', 'children'),Input(baseId + 'btn_style','n_clicks'))
        def updateStyleBtn(styleSel):return self.dtu.changeStyleBtnState(styleSel)

        @self.dtu.app.callback(Output(baseId + 'graph1', 'figure'),
        [Input(baseId+k,v) for k,v in dictOptsGraph.items()])
        def updateGraphInput(filename,unit,tagPat,legendType,styleSel,step,cmapName):
            df  = self.cfgtu.loadFile(filename)
            fig = self.updateTUGraph(df,tagPat,unit,step,cmapName,legendType,breakLine=None)
            fig = self.dtu.updateStyleGraph(fig,styleSel)
            return fig

            @self.dtu.app.callback(Output(baseId + 'btn_export','children'),Input(baseId + 'btn_export', 'n_clicks'),
                State(baseId + 'graph1','figure'),State(baseId + 'dd_listFiles','value'),
                State(baseId + 'in_patternTag','value'),State(baseId + 'dd_Units','value'))
            def exportClick(btn,fig,filename,tagPattern,unit):
                changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
                if 'btn_export' in changed_id:
                    df = self.dtu.cfgtu.loadFile(filename)
                    df = self.dtu.cfgtu.getDFTagsTU(df,tagPattern,unit,printRes=0)
                    df = self.dtu.cfgtu.pivotDF(df)
                    self.dtu.exportDFOnClick(df,fig,folder=self.dtu.cfgtu.folderExport,baseName='smallPower')
                return 'export Data'
        return TUinGhtml

    def tagUnit_in_pdr_resample(self,baseId,unitDefault='W',patternDefault='',widthG=80,heightGraph=900):
        dicWidgets = {'pdr_time' : None,'in_timeRes':str(60*10)+'s','dd_resampleMethod':'mean',
                        'dd_Units':unitDefault,'in_patternTag':patternDefault,'dd_typeGraph':0,'dd_style':'lines+markers',
                        'btn_legend':0,'btn_export':0,'dd_cmap':'jet'}

        TUinPDRrs_html = self.dtu.buildLayout(dicWidgets,baseId,widthG=widthG,nbCaches=1,nbGraphs=1)
        listIds = self.dccE.parseLayoutIds(TUinPDRrs_html)
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
        def updateGraph(unit,tagPat,timeBtn,rsMethod,typeGraph,cmap,lgd,style,fig,rs,date0,date1,t0,t1):
            ctx = dash.callback_context
            trigId = ctx.triggered[0]['prop_id'].split('.')[0]
            # to ensure that action on graphs only without computation do not
            # trigger computing the dataframe again
            if not timeBtn or trigId in [baseId+k for k in ['pdr_timeBtn']] :
                if not timeBtn : timeBtn=1 # to initialize the first graph
                start     = time.time()
                timeRange = [date0+' '+t0,date1+' '+t1]
                listTags  = self.cfgtu.getTagsTU(tagPat,unit)
                df        = self.cfgtu.DF_loadTimeRangeTags(timeRange,listTags,rs=rs,applyMethod=rsMethod)
                # names     = self.cfgtu.getUnitsOfpivotedDF(df,True)
                print(time.time()-start, 's')
                fig     = self.dtu.drawGraph(df,typeGraph)
                nameGrandeur = self.cfgtu.utils.detectUnit(unit)
                fig.update_layout(yaxis_title = nameGrandeur + ' in ' + unit)
                timeBtn = max(timeBtn,1) # to close the initialisation
            else :fig = go.Figure(fig)
            fig = self.dtu.updateStyleGraph(fig,style,cmap)
            fig = self.dtu.updateLegend(fig,lgd)
            return fig,timeBtn
        # ==========================================================================
        #                           EXPORT CALLBACK
        # ==========================================================================
        listStatesExport = [baseId+l for l in ['graph1','in_patternTag','dd_Units']]
        @self.dtu.app.callback(Output(baseId + 'btn_export','children'),
        Input(baseId + 'btn_export', 'n_clicks'),
        [State(k,v) for k,v in {key: dictOpts[key] for key in listStatesExport}.items()],
        State(baseId + 'pdr_timePdr','start_date'),State(baseId + 'pdr_timePdr','end_date'),
        State(baseId + 'pdr_timeStart','value'),State(baseId + 'pdr_timeEnd','value'))
        def exportClick(btn,fig,tagPattern,unit,date0,date1,t0,t1):
            if btn>1:
                df = self.dtu.computeDataFrame(date0,date1,t0,t1,toJson=False)
                xlims = fig['layout']['xaxis']['range']
                print('xlims : ',xlims)
                self.dtu.exportDFOnClick(xlims,tagPattern,unit,fig,df=df)
            return 'export Data'

        return TUinPDRrs_html

    # ==========================================================================
    #                           with preselected graphs
    # ==========================================================================
    def tagUnit_preSelected_pdr_cached(self,baseId,widthG=80,heightGraph=900):
        listWidgets = ['pdr_time','dd_typeTags','btn_legend',
                        'btn_style','btn_export','in_step','dd_cmap',]

        TUddPSG_html=self.dtu.buildLayout(listWidgets,baseId,widthG=widthG,nbCaches=1)
        listIds = self.dccE.parseLayoutIds(TUddPSG_html)
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
            State(baseId + 'pdr_timePdr','start_date'),State(baseId + 'pdr_timePdr','end_date'),
            State(baseId + 'pdr_timeStart','value'),State(baseId + 'pdr_timeEnd','value'))
        def computeDataFrame(btnUpdate,date0,date1,t0,t1):
            return self.dtu.computeDataFrame(date0,date1,t0,t1)

        listInputsGraph = [baseId+l for l in ['fileInCache1','dd_typeTags','dd_cmap','btn_legend','btn_style','in_step']]
        @self.dtu.app.callback(Output(baseId + 'graph1', 'figure'),
        [Input(k,v) for k,v in {key: dictOpts[key] for key in listInputsGraph}.items()])
        def updateGraphDD(dfjson,keyDD,cmapName,legendType,styleSel,step):
            df = pd.read_json(dfjson, orient='split')
            unit    = self.cfgtu.usefulTags.loc[keyDD,'Unit']
            tagPat  = self.cfgtu.usefulTags.loc[keyDD,'Pattern']
            fig = self.updateTUGraph(df,tagPat,unit,step,cmapName,legendType,breakLine=None)
            fig = self.dtu.updateStyleGraph(fig,styleSel)
            return fig

        # ==========================================================================
        #                           EXPORT CALLBACKS
        # ==========================================================================
        listStatesExport = [baseId+l for l in ['fileInCache1','graph1','dd_typeTags']]
        @self.dtu.app.callback(Output(baseId + 'btn_export','children'),
        Input(baseId + 'btn_export', 'n_clicks'),
        [State(k,v) for k,v in {key: dictOpts[key] for key in listStatesExport}.items()])
        def exportClick(btn,df,fig,keyDD):
            if btn>1:
                df = pd.read_json(dfjson, orient='split')
                xlims = fig['layout']['xaxis']['range']
                print('xlims : ',xlims)
                unit    = self.cfgtu.usefulTags.loc[keyDD,'Unit']
                tagPat  = self.cfgtu.usefulTags.loc[keyDD,'Pattern']
                self.dtu.exportDFOnClick(xlims,tagPattern,unit,fig,df=df)
            return 'export Data'

        return TUddPSG_html

    def tagUnit_preSelected_pdr(self,baseId,widthG=80,heightGraph=900):
        dicWidgets = {'pdr_time' : None,'dd_typeTags':0,'in_step':20,
                        'btn_legend':0,'btn_style':0,'btn_export':0,'dd_cmap':'jet'}
        TUddPSG_html = self.dtu.buildLayout(dicWidgets,baseId,widthG=widthG,nbCaches=1,nbGraphs=1)
        listIds = self.dccE.parseLayoutIds(TUddPSG_html)
        dictOpts = self.dccE.autoDictOptions(listIds)

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
        listInputsGraph = [baseId+l for l in ['dd_typeTags','dd_cmap','btn_legend','btn_style','in_step']]
        @self.dtu.app.callback(Output(baseId + 'graph1', 'figure'),
        Input(baseId + 'pdr_timeBtn','n_clicks'),
        [Input(k,v) for k,v in {key: dictOpts[key] for key in listInputsGraph}.items()],
        State(baseId + 'pdr_timePdr','start_date'),State(baseId + 'pdr_timePdr','end_date'),
        State(baseId + 'pdr_timeStart','value'),State(baseId + 'pdr_timeEnd','value'))
        def updateGraphDD(btnUpdate,keyDD,cmapName,legendType,styleSel,step,date0,date1,t0,t1,):
            df = self.cfgtu.loadDFTimeRange([date0+' '+t0,date1+' '+t1],'',self.dtu.skipEveryHours)
            unit    = self.cfgtu.usefulTags.loc[keyDD,'Unit']
            tagPat  = self.cfgtu.usefulTags.loc[keyDD,'Pattern']
            print
            fig     = self.updateTUGraph(df,tagPat,unit,step,cmapName,legendType,breakLine=None)
            fig     = self.dtu.updateStyleGraph(fig,styleSel)
            return fig

        # ==========================================================================
        #                           EXPORT CALLBACKS
        # ==========================================================================
        listStatesExport = [baseId+l for l in ['graph1','dd_typeTags']]
        @self.dtu.app.callback(Output(baseId + 'btn_export','children'),
        Input(baseId + 'btn_export', 'n_clicks'),
        [State(k,v) for k,v in {key: dictOpts[key] for key in listStatesExport}.items()],
        State(baseId + 'pdr_timePdr','start_date'),State(baseId + 'pdr_timePdr','end_date'),
        State(baseId + 'pdr_timeStart','value'),State(baseId + 'pdr_timeEnd','value'))
        def exportClick(btn,fig,keyDD,date0,date1,t0,t1):
            if btn>1:
                df    = self.dtu.computeDataFrame(date0,date1,t0,t1,toJson=False)
                xlims = fig['layout']['xaxis']['range']
                print('xlims : ',xlims)
                unit    = self.cfgtu.usefulTags.loc[keyDD,'Unit']
                tagPat  = self.cfgtu.usefulTags.loc[keyDD,'Pattern']
                self.dtu.exportDFOnClick(xlims,tagPattern,unit,fig,df=df)
            return 'export Data'

        return TUddPSG_html

    def tagUnit_preSelected_f(self,baseId,widthG=80,heightGraph=900):
        listWidgets = ['dd_listFiles','dd_typeTags','btn_legend',
                        'btn_style','btn_export','in_step','dd_cmap']

        dictOptsGraph = {k : 'value' for k in listWidgets}
        dictOptsGraph['btn_legend'] = 'n_clicks'
        dictOptsGraph['btn_style'] = 'n_clicks'
        del dictOptsGraph['btn_export']

        TUinGhtml=self.dtu.buildLayout(listWidgets,baseId,widthG=widthG)

        @self.dtu.app.callback(Output(baseId + 'btn_legend', 'children'),Input(baseId + 'btn_legend','n_clicks'))
        def updateLgdBtn(legendType):return self.dtu.changeLegendBtnState(legendType)

        @self.dtu.app.callback(Output(baseId + 'btn_style', 'children'),Input(baseId + 'btn_style','n_clicks'))
        def updateStyleBtn(styleSel):return self.dtu.changeStyleBtnState(styleSel)

        @self.dtu.app.callback(Output(baseId + 'graph1', 'figure'),
        [Input(baseId+k,v) for k,v in dictOptsGraph.items()])
        def updateGraphInput(filename,keyDD,legendType,styleSel,step,cmapName):
            df  = self.cfgtu.loadFile(filename)
            unit    = self.cfgtu.usefulTags.loc[keyDD,'Unit']
            tagPat  = self.cfgtu.usefulTags.loc[keyDD,'Pattern']
            fig = self.updateTUGraph(df,tagPat,unit,step,cmapName,legendType,breakLine=None)
            fig = self.dtu.updateStyleGraph(fig,styleSel)
            return fig

            @self.dtu.app.callback(Output(baseId + 'btn_export','children'),Input(baseId + 'btn_export', 'n_clicks'),
                State(baseId + 'graph1','figure'),State(baseId + 'dd_listFiles','value'),
                State(baseId + 'dd_typeTags','value'))
            def exportClick(btn,fig,filename,tagPattern,unit):
                changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
                if 'btn_export' in changed_id:
                    df      = self.dtu.cfgtu.loadFile(filename)
                    unit    = self.cfgtu.usefulTags.loc[keyDD,'Unit']
                    tagPat  = self.cfgtu.usefulTags.loc[keyDD,'Pattern']
                    df = self.dtu.cfgtu.getDFTagsTU(df,tagPattern,unit,printRes=0)
                    df = self.dtu.cfgtu.pivotDF(df)
                    self.dtu.exportDFOnClick(df,fig,folder=self.dtu.cfgtu.folderExport,baseName='smallPower')
                return 'export Data'
        return TUinGhtml

    def tagUnit_preSelected_pdr_resample(self,baseId,widthG=80,heightGraph=900):
        dicWidgets = {'pdr_time' : None,'in_timeRes':str(60*10)+'s','dd_resampleMethod' : 'mean',
                        'dd_typeTags':0,'dd_typeGraph':0,'dd_style':'lines+markers',
                        'dd_cmap':'jet','btn_legend':0,'btn_export':0}
        TUinPDRrs_html = self.dtu.buildLayout(dicWidgets,baseId,widthG=widthG,nbCaches=1,nbGraphs=1)
        listIds = self.dccE.parseLayoutIds(TUinPDRrs_html)
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
                        'dd_typeTags':'value',
                        'pdr_timeBtn':'n_clicks',
                        'dd_resampleMethod':'value',
                        'dd_typeGraph':'value',
                        'dd_cmap':'value',
                        'btn_legend':'children',
                        'dd_style':'value'}
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
        def updateGraph(preSelGraph,timeBtn,rsMethod,typeGraph,colmap,lgd,style,fig,rs,date0,date1,t0,t1):
            ctx = dash.callback_context
            trigId = ctx.triggered[0]['prop_id'].split('.')[0]
            # to ensure that action on graphs only without computation do not
            # trigger computing the dataframe again
            if not timeBtn or trigId in [baseId+k for k in ['dd_typeTags','pdr_timeBtn','dd_resampleMethod','dd_typeGraph']] :
                if not timeBtn : timeBtn=1 # to initialize the first graph
                start       = time.time()
                print('here')
                timeRange   = [date0+' '+t0,date1+' '+t1]
                listTags    = self.cfgtu.getUsefulTags(preSelGraph)
                df          = self.cfgtu.DF_loadTimeRangeTags(timeRange,listTags,rs=rs,applyMethod=rsMethod)
                print(df)
                names       = self.cfgtu.getUnitsOfpivotedDF(df,True)
                self.utils.printCTime(start)
                fig     = self.dtu.drawGraph(df,typeGraph)
                # nameGrandeur = self.cfgtu.utils.detectUnit(unit)
                # fig.update_layout(yaxis_title = nameGrandeur + ' in ' + unit)
                # timeBtn = max(timeBtn,1) # to close the initialisation
            else :fig = go.Figure(fig)
            fig = self.dtu.updateStyleGraph(fig,style,colmap)
            fig = self.dtu.updateLegend(fig,lgd)
            return fig,timeBtn

        # ==========================================================================
        #                           EXPORT CALLBACK
        # ==========================================================================
        listStatesExport = [baseId+l for l in ['graph1','dd_typeTags','in_timeRes']]
        @self.dtu.app.callback(Output(baseId + 'btn_export','children'),
        Input(baseId + 'btn_export', 'n_clicks'),
        [State(k,v) for k,v in {key: dictOpts[key] for key in listStatesExport}.items()],
        State(baseId + 'pdr_timePdr','start_date'),State(baseId + 'pdr_timePdr','end_date'),
        State(baseId + 'pdr_timeStart','value'),State(baseId + 'pdr_timeEnd','value'))
        def exportClick(btn,fig,preSelGraph,rs,date0,date1,t0,t1):
            if btn>1:
                timeRange = [date0+' '+t0,date1+' '+t1]
                # # df = computeDataFrame(timeRange,preSelGraph,rs)
                # xlims = fig['layout']['xaxis']['range']
                # print('xlims : ',xlims)
                # self.dtu.exportDFOnClick(xlims,tagPattern,unit,fig,df=df)
            return 'export Data'

        return TUinPDRrs_html

    def tagUnit_preSelected_realTime(self,baseId,refreshTime=10,widthG=80,heightGraph=900):
        dicWidgets = {'in_timeRes':str(10)+'s','dd_resampleMethod' : 'mean','dd_typeTags':0,'dd_typeGraph':0,'dd_style':'lines+markers',
                        'dd_cmap':'jet','btn_legend':0,'btn_export':0,'interval':refreshTime}
        TU_RT_html = self.dtu.buildLayout(dicWidgets,baseId,widthG=widthG,nbCaches=1,nbGraphs=1)
        listIds = self.dccE.parseLayoutIds(TU_RT_html)
        # print(listIds)
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
                        'in_timeRes':'value',
                        'dd_resampleMethod':'value',
                        'interval':'n_intervals',
                        'dd_typeTags':'value',
                        'dd_typeGraph':'value',
                        'dd_cmap':'value',
                        'btn_legend':'children',
                        'dd_style':'value'}
        @self.dtu.app.callback(
        Output(baseId + 'graph1', 'figure'),
        [Input(baseId + k,v) for k,v in listInputsGraph.items()],
        State(baseId + 'graph1','figure'))
        def updateGraph(rs,rsMethod,n,preSelGraph,typeGraph,colmap,lgd,style,fig):
            ctx = dash.callback_context
            trigId = ctx.triggered[0]['prop_id'].split('.')[0]
            # to ensure that action on graphs only without computation do not
            # trigger computing the dataframe again
            if n==0 or trigId in [baseId+k for k in ['interval','dd_typeTags','dd_typeGraph','dd_resampleMethod']] :
                df,unit = self.cfgtu.realtimeDF(preSelGraph,rs,rsMethod)
                fig     = self.dtu.drawGraph(df,typeGraph)
                nameGrandeur = self.utils.detectUnit(unit)
                fig.update_layout(yaxis_title = nameGrandeur + ' in ' + unit)
            else :fig = go.Figure(fig)
            fig = self.dtu.updateStyleGraph(fig,style,colmap)
            fig = self.dtu.updateLegend(fig,lgd)
            return fig

        # ==========================================================================
        #                           EXPORT CALLBACK
        # ==========================================================================
        # listStatesExport = [baseId+l for l in ['graph1','dd_typeTags']]
        # @self.dtu.app.callback(Output(baseId + 'btn_export','children'),
        # Input(baseId + 'btn_export', 'n_clicks'),
        # [State(k,v) for k,v in {key: dictOpts[key] for key in listStatesExport}.items()])
        # def exportClick(btn,fig,preSelGraph,rs,date0,date1,t0,t1):
        #     if btn>1:
        #         df = fig.data(timeRange,preSelGraph,rs)
        #         self.dtu.exportDFOnClick(xlims,tagPattern,unit,fig,df=df)
        #     return 'export Data'

        return TU_RT_html
