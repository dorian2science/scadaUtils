from flask import Flask,Blueprint,request,session,render_template,send_file,jsonify
from subprocess import check_output
import json,os,sys,glob,time,traceback
from IPython.core.ultratb import AutoFormattedTB
import numpy as np,pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from string import ascii_letters,digits
from sylfenUtils.comUtils import (timenowstd,computetimeshow,print_file)
from sylfenUtils.Conf_generator import create_folder_if_not
NOTIFS={
    'too_many_datapoints':''' TOO MANY DATAPOINTS\n
        You have requested XXXk datapoints which is over AAAk datapoints.\n
        The plotly graph would be to slow to load and the interaction very unconvenient.\n
        Your request had been modified to limit the number of data points to AAAk by choosing a higher resampling period of : YYY.\n
        If you are not happy with these settings please select another period or/and resampling period or/and total number of tags keeping in mind that you should not exceed AAAk datapoints in total.
        Take into account as well that the more datapoints you ask the more you have to wait for the figure to load.
        ''',
    'figure_generation_impossible':'''Impossible to generate your figure.\n
        Please take note of your settings or take a screenshot of your screen and report it to the webmaster: dorian.drevon@sylfen.com.
        ''',
    'no_data':'''NO DATA\n
        There is no data for your list of tags and the selected period.\n
        if this is not supposed to be the case please report it to the webmaster: dorian.drevon@sylfen.com.
        ''',
    'excel_generation_impossible': '''EXCEL BUG\n
        Impossible to generate your excel file.\n
        Please take note of your settings or take a screenshot of your screen and report it to the webmaster: dorian.drevon@sylfen.com.'''
}

