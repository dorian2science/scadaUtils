import sylfenUtils.comUtils as comUtils
import sylfenUtils.Conf_generator as Conf_generator
from sylfenUtils.dashboard import Dashboard
import os,inspect
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
    devicesInfo=devicesInfo[devicesInfo['status']=='actif']
    devicesInfo.columns=[k.lower() for k in devicesInfo.columns]
    # comUtils.print_file(devicesInfo['protocole'])
    devicesInfo['protocole']=devicesInfo['protocole'].apply(lambda x:x.lower().strip().replace('modebus','modbus'))
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
        # comUtils.print_file(d_info)
        DEVICES[device_name]=comUtils.ADS_Client(
            device_name=device_name,
            ip=d_info['ip'],
            port=d_info['port'],
            dfplc=plcs[device_name],
        )
    return DEVICES

class GAIA():
    def __init__(self,*args,root_folder=None,realtime=True,**kwargs):
        '''
        Super instance that create a project from scratch to dump data from devices,
        load, visualize, and serve those data on a web GUI.
        Parameters:
        -----------------
            - *args,**kwargs : see sylfenUtils.Conf_generator.Conf_generator arguments
            - root_folder : [str] root_folder of the dashboard web service.
            - realtime:[bool] if True Gaia uses postgressql database as buffer otherwise
                it is just static data loading from folderpkl.
        '''
        if realtime:self.conf = Conf_generator.Conf_generator_RT(*args,**kwargs)
        else:self.conf        = Conf_generator.Conf_generator_Static(*args,**kwargs)
        self.dfplc            = self.conf.dfplc
        #### INITIALIZE DEVICES
        # comUtils.print_file(self.conf)
        if not hasattr(self.conf,'modbus_maps'):self.conf.modbus_maps=None
        if not hasattr(self.conf,'plcs'):self.conf.plcs=None
        self.devices     = build_devices(self.conf.df_devices,self.conf.modbus_maps,self.conf.plcs)
        self._dumper     = comUtils.SuperDumper_daily(self.devices,self.conf)
        self._visualiser = comUtils.VisualisationMaster_daily(self.conf)
        if root_folder is None:
            root_folder=os.path.join(self.conf.project_folder,'dashboard')

        _initial_tags=self.conf.INITIAL_TAGS.strip(';').split(';')
        if len(_initial_tags)==1 and _initial_tags[0].lower().strip()=='random':
            _initial_tags=self.dfplc.sample(n=min(3,len(self.dfplc.index))).index.to_list()
        else:
            alltags=[]
            for t in _initial_tags:
                alltags+=self.conf.getTagsTU(t)
            _initial_tags=alltags

        self._init_parameters={
            'tags':_initial_tags,
            'fig_name':self.conf.INITIAL_FIGNAME,
            'rs':self.conf.INITIAL_RESAMPLING_TIME,
            'time_window':self.conf.INITIAL_TIME_WINDOW,
            'delay_minutes':0,
            'log_versions':None #you can enter the relative path of (in folder static) a .md file summarizing some evolution in your code.
        }
        if self.conf.TEST_ENV:
            self._init_parameters['delay_minutes']=self.conf.DASHBOARD_DELAY_MINUTES
        #### configure web GUI
        self._dashboard=Dashboard(
            self._visualiser,
            self.conf.LOG_FOLDER,
            root_folder,
            app_name=self.conf.project_name,
            init_parameters=self._init_parameters,
            plot_function=utils.Graphics().multiUnitGraph, ## you can use your own function to display the data
            version_dashboard='1.0')
        self._dashboard.helpmelink='' ### you can precise a url link on how to use the web interface
        self._dashboard.fig_wh=780### size of the figure

        print('='*60,'\nYOUR ATTENTION PLEASE.\nPlease check your default settings for the application in the file.\n\n',self.conf.file_parameters)
        print('\nIf necessary change the settings and reinstanciate your GAIA object\n'+'='*60)

    def start_dumping(self,*args,**kwargs):
        self._dumper.start_dumping(*args,**kwargs)

    def stop_dumping(self):
        self._dumper.stop_dumping()

    def getTagsTU(self,*args,**kwargs):
        return self.conf.getTagsTU(*args,**kwargs)

    def loadtags_period(self,*args,**kwargs):
        '''
        Documentation of comUtils.VisualisationMaster_daily.loadtags_period
        '''
        return self._visualiser.loadtags_period(*args,**kwargs)

    def plot_data(self,df,**kwargs):
        return self._visualiser.multiUnitGraph(df,**kwargs)

    def read_db(self,*args,**kwargs):
        return self._dumper.read_db(*args,**kwargs)

    def flush_db(self,*args,**kwargs):
        return self._dumper.flushdb(*args,**kwargs)

    def park_database(self,*args,**kwargs):
        return self._dumper.park_database(*args,**kwargs)

    def run_GUI(self,*args,**kwargs):
        self._dashboard.app.run(host='0.0.0.0',*args,**kwargs)

    def _quick_read(self,filename='dumper',n=100,last=True):
        if filename=='dumper':
            filename=self._dumper.log_file
        elif filename in self.devices.keys():
            filename=self.devices[filename]._collect_file
        elif filename=='dashboard':
            filename=self._dashboard.log_file
        with open(filename, 'r') as f:
            lines = f.readlines()
            for line in lines[-n:]:
                print(line)

    loadtags_period.__doc__+=comUtils.VisualisationMaster_daily.loadtags_period.__doc__

class Tester:
    def __init__(self,gaia,log_file_tester=None):
        '''
        gaia : [sylfenUtils.gaia] instance
        '''
        self.cfg    = gaia._visualiser
        self.conf   = gaia.conf
        self.dumper = gaia._dumper
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
        fix=comUtils.Fix_daily_data(self.conf)
        res={}
        for t in tags:
            if print_tag:print_file(tag)
            res[t]=fix.load_raw_tag_period(t,t0,t1,*args,**kwargs)
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
