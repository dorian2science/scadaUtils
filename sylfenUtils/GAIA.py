import sylfenUtils.comUtils as comUtils
from sylfenUtils.Conf_generator import Conf_generator
from sylfenUtils.dashboard import Dashboard
import os
from . import utils
##### this is the superinstance
# put the initial parameters of the dashboard in the user_settings default file so that to start the whole
# programm (configurating,dumping, and web service) the user should only do#
# ====> gaia=Gaia(myproject_name,my_conf_generator_function)
### programm should then pop up the user_settings file and ask to modify it if necessary. And tell
# him that he can modifiy this file at any time. Then tell him to systemctl restart GAIA.py.
### Make sure the user can only have one instance of GAIA.py running
##
def build_devices(df_devices,modbus_maps=None,opcua_plcs=None):
    DEVICES = {}
    devicesInfo=df_devices.copy()
    devicesInfo.columns=[k.lower() for k in devicesInfo.columns]
    ###### MODBUS DEVICES
    for device_name in devicesInfo[devicesInfo['protocole']=='modbus'].index:
        d_info=devicesInfo.loc[device_name]
        DEVICES[device_name]=comUtils.ModbusDevice(
            ip=d_info['ip'],
            port=d_info['port'],
            device_name=device_name,
            modbus_map=modbus_maps[device_name],
            bo=d_info['byte_order'],
            wo=d_info['word_order'],
        )
    ###### OPCUA DEVICES
    for device_name in devicesInfo[devicesInfo['protocole']=='opcua'].index:
        d_info=devicesInfo.loc[device_name]
        DEVICES[device_name]=comUtils.Opcua_Client(
            device_name=device_name,
            ip=d_info['ip'],
            port=d_info['port'],
            dfplc=opcua_plcs[device_name],
            nameSpace=d_info['namespace'],
        )
    return DEVICES

class GAIA():
    def __init__(self,*args,root_folder=None,**kwargs):
        self.conf=Conf_generator(*args,**kwargs)
        self.dfplc=self.conf.dfplc
        #### INITIALIZE DEVICES
        self.devices=build_devices(self.conf.df_devices,self.conf.modbus_maps,self.conf.plcs)
        self._dumper=comUtils.SuperDumper_daily(self.devices,self.conf)
        self._visualiser=comUtils.VisualisationMaster_daily(self.conf)
        if root_folder is None:
            root_folder=os.path.join(self.conf.project_folder,'dashboard')

        _initial_tags=self.conf.INITIAL_TAGS.split(';')
        if len(_initial_tags)==1:
            _initial_tags=_initial_tags[0]
            if _initial_tags.lower().strip()=='random':
                _initial_tags=self.dfplc.sample(n=max(3,self.dfplc.index)).index.to_list()
            else:
                _initial_tags=self.conf.getTagsTU(_initial_tags)

        self._init_parameters={
            'tags':_initial_tags,
            'fig_name':self.conf.INITIAL_FIGNAME,
            'rs':self.conf.INITIAL_RESAMPLING_TIME,
            'time_window':self.conf.INITIAL_TIME_WINDOW,
            'delay_minutes':0,
            'log_versions':None #you can enter the relative path of (in folder static) a .md file summarizing some evolution in your code.
        }

        #### configure web GUI
        self._dashboard=Dashboard(
            self._visualiser,
            self.conf.LOG_FOLDER,
            root_folder,
            app_name='dummy_app',
            init_parameters=self._init_parameters,
            plot_function=utils.Graphics().multiUnitGraph, ## you can use your own function to display the data
            version_dashboard='1.0')
        self._dashboard.helpmelink='' ### you can precise a url link on how to use the web interface
        self._dashboard.fig_wh=780### size of the figure

        print('='*60,'\nYOUR ATTENTION PLEASE.\nPlease check your default settings for the application in the file.',self.conf.file_parameters)
        print('If necessary change the settings and reinstanciate your GAIA object\n'+'='*60)

    def start_dumping(self):
        self._dumper.start_dumping()

    def stop_dumping(self):
        self._dumper.stop_dumping()

    def getTagsTU(self,*args,**kwargs):
        return self.conf.getTagsTU(*args,**kwargs)

    def loadtags_period(self,*args,**kwargs):
        return self._visualiser.loadtags_period(*args,**kwargs)

    def read_db(self,*args,**kwargs):
        return self._dumper.read_db(*args,**kwargs)

    def park_database(self,*args,**kwargs):
        return self._dumper.park_database(*args,**kwargs)

    def run_GUI(self,*args,**kwargs):
        self._dashboard.app.run(host='0.0.0.0',*args,**kwargs)
