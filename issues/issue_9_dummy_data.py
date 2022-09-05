### FIRST THING FIRST. Install sylfenUtils==1.5 in a virtual environment
# pip install sylfenUtils==1.5

from sylfenUtils import comUtils

import os,sys,re, pandas as pd

# BUILD THE CONFIGURATION OF YOUR PROJECT
# for convenience put your configuration work in a conf.py file which should serve as an object with all
# the important information. It will be called as a module(import conf) or it will be instanciated from a class (conf=Conf()).
class Conf():
    pass

conf=Conf()
# let's say you have a modbus table of a device that you call "dummy" in a "modbus_dummy.csv" file
conf.dummy_modbus_map=pd.read_csv('modbus_dummy.csv',index_col=0)
print(conf.dummy_modbus_map)
### to use the dumper class of the comUtils module of the sylfenUtils library you need to build a df_plc dataframe with at least following columns
# TAGS(as index), DESCRIPTION, UNITE, DATATYPE. For example you can build it from your dummy_modbus_device as follow:
df_plc=conf.dummy_modbus_map[['description','unit','type']]
df_plc.columns=['DESCRIPTION','UNITE','DATATYPE']
conf.dummy_df_plc=df_plc
## a trick in order not to have to generate the whole configuration you can store the result in a .pkl file
# and put the whole creation of the configuration in a function "createMyConf"(for example) so that if you
# need to regenerate the conf you can call this function. Otherwise just load the .pkl file(will be much faster).
# you need to precise the parameters of the database you want to use and where the data will be stored on your machine.
# for the data acquisition to work you NEED TO INSTALL POSTGRESSQL and CREATE A DATABASE WITH A USER.
# Follow instructions [here](http://wiki.sylfen.com/sql/)

conf.DB_PARAMETERS={
    'host'     : "localhost",
    'port'     : "5432",
    'dbname'   : "db_test",
    'user'     : "test_user",
    'password' : "test"
}

conf.DB_TABLE  = 'realtimedata_test'
### automatic creation of the adequate table if it does not exist in the postgressql database
from sylfenUtils.utils import DataBase
DataBase().create_sql_table(conf.DB_PARAMETERS,conf.DB_TABLE)

conf.TZ_RECORD = 'CET'## the timezone used to park the data
BASE_FOLDER = os.getenv('HOME')+'/dummy_project/'
if not os.path.exists(BASE_FOLDER):os.mkdir(BASE_FOLDER)#create the folder it if does not exist
conf.FOLDERPKL   = BASE_FOLDER + '/data_daily/' ### where the (daily)parked data will be stored
if not os.path.exists(conf.FOLDERPKL):os.mkdir(conf.FOLDERPKL)#create the folder it if does not exist
conf.LOG_FOLDER  = BASE_FOLDER + '/log/'
if not os.path.exists(conf.LOG_FOLDER):os.mkdir(conf.LOG_FOLDER)#create the folder it if does not exist
conf.PARKING_TIME  = 60*10 #### how often (in seconds) the data should be parked from the buffer database(the database is then flushed)

# your conf in now ready and can be seen and used independenly. As long as your are not happy with your conf work on it before
# going to the next step.
# CREATE MODBUS DEVICES, ADD THEM TO YOUR DUMPER WHICH WILL RECORD DATA AS PARKED FORMAT
## Instanciate your devices
# your first device is the dummy device whose ip adress, byte order, word order are known.
from sylfenUtils.comUtils import ModbusDevice
dummy_device=ModbusDevice(ip='localhost',port=3569,device_name='dummy_device',
    dfplc=conf.dummy_df_plc,modbus_map=conf.dummy_modbus_map,bo='big',wo='big',freq=2)

### Start the SIMULATOR of the modbus device
# that this step is supposed to work we will create a simulator of the device based on the same modbus map
# and we will run the modbus server to serve data (random data). For your real project you can of course skip this step.
from sylfenUtils.Simulators import SimulatorModeBus
dummy_simulator=SimulatorModeBus(port=dummy_device.port,modbus_map=dummy_device.modbus_map,bo=dummy_device.byte_order,wo=dummy_device.word_order)
dummy_simulator.start()

### check that you can COLLECT ALL THE DATA from your modbus in real time. Because we want to demonstrate here
tags=dummy_device.dfplc.index.to_list()
dummy_device.connectDevice()
### you can first try to guess the endianess if you didnot know it
dummy_device.quick_modbus_single_register_decoder(10,2,'float32',unit=1);
### collect all the data
data=dummy_device.collectData('CET',tags)## do not forget to precise the time zome

