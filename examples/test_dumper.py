import os,pandas as pd,importlib
import sylfenUtils.comUtils as comUtils
from sylfenUtils.Simulators import SuperSimulator
import sylfenUtils.Simulators as Simulators
from sylfenUtils.GAIA import build_devices
importlib.reload(comUtils)
from test_confGenerator import conf

####################
# SUGGESTION MODIF #
####################
conf.df_devices.port=[5301,6511]
devices=build_devices(conf.df_devices,conf.modbus_maps)
devices
dumper=comUtils.SuperDumper_daily(devices,conf)
##### START SIMULATORS
importlib.reload(Simulators)
dummy_simulator=Simulators.SuperSimulator(conf)
dummy_simulator.start_all_devices()
dumper.log_file=None

def test_collect_insert():
    dummy_device=dumper.devices['dummy1']
    dummy_device.connectDevice()
    dummy_device.quick_modbus_single_register_decoder(10,2,'float32',unit=1);
    tags=dummy_device.dfplc.sample(n=3).index.to_list()
    dummy_device.connectDevice()
    data=dummy_device.collectData('CET',tags)## do not forget to precise the time zome
    dummy_device.insert_intodb(conf.DB_PARAMETERS,conf.DB_TABLE,'CET',tags)
    comUtils.read_db(conf.DB_PARAMETERS,conf.DB_TABLE)

dumper.park_database()
dumper.start_dumping()
