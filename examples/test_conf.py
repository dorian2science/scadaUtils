from sylfenUtils import comUtils,Conf_generator
import importlib
importlib.reload(comUtils)
importlib.reload(Conf_generator)
import warnings
warnings.filterwarnings("ignore")
import os,sys,re, pandas as pd

def generate_conf():
    import time
    conf={}
    time.sleep(2) ### on purpose to make it slow and make the loading of Conf_generator relevant.
    # conf['cst'],conf['dfConstants'] = self.load_material_dfConstants()
    # unitDefaultColors = pd.read_excel('default_values.ods',sheet_name='units_colorCode',index_col=0)
    # dftagColorCode = self._buildColorCode(palettes,pd.concat([beckhoff_plc,plc_indicator_tags]),unitDefaultColors)

    conf['dummy_modbus_map']=pd.read_csv('data/modbus_dummy.csv',index_col=0)
    dummy_df_plc=conf['dummy_modbus_map'][['description','unit','type']]
    dummy_df_plc.columns=['DESCRIPTION','UNITE','DATATYPE']
    conf['PLCS']={'dummy':dummy_df_plc}
    conf['modebus_maps']={'dummy':conf['dummy_modbus_map']}
    conf['df_plc']=dummy_df_plc

    return conf


class Conf_dummy(Conf_generator.Conf_generator):
    def __init__(self):
        Conf_generator.Conf_generator.__init__(self,'dummy2',self.generate_conf_dummy,'/home/dorian/sylfen/tmp/dummy2_user/')
        self.port_dummy=6000
        self.byte_order='big'
        self.word_order='big'
        self.freq=2

    def generate_conf_dummy(self):
        import time
        conf={}
        # time.sleep(2) ### on purpose to make it slow and make the loading of Conf_generator relevant.
        conf['cst'],conf['dfConstants'] = self._load_material_dfConstants()

        conf['dummy_modbus_map']=pd.read_csv('data/modbus_dummy.csv',index_col=0)
        dummy_df_plc=conf['dummy_modbus_map'][['description','unit','type']]
        dummy_df_plc.columns=['DESCRIPTION','UNITE','DATATYPE']
        conf['PLCS']={'dummy':dummy_df_plc}
        conf['modebus_maps']={'dummy':conf['dummy_modbus_map']}
        conf['df_plc']=dummy_df_plc
        conf['tag_color_user']=pd.DataFrame(['Light green'],index=['TT_L5_H2O.HM05'],columns=['colorName'])
        conf['unit_color_code']=pd.Series({
            'mbar':'blues',
            'g/s':'reds',
            'C':'greens',
            'h':'blacks'
        })

        conf['dftagColorCode'] = self._buildColorCode(conf['tag_color_user'],conf['df_plc'],conf['unit_color_code'],False)

        return conf


# conf=Conf_generator.Conf_generator('dummy2',generate_conf,'/home/dorian/sylfen/tmp/dummy2_user/')
# conf.port_dummy=6000
# conf.byte_order='big'
# conf.word_order='big'
# conf.freq=2
conf=Conf_dummy()
conf.generate_conf()
conf._load_conf()