### check that you can insert them into your database (which serve as a buffer for the realtime service)
dummy_device.insert_intodb(conf.DB_PARAMETERS,conf.DB_TABLE,'CET',tags)
#### check that your database was filled with the data
def quick_check_db():
    import psycopg2
    connReq = ''.join([k + "=" + v + " " for k,v in conf.DB_PARAMETERS.items()])
    dbconn = psycopg2.connect(connReq)
    sqlQ ="select * from " + conf.DB_TABLE +" order by timestampz asc;"
    df = pd.read_sql_query(sqlQ,dbconn,parse_dates=['timestampz'])
    print(df)
quick_check_db()

def add_meteo():
    # your second device is the meteo.
    from comUtils import Meteo_Client
    ### put your own token please
    meteo_paris=Meteo(
        cities=pd.DataFrame({'Paris':{'lat' : '46.89','lon':'6.0000'}}),
        variables={'temperature','clouds','pressure'},freq='300s',
        service='openweather',apitoken='79e8bbe89ac67324c6a6cdbf76a450c0'
    )

## instanciate your DUMPER
# with your devices you are ready to start your dumper
DEVICES = {
    'dummy_device':dummy_device,
    # 'meteo_paris':meteo
}
from sylfenUtils.comUtils import SuperDumper_daily
log_file_name=conf.LOG_FOLDER+'/dumper.log'
log_file_name=None
dumper=SuperDumper_daily(DEVICES,conf.FOLDERPKL,conf.DB_PARAMETERS,conf.PARKING_TIME,
    dbTable=conf.DB_TABLE,tz_record=conf.TZ_RECORD,log_file=log_file_name)

### park the database first in case it is already big
dumper.park_database()
### then start to dump again
dumper.start_dumping()
# check that it is correctly feeding the database
quick_check_db()
# opcua device are also available
# if you want to create a new device class that works neither with modbus nor with OPCUA protocole you can create a
# children class of comUtils.Device. Just make sure you have
# - a function <collectData> that collect all the data from the plc dataframe of the device.
# - a function <connectDevice> that connect to the device.
# - a plc dataframe with all the tags/variables for your device.

# READ THE DATA in REAL TIME
### now you can load your parked data as follow
### instanciate the object
from sylfenUtils.comUtils import VisualisationMaster_daily
cfg=VisualisationMaster_daily(conf.FOLDERPKL,conf.DB_PARAMETERS,conf.PARKING_TIME,dbTable=conf.DB_TABLE,tz_record=conf.TZ_RECORD)
cfg.dfplc=dumper.dfplc #### SMALL SHORTCOMING OF THE LIBRARY. You should not need to use the dumper to instanciate the visualiser
cfg.listUnits=list(cfg.dfplc['UNITE'].unique())
 #### SHORTCOMING OF THE LIBRARY.If you do not do that you can"t use the next convenient function.
#### get tags with regular expression with cfg.getTagsTU. For example you want to get all the pressure and
# temperature sensors that works with water(H2O) in your system.
tags=cfg.getTagsTU('[PT]T.*H2O')

##### you can just plot it with a standard multi unit scale graph
##### of course you can require the last 2 hours in real time for example
t1=pd.Timestamp.now(tz='CET')
t0=t1-pd.Timedelta(hours=2)
df=cfg.loadtags_period(t0,t1,tags,rs='2s',rsMethod='mean')
#### here is your dataframe
print(df)
#### you can also call the special function multiunitgraph to sho the graph
from sylfenUtils.utils import Graphics
Graphics().multiUnitGraph(df).show()
# of course you can get the data from anytime to anytime given t0,t1 as timestamps.

sys.exit()
# DEPLOY THE WEB INTERFACE
# the interface enables other people to access the data in a convenient way from the web plateform you configure
## start with some default settings
init_parameters={
    'tags':cfg.getTagsTU('[PTF]T.*H2O'),
    'fig_name':'temperatures and pressures',
    'rs':'30s',
    'time_window':str(2*60),
    'delay_minutes':0,
    'log_versions':None #you can enter the relative path of (in folder static) a .md file summarizing some evolution in your code.
}
root_folder=os.path.dirname(__file__)

dash=dashboard.Dashboard(cfg,conf.LOG_FOLDER,root_folder,app_name='dummy_app',
        init_parameters=init_parameters,plot_function=cfg.multiUnitGraph,version_dashboard='1.0')

dash.helpmelink='http://wiki.sylfen.com/smallPower/' ### you can precise a url link on how to use the web interface
dash.fig_wh=780### size of the figure

#### example of some back-end extension with front-end routing
@dash.app.route('/example', methods=['GET'])
def example_extension():
    print('this is a test')
## start the app
dash.app.run(host='0.0.0.0',port=30000,debug=False,use_reloader=False)
### debug and use_reloader as True can only be used in developpment work but not in production
