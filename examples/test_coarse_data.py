#!/usr/bin/env python
# coding: utf-8
from sylfenUtils import comUtils
from sylfenUtils.comUtils import SetInterval,print_file
import os,sys,re, pandas as pd,numpy as np
import importlib
importlib.reload(comUtils)

### load the conf
from test_conf import Conf_dummy
conf=Conf_dummy()

### VISUALISER ---------------
from sylfenUtils.comUtils import VisualisationMaster_daily
cfg=VisualisationMaster_daily(
    conf.FOLDERPKL,
    conf.DB_PARAMETERS,
    conf.PARKING_TIME,
    dbTable=conf.DB_TABLE,
    tz_record=conf.TZ_RECORD
)
cfg.dfplc=conf.df_plc ### required to use the function getTagsTU

#### dump coarse data
def compute_coarse():
    import time
    start=time.time()
    for tag in cfg.dfplc.index:
        try:
            cfg._park_coarse_tag(tag,verbose=True)
        except:
            print_file(timenowstd()+tag + ' not possible to coarse-compute',log_file)
    print_file('coarse computation done in ' + str(time.time()-start) + ' seconds',mode='a')

def read_coarse_data():
    cfg.listUnits=list(cfg.dfplc['UNITE'].unique())
    tags=cfg.getTagsTU('[PT]T.*H2O')
    t1=pd.Timestamp.now(tz='CET')
    t0=t1-pd.Timedelta(hours=1)
    insert_data=False
    df=cfg.load_coarse_data(t0,t1,tags,rs='80s',rsMethod='mean',verbose=False);print(df)
    # sys.exit()
    from sylfenUtils.utils import Graphics
    Graphics().multiUnitGraph(df).show()

compute_coarse()
read_coarse_data()
