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
def build_devices(df_devices,modbus_maps=None,plcs=None):
    DEVICES = {}
    devicesInfo=df_devices.copy()
    devicesInfo.columns=[k.lower() for k in devicesInfo.columns]
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
    for device_name in devicesInfo[devicesInfo['protocole']=='opcua'].index:
        d_info=devicesInfo.loc[device_name]
        DEVICES[device_name]=comUtils.Opcua_Client(
            device_name=device_name,
            ip=d_info['ip'],
            port=d_info['port'],
            dfplc=plcs[device_name],
            nameSpace=d_info['namespace'],
        )
    for device_name in devicesInfo[devicesInfo['protocole']=='ads'].index:
        d_info=devicesInfo.loc[device_name]
        DEVICES[device_name]=comUtils.ADS_Client(
            device_name=device_name,
            ip=d_info['ip'],
            port=d_info['port'],
            dfplc=plcs[device_name],
        )
    return DEVICES

class GAIA():
    def __init__(self,*args,root_folder=None,**kwargs):
        '''
        Super instance that create a project from scratch to dump data from devices,
        load, visualize, and serve those data on a web GUI.
        Parameters:
        -----------------
            - *args,**kwargs : see Conf_generator arguments
            - root_folder : [str] root_folder of the dashboard web service.
        '''
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

    def flush_db(self,*args,**kwargs):
        return self._dumper.flushdb(*args,**kwargs)

    def park_database(self,*args,**kwargs):
        return self._dumper.park_database(*args,**kwargs)

    def run_GUI(self,*args,**kwargs):
        self._dashboard.app.run(host='0.0.0.0',*args,**kwargs)

class Test_GAIA():
    def __init__(self,gaia):
        '''
        Parameters
        -----------
        - gaia[Gaia]
        '''
        self.gaia=gaia

class Tester:
    def __init__(self,gaia,log_file_tester=None):
        '''
        gaia : [sylfenUtils.gaia] instance
        '''
        self.cfg    = gaia._cfg
        self.conf   = gaia.conf
        self.dumper = gaia_dumper
        self.dumper.log_file=log_file_tester

## private methods
    def _test_collect_data_device(self,device_name):
        device=self.dumper.devices[device_name]
        device.connectDevice()
        tags=device.dfplc.index.to_list()
        return device.collectData('CET',tags)

    def _test_read_db():
        return self.dumper.read_db()

    def _get_random_period(self,nbHours=55):
        valid_days=self.dumper.getdaysnotempty()
        d1 = valid_days.sample(n=1).squeeze()
        d1 = dumper.getdaysnotempty().sample(n=1).squeeze()
        t1 = d1+pd.Timedelta(hours=np.random.randint(24))
        t0 = t1 - pd.Timedelta(hours=nbHours)
        min_t0=valid_days.min()
        if t0<min_t0:
            t0=min_t0
            t1=min_t0+pd.Timedelta(hours=nbHours)
        return t0,t1

    def load_raw_data(self,tags,t0,t1,*args,print_tag=False,**kwargs):
        fix=Fix_daily_data(self.conf)
        res={}
        for t in tag:
            if print_tag:print_file(tag)
            res[tag]=fix.load_raw_tag_period(tags,t0,t1,*args,**kwargs)
        return res

## regression tests
    def test_load_real_time_data(self,only_database=False):
        t1=pd.Timestamp.now(tz='CET')
        t0=t1-pd.Timedelta(hours=2)
        tags=self.cfg.dfplc.sample(n=10).index.to_list()
        if only_database:
            df = cfg._load_database_tags(t0,t1,tags,rs='1s',rsMethod="mean_mix",closed='right',verbose=True)
        else:
            df = self.cfg.loadtags_period(t0,t1,tags,rs='10s',rsMethod="mean_mix",closed='right',verbose=True)
        return df

    def test_load_data(self):
        t0,t1=self._get_random_period(nbHours=60)
        tags = self.cfg.dfplc.sample(n=10).index.to_list()
        # df = Streamer().load_parkedtags_daily(t0,t1,tags,cfg.folderPkl,rs='60s',pool='tag',verbose=True)
        # Streamer()._load_raw_day_tag('2022-06-22',tags[0],cfg.folderPkl,rs='60s',rsMethod='mean_mix',closed='right')
        try:
            df  = self.cfg.loadtags_period(t0,t1,tags,rs='20s',rsMethod="mean_mix",closed='right',verbose=True)
            return df
        except:
            return ('failed with arguments',t0,t1,tags)

    def test_collect_data(self):
        return {device_name:self._test_collect_data_device(device_name) for device_name in self.dumper.devices.keys()}

    def test_load_coarse_data():
        t0,t1=self._get_random_period(nbHours=24*15)
        tags = self.cfg.dfplc.sample(n=10).index.to_list()
        try:
            return self.cfg.load_coarse_data(t0,t1,tags,rs='60s',verbose=True)
        except:
            return ('failed with arguments',t0,t1,tags)
