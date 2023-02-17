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
LIST_SERVICES=[
    'dashboard',
    'dumper',
    'coarse_parker'
]

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
    __init__.__doc__+=Conf_generator.Conf_generator.__init__.__doc__

    def start_dumping(self,*args,**kwargs):
        self._dumper.start_dumping(*args,**kwargs)
    start_dumping.__doc__=comUtils.SuperDumper_daily.start_dumping.__doc__

    def stop_dumping(self):
        self._dumper.stop_dumping()

    def getTagsTU(self,*args,**kwargs):
        return self.conf.getTagsTU(*args,**kwargs)
    getTagsTU.__doc__=Conf_generator.Conf_generator.getTagsTU.__doc__

    def loadtags_period(self,*args,**kwargs):
        return self._visualiser.loadtags_period(*args,**kwargs)
    loadtags_period.__doc__=comUtils.VisualisationMaster_daily.loadtags_period.__doc__

    def plot_data(self,df,**kwargs):
        return self._visualiser.multiUnitGraph(df,**kwargs)
    plot_data.__doc__=comUtils.VisualisationMaster_daily.multiUnitGraph.__doc__

    def read_db(self,*args,**kwargs):
        return self._dumper.read_db(*args,**kwargs)
    read_db.__doc__=comUtils.SuperDumper_daily.read_db.__doc__

    def flush_db(self,*args,**kwargs):
        return self._dumper.flushdb(*args,**kwargs)
    flush_db.__doc__=comUtils.SuperDumper_daily.flushdb.__doc__

    def park_database(self,*args,**kwargs):
        return self._dumper.park_database(*args,**kwargs)
    park_database.__doc__=comUtils.SuperDumper_daily.park_database.__doc__

    def run_GUI(self,*args,**kwargs):
        self._dashboard.app.run(host='0.0.0.0',*args,**kwargs)
    import flask
    run_GUI.__doc__=flask.app.Flask.run.__doc__

    def _quick_log_read(self,filename='dumper',n=100,last=True):
        '''
        filename:[str] either the filename or one of 'dumper','dashboard' or the name of a device.
        '''
        if filename=='dumper':
            filename=self._dumper.log_file
        elif filename in self.devices.keys():
            filename=self.devices[filename]._collect_file
        elif filename=='dashboard':
            filename=self._dashboard.infofile_name
        comUtils.print_file(filename)
        with open(filename, 'r') as f:
            lines = f.readlines()
            for line in lines[-n:]:
                print(line)

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

import psutil,pandas as pd,subprocess as sp,re
from sylfenUtils.utils import EmailSmtp
from sylfenUtils.comUtils import print_file
import time

