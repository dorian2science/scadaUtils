#!/usr/bin/env python
# coding: utf-8
import importlib
import sylfenUtils.comUtils as comUtils
importlib.reload(dashboard)
cfg=comUtils.VisualisationMaster_daily(
    dummy_conf.FOLDERPKL,
    dummy_conf.DB_PARAMETERS,
    dummy_conf.PARKING_TIME,
    dbTable=dummy_conf.DB_TABLE,
    tz_record=dummy_conf.TZ_RECORD
)
####################
# SUGGESTION MODIF #
####################
###### REPLACE BY FOLLOWING #### =======>>> dumper=VisualisationMaster_daily(conf)

def test_load_tags_period():
    tags=cfg.getTagsTU('[PT]T.*H2O')
    t1=pd.Timestamp.now(tz='CET')
    t0=t1-pd.Timedelta(hours=2)
    df=cfg.loadtags_period(t0,t1,tags,rs='2s',rsMethod='mean')
    df
    from sylfenUtils.utils import Graphics
    Graphics().multiUnitGraph(df).show()

root_folder=os.path.join(dummy_conf.project_folder,'dashboard')
import sylfenUtils.dashboard as dashboard
importlib.reload(dashboard)
init_parameters={
    'tags':cfg.getTagsTU('[PTF]T.*H2O'),
    'fig_name':'temperatures, pressures, and mass flows',
    'rs':'30s',
    'time_window':str(2*60),
    'delay_minutes':0,
    'log_versions':None #you can enter the relative path of (in folder static) a .md file summarizing some evolution in your code.
}
dash=dashboard.Dashboard(
    cfg,
    dummy_conf.LOG_FOLDER,
    root_folder,
    app_name='dummy_app',
    init_parameters=init_parameters,
    plot_function=cfg.utils.multiUnitGraph, ## you can use your own function to display the data
    version_dashboard='1.0')
dash.helpmelink='' ### you can precise a url link on how to use the web interface
dash.fig_wh=780### size of the figure
sylfenUtils.Conf_generator.__file__
port_app=15000
dash.app.run(host='0.0.0.0',port=port_app,debug=False,use_reloader=False)

####################
# SUGGESTION MODIF #
####################
# put the initial parameters in the user_settings default file so that to start the whole
# programm (configurating,dumping, and web service) the user should only do#
# ====> gaia=Gaia(myproject_name,my_conf_generator_function)
### programm should then pop up the user_settings file and ask to modify it if necessary. And tell
# him that he can modifiy this file at any time. Then tell him to systemctl restart GAIA.py.
### Make sure the user can do GAIA,py
##
