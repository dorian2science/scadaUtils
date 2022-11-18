import importlib,pandas as pd,sys
from sylfenUtils.GAIA import build_devices
from sylfenUtils.Simulators import SuperSimulator
from sylfenUtils import GAIA
importlib.reload(GAIA)

df_devices=pd.read_csv('data/dummy_devices.csv',index_col=0)
df_devices['port']=[3505,6501]
dummy_1_modbus_map=pd.read_excel('data/dummy_modbus_devices.ods',sheet_name='dummy1',index_col=0)
dummy_2_modbus_map=pd.read_excel('data/dummy_modbus_devices.ods',sheet_name='dummy2',index_col=0)
def generate_dummy_conf():
    return {
        'df_devices':df_devices,
        'modbus_maps':{
            'dummy1':dummy_1_modbus_map,
            'dummy2':dummy_2_modbus_map,
            },
    }

gaia_dummy=GAIA.GAIA('gaia_dummy',generate_dummy_conf)
gaia_dummy._dumper.log_file=None

### start the simulators
# sys.exit()
# conf=gaia_dummy.conf
# dummy_simulator=SuperSimulator(conf)
# dummy_simulator.start_all_devices()
### park and start dumping
# gaia_dummy.park_database()
# gaia_dummy.start_dumping()

### quick checked reading ok
def test_loading_data():
    tags=gaia_dummy.getTagsTU('FT')
    gaia_dummy.read_db(tagPat='FT')
    t1=pd.Timestamp.now('CET')
    t0=t1-pd.Timedelta(hours=3)
    df=gaia_dummy.loadtags_period(t0,t1,tags)

### run GUI
gaia_dummy._dashboard.max_nb_pts=500*1000
gaia_dummy._dashboard.rs_min_coarse=5*60
gaia_dummy._dashboard.nb_days_min_coarse=3
gaia_dummy.run_GUI(port=20003)
