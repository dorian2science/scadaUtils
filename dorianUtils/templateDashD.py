import pandas as pd, os
import dash, dash_core_components as dcc, dash_html_components as html, dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.express as px, plotly.graph_objects as go
import matplotlib.pyplot as plt, matplotlib.colors as mtpcl
from pylab import cm
import pickle, time, datetime as dt
from dateutil import parser
from flask_caching import Cache
from dorianUtils.dccExtendedD import DccExtended
from dorianUtils.utilsD import Utils

class TemplateDashMaster:

    def __init__(self,baseNameUrl='/templateDash/',title='tempDash',port=45000,
                    extSheets='bootstrap',cacheRedis=False):
        self.port       = port
        self.title      =title
        self.extSheets  = self.selectExternalSheet(extSheets)
        self.cacheRedis = cacheRedis

        self.app        = dash.Dash(__name__, external_stylesheets=self.extSheets,
                                    url_base_pathname = baseNameUrl,title=title)

        self.app        = dash.Dash(__name__, external_stylesheets=self.extSheets,
                                url_base_pathname = baseNameUrl,title=title)

        self.formatTime   = '%Y-%m-%d %H:%M'
        self.utils=Utils()
    # ==============================================================================
    #                       BASIC FUNCTIONS
    # ==============================================================================
    def selectExternalSheet(self,extSheets):
        if extSheets == 'bootstrap':
            return  [dbc.themes.BOOTSTRAP]
        elif extSheets =='mysheet1' :
            return [
            'https://codepen.io/chriddyp/pen/bWLwgP.css',
            'https://codepen.io/chriddyp/pen/brPBPO.css']
        else :
            return ['https://codepen.io/chriddyp/pen/bWLwgP.css']

    def _getDefaultFolder(self):
        folderExport = os.getenv('HOME') + '/' + self.title
        if not os.path.exists(folderExport) : os.mkdir(folderExport)
        return folderExport

    def runServer(self,**kwargs):
        if self.cacheRedis:
            from flask_caching import Cache
            self.cache      = Cache()
            CACHE_CONFIG = {
            'CACHE_TYPE': 'redis',
            'CACHE_REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379')}
            self.cache.init_app(self.app.server, config=CACHE_CONFIG)
        self.app.run_server(port = self.port,**kwargs)

    def basicLayout(self,title,content):
        self.app.layout = html.Div([
            html.H1(children=title),content
        ])

    def createTab(self,dashContent,tabName):
        return dbc.Tab(dashContent,label=tabName)

    def createTabs(self,tabs):
        return dbc.Tabs([t for t in tabs])

    # ==============================================================================
    #                       GRAPH functions
    # ==============================================================================
    def preparePivotedData(self,df,tags,rs='1s'):
        df = self.cfg.getDFfromTagList(df,tags)
        df = self.cfg.pivotDF(df,rs)
        return df

    def drawGraph(self,df,typeGraph='singleGraph',cmapName='jet',**kwargs):
        cmap        = cm.get_cmap(cmapName, len(df.Tag.unique()))
        colorList   = []
        for i in range(cmap.N):colorList.append(mtpcl.rgb2hex(cmap(i)))
        if typeGraph == 'singleGraph' :
            fig = px.scatter(df, x='timestamp', y='value', color='Tag',color_discrete_sequence=colorList,**kwargs)
        elif typeGraph == 'area':
            fig = px.area(df, color_discrete_sequence=colorList,**kwargs)
        return fig

    def updateStyleGraph(self,fig,style=0,heightGraph=700):
        if style%2==0 :
            fig.update_traces(mode='lines+markers', marker_line_width=0.2, marker_size=6,
                            line=dict(width=3))
            # fig.update_layout(font=dict(family="Courier New, monospace",size=12))
        elif style%2==1:
            fig.update_traces(mode='lines+markers',line_shape='hv', marker_line_width=0.2, marker_size=6,
                            line=dict(width=3))
        # elif style == 2 :
        #     fig.update_traces(selector=dict(mode='markers'))
        fig.update_layout(height=heightGraph)
        return fig

    def generate_facetGraph(self,df,**kwargs):
        fig = px.line(df, x='timestamp', y='value', color='Tag',facet_col='categorie',**kwargs)
        fig.update_yaxes(matches=None)
        fig.update_yaxes(showticklabels=True)
        fig.update_traces(marker=dict(size=2),selector=dict(mode='markers'))
        return fig

    # ==========================================================================
    #                       for callback functions
    # ==========================================================================
    def exportDFOnClick(self,df,fig,folder=None,timeStamp=False,parseYes=False,baseName=None):
        xlims=fig['layout']['xaxis']['range']
        print('xlims : ',xlims)
        trange=[parser.parse(k) for k in xlims]
        if parseYes : xlims=trange
        if timeStamp ==True : df = df[(df.timestamp>xlims[0]) & (df.timestamp<xlims[1])]
        else : df = df[(df.index>xlims[0]) & (df.index<xlims[1])]
        print('df \n: ',df)
        dateF=[k.strftime('%Y-%m-%d %H_%M') for k in trange]
        if not baseName : baseName = self.title
        filename = baseName+ '_' + dateF[0]+ '_' + dateF[1]
        if not folder:folder=self._getDefaultFolder()
        df.to_csv(self.utils.slugify(folder + filename + '.csv'))

    def saveImage(self,fig,folder=None,figname=None,w=1500,h=400):
        if not figname :
            timeNow = dt.datetime.now().strftime(self.formatTime)
            figname = self.utils.slugify(fig.layout.title['text'])
        if not folder : folder=self._getDefaultFolder()
        fig.write_image(folder + '/' + figname + '.png',width=w,height=h)

    def changeLegendBtnState(self,legendType):
        if legendType%3==0 :
            buttonMessage = 'tag '
        elif legendType%3==1 :
            buttonMessage = 'description '
        elif legendType%3==2:
            buttonMessage = 'unvisible '
        return buttonMessage

    def changeStyleBtnState(self,styleSel):
        if styleSel%2==0:
            buttonMessage = 'lines+markers'
        elif styleSel%2==1:
            buttonMessage = 'stairs'
        # elif styleSel%3==2:
        #     buttonMessage = 'markers'
        return buttonMessage


