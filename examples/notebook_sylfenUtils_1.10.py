#!/usr/bin/env python
# coding: utf-8
from sylfenUtils import comUtils
import os,sys,re, pandas as pd
class Conf():pass

### load the conf
conf=pd.read_pickle(open('data/conf.pkl','rb'))

### MODBUS DEVICE AND SIMULATOR
from sylfenUtils.comUtils import ModbusDevice
dummy_device=ModbusDevice(ip='localhost',port=4580,device_name='dummy_device',
    dfplc=conf.dummy_df_plc,modbus_map=conf.dummy_modbus_map,bo='big',wo='big',freq=2)

from sylfenUtils.Simulators import SimulatorModeBus
dummy_simulator=SimulatorModeBus(port=dummy_device.port,modbus_map=dummy_device.modbus_map,bo=dummy_device.byte_order,wo=dummy_device.word_order)
dummy_simulator.start()

# # 2. DUMP DATA
def test_device_connection():
    dummy_device.connectDevice()
    dummy_device.quick_modbus_single_register_decoder(10,2,'float32',unit=1);
    tags=dummy_device.dfplc.index.to_list()
    dummy_device.connectDevice()
    data=dummy_device.collectData('CET',tags)## do not forget to precise the time zome
    dummy_device.insert_intodb(conf.DB_PARAMETERS,conf.DB_TABLE,'CET',tags)
    comUtils.read_db(conf.DB_PARAMETERS,conf.DB_TABLE)

# # 3. READ THE DATA in REAL TIME
def read_the_data():
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
    tags=cfg.getTagsTU('[PT]T.*H2O')
    t1=pd.Timestamp.now(tz='CET')
    t0=t1-pd.Timedelta(hours=2)
    df=cfg.loadtags_period(t0,t1,tags,rs='2s',rsMethod='mean')
    from sylfenUtils.utils import Graphics
    Graphics().multiUnitGraph(df).show()

# # 4. DEPLOY THE WEB INTERFACE
def deploy_web_GUI():
    # The interface enables other people(or you) to access the data in a convenient way from the web plateform.
    BASE_FOLDER = os.getenv('HOME')+'/dummy_project/'
    root_folder=os.path.dirname(BASE_FOLDER)+'/dummy_app/'
    root_folder
    if not os.path.exists(root_folder):os.mkdir(root_folder)
    import subprocess as sp
    import sylfenUtils
    sylfenUtils_env_dir=os.path.dirname(sylfenUtils.__file__)
    templates_dir=sylfenUtils_env_dir + '/templates'
    templates_folder=root_folder + '/templates'
    if os.path.exists(templates_folder):os.remove(templates_folder)
    sp.run('ln -s '+templates_dir + ' ' + root_folder,shell=True)
    static_folder=root_folder+'/static/'
    if not os.path.exists(static_folder):os.mkdir(static_folder) #create folder if it does not exist
    lib_dir=sylfenUtils_env_dir + '/static/lib'
    lib_folder=static_folder + '/lib'
    if os.path.exists(lib_folder):os.remove(lib_folder)
    sp.run('ln -s ' + lib_dir + ' ' + static_folder,shell=True)
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
    version_dashboard='1.0')

    dash.helpmelink='' ### you can precise a url link on how to use the web interface
    dash.fig_wh=780### size of the figure

    @dash.app.route('/example', methods=['GET'])
    def example_extension():
        print('this is a test')

    dash.app.run(host='0.0.0.0',debug=False,use_reloader=False)


from sylfenUtils.comUtils import SuperDumper_daily
DEVICES = {
    'dummy_device':dummy_device,
}
log_file_name=None ## if you want either to have the information in the console use None.
dumper=SuperDumper_daily(DEVICES,conf.FOLDERPKL,conf.DB_PARAMETERS,conf.PARKING_TIME,
    dbTable=conf.DB_TABLE,tz_record=conf.TZ_RECORD,log_file=log_file_name)
dumper.park_database()
dumper.start_dumping()
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


deploy_web_GUI()
