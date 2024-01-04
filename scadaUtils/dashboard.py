from flask import Flask, request, session, render_template, send_file, jsonify
from subprocess import check_output
import json,os,sys,glob,time,traceback
from IPython.core.ultratb import AutoFormattedTB
import numpy as np,pandas as pd
import plotly.express as px
import re
import plotly.graph_objects as go
from string import ascii_letters,digits
from .comUtils import (timenowstd,computetimeshow,print_file,to_folderday)
from .utils import graphics
from .Conf_generator import create_folder_if_not
import os
from IPython.core.ultratb import AutoFormattedTB
import pkg_resources

def detect_empty_columns(df):
    s = df.isna().all()
    return s[s].index.to_list()

def quick_resample(df,rs,rsMethod):
    if rsMethod=='min':
        df = df.resample(rs).min()
    elif rsMethod=='max':
        df = df.resample(rs).max()
    elif rsMethod=='mean':
        df = df.resample(rs).mean()
    elif rsMethod=='median':
        df = df.resample(rs).median()
    elif rsMethod=='forwardfill':
        df = df.resample(rs).ffill()
    elif rsMethod=='nearest':
        df = df.resample(rs).nearest()
    return df

class Basic_Dashboard():
    def __init__(self,conf):
        self.dashboard_html = 'dashboard.html'
        parameters =  conf.parameters
        self.conf = conf
        self.init_parameters = parameters['dashboard']
        self.folder_datasets = parameters['dashboard']['folder_datasets']
        self.tmp_folder = parameters['dashboard']['tmp_folder']
        self.NOTIFS = parameters['dashboard_notifs']
        rs_number,rs_unit = re.search('(\d+)(\w)',self.init_parameters['initial_resampling_time']).groups()
        self.init_parameters['rs_number'] = rs_number
        self.init_parameters['rs_unit'] = rs_unit
        self.init_parameters['initial_time_window'] = pd.Timedelta(self.init_parameters['initial_time_window']).total_seconds()

        self.log_folder = parameters['log_folder']

        self.infofile_name = os.path.join(self.log_folder,'dashboard_' + conf.project_name + '.log');
        start_msg = timenowstd() + ' '*10+ ('starting ' + conf.project_name + ' dashboard\n').upper() + '*'*60 + '\n'
        with open(self.infofile_name,'a') as logfile:
            logfile.write(start_msg)

        self.errorfile_name = os.path.join(self.log_folder,'dashboard_' + conf.project_name + '.err');
        with open(self.errorfile_name,'a') as logfile:
            logfile.write(start_msg)

        project_folder = conf.project_folder
        if self.init_parameters['root_path'] == '':
            self.init_parameters['root_path'] = os.path.join(project_folder,'dashboard/')

        if self.init_parameters['log_version_file'] == '':
            self.init_parameters['log_version_file'] = os.path.join(project_folder,'dashboard','static','log_versions.md')
        if self.init_parameters['folder_datasets'] == '':
            self.init_parameters['folder_datasets'] = os.path.join(project_folder,'datasets/')
        if self.init_parameters['tmp_folder'] == '':
            self.init_parameters['tmp_folder'] = os.path.join(project_folder,'tmp/')
        self.version_dashboard = '.'.join(pkg_resources.get_distribution('scadaUtils').version.split('.')[:-1])

        self.app = Flask(__name__,root_path = self.init_parameters['root_path'])

        self.routes = [
            ("/", self.main_viewport,['GET']),
            ('/init',self.init_dashboard,['GET']),
            ('/generate_dataset_fig',self.generate_dataset_fig,['POST']),
            ('/export2excel',self.export2excel,['POST']),
            ('/send_description_names',self.send_description_names,['POST']),
            ('/send_dfplc',self.send_dfplc,['POST']),
            ('/send_data_sets',self.send_data_sets,['POST']),
            ('/send_sessions',self.send_sessions,['GET']),
            ('/upload',self.process_new_file,['POST'])
        ]
        
        self.sessions = {}

    def define_routes(self):
        for route, route_function,methods in self.routes:
            self.app.route(route, methods=methods)(route_function)

    # #####################
    #    ROUTES FUNCTIONS #
    # #####################
    def send_sessions(self):
        return os.listdir(self.folder_datasets)

    def main_viewport(self):
        return render_template(self.dashboard_html,
            helpmelink = self.init_parameters['helpmelink'],
            version_title = 'gaia ' + self.version_dashboard,
            )

    def init_dashboard(self):
        return json.dumps(self.init_parameters)

    def generate_dataset_fig(self):
        debug = False
        notif = 200
        Time,data=[],[]
        try:
            start = time.time()
            data = request.get_data()
            parameters = json.loads(data.decode())
            if debug:print_file(parameters)

            data_set = parameters['data_set']
            session = parameters['session']
            file_path = os.path.join(self.folder_datasets,session,data_set + '.pkl')
            # print_file(file_path)
            df = pd.read_pickle(file_path)
            tags = parameters['tags']
            if parameters['all_tags'] == True:
                tags = df.columns
            df = df[tags]
            t0,t1 = [pd.Timestamp(t,tz='CET') for t in parameters['timerange'].split(' - ')]
            if not parameters['all_times']:
                df = df[(df.index>=t0)&(df.index<=t1)]

            rs,rsMethod = parameters['rs_time'],parameters['rs_method']
            # print_file(computetimeshow('df read',start))

            df = quick_resample(df,rs,rsMethod)
            # print_file(computetimeshow('resample done',start))

            if df.empty:
                notif = self.NOTIFS['no_data']
                raise Exception('no data')

            ####### check that the request does not have TOO MANY DATAPOINTS
            df,notif = self.check_nb_data_points(df)

            ####### generate graph
            dfplc_path = os.path.join(self.folder_datasets,session,'dfplc',data_set + '_dfplc.pkl')
            dfplc = pd.read_pickle(dfplc_path)
            # print_file(computetimeshow('dfplc read',start))
            if debug:print_file(df)
            units = dfplc.loc[list(df.columns),'UNITE'].to_dict()

            #### replace ffill.bfill by fill(null)?
            data = {k:df[k].ffill().bfill().to_list() for k in df.columns}
            print_file('starting reindexing')
            Time = [k.isoformat() for k in df.index]
                        

        except:
            if notif==200:
                notif = 'figure_generation_impossible'
                error = {'msg':' problem in the figure generation with generate_fig','code':1}
                # error_message = self.notify_error(sys.exc_info(),error)
                error_message = traceback.format_exc()
                notif = self.NOTIFS[notif] + error_message

        res = {'Time':Time,'data':data,'units':units,'notif':notif}
        return jsonify(res)

    def export2excel(self):
        try:
            start = time.time()
            data = request.get_data()
            fig = json.loads(data.decode())
            baseName = 'data'
            dfs = [pd.Series(trace['y'],index=trace['x'],name=trace['name']) for trace in fig['data']]
            df = pd.concat(dfs,axis=1)
            df.index = [pd.Timestamp(t) for t in df.index]
            t0,t1 = fig['layout']['xaxis']['range']
            df = df[(df.index>=t0) & (df.index<=t1)]

            dateF = [pd.Timestamp(t).strftime('%Y-%m-%d %H_%M') for t in [t0,t1]]
            filename = 'static/tmp/' + baseName +  '_' + dateF[0]+ '_' + dateF[1]+'.xlsx'
            if isinstance(df.index,pd.core.indexes.datetimes.DatetimeIndex):
                df.index = [k.isoformat() for k in df.index]
            df.to_excel(os.path.join(self.init_parameters['root_path'],filename))
            self.log_info(computetimeshow('.xlsx downloaded',start))
            res = {'status':'ok','filename':filename}
        except:
            error = {'msg':'service export2excel not working','code':3}
            notif = 'excel_generation_impossible'
            # self.notify_error(sys.exc_info(),error)
            error_message = traceback.format_exc()
            notif = self.NOTIFS[notif] + error_message
            res = {'status':'failed','notif':notif}
        return jsonify(res)

    def send_description_names(self):
        data = request.get_data()
        data = json.loads(data.decode())
        new_names = self.cfg.toogle_tag_description(data['tags'],data['mode'])
        return jsonify(new_names)

    def process_new_file(self):
        if 'file' not in request.files:
            return 'No file part'

        file = request.files['file']
        session = request.form['session']

        if file.filename == '':
            return 'No selected file'

        print_file(session)        
        filepath = os.path.join(self.conf.parameters['dashboard']['upload_folder'],session, file.filename)
        file.save(filepath)
        print_file('file stored successfully')
        if session in self.sessions.keys():
            try:
                self.sessions[session](filepath)
                return ""
            except:
                error_message = traceback.format_exc()
                notif = "impossible to parse your file : " + file.filename +". Please make sure you are in the correct session."
                # notif = "impossible to parse your file : " + error_message 
                return notif
        else:
            return 'no available parser for session : '+ session


    def send_data_sets(self):
        data = request.get_data()
        session = data.decode()
        print_file(session)
        return [k.strip('.pkl') for k in os.listdir(os.path.join(self.folder_datasets,session)) if '.pkl' in k]

    def send_dfplc(self):
        data = request.get_data()
        data = json.loads(data.decode())
        # print_file(data)
        dfplc_path = os.path.join(self.folder_datasets,data['session'],'dfplc',data['dataset'] + '_dfplc.pkl')
        print_file(dfplc_path)
        dfplc = pd.read_pickle(dfplc_path)
        return dfplc.index.to_list()

    # ###################
    #    MANAGE LOGS    #
    # ###################
    def check_nb_data_points(self,df):
        nb_datapoints = len(df)*len(df.columns)
        max_nb_pts = self.init_parameters['max_nb_pts']
        notif = 200
        if nb_datapoints>max_nb_pts:
            nb_pts_curve = max_nb_pts//len(df.columns)
            total_seconds = (df.index[-1]-df.index[0]).total_seconds()
            new_rs = str(total_seconds//nb_pts_curve)
            df = df.resample(new_rs+'S').mean()
            notif = self.NOTIFS['too_many_datapoints'].replace('XXX',str(nb_datapoints//1000)).replace('YYY',new_rs).replace('AAA',str(MAX_NB_PTS//1000))
        return df,notif

    def parse_file(self,f):
        df = pd.read_excel(f)
        dfplc = df.iloc[:2,1:].T
        dfplc.columns = ['UNITE','description']
        dfplc['MODEL'] = 'cea_pacmat2'
        dfplc['UNITE'].unique()
        ## find the time
        t = df['temps'][1]
        a = re.search(r'\w+ (\d+-\w+-\d+ \d{2}:\d{2}:\d{2}).*',t)
        t0 = pd.Timestamp(a.groups()[0],tz='CET')
        df2 = df.iloc[2:,1:]
        df2.index = [t0+pd.Timedelta(k,'seconds') for k in df2.index]
        ## save the file
        file_name = f.split('/')[-1]
        new_file_name = '.'.join(file_name.split('.')[:-1])
        new_file_path = self.folder_datasets + new_file_name+'.pkl'
        df2.ffill().bfill().to_pickle(new_file_path)
        dfplc_path = self.folder_dfplc + new_file_name+'_dfplc.pkl'
        dfplc.to_pickle(dfplc_path)

    def parse_AVL(self,f):
        df = pd.read_csv(f,skiprows=15,sep=',',encoding="iso-8859-1")
        dfplc = df.iloc[0,3:].to_frame()
        dfplc.columns = ['UNITE']
        df2 = df.iloc[2:,3:]
        df2.index = [pd.Timestamp(k,tz='CET') for k in  df.iloc[2:,0]]
        df2=df2.astype(float).ffill().bfill()
        new_file_name = f.split('/')[-1].strip('.csv')
        parked_folder = '/data/uploaded/AVL/'
        df2.to_pickle(os.path.join(parked_folder,new_file_name+'.pkl'))
        dfplc_path = os.path.join(parked_folder,'dfplc',new_file_name+'_dfplc.pkl')
        dfplc.to_pickle(dfplc_path)

    # ###################
    #    MANAGE LOGS    #
    # ###################
    def log_info(self,msg):
        print_file(msg,filename=self.infofile_name,with_infos=False)
        # with open(self.infofile_name,'a') as loginfo_file:
            # loginfo_file.write('-'*60 +'\n'+ msg +'\n')
            # loginfo_file.write('-'*60+'\n')

    def notify_error(self,tb,error):
        AutoTB = AutoFormattedTB(mode = 'Verbose',color_scheme='Linux')
        print_file('-'*60 +'\n'+timenowstd()+' '*10 + error['msg']+'\n',filename=self.errorfile_name)
        if self.errorfile_name is None:
            x=AutoTB(*tb,out=self.errorfile_name)
        print_file('-'*60+'\n',filename=self.errorfile_name)

    def _create_dashboard_links(self):
        '''
        Copy the static and templates folders into the root folder of the dashboard to be able to run the Dashboard instance.
        '''
        import shutil
        create_folder_if_not(self.init_parameters["root_path"])
        #### TEMPLATE FOLDER
        scadaUtils_env_dir = os.path.dirname(__file__)
        templates_folder = os.path.join(self.init_parameters["root_path"],'templates')
        shutil.copytree(os.path.join(scadaUtils_env_dir,'templates'),templates_folder,dirs_exist_ok=True)
        print('templates files have been copied into ',self.init_parameters["root_path"])

        #### STATIC FOLDER
        static_folder = os.path.join(self.init_parameters["root_path"],'static')
        shutil.copytree(os.path.join(scadaUtils_env_dir,'static'),static_folder,dirs_exist_ok=True)
        # lib_folder = os.path.join(static_folder,'lib')
        # if not os.path.exists(lib_folder):
        #     shutil.copytree(os.path.join(scadaUtils_env_dir,'static/lib'),lib_folder)
        print('static files have been copied into ',self.init_parameters["root_path"])

        tmp_folder = os.path.join(static_folder,'tmp')
        create_folder_if_not(tmp_folder)

class Dashboard(Basic_Dashboard):
    '''
    Instanciate a dashboard to monitor data.

    :param conf: conf object create by confGenerator 
    '''

    def __init__(self,conf,visualiser,plot_function=None,app_name='',**kwargs):
        Basic_Dashboard.__init__(self,conf,**kwargs)
        self.visualiser = visualiser
        self.app_name = app_name
        if plot_function is None :
            plot_function = graphics.multiUnitGraph
        self.plot_function = plot_function

        #### initial parameters
        init_par_keys = list(self.init_parameters.keys())
        self.init_parameters['models'] = list(conf.dfplc['MODEL'].unique())
        if self.init_parameters['initial_model'] =="":
            self.init_parameters['initial_model'] = self.init_parameters['models'][0] 
        self.init_parameters['all_tags'] = conf.getTagsTU('',model=self.init_parameters['initial_model'])
        self.init_parameters['tag_categories'] = list(conf.tag_categories[self.init_parameters['initial_model']].keys())
        self.init_parameters['rsMethods'] = visualiser.methods

        self.routes += [
            ("/generate_fig", self.generate_fig,['POST']),
            ("/send_model_tags", self.send_model_tags,['POST']),
        ]
        self.define_routes()

    def send_model_tags(self):
        data = request.get_data()
        model = json.loads(data.decode())
        data = {}
        data['categories'] = list(self.visualiser.conf.tag_categories[model].keys())
        data['all_tags'] = self.visualiser.conf.getTagsTU('',model=model)
        list_days = self.visualiser.conf.getdaysnotempty(model)
        max_day =  list_days.max()
        min_day = list_days.min()
        all_days=pd.date_range(start=min_day,end=max_day)
        all_days
        excludeddates = [k for k in all_days if k not in list_days.to_list()]
        data['max_date'] = to_folderday(max_day)
        data['min_date'] = to_folderday(min_day)
        data['excludeddates'] = [to_folderday(k) for k in excludeddates]
        return json.dumps(data)

    def generate_fig(self):
        debug = False
        notif = 200
        print_file(timenowstd(),'request received')
        try:
            start=time.time()
            data = request.get_data()
            parameters = json.loads(data.decode())
            if debug:print_file(parameters)

            t0,t1 = [pd.Timestamp(t,tz='CET') for t in parameters['timerange'].split(' - ')]

            if debug:print_file('t0,t1:',t0,t1)
            tags = parameters['tags']
            model_categories = self.visualiser.conf.tag_categories[parameters['model']]
            if parameters['categorie'] in model_categories:
                tags += model_categories[parameters['categorie']]
            if debug:print_file('alltags:',tags)
            rs,rsMethod = parameters['rs_time'],parameters['rs_method']
            model = parameters['model']
            ####### determine if it should be loaded with COARSE DATA or fine data
            # if pd.to_timedelta(rs)>=pd.Timedelta(seconds=self.rs_min_coarse) or t1-t0>pd.Timedelta(days=self.nb_days_min_coarse):
            print_file(timenowstd(),'load data')
            if parameters['coarse']:
                pool='coarse'
                df = self.visualiser.load_coarse_data(t0,t1,tags,model=model,rs=rs,rsMethod=rsMethod)
            else:
                if debug :print_file(tags)
                df = self.visualiser.loadtags_period(t0,t1,model=model,tags=tags,rs=rs,rsMethod=rsMethod,pool=False,verbose=True)
                if debug :print_file(df)
            if df.empty:
                notif = self.NOTIFS['no_data']
                raise Exception('no data')
            # print_file(timenowstd(),'finish loading')

            # print_file(timenowstd(),'check nb points')
            ####### check that the request does not have TOO MANY DATAPOINTS
            df, notif = self.check_nb_data_points(df)
            if debug:print_file(df)

            tags_empty = detect_empty_columns(df)
            if len(tags_empty)>0:
                notif = "No data could be found for the tags " + ', '.join(tags_empty)
            # fig = self.plot_function(df,model)()

            # self.log_info(computetimeshow('fig generated with pool =' + str(pool),start))

        except:
            if notif==200:
                notif = 'figure_generation_impossible'
                error = {'msg':' problem in the figure generation with generate_fig','code':1}
                # error_message = self.notify_error(sys.exc_info(),error)
                error_message = traceback.format_exc()
                notif = self.NOTIFS[notif] + error_message
            fig = go.Figure()

        # res = {'fig':fig.to_json(),'notif':notif}
        dfplc = self.conf.dfplc
        dfplc = dfplc[dfplc['MODEL']==model]
        units = dfplc.loc[tags,'UNITE'].to_dict()
        #### replace ffill.bfill by fill(null)?
        data = {k:df[k].ffill().bfill().to_list() for k in df.columns}
        # print_file(timenowstd(),'starting reindexing')
        Time = [k.isoformat() for k in df.index]
        # fig = self.plot_function(df,model)()
        # print_file(timenowstd(),'starting jsonify')

        res = {'Time':Time,'data':data,'units':units,'notif':notif}
        res=jsonify(res)
        # print_file(timenowstd(),'done send to front')
        return res

from .flask_utilities import app, register_user, user_login, redirect, url_for, login_required, logout_user
class Protected_dragdrop_dashboard(Basic_Dashboard):
    def __init__(self,*args,**kwargs):
        Basic_Dashboard.__init__(self,*args,**kwargs)
        self.tmp_folder = '/data/tmp/'

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        return register_user()

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        return user_login()

    @app.route('/logout')
    @login_required  # Requires the user to be logged in
    def logout():
        logout_user()
        return redirect(url_for('index'))

    @app.route('/index')
    @app.route('/')
    @login_required
    def index():
        return render_template('index.html')