from IPython.core.ultratb import AutoFormattedTB
class Dashboard():
    def __init__(self,cfg,log_dir,root_path,
            plot_function=None,app_name='',
            init_parameters={},version_dashboard='',
            max_nb_pts=500*1000,rs_min_coarse=5*60,nb_days_min_coarse=3,
        ):
        '''
        Instanciate a dashboard to monitor data.
        - cfg: instance of type comUtils.VisualisationMaster
        - log_dir:log directory where to put the logs
        - root_path:path of the directory where the static and templates files are.
        '''

        cfg.styles = ['default'] + cfg.utils.styles
        self.fig_wh=780
        self.cfg=cfg
        self.max_nb_pts=max_nb_pts
        self.rs_min_coarse=rs_min_coarse
        self.nb_days_min_coarse=nb_days_min_coarse
        self.log_dir=log_dir
        print('your log is in:',log_dir)
        self.app_name=app_name
        self.root_path=root_path
        self._create_dashboard_links(root_path)
        if plot_function is None :plot_function=cfg.multiUnitGraph
        self.plot_function = plot_function
        self.infofile_name  = log_dir+'dashboard_' + app_name + '.log';
        self.helpmelink=''
        self.version_dashboard = version_dashboard
        start_msg=timenowstd() + ' '*10+ ('starting ' + app_name + ' dashboard\n').upper() + '*'*60 + '\n'
        # start_msg=timenowstd() + ' STARTING DASHBOARD\n'
        with open(self.infofile_name,'a') as logfile:logfile.write(start_msg)
        self.errorfile_name = log_dir+'dashboard_'+ app_name +'.err';
        with open(self.errorfile_name,'a') as logfile:logfile.write(start_msg)
        self.app = Flask(__name__,root_path=self.root_path)

        #### initial parameters
        init_par_keys=list(init_parameters.keys())
        if not 'all_tags' in init_par_keys:init_parameters['all_tags']=self.cfg.getTagsTU('')
        if not 'styles' in init_par_keys:init_parameters['styles']=self.cfg.styles
        if hasattr(cfg.conf,'categories'):
            tag_categories=list(cfg.conf.tag_categories.keys())
        else:
            tag_categories=[]
        if not 'categories' in init_par_keys:init_parameters['categories']=tag_categories
        if not 'rsMethods' in init_par_keys:init_parameters['rsMethods']=cfg.methods
        if not 'tags' in init_par_keys:init_parameters['tags']=[]
        if not 'fig_name' in init_par_keys:init_parameters['fig_name']='Change me '
        if not 'rs' in init_par_keys:init_parameters['rs']='60s'
        if not 'time_window' in init_par_keys:init_parameters['time_window']='120'
        if not 'title' in init_par_keys:init_parameters['title']=app_name
        if not 'delay_minutes' in init_par_keys:init_parameters['delay_minutes']=0
        if not 'log_versions' in init_par_keys:init_parameters['log_versions']=''

        self.init_parameters=init_parameters

        # ###############
        #    ROUTING    #
        # ###############
        @self.app.route('/', methods=['GET'])
        def main_viewport():
            return render_template('dashboard.html',
                helpmelink=self.helpmelink,
                version_title=self.app_name+' '+self.version_dashboard,
                )

        @self.app.route('/init', methods=['GET'])
        def init_dashboard():
            return self._init_dashboard()

        @self.app.route('/generate_fig', methods=['POST'])
        def generate_fig():
            return self._generate_fig()

        @self.app.route('/export2excel', methods=['POST'])
        def export2excel():
            return self._export2excel()

        @self.app.route('/send_description_names',methods=['POST'])
        def send_names():
            return self._send_names()

    def _create_dashboard_links(self,root_folder):
        '''
        Copy the static and templates folders into root folder of the dashboard to be able to run the Dashboard instance.
        '''
        import shutil
        create_folder_if_not(root_folder)
        #### TEMPLATE FOLDER
        sylfenUtils_env_dir=os.path.dirname(__file__)
        templates_folder=os.path.join(root_folder,'templates')
        if not os.path.exists(templates_folder):
            shutil.copytree(os.path.join(sylfenUtils_env_dir,'templates'),templates_folder)
            print('templates files have been copied into ',root_folder)
        #### STATIC FOLDER
        static_folder=os.path.join(root_folder,'static')
        if not os.path.exists(static_folder):
            shutil.copytree(os.path.join(sylfenUtils_env_dir,'static'),static_folder)
        lib_folder=os.path.join(static_folder,'lib')
        if not os.path.exists(lib_folder):
            shutil.copytree(os.path.join(sylfenUtils_env_dir,'static/lib'),lib_folder)
            print('static files have been copied into ',root_folder)

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

    # ###################
    #    FUNCTIONS      #
    # ###################
    def _init_dashboard(self):
        return json.dumps(self.init_parameters)

    def _generate_fig(self):
        debug=False
        notif=200
        try:
            start=time.time()
            data=request.get_data()
            parameters=json.loads(data.decode())
            if debug:print_file(parameters)

            t0,t1=[pd.Timestamp(t,tz='CET') for t in parameters['timerange'].split(' - ')]
            tag_x=parameters['x']

            if debug:print_file('t0,t1:',t0,t1)
            tags = parameters['tags']
            if not tag_x.lower()=='time':tags+=[tag_x]
            if parameters['categorie'] in self.init_parameters['categories']:
                tags+=self.cfg.conf.tag_categories[parameters['categorie']]
            if debug:print_file('alltags:',tags)
            rs,rsMethod=parameters['rs_time'],parameters['rs_method']

            pool='auto'
            ####### determine if it should be loaded with COARSE DATA or fine data
            if pd.to_timedelta(rs)>=pd.Timedelta(seconds=self.rs_min_coarse) or t1-t0>pd.Timedelta(days=self.nb_days_min_coarse):
                pool='coarse'
                df = self.cfg.load_coarse_data(t0,t1,tags,rs=rs,rsMethod=rsMethod)
            else:
                if debug :print_file(tags)
                df = self.cfg.loadtags_period(t0,t1,tags,rsMethod=rsMethod,rs=rs,checkTime=False,pool=pool)
                if debug :print_file(df)
            if df.empty:
                notif=NOTIFS['no_data']
                raise Exception('no data')

            ####### check that the request does not have TOO MANY DATAPOINTS
            nb_datapoints=len(df)*len(df.columns)
            if nb_datapoints>self.max_nb_pts:
                df=self.cfg.auto_resample_df(df,self.max_nb_pts)
                new_rs=df.index.freq.freqstr.replace('S',' seconds')
                notif=NOTIFS['too_many_datapoints'].replace('XXX',str(nb_datapoints//1000)+' ').replace('YYY',new_rs).replace('AAA',str(self.max_nb_pts//1000))
            if debug:print_file(df)

            if not tag_x.lower()=='time':
                df.index=df[tag_x]
                fig=self.plot_function(df)
                fig.update_traces(hovertemplate='  x:%{x:.1f}<br>  y:%{y:.1f}')
                fig.update_layout(xaxis_title=tag_x+ '('+self.cfg.getUnitofTag(tag_x) + ')')
                fig.update_traces(mode='markers')
            else:
                fig=self.plot_function(df)
            fig.update_layout(width=1260,height=750,legend_title='tags')
            self.log_info(computetimeshow('fig generated with pool =' + str(pool),start))

        except:
            if notif==200:
                notif='figure_generation_impossible'
                error={'msg':' problem in the figure generation with generate_fig','code':1}
                notif=NOTIFS[notif]
                self.notify_error(sys.exc_info(),error)
            fig=go.Figure()
        res={'fig':fig.to_json(),'notif':notif}
        return jsonify(res)

    def _export2excel(self):
        try:
            start=time.time()
            data=request.get_data()
            fig=json.loads(data.decode())
            baseName='data'
            dfs = [pd.Series(trace['y'],index=trace['x'],name=trace['name']) for trace in fig['data']]
            df = pd.concat(dfs,axis=1)
            df.index = [pd.Timestamp(t) for t in df.index]
            t0,t1 = fig['layout']['xaxis']['range']
            df = df[(df.index>=t0) & (df.index<=t1)]

            dateF=[pd.Timestamp(t).strftime('%Y-%m-%d %H_%M') for t in [t0,t1]]
            filename = 'static/tmp/' + baseName +  '_' + dateF[0]+ '_' + dateF[1]+'.xlsx'
            if isinstance(df.index,pd.core.indexes.datetimes.DatetimeIndex):
                df.index=[k.isoformat() for k in df.index]
            df.to_excel(filename)
            self.log_info(computetimeshow('.xlsx downloaded',start))
            res={'status':'ok','filename':filename}
        except:
            error={'msg':'service export2excel not working','code':3}
            self.notify_error(sys.exc_info(),error)
            res={'status':'failed','notif':NOTIFS['excel_generation_impossible']}
        return jsonify(res)

    def _send_names(self):
        try:
            data=request.get_data()
            data=json.loads(data.decode())
            new_names=self.cfg.toogle_tag_description(data['tags'],data['mode'])
            print(data['mode'])
            return pd.Series(new_names).to_json()
        except:
            error={'msg':'impossible to send the description names','code':1}
            self.notify_error(sys.exc_info(),error)
            return error,201

class StaticDashboard(Dashboard):
    def __init__(self,*args,**kwargs):
        '''
        see Dashboard
        '''
        Dashboard.__init__(self,*args,**kwargs)
        self.rs_min_coarse=100000000
        self.nb_days_min_coarse=100000
