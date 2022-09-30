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

#### dump coarse data
def compute_coarse():
    start=time.time()
    for tag in cfg.alltags:
        try:
            cfg._park_coarse_tag(tag,verbose=False)
        except:
            print_file(timenowstd()+tag + ' not possible to coarse-compute',log_file)
    print_file('coarse computation done in ' + str(time.time()-start) + ' seconds',filename=log_file,mode='a')

thread_coarse=SetInterval(3600,compute_coarse)
thread_coarse.start()
