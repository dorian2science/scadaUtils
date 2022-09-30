from sylfenUtils import comUtils,Conf_generator
import importlib
importlib.reload(comUtils)
importlib.reload(Conf_generator)

import os,sys,re, pandas as pd

class Conf_dummy(Conf_generator.Conf_generator):
    def __init__(self):
        Conf_generator.Conf_generator.__init__(self,'dummy1','/home/dorian/tmp/dummy1/')
        self.port_dummy=5000
        self.byte_order='big'
        self.word_order='big'
        self.freq=2


    def generate_conf(self):
        import time
        time.sleep(2) ### on purpose to make it slow and make the loading of Conf_generator relevant.
        # palettes = self.__loadcolorPalettes()
        # cst,dfConstants = self.load_material_dfConstants()
        # unitDefaultColors = pd.read_excel('default_values.ods',sheet_name='units_colorCode',index_col=0)
        # dftagColorCode = self._buildColorCode(palettes,pd.concat([beckhoff_plc,plc_indicator_tags]),unitDefaultColors)

        dummy_modbus_map=pd.read_csv('data/modbus_dummy.csv',index_col=0)
        dummy_df_plc=dummy_modbus_map[['description','unit','type']]
        dummy_df_plc.columns=['DESCRIPTION','UNITE','DATATYPE']
        PLCS={'dummy':dummy_df_plc}
        modebus_maps={'dummy':dummy_modbus_map}
        df_plc=dummy_df_plc

        return {
            'dummy_modbus_map':dummy_modbus_map,
            'modebus_maps':modebus_maps,
            'PLCS':PLCS,
            'df_plc':df_plc,
        }

conf=Conf_dummy()
