import os,sys,re, pandas as pd,importlib
from sylfenUtils import Conf_generator
importlib.reload(Conf_generator)


dummy_modbus_map=pd.read_csv('data/modbus_dummy.csv',index_col=0)
dummy_modbus_map
df_plc=dummy_modbus_map[['description','unit','type']]
df_plc.columns=['DESCRIPTION','UNITE','DATATYPE']
dummy_df_plc=df_plc
def generate_dummy_conf():
    return {
        'dummy_modbus_map':dummy_modbus_map,
        'dummy_df_plc':dummy_df_plc,
        'dfplc':df_plc
    }
conf=Conf_generator.Conf_generator('dummy_project',generate_dummy_conf)
os.listdir(conf.project_folder)
with open(conf.file_parameters,'r') as f :
    for l in f.readlines():
        print(l)