class TemplateDashTagsUnit(TemplateDashMaster):
    ''' you need a configuration file instance from the class ConfigDashTagUnitTimestamp
    meaning having a dfPLC with at least columns : tag,unit and description '''
    def __init__(self,cfg,title='tagsUnitTemplate',baseNameUrl='/tagsUnitTemplate/',
                    skipEveryHours=120,**kwargs):
        super().__init__(baseNameUrl=baseNameUrl,title=title,**kwargs)
        self.cfg = cfg
        self.skipEveryHours = skipEveryHours
        self.dccE = DccExtended()

    # ==========================================================================
    #                       LAYOUT functions
    # ==========================================================================
    def updateLegend(self,df,fig,legendType,pivoted=False,breakLine=None,addUnit=False):
        if legendType%3==1: # description name
            dfDes       = self.cfg.getTagDescription(df,pivoted,2)
            newNames    = dfDes[self.cfg.descriptCol]
            dictNames   = dict(zip(dfDes[self.cfg.tagCol],newNames))
            fig         = self.utils.customLegend(fig,dictNames,breakLine=breakLine)
        elif legendType%3==2: # unvisible
            fig.update_layout(showlegend=False)
        return fig

    def buildLayout(self,listWidgets,baseId,widthG=80,nbGraphs=1,nbCaches=0):
        widgetLayout,dicLayouts = [],{}
        for widgetId in listWidgets:
            if 'dd_listFiles' in widgetId  :
                widgetObj = self.dccE.dropDownFromList(baseId+widgetId,self.cfg.filesDir,'Select your File : ',
                    labelsPattern='\d{4}-\d{2}-\d{2}-\d{2}',defaultIdx=-1)

            elif 'dd_Tag' in widgetId:
                widgetObj = self.dccE.dropDownFromList(baseId+widgetId,list(self.cfg.getTagsRegexp('').TAG),
                'Select type graph : ',defaultIdx=0,multi=True,
                style={'fontsize':'20 px','height': '40px','min-height': '1px',},optionHeight=20)

            elif 'dd_cmap' in widgetId:
                widgetObj = self.dccE.dropDownFromList(baseId+widgetId,self.utils.cmapNames[0],
                                                'select the colormap : ',value='jet')

            elif 'in_step' in widgetId:
                widgetObj = [html.P('skip points : '),
                dcc.Input(id=baseId+widgetId,placeholder='skip points : ',type='number',min=1,step=1,value=20)]

            elif 'in_timeRes' in widgetId:
                widgetObj = [html.P('time resolution : '),
                dcc.Input(id=baseId+widgetId,placeholder='time resolution : ',type='text',value='60s')]

            elif 'btn_legend' in widgetId:
                widgetObj = [html.Button('tag',id=baseId+widgetId, n_clicks=0)]

            elif 'btn_export' in widgetId:
                widgetObj = [html.Button('export .txt',id=baseId+widgetId, n_clicks=0)]

            elif 'btn_style' in widgetId:
                widgetObj = [html.Button('lines+markers',id=baseId+widgetId, n_clicks=0)]

            elif 'btn_Update' in widgetId:
                widgetObj = [html.Button(children='recompute',id=baseId+widgetId, n_clicks=0)]

            elif 'dd_Units' in widgetId :
                widgetObj = self.dccE.dropDownFromList(baseId+widgetId,self.cfg.listUnits,'Select units graph : ',value='W')

            elif 'in_patternTag' in widgetId  :
                widgetObj = [html.P('pattern with regexp on tag : '),
                dcc.Input(id=baseId+widgetId,type='text',value='B001')]

            elif 'dd_typeTags' in widgetId:
                widgetObj = self.dccE.dropDownFromList(baseId+widgetId,list(self.cfg.usefulTags.index),
                            'Select type graph : ',defaultIdx=0,
                            style={'fontsize':'20 px','height': '40px','min-height': '1px',},optionHeight=20)

            elif 'dd_patternCat' in widgetId:
                widgetObj = self.dccE.dropDownFromList(baseId+widgetId,self.cfg.allPatterns,
                            'Select regExpPattern : ',defaultIdx=0,
                            style={'fontsize':'20 px','height': '40px','min-height': '1px',},optionHeight=20)

            elif 'dd_multiPattern' in widgetId:
                widgetObj = self.dccE.dropDownFromList(baseId+widgetId,self.cfg.allPatterns,
                                            style={'fontsize':'20 px','height': '40px','min-height': '1px',},
                                            multi=True,optionHeight=20)
            elif 'rs_time' in widgetId:
                widgetObj = self.dccE.timeRangeSlider(baseId+widgetId)

            elif 'in_time' in widgetId:
                t1 = dt.datetime.now()
                t1 = t1 - dt.timedelta(hours=t1.hour+1)
                t0 = t1 - dt.timedelta(days=3)
                t0,t1 = [d.strftime(self.formatTime) for d in [t0,t1]]
                widgetObj = [
                html.Div([
                    dbc.Row([dbc.Col(html.P('select start and end time : '))]),
                    dbc.Row([dbc.Col(dcc.Input(id = baseId + widgetId + 'Start',type='text',value = t0,size='13',style={'font-size' : 13})),
                            dbc.Col(dcc.Input(id = baseId + widgetId + 'End',type='text',value = t1,size='13',style={'font-size' : 13}))])
                ])]

            elif 'pdr_time' in widgetId :
                tmax = dt.datetime.now()
                t1 = tmax - dt.timedelta(hours=tmax.hour+1)
                t0 = t1 - dt.timedelta(days=3)

                widgetObj = [
                html.Div([
                    dbc.Row([dbc.Col(html.P('select start and end time : ')),
                        dbc.Col(html.Button(id  = baseId + widgetId + 'Btn',children='update Time'))]),

                    dbc.Row([dbc.Col(dcc.DatePickerRange( id = baseId + widgetId + 'Pdr',
                                min_date_allowed = dt.date(2021, 3, 15),max_date_allowed = tmax, initial_visible_month = t0.date(),
                                display_format = 'MMM D, YY',minimum_nights=0,
                                start_date = t0.date(), end_date   = t1.date()))]),

                    dbc.Row([dbc.Col(dcc.Input(id = baseId + widgetId + 'Start',type='text',value = '07:00',size='13',style={'font-size' : 13})),
                            dbc.Col(dcc.Input(id = baseId + widgetId + 'End',type='text',value = '21:00',size='13',style={'font-size' : 13}))])
                ])]

            elif 'in_axisSp' in widgetId  :
                widgetObj = [html.P('select the space between axis : '),
                dcc.Input(id=baseId+widgetId,type='number',value=0.1,max=1,min=0,step=0.02)]

            for widObj in widgetObj:
                widgetLayout.append(widObj)

        dicLayouts['widgetLayout'] = html.Div(widgetLayout,
                                    style={"width": str(100-widthG) + "%", "float": "left"})

        dicLayouts['cacheLayout']= html.Div([html.Div(id=baseId+'fileInCache' + str(k)) for k in range(1,nbCaches+1)],
                                    style={"display": "none"})

        dicLayouts['graphLayout']= html.Div([dcc.Graph(id=baseId+'graph' + str(k)) for k in range(1,nbGraphs+1)],
                                    style={"width": str(widthG) + "%", "display": "inline-block"})


        layout = html.Div(list(dicLayouts.values()))
        return layout

    def buildLayout_vdict(self,dicWidgets,baseId,widthG=80,nbGraphs=1,nbCaches=0):
        widgetLayout,dicLayouts = [],{}
        for widgetId in dicWidgets.items():
            print(widgetId)
            if 'dd_listFiles' in widgetId[0]:
                widgetObj = self.dccE.dropDownFromList(baseId+widgetId[0],self.cfg.filesDir,'Select your File : ',
                    labelsPattern='\d{4}-\d{2}-\d{2}-\d{2}',defaultIdx=widgetId[1])

            elif 'dd_Tag' in widgetId[0]:
                widgetObj = self.dccE.dropDownFromList(baseId+widgetId[0],self.cfg.getTagsTU('',self.cfg.listUnits),
                'Select type graph : ',value=widgetId[1],multi=True,
                style={'fontsize':'20 px','height': '40px','min-height': '1px',},optionHeight=20)

            elif 'dd_cmap' in widgetId[0]:
                widgetObj = self.dccE.dropDownFromList(baseId+widgetId[0],self.utils.cmapNames[0],
                                                'select the colormap : ',value=widgetId[1])

            elif 'in_step' in widgetId[0]:
                widgetObj = [html.P('skip points : '),
                dcc.Input(id=baseId+widgetId[0],placeholder='skip points : ',type='number',
                            min=1,step=1,value=widgetId[1])]

            elif 'in_timeRes' in widgetId[0]:
                widgetObj = [html.P('time resolution : '),
                dcc.Input(id=baseId+widgetId[0],placeholder='time resolution : ',type='text',value=widgetId[1])]

            elif 'btn_legend' in widgetId[0]:
                widgetObj = [html.Button('tag',id=baseId+widgetId[0], n_clicks=widgetId[1])]

            elif 'btn_export' in widgetId[0]:
                widgetObj = [html.Button('export .txt',id=baseId+widgetId[0], n_clicks=widgetId[1])]

            elif 'btn_style' in widgetId[0]:
                widgetObj = [html.Button('lines+markers',id=baseId+widgetId[0], n_clicks=widgetId[1])]

            elif 'btn_Update' in widgetId[0]:
                widgetObj = [html.Button(children='recompute',id=baseId+widgetId[0], n_clicks=widgetId[1])]

            elif 'dd_Units' in widgetId[0] :
                widgetObj = self.dccE.dropDownFromList(baseId+widgetId[0],self.cfg.listUnits,'Select units graph : ',value=widgetId[1])

            elif 'in_patternTag' in widgetId[0]  :
                widgetObj = [html.P('pattern with regexp on tag : '),
                dcc.Input(id=baseId+widgetId[0],type='text',value=widgetId[1])]

            elif 'dd_typeTags' in widgetId[0]:
                widgetObj = self.dccE.dropDownFromList(baseId+widgetId[0],list(self.cfg.usefulTags.index),
                            'Select type graph : ',defaultIdx=widgetId[1],
                            style={'fontsize':'20 px','height': '40px','min-height': '1px',},optionHeight=20)

            elif 'dd_patternCat' in widgetId[0]:
                widgetObj = self.dccE.dropDownFromList(baseId+widgetId[0],self.cfg.allPatterns,
                            'Select regExpPattern : ',defaultIdx=widgetId[1],
                            style={'fontsize':'20 px','height': '40px','min-height': '1px',},optionHeight=20)

            elif 'dd_multiPattern' in widgetId[0]:
                widgetObj = self.dccE.dropDownFromList(baseId+widgetId[0],self.cfg.allPatterns,
                                            style={'fontsize':'20 px','height': '40px','min-height': '1px',},
                                            multi=True,optionHeight=20)

            elif 'rs_time' in widgetId[0]:
                widgetObj = self.dccE.timeRangeSlider(baseId+widgetId[0])

            elif 'in_time' in widgetId[0]:
                t1=widgetId[1]
                if not t1 : t1 = dt.datetime.now()
                t1 = t1 - dt.timedelta(hours=t1.hour+1)
                t0 = t1 - dt.timedelta(days=3)
                t0,t1 = [d.strftime(self.formatTime) for d in [t0,t1]]
                widgetObj = [
                html.Div([
                    dbc.Row([dbc.Col(html.P('select start and end time : '))]),
                    dbc.Row([dbc.Col(dcc.Input(id = baseId + widgetId[0] + 'Start',type='text',value = t0,size='13',style={'font-size' : 13})),
                            dbc.Col(dcc.Input(id = baseId + widgetId[0] + 'End',type='text',value = t1,size='13',style={'font-size' : 13}))])
                ])]

            elif 'pdr_time' in widgetId[0] :
                tmax=widgetId[1]
                # if not tmax : tmax = dt.datetime.now()
                if not tmax :
                    tmax = cfg.filesDir[-1].split('-')[:3]# read the date of the last file in the folder
                    tmax = dt.datetime(int(tmax[0]),int(tmax[1]),int(tmax[2]-1))
                t1 = tmax - dt.timedelta(hours=tmax.hour+1)
                t0 = t1 - dt.timedelta(days=3)

                widgetObj = [
                html.Div([
                    dbc.Row([dbc.Col(html.P('select start and end time : ')),
                        dbc.Col(html.Button(id  = baseId + widgetId[0] + 'Btn',children='update Time'))]),

                    dbc.Row([dbc.Col(dcc.DatePickerRange( id = baseId + widgetId[0] + 'Pdr',
                                max_date_allowed = tmax, initial_visible_month = t0.date(),
                                display_format = 'MMM D, YY',minimum_nights=0,
                                start_date = t0.date(), end_date   = t1.date()))]),

                    dbc.Row([dbc.Col(dcc.Input(id = baseId + widgetId[0] + 'Start',type='text',value = '07:00',size='13',style={'font-size' : 13})),
                            dbc.Col(dcc.Input(id = baseId + widgetId[0] + 'End',type='text',value = '21:00',size='13',style={'font-size' : 13}))])
                ])]

            elif 'in_axisSp' in widgetId[0]  :
                widgetObj = [html.P('select the space between axis : '),
                dcc.Input(id=baseId+widgetId[0],type='number',value=widgetId[1],max=1,min=0,step=0.02)]

            for widObj in widgetObj:
                widgetLayout.append(widObj)

        dicLayouts['widgetLayout'] = html.Div(widgetLayout,
                                    style={"width": str(100-widthG) + "%", "float": "left"})

        dicLayouts['cacheLayout']= html.Div([html.Div(id=baseId+'fileInCache' + str(k)) for k in range(1,nbCaches+1)],
                                    style={"display": "none"})

        dicLayouts['graphLayout']= html.Div([dcc.Graph(id=baseId+'graph' + str(k)) for k in range(1,nbGraphs+1)],
                                    style={"width": str(widthG) + "%", "display": "inline-block"})

        layout = html.Div(list(dicLayouts.values()))
        return layout
