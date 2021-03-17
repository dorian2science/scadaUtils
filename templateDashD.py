# import pandas as pd
import os
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.colors as mtpcl
from pylab import cm
import pickle, time
from flask_caching import Cache
import re
from dccExtended import DccExtended

class TemplateDashMaster:
        # ==========================================================================
        #                       BASIC FUNCTIONS
        # ==========================================================================

        def __init__(self,cfg,baseNameUrl='/templateDash/',title='tempDash',port=45103,extSheets='bootstrap'):
            self.cfg = cfg
            self.port = port

            if extSheets =='bootstrap' :
                self.external_stylesheets = [dbc.themes.BOOTSTRAP]
            if extSheets =='mysheet1' :
                external_stylesheets = [
                'https://codepen.io/chriddyp/pen/bWLwgP.css',
                'https://codepen.io/chriddyp/pen/brPBPO.css']
            else :
                external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

            self.dccE       = DccExtended()
            self.app        = dash.Dash(__name__, external_stylesheets=self.external_stylesheets,
                                        url_base_pathname = baseNameUrl + str(port) + "/",title=title)
            self.cache      = Cache()

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
        def singleCatGraph(self,df,cmapName=None,**kwargs):
            cmap        = cm.get_cmap(cmapName, len(df.Tag.unique()))
            colorList   = []
            print('cmap : ',cmapName)
            for i in range(cmap.N):colorList.append(mtpcl.rgb2hex(cmap(i)))
            # fig = px.scatter(df, x='timestamp', y='value', color='Tag',color_discrete_sequence=colorList,**kwargs)
            fig = px.line(df, x='timestamp', y='value', color='Tag',
            color_discrete_sequence=colorList,**kwargs)
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
