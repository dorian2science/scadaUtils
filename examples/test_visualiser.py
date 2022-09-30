#!/usr/bin/env python
# coding: utf-8
from sylfenUtils import comUtils
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
cfg.dfplc=conf.dfplc ### required to use the function getTagsTU

# # 3. READ THE DATA in REAL TIME
def read_the_data():
    cfg.listUnits=list(cfg.dfplc['UNITE'].unique())
    tags=cfg.getTagsTU('[PT]T.*H2O')
    t1=pd.Timestamp.now(tz='CET')
    t0=t1-pd.Timedelta(minutes=5)
    test_dumping()
    db=(dumper.read_db()).set_index('timestampz')
    db.index=db.index.tz_convert('CET')
    print(db)
    import time;time.sleep(0.3)
    df=cfg.loadtags_period(t0,t1,tags,rs='1s',rsMethod='mean',verbose=False);print(df)
    sys.exit()
    from sylfenUtils.utils import Graphics
    Graphics().multiUnitGraph(df).show()
