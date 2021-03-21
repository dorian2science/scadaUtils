import pandas as pd, os
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.colors as mtpcl
from pylab import cm
import pickle, time
from flask_caching import Cache
from dccExtendedD import DccExtended

class TemplateDashMaster:

    def __init__(self,cfg,baseNameUrl='/templateDash/',title='tempDash',port=45103,extSheets='bootstrap'):
        self.cfg = cfg
        self.port = port

        if extSheets == 'bootstrap':
            self.external_stylesheets = [dbc.themes.BOOTSTRAP]
        elif extSheets =='mysheet1' :
            self.external_stylesheets = [
            'https://codepen.io/chriddyp/pen/bWLwgP.css',
            'https://codepen.io/chriddyp/pen/brPBPO.css']
        else :
            self.external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

        self.dccE       = DccExtended()
        self.app        = dash.Dash(__name__, external_stylesheets=self.external_stylesheets,
                                    url_base_pathname = baseNameUrl + str(port) + "/",title=title)
        self.cache      = Cache()

    # ==========================================================================
    #                       BASIC FUNCTIONS
    # ==========================================================================
    def run_cache(self):
        CACHE_CONFIG = {
        # try 'filesystem' if you don't want to setup redis
        'CACHE_TYPE': 'redis',
        'CACHE_REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379')
        }
        self.cache.init_app(self.app.server, config=CACHE_CONFIG)

    def runServer(self,**kwargs):
        self.run_cache()
        self.app.run_server(port = self.port,**kwargs) # debug = False in deployment

    def basicLayout(self,title,content):
        self.app.layout = html.Div([
            html.H1(children=title),content
        ])

    def createTab(self,dashContent,tabName):
        return dbc.Tab(dashContent,label=tabName)

    def createTabs(self,tabs):
        return dbc.Tabs([t for t in tabs])

    def loadFile(self,filename):
        return self.cfg.loadFile(filename)

    # ==========================================================================
    #                       GRAPH functions
    # ==========================================================================
    def singleCatGraph(self,df,typeGraph='line',cmapName='jet',**kwargs):
        cmap        = cm.get_cmap(cmapName, len(df.Tag.unique()))
        colorList   = []
        for i in range(cmap.N):colorList.append(mtpcl.rgb2hex(cmap(i)))
        print('typeGraph',typeGraph)
        if typeGraph == 'scatter' :
            fig = px.scatter(df, x='timestamp', y='value', color='Tag',color_discrete_sequence=colorList,**kwargs)
        elif typeGraph == 'line' :
            fig = px.line(df, x='timestamp', y='value', color='Tag',
                color_discrete_sequence=colorList,**kwargs)
        elif typeGraph == 'area':
            fig = px.area(df, color_discrete_sequence=colorList,**kwargs)

        fig.update_traces(mode='lines + markers', marker_line_width=0.8, marker_size=10)
        # fig.update_traces(line=dict(width=4, dash='dash'),marker=dict(size=5),selector=dict(mode='line + markers'))
        return fig

    def generate_facetGraph(self,df,**kwargs):
        fig = px.line(df, x='timestamp', y='value', color='Tag',facet_col='categorie',**kwargs)
        fig.update_yaxes(matches=None)
        fig.update_yaxes(showticklabels=True)
        fig.update_traces(marker=dict(size=2),selector=dict(mode='markers'))
            # fig['layout'] = {'margin': {'l': 20, 'r': 10, 'b': 20, 't': 10}}
        return fig

        # ==========================================================================
        #                       DASH LAYOUTS
        # ==========================================================================

    # def exploreDFDash(self,idBase,widthG=80):
    #     dimensions = ["x", "y", "color", "facet_col", "facet_row"]
    #     layoutExplore = html.Div(
    #         [
    #             html.H1("Explore graphs"),
    #             html.Div(
    #                 self.dccE.dropDownFromList(idBase + 'dd_listFiles',self.cfg.filesDir,
    #                 'Select your File : ',defaultIdx=0) +
    #                 [html.P([d + ":", dcc.Dropdown(id=d, options=col_options)])
    #                     for d in dimensions],
    #                 [html.P('skip points: '),dcc.Input(id=idBase + 'in_skip',
    #                     placeholder='skip points : ',type='text',value=1)],
    #                 ,style={"width": "15%", "float": "left",'color':'blue','fontsize':15},
    #             ),
    #             dcc.Graph(id=idBase + "graph", style={"width": "85%", "display": "inline-block"}),
    #             html.Div(id=idBase + 'cacheFile', style={'display': 'none'}),
    #         ]
    #     )
    #
    #     @self.cache.memoize()
    #     def store_df_inCache(filename):
    #         df = self.loadFile(filename)
    #         return df
    #
    #     @self.app.callback(Output(idBase + 'cacheFile', 'children'),
    #                         Input(idBase + 'dd_listFiles','value'))
    #     def load_Df(filename):
    #         print(filename)
    #         store_df_inCache(filename)
    #         return filename
    #
    #     @self.app.callback([Output(idBase + 'dd_' + d, "options") for d in dimensions],
    #     Input(idBase + 'cacheFile','children'))
    #     def updateDropdowns(filename):
    #         df = store_df_inCache(filename)
    #         return [[dict(label=x, value=x) for x in df.columns] for d in dimensions]
    #
    #     @self.app.callback(Output(idBase + "graph", "figure"),
    #                 Input(idBase + 'cacheFile','children'),
    #                 [Input(idBase + 'dd_' + d, "value") for d in dimensions],
    #                 Input(idBase + 'in_skip', "value"))
    #     def make_figure(signalCache,x, y,color,facet_col,facet_row,skip):
    #         df = store_df_inCache(signalCache)
    #         df=df.iloc[::skip]
    #         return px.scatter(
    #             df,
    #             x=x,
    #             y=y,
    #             color=color,
    #             facet_col=facet_col,
    #             facet_row=facet_row,
    #             height=900,title=signalCache
    #         )
    #     return layoutExplore
