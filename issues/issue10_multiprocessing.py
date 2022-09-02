import plotly.express as px, plotly.graph_objects as go
from sylfenUtils.comUtils import (timenowstd,computetimeshow)
from sls_monitoring import sls_conf as conf
from sylfenUtils.monitoring import (Monitoring_dumper,Monitoring_visu)
from sylfenUtils import dashboard
import importlib
import os,sys,re
import pandas as pd
importlib.reload(dashboard)
importlib.reload(conf)


# def test_multialone():
from multiprocessing import Pool

def quick_load_debug():
    t1=pd.Timestamp('2022-06-24 12:00',tz='CET')
    t0=t1-pd.Timedelta(hours=12)
    tags=cfg.getTagsTU('PV')
    df=cfg.loadtags_period(t0,t1,tags,rs='60s')

def test_dummy_dashboard():
    cfg=Monitoring_visu(conf)
    from sylfenUtils.monitoring import Monitoring_dumper
    # dumper = Monitoring_dumper(conf,None)
    # dumper.start_dumping()
