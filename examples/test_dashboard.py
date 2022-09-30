from sylfenUtils import comUtils
import os,sys,re, pandas as pd,numpy as np
import importlib
importlib.reload(comUtils)

### load the conf
class Conf():pass
conf=pd.read_pickle(open('data/conf.pkl','rb'))

from sylfenUtils.comUtils import VisualisationMaster_daily
cfg=VisualisationMaster_daily(
    conf.FOLDERPKL,
    conf.DB_PARAMETERS,
    conf.PARKING_TIME,
    dbTable=conf.DB_TABLE,
    tz_record=conf.TZ_RECORD
)
cfg.dfplc=dumper.dfplc ### required to use the function getTagsTU
cfg.listUnits=list(cfg.dfplc['UNITE'].unique())

init_parameters={
    'tags':cfg.getTagsTU('[PTF]T.*H2O'),
    'fig_name':'temperatures, pressures, and mass flows',
    'rs':'2s',
    'time_window':str(20),
    'delay_minutes':0,
    'log_versions':None #you can enter the relative path of (in folder static) a .md file summarizing some evolution in your code.
}

from sylfenUtils import dashboard
APP_NAME='dummy_app'
dash=dashboard.Dashboard(
    cfg,
    conf.LOG_FOLDER,
    root_folder,
    app_name=APP_NAME,
    init_parameters=init_parameters,
    plot_function=cfg.utils.multiUnitGraph, ## you can use your own function to display the data
    version_dashboard='1.0'
    )

dash.helpmelink='' ### you can precise a url link on how to use the web interface
dash.fig_wh=780### size of the figure

@dash.app.route('/example', methods=['GET'])
def example_extension():
    print('this is a test')

dash.app.run(host='0.0.0.0',debug=False,use_reloader=False)
