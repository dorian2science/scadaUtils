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
from dateutil import parser
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
    def drawGraph(self,df,typeGraph='singleGraph',cmapName='jet',**kwargs):
        cmap        = cm.get_cmap(cmapName, len(df.Tag.unique()))
        colorList   = []
        for i in range(cmap.N):colorList.append(mtpcl.rgb2hex(cmap(i)))
        # print('typeGraph',typeGraph)
        if typeGraph == 'singleGraph' :
            fig = px.scatter(df, x='timestamp', y='value', color='Tag',color_discrete_sequence=colorList,**kwargs)
        elif typeGraph == 'area':
            fig = px.area(df, color_discrete_sequence=colorList,**kwargs)
        # fig.update_traces(line=dict(width=4, dash='dash'),marker=dict(size=5),selector=dict(mode='line + markers'))
        return fig

    def exportDFOnClick(self,df,fig,folder=None,timeStamp=False,parseYes=False):
        if not folder:
            folder = '/home/dorian/testsCode/testDir/'
        xlims=fig['layout']['xaxis']['range']
        print('xlims : ',xlims)
        trange=[parser.parse(k) for k in xlims]
        if parseYes :
            xlims=trange
        if timeStamp ==True :
            df = df[(df.timestamp>xlims[0]) & (df.timestamp<xlims[1])]
        else :
            df = df[(df.index>xlims[0]) & (df.index<xlims[1])]
        print('df \n: ',df)
        dateF=[k.strftime('%Y-%m-%d-%H-%M') for k in trange]
        filename = 'test_' + dateF[0]+ '_' + dateF[1]
        df.to_csv(folder + filename + '.txt')

    def generate_facetGraph(self,df,**kwargs):
        fig = px.line(df, x='timestamp', y='value', color='Tag',facet_col='categorie',**kwargs)
        fig.update_yaxes(matches=None)
        fig.update_yaxes(showticklabels=True)
        fig.update_traces(marker=dict(size=2),selector=dict(mode='markers'))
            # fig['layout'] = {'margin': {'l': 20, 'r': 10, 'b': 20, 't': 10}}
        return fig