class Heartbeat():
    def __init__(self,gaia,web_service_name,programme_names,smtp_args=None):
        '''
        :Parameters:
        ---------------
            - web_service_name[str]:for example : "http://reflex.sylfen.com/"
            - programme_names[list] of strings of program names that are going to be checked.
            - **smtp_args[dict]:arguments of EmailSmtp. By default Dorian send mails
        '''
        self.gaia=gaia
        NAME_SERVICE_WEB=web_service_name
        self.LISTPROGRAMS=[self.gaia.project_name + k for k in LIST_SERVICES]
        self.listHours_heartbeats=['06:30','09:00','13:00','20:00']
        if smtp_args is None:
            smtp_args={
            # host:'smtp.gmail.com',
            # user:'drevondorian@gmail.com',
                'host':'smtp.office365.com',
                'port' : 587,
                'user':'dorian.drevon@sylfen.com',
                'password':'Qoh26867',
                'isTls':True
            }

        SMTP = EmailSmtp(**smtp_args)
        DEVICES=gaia.devices

    def check_device_collect(self,device_name,threshold='1H',verbose=False):
        '''
        Check if collecting data are still in the log according to a certain threshold
        :Parameters:
        --------------
            - device_name[str]: One of gaia.devices
            - threshold[str]:duration in pandas format. Default is '1H'
        '''
        def count_lines(filename):
            result = sp.run(['/usr/bin/wc', '-l', filename], stdout=sp.PIPE)
            output = result.stdout.decode('utf-8')
            num_lines = int(output.split()[0])
            return num_lines

        device=DEVICES[device_name]

        #### read the last 50 lines of the log
        result = sp.run('/usr/bin/tail -n 50 ' + device._collect_file,shell=True,stdout=sp.PIPE,stderr=sp.PIPE)
        lines = result.stdout.decode('utf-8').split('\n')
        # return 'collect file does not exist'

        #### find the timestamps and convert them to pd format
        timestamps=[re.findall('\d{4}-\w{3}-\d{2} \d{2}:\d{2}:\d{2}',l) for l in lines]
        if verbose:print_file(timestamps)
        timestamps=pd.Series([pd.Timestamp(k,tz='CET') for l in timestamps for k in l])
        if verbose:print_file(timestamps)
        #### the the max timestamp
        if len(timestamps)>0:
            max_ts=timestamps.max()
            # get the number of lines in the file
            n=count_lines(device._collect_file)
            ## if this is >10000 then delete back to 1000.
            max_lines=10000;nb_lines=1000
            # max_lines=10;nb_lines=2
            if n>max_lines:
                with open(device._collect_file, 'r') as f:
                    lines = f.readlines()
                with open(device._collect_file, 'w') as f:
                    f.writelines(lines[-nb_lines:])

            #### does the last collect compare to now > threshold?
            now=pd.Timestamp.now(tz='CET')
            if now-max_ts>pd.Timedelta(threshold):
                return max_ts.isoformat()
            else:
                return 1
        else:
            error_msg='no timestamps or file does not exist with content of log_file of device:\n'
            error_msg+= '\n'.join(lines) + 'for file : '+device._collect_file + '\n'
            error_msg+='error message:'+ result.stderr.decode()
            return error_msg

    def send_alert(self,body,msg,to_marc=False):
        # print_file(body)
        toAddrs=["DorianSylfen<dorian.drevon@sylfen.com>"]
        to_marc=False
        if to_marc:
            toAddrs+=[
                "Marc Potron<marc.potron@sylfen.com>",
                "Damien Messi<damien.messi@sylfen.com>"
            ]
        try:
            SMTP.sendMessage(
                 fromAddr = "ALERTING <dorian.drevon@sylfen.com>",
                 toAddrs = toAddrs,
                 subject = "ALERT: "+body,
                 content = msg,
                 )
        except:
            print('impossible to send mail for an unkown reason.')

    def is_program_running(self,program_name):
        for process in psutil.process_iter():
            try:
                process_name=' '.join(process.cmdline())
                if program_name in process_name:
                    # print(process_name)
                    return True
            except Exception as e:
                print_file(e)
                return True
        return False

    def collecting_alert(self,device_name,collect_status,threshold='1H'):
        '''
        - Send an alert if the collecting of a device stopped working started working again
        :Parameters:
            - device_name[str]
            - collect_status[bool]:if True collect is working okay.
        returns : [bool] collect_status
        '''
        res_collect=check_device_collect(device_name,threshold=threshold)
        if collect_status and not res_collect==1:
            msgContent = """Cher collègues,
            La collecte des données pour l'appareil suivant :""" + device_name +' a cessé  de  fonctioner depuis ' + res_collect+"""
            Veuillez trouver la cause du problème.
            Cordialement,
            """
            send_alert(device_name + ' stopped collecting',msgContent,to_marc=True)
            collect_status = False
        elif not collect_status and res_collect==1:
            collect_status = True
            msgContent = """Dear colleague,
            La collecte des données pour l'appareil suivant:""" + device_name + """
            fonctionne à nouveau.
            Cordialement,
            """
            send_alert(device_name + ' collecting again',msgContent,to_marc=True)
        return collect_status

    def program_alert(self,program_name,was_running):
        '''
        - Send an alert if the program stopped again or was started working again
        :Parameters:
            - program_name[str]
            - was_running[bool]:current state of the program
        returns : [bool] state of the program
        '''
        # print_file(program_name,was_running,is_program_running(program_name))
        if was_running and not is_program_running(program_name):
            msgContent = """Dear colleague,
            The following service stopped working :""" + program_name + """
            Please check the reason for the application service failure.
            Sincerely
            """
            send_alert(program_name + ' stopped working',msgContent)
            was_running = False
        elif not was_running and is_program_running(program_name):
            was_running = True
            msgContent = """Dear colleague,
            The following service is available again:""" + program_name + """
            Sincerely
            """
            send_alert(program_name + ' working again',msgContent)
        return was_running

    def heartBeat(self,hearbeat):
        if pd.Timestamp.now().strftime('%H:%M') in self.listHours_heartbeats:
            hearbeat_msg=True
            msgContent = """Dear colleague,
            I am still alive!
            Please have a quick look on the dashboard at (the services?) """+NAME_SERVICE_WEB+""" to make
            sure you are still happy with the data and service.
            Sincerely
            """
            body = "Heartbeat of gaia"
            if not hearbeat:
                send_alert(body,msgContent)
                hearbeat=True
        else:
            hearbeat=False
        return hearbeat

    def start_watchdog(self):
        running_programs={k:True for k in self.LISTPROGRAMS}
        collecting_devices={k:True for k in DEVICES.keys()}
        hearbeat=False
        while True:
            ### check if services are running
            for program_name,was_running in running_programs.items():
                running_programs[program_name]=program_alert(program_name,was_running)
            ### check if data are correctly collected
            for device_name,collect_status in collecting_devices.items():
                collecting_devices[device_name]=self.collecting_alert(device_name,collect_status)

            hearbeat=self.heartBeat(hearbeat)
            time.sleep(5)


    ##### quick test
    def test():
        check_device_collect('battery',verbose=True)
        check_device_collect('beckhoff',verbose=True)
        collecting_alert('battery',True,'2S')
        collecting_alert('beckhoff',True,'0.5S')
        program_alert('gaia_cycling_trials',True)
        program_alert('gaia_dashboard',True)
        program_alert('gaia_dumper',True)
        program_alert('gaia_coarse_parker',True)

        device_name='battery';threshold='1H';verbose=False

        ### test send message
        SMTP = EmailSmtp(
            host='smtp.office365.com',
            # host='smtp.gmail.com',
            port = 587,
            # user='drevondorian@gmail.com',
            user='dorian.drevon@sylfen.com',
            password='Qoh26867',
            isTls=True
            )

        toAddrs=["DorianSylfen<dorian.drevon@sylfen.com>"]
        SMTP.sendMessage(
             fromAddr = "ALERTING <dorian.drevon@sylfen.com>",
             toAddrs = toAddrs,
             subject = "ALERT: ",
             content = 'hello',
             )
