from flask import Flask,Blueprint,request,session,render_template,send_file
from subprocess import check_output
import json,os,sys,glob,time,traceback
import numpy as np,pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from string import ascii_letters,digits
from sylfenUtils.comUtils import (timenowstd,computetimeshow)

class Dashboard():
    def __init__(self,cfg,log_dir,root_path,initial_tags=[],
        plot_function=px.line,app_name='',helpmelink='',
        log_versions='',init_parameters={},version_dashboard=''):
        cfg.styles = ['default'] + cfg.utils.styles
        self.fig_wh=780
        self.cfg=cfg
        self.log_dir=log_dir
        self.app_name=app_name
        self.root_path=root_path
        self.initial_tags=initial_tags
        self.plot_function=plot_function
        self.infofile_name  = log_dir+'app.log';
        self.helpmelink=helpmelink
        self.log_versions = log_versions
        self.version_dashboard = version_dashboard
        start_msg=timenowstd() + ' '*10+ 'starting '+app_name + ' dashboard\n'.upper()+'*'*60+'\n'
        with open(self.infofile_name,'w') as logfile:logfile.write(start_msg)
        self.errorfile_name = log_dir+'app.err';
        with open(self.errorfile_name,'w') as logfile:logfile.write(start_msg)
        self.app = Flask(__name__,root_path=self.root_path)

        #### initial parameters
        init_par_keys=list(init_parameters.keys())
        if not 'all_tags' in init_par_keys:init_parameters['all_tags']=self.cfg.getTagsTU('')
        if not 'styles' in init_par_keys:init_parameters['styles']=self.cfg.styles
        if not 'categories' in init_par_keys:init_parameters['categories']=cfg.usefulTags.index.to_list()
        if not 'rsMethods' in init_par_keys:init_parameters['rsMethods']=cfg.methods
        if not 'tags' in init_par_keys:init_parameters['tags']=[]
        if not 'fig_name' in init_par_keys:init_parameters['fig_name']='prout'
        if not 'rs' in init_par_keys:init_parameters['rs']='60s'
        if not 'time_window' in init_par_keys:init_parameters['time_window']='120'
        if not 'title' in init_par_keys:init_parameters['title']=app_name
        if not 'delay_minutes' in init_par_keys:init_parameters['delay_minutes']=0
        self.init_parameters=init_parameters

        # ###############
        #    ROUTING    #
        # ###############
        @self.app.route('/'+self.app_name, methods=['GET'])
        def main_viewport():
            return render_template('dashboard.html',
                helpmelink=self.helpmelink,
                version_title=self.app_name+' '+self.version_dashboard,
                # log_versions=self.log_versions
                )

        @self.app.route('/init', methods=['GET'])
        def init_dashboard():
            return self.init_dashboard()

        @self.app.route('/generate_fig', methods=['POST'])
        def generate_fig():
            return self.generate_fig()

        @self.app.route('/export2excel', methods=['POST'])
        def export2excel():
            return self.export2excel()

        @self.app.route('/send_description_names',methods=['POST'])
        def send_names():
            return self.send_names()

    # ###################
    #    MANAGE LOGS    #
    # ###################
    def log_info(self,msg):
        with open(self.infofile_name,'a') as loginfo_file:
            loginfo_file.write('-'*60 +'\n'+ msg +'\n')
            loginfo_file.write('-'*60+'\n')

    def notify_error(self,tb,error):
        with open(self.errorfile_name,'a') as logerror_file:
            logerror_file.write('-'*60 +'\n'+timenowstd()+' '*10 + error['msg']+'\n')
            traceback.print_exception(*tb,file=logerror_file)
            logerror_file.write('-'*60+'\n')

    # ###################
    #    FUNCTIONS      #
    # ###################
    def init_dashboard(self):
        return json.dumps(self.init_parameters)

    def generate_fig(self):
        debug=False
        try:
            start=time.time()
            data=request.get_data()
            parameters=json.loads(data.decode())
            if debug:
                print('+'*100 + '\n')
                for k,v in parameters.items():print(k,':',v)
                print('+'*100 + '\n')

            t0,t1=[pd.Timestamp(t,tz='CET') for t in parameters['timerange'].split(' - ')]
            # t0=pd.Timestamp('2022-02-20 10:00',tz='CET')
            # t0,t1=[t-pd.Timedelta(days=47) for t in [t0,t1]]

            if debug:print('t0,t1:',t0,t1)
            tags = parameters['tags']
            if parameters['categorie'] in self.cfg.tag_categories.keys():
                tags+=cfg.tag_categories[parameters['categorie']]
            if debug:print('alltags:',tags)
            rs,rsMethod=parameters['rs_time'],parameters['rs_method']
            # pool=False
            pool='auto'
            df = self.cfg.loadtags_period(t0,t1,tags,rsMethod=rsMethod,rs=rs,checkTime=False,pool=pool,verbose=True)
            # df = self.cfg.loadtags_period(t0,t1,tags,rsMethod=rsMethod,rs=rs,checkTime=False)
            if debug:print(df)
            fig=self.plot_function(df)
            fig.update_layout(width=1260,height=750,legend_title='tags')
            self.log_info(computetimeshow('fig generated with pool ='+str(pool),start))
            return fig.to_json(),200
        except:
            error={'msg':'impossible to generate figure','code':1}
            self.notify_error(sys.exc_info(),error)
            fig=go.Figure()
        return error,201

    def export2excel(self):
        try:
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
            # self.log_info(computetimeshow('.xlsx downloaded',start))
            return filename
        except:
            error={'msg':'service export2excel not working','code':3}
            self.notify_error(sys.exc_info(),error)
            return error

    def send_names(self):
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
