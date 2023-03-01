import os
import subprocess as sp

class Services_creator():
    def __init__(self,gaia_conf,url_dashboard=None,port=15000,user='sylfen'):
        """
        Create script files for the dumper, the coarse parker, the dashboard and the heartbeat(notifications service) as well
        the services conf files to enable/start with systemctl those applications. The reverse proxy is also configured.
        :Parameters:
        ------------
            - gaia_conf[GAIA] : the conf of the gaia instance of the project
            - folder_project[str] : the folder where the script files should be stored.
            - url[str]: the url of the dashboard
            - port[int]: the port on which the dashboard will be served.
            - user[str]: the user owner of the services.
        """
        self.user=user
        self.name_env='.env'
        # self.project_name=project_name
        self.project_name=gaia_conf.project_name
        self.folder_project=gaia_conf.folder_project
        self.folder_tmp='/tmp'
        self.folder_nginx='/etc/nginx'
        self.folder_systemd='/etc/systemd/system'
        self.folder_templates=os.path.dirname(__file__)
        # self.folder_project=os.path.join("/home",self.user,self.project_name+'_user')
        self.gaia_instance=gaia_conf.gaia_name
        self.url_dashboard=url_dashboard
        if self.url_dashboard is None:
            self.url_dashboard='www.'+self.project_name+'_sylfen.com'
        self.port=port
        self.services={
            'dumper': {
                'DESCRIPTION':'Data dumper of ' + self.project_name,
                'appname':'python',
                'script_name':self.project_name+'_dumper.py',
                'function':self.gaia_instance+'.start_dumping()'
            },
            'dashboard': {
                'DESCRIPTION':'dashboard of ' + self.project_name,
                'appname':'gunicorn',
                'script_name':'-b localhost:'+str(self.port)+ ' -w 2 '+ self.project_name +'_dashboard:app',
                'function':'app='+self.gaia_instance+'._dashboard.app'
            },
            'coarse_parker': {
                'DESCRIPTION':'parker of ' + self.project_name,
                'appname':'python',
                'script_name':self.project_name+'_coarse_parker.py',
                'function':self.gaia_instance+'.start_dumping_coarse()'
            },
            'heartbeat': {
                'DESCRIPTION':'Heatbeat of ' + self.project_name,
                'appname':'python',
                'function':self.gaia_instance+'.start_watchdog()',
                'script_name':self.project_name+'_heartbeat.py',
            },
        }
        self.filenames=self._generate_filenames()
        self.create_files()
        self.generate_sudo_bash_file()


    def _generate_filenames(self):
        folder_nginx=os.path.join(self.folder_nginx,'sites-available')
        file_nginx=self.url_dashboard + '.conf'
        filenames={
            'nginx_file':file_nginx,
            'bash_file':'start_up_'+self.project_name+'.sh'
        }
        for name_service in self.services.keys():
            filenames[name_service+'_service']=self.project_name + '_' + name_service +'.service'
            filenames[name_service+'_script']=self.project_name + '_' + name_service +'.py'
        return filenames

    def create_files(self):
        self._create_the_nginx_file()
        for name_service,infos in self.services.items():
            file_script=self._create_script_file(name_service,infos['function'])
            self._create_service_file(name_service,file_script)

    def _create_script_file(self,name_service,function_name):
        template_script="""from PROJECT_NAME import GAIA_INSTANCE\n"""
        template_script=template_script.replace('PROJECT_NAME',self.project_name).replace("GAIA_INSTANCE",self.gaia_instance)

        service_script=template_script + function_name

        file_script=os.path.join(self.folder_tmp,self.filenames[name_service+'_script'])
        with open(file_script,'w') as f:f.write(service_script)

    def _create_service_file(self,service_name,name_script):
        ### READ THE CONTENT OF THE SERVICE TEMPLATE FILE ####
        filename=os.path.join(os.path.dirname(__file__),'template_service.txt')
        with open(filename,'r') as f:content=''.join(f.readlines())

        infos=self.services[service_name]
        ### adjust the content of the file.service
        serviceContent=content.replace('DESCRIPTION',infos['DESCRIPTION']).replace('USER',self.user)
        serviceContent=serviceContent.replace('PROJECT_FOLDER',self.folder_project).replace('NAME_ENV',self.name_env)
        serviceContent=serviceContent.replace('SERVICE_PROJECT_NAME',infos['script_name']).replace('APP_NAME',infos['appname'])

        file_service=os.path.join('/tmp',self.filenames[service_name + '_service'])
        ### write the content of the service file
        with open(file_service,'w') as f:f.write(serviceContent)

    def _create_the_nginx_file(self):
        ### READ THE CONTENT OF THE NGINX TEMPLATE FILE ####
        filename=os.path.join(os.path.dirname(__file__),'template_url.conf')
        with open(filename,'r') as f:content=''.join(f.readlines())
        nginxContent=content.replace('PROJECT_NAME',self.url_dashboard).replace('PORT',str(self.port))
        ### write the content of the nginx file
        nginx_file=os.path.join(self.folder_tmp,self.filenames['nginx_file'])
        with open(nginx_file,'w') as f:f.write(nginxContent)

    def generate_sudo_bash_file(self):
        nginx_folder_available=os.path.join(self.folder_nginx,'sites-available')
        nginx_folder_enabled=os.path.join(self.folder_nginx,'sites-enabled')
        nginx_tmp=os.path.join(self.folder_tmp,self.filenames['nginx_file'])
        ### copy the reverse_proxy.conf file to nginx folder
        cmd=['### copy the reverse_proxy.conf file to nginx folder']
        cmd+=['cp ' + nginx_tmp + ' ' + nginx_folder_available]
        cmd+=['\n']
        ### create symbolic link to enabled sites
        cmd+=['### create symbolic link to enabled sites']
        cmd+=['ln -s ' + os.path.join(nginx_folder_available,) + ' ' +  nginx_folder_enabled]
        cmd+=['\n']

        for name_service in self.services.keys():
            cmd+=['### copy the service file to systemd folder ']
            cmd+=['cp ' + os.path.join(self.folder_tmp,self.filenames[name_service+'_service']) + ' ' + self.folder_systemd]
            cmd+=['### copy the script file to the project folder ']
            cmd+=['cp ' + os.path.join(self.folder_tmp,self.filenames[name_service+'_script']) + ' ' + self.folder_project]
            service_file=self.filenames[name_service+'_service']
            cmd+=['### enable and start the service']
            cmd+=['systemctl enable '+service_file]
            cmd+=['systemctl start '+service_file]
            cmd+=['\n']

        #### concatenate the content of the file
        bash_script='\n'.join(cmd)
        bash_file=os.path.join(self.folder_tmp,self.filenames['bash_file'])
        ### create the bash file
        with open(bash_file,'w') as f:f.write(bash_script)
        ##### display the command to execute
        print('please run the command\n'.rjust(50),'-'*60,'\n')
        print(('sudo sh '+bash_file).rjust(50))

    def show_file_content(self,file):
        sp.run(['cat',os.path.join(self.folder_tmp,self.filenames[file])])

class Conf():
    pass
gaia_conf=Conf()
gaia_conf.project_name='quickPro'
gaia_conf.folder_project='/home/dorian/sylfen/quickPro'
gaia_conf.gaia_name='gaia_test'
s=Services_creator(gaia_conf)
sys.exit()

##### TESTS ####
def tests():
    s.filenames
    s.show_file_content('nginx_file')
    s.show_file_content('bash_file')
    s.show_file_content('dumper_script')
    s.show_file_content('dumper_service')
    s.show_file_content('dashboard_script')
    s.show_file_content('dashboard_service')
