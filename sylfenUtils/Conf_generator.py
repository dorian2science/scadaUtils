import pickle,os,sys,re,subprocess as sp
import pandas as pd
from sylfenUtils.comUtils import print_file

def create_folder_if_not(folder_path,*args,**kwargs):
    if not os.path.exists(folder_path):
        os.mkdir(folder_path)
        print_file('folder ' + folder_path + ' created!',*args,**kwargs)

def create_sql_table(connParameters,db_table):
    connReq = ''.join([k + "=" + v + " " for k,v in connParameters.items()])
    import psycopg2
    conn = psycopg2.connect(connReq)
    cur  = conn.cursor()
    # creation table
    sqlR='create table if not exists ' + db_table + ' ( timestampz timestamp with time zone, tag varchar ( 200 ), value varchar ( 200 ));'
    cur.execute(sqlR)
    cur.close()
    conn.commit()
    conn.close()

class Conf_generator():
    '''
    Class to generate a configuration with default folders and automatic creation of
    user_setting file. For a project it is supposed to make a children class a build
    a specific **generate_conf** function to add specific configuration features of the project.
    '''
    def __init__(self,project_name,project_folder=None):
        self.project_name=project_name
        self._lib_sylfenUtils_path=os.path.dirname(__file__) + '/'

        if project_folder is None:project_folder=os.getenv('HOME')+'/'+project_name+'_user/'

        self.project_folder=project_folder

        #### if the PROJECT FOLDER does not exists create it
        create_folder_if_not(self.project_folder)

        self._file_conf_pkl=self.project_folder+'/conf_' + self.project_name + '.pkl'
        self.file_parameters=self.project_folder + '/parameters.conf'

        ## copy the DEFAULT PARAMETERS file as the parameters File into the user folder
        if not os.path.exists(self.file_parameters):
            _default_file_parameters= self._lib_sylfenUtils_path + '/conf/parameters.default.conf'
            sp.run('cp ' + _default_file_parameters + ' ' + self.file_parameters,shell=True)

        ############# LOAD THE PARAMETERS ############
        with open(self.file_parameters,'r') as f :
            parameters=f.read()

        for l in parameters.split('\n'):
            t=re.search('(^[^#].*)=(.*)',l)
            if not t is None:
                t=t.groups()
                if len(t)==2:
                    setattr(self,t[0].strip(),t[1].strip())

        self.SIMULATOR=bool(self.SIMULATOR)
        self.TEST_ENV=bool(self.TEST_ENV)
        self.PARKING_TIME=eval(self.PARKING_TIME)
        self.DB_PARAMETERS = {
            'host'     : self.db_host,
            'port'     : self.db_port,
            'dbname'   : self.dbname,
            'user'     : self.db_user,
            'password' : self.db_password
        }
        del self.db_host,self.db_port,self.dbname,self.db_user,self.db_password

        ##### dashboard delay
        if not self.TMAX is None:
            td=pd.Timestamp.now(self.TZ_RECORD)-pd.Timestamp(self.TMAX,tz=self.TZ_RECORD)
            self.DASHBOARD_DELAY_MINUTES = int(td.total_seconds()/60)

        ###### DATA FOLDER PKL ######
        if self.FOLDERPKL=='default':self.FOLDERPKL=self.project_folder+project_name+'_daily/'
        create_folder_if_not(self.FOLDERPKL)
        ###### LOG FOLDER ######
        if self.LOG_FOLDER=='default':self.LOG_FOLDER=self.project_folder+'log/'
        create_folder_if_not(self.LOG_FOLDER)

        ###### create the REALTIME TABLE in the database if it does not exist
        create_sql_table(self.DB_PARAMETERS,self.DB_TABLE)

        ###### load the rest of the Conf
        self.__load_conf()

    def generate_conf(self):
        '''
        This is the function to create for a new project. It should return a dictionnary of all the objects needed.
        '''
        return {}

    def create_dashboard_links(self,root_folder):
        '''
        create the static and templates symbolic in the root folder of the dashboard to be able to run the Dashboard instance.
        '''
        import subprocess as sp
        import sylfenUtils

        sylfenUtils_env_dir=os.path.dirname(sylfenUtils.__file__)
        templates_dir=sylfenUtils_env_dir + '/templates'
        templates_folder=root_folder + '/templates'
        if os.path.exists(templates_folder):os.remove(templates_folder)
        sp.run('ln -s '+templates_dir + ' ' + root_folder,shell=True)
        static_folder=root_folder+'/static/'
        if not os.path.exists(static_folder):os.mkdir(static_folder) #create folder if it does not exist
        self.lib_dir=sylfenUtils_env_dir + '/static/lib'
        lib_folder=static_folder + '/lib'
        if os.path.exists(lib_folder):os.remove(lib_folder)
        sp.run('ln -s ' + self.lib_dir + ' ' + static_folder,shell=True)


    ####### private ####
    def __load_conf(self):
        import time,pickle
        _appdir    = os.path.dirname(os.path.realpath(__file__))
        exists_conf=False
        if os.path.exists(self._file_conf_pkl):
            exists_conf=True
            conf_objs= pickle.load(open(self._file_conf_pkl,'rb'))
            # exists_conf=False
        if not exists_conf:
            f = open(self._file_conf_pkl,'wb')
            start=time.time()
            print('generating configuration files and store it in :',self._file_conf_pkl)
            conf_objs=self.generate_conf()
            pickle.dump(conf_objs,f)
            f.close()
            print('configuration file generated in  : '+ str(time.time()-start)+' seconds.')

        for k,v in conf_objs.items():
            setattr(self,k,v)

    def __loadcolorPalettes(self):
        # colPalettes = Utils().colorPalettes
        colPalettes = pickle.load('conf/palettes.pkl')
        colPalettes['reds']     = colPalettes['reds'].drop(['Misty rose',])
        colPalettes['greens']   = colPalettes['greens'].drop(['Honeydew',])
        colPalettes['blues']    = colPalettes['blues'].drop(['Blue (Munsell)','Powder Blue','Duck Blue','Teal blue'])
        colPalettes['magentas'] = colPalettes['magentas'].drop(['Pale Purple','English Violet'])
        colPalettes['cyans']    = colPalettes['cyans'].drop(['Azure (web)',])
        colPalettes['yellows']  = colPalettes['yellows'].drop(['Light Yellow',])
        ### manual add colors
        colPalettes['blues'].loc['Indigo']='#4B0082'
        #### shuffle them so that colors attribution is random
        for c in colPalettes.keys():
            colPalettes[c]=colPalettes[c].sample(frac=1)
        return colPalettes

    def __load_material_dfConstants(self):
        dfConstants = pd.read_excel('conf/data_values.ods',sheet_name='physical_constants',index_col=1)
        cst = {}
        for k in dfConstants.index:
            # setattr(cst,k,dfConstants.loc[k].value)
            cst[k]=dfConstants.loc[k].value
        return cst,dfConstants

    def _buildColorCode(self,colorPalettes,dfplc,unitDefaultColors):
        dftagColorCode = pd.read_excel(FILECONF_SMALLPOWER,sheet_name='tags_color_code',index_col=0,keep_default_na=False)
        from plotly.validators.scatter.marker import SymbolValidator
        raw_symbols = pd.Series(SymbolValidator().values[2::3])
        listLines = pd.Series(["solid", "dot", "dash", "longdash", "dashdot", "longdashdot"])
        allHEXColors=pd.concat([k['hex'] for k in colorPalettes.values()])
        ### remove dupplicates index (same colors having different names)
        allHEXColors=allHEXColors[~allHEXColors.index.duplicated()]

        dfplc
        alltags = list(dfplc.index)
        dfplc.UNITE=dfplc.UNITE.fillna('u.a.')
        def assignRandomColor2Tag(tag):
            unitTag  = dfplc.loc[tag,'UNITE'].strip()
            shadeTag = unitDefaultColors.loc[unitTag].squeeze()
            color = colorPalettes[shadeTag]['hex'].sample(n=1)
            return color.index[0]

        # generate random color/symbol/line for tags who are not in color_codeTags
        listTags_wo_color=[k for k in alltags if k not in list(dftagColorCode.index)]
        d = {tag:assignRandomColor2Tag(tag) for tag in listTags_wo_color}
        dfRandomColorsTag = pd.DataFrame.from_dict(d,orient='index',columns=['colorName'])
        dfRandomColorsTag['symbol'] = pd.DataFrame(raw_symbols.sample(n=len(dfRandomColorsTag),replace=True)).set_index(dfRandomColorsTag.index)
        dfRandomColorsTag['line'] = pd.DataFrame(listLines.sample(n=len(dfRandomColorsTag),replace=True)).set_index(dfRandomColorsTag.index)
        # concatenate permanent color_coded tags with color-random-assinged tags
        dftagColorCode = pd.concat([dfRandomColorsTag,dftagColorCode],axis=0)
        # assign HEX color to colorname
        dftagColorCode['colorHEX'] = dftagColorCode.apply(lambda x: allHEXColors.loc[x['colorName']],axis=1)
        dftagColorCode['color_appearance']=''
        return dftagColorCode
