import os,sys,re, pandas as pd,importlib
from sylfenUtils import Conf_generator
importlib.reload(Conf_generator)

df_devices=pd.read_csv('data/dummy_devices.csv',index_col=0)
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
conf=Conf_generator.Conf_generator('dummy_project',generate_dummy_conf)
os.listdir(conf.project_folder)
conf.generate_conf()
conf=Conf_generator.Conf_generator('dummy_project',generate_dummy_conf)
