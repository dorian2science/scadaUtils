import pickle,os,sys,re,subprocess as sp,time,shutil
import pandas as pd
from sylfenUtils.comUtils import (print_file,FileSystem,create_folder_if_not)
import psycopg2

FS=FileSystem()

def create_sql_table(connParameters,db_table):
    connReq = ''.join([k + "=" + v + " " for k,v in connParameters.items()])
    conn = psycopg2.connect(connReq)
    cur  = conn.cursor()
    # creation table
    sqlR='create table if not exists ' + db_table + ' ( timestampz timestamp with time zone, tag varchar ( 200 ), value varchar ( 200 ));'
    cur.execute(sqlR)
    cur.close()
    conn.commit()
    conn.close()

class Conf_generator():
    def __init__(self,project_name,function_generator,project_folder=None):
        '''
        Class to generate a configuration with default folders and automatic creation of
        user_setting file.

        Loading of the configuation will be automatic whether the configuration file already exists or not.

        Parameters
        -----------------
        - project_name:name of the project. Important if default folder are being used and project_folder is None.
        - function_generator : function that generates a list of objects needed for a project. Should return a dictionnary with at least following keys:
            * df_devices : a dataframe containing the information of the devices (device_name,protocole,IP,port,table_link) and byte_order word_order for modbus protocole.
            * dfplc      : dataframe with columns DESCRIPTION, UNITE, DATAYPE, FREQUENCY and tags as index.
            * and/or modbus_maps(only if there are modbus devices): dictionnary. Keys are the names of devices and value is the corresponding modbus map.
        - project_folder(optional) : path of the folder where the parameters.conf file, the log folder, the dashboard ...
        are going to be stored.
        '''
        self.project_name=project_name
        self._function_generator=function_generator
        self._lib_sylfenUtils_path=os.path.dirname(__file__)

        homepath = {'posix': 'HOME', 'nt':'homepath'}
        if project_folder is None:project_folder=os.path.join(os.getenv(homepath[os.name]),project_name+'_user')

        self.project_folder=project_folder

        #### if the PROJECT FOLDER does not exists create it
        create_folder_if_not(self.project_folder)

        self._file_conf_pkl=os.path.join(self.project_folder,'conf_' + self.project_name + '.pkl')
        self.file_parameters=os.path.join(self.project_folder,'parameters.conf')

        ## copy the DEFAULT PARAMETERS file as the parameters File into the user folder
        if not os.path.exists(self.file_parameters):
            _default_file_parameters= os.path.join(self._lib_sylfenUtils_path,'conf/parameters.default.conf')
            # sp.run('cp ' + _default_file_parameters + ' ' + self.file_parameters,shell=True)
            shutil.copy(_default_file_parameters,self.file_parameters)

        ############# LOAD THE PARAMETERS ############
        with open(self.file_parameters,'r') as f :
            parameters=f.read()

        for l in parameters.split('\n'):
            t=re.search('(^[^#].*)=(.*)',l)
            if not t is None:
                t=t.groups()
                if len(t)==2:
                    setattr(self,t[0].strip(),t[1].strip())

        self.SIMULATOR=self.SIMULATOR=='True'
        self.TEST_ENV=self.TEST_ENV=='True'


        ##### dashboard delay
        self.DASHBOARD_DELAY_MINUTES=0
        if self.TEST_ENV:
            try:
                td=pd.Timestamp.now(self.TZ_RECORD)-pd.Timestamp(self.TMAX,tz=self.TZ_RECORD)
                self.DASHBOARD_DELAY_MINUTES = int(td.total_seconds()/60)
            except:
                print('='*60,'\n','impossible to parse TMAX in your conf file:\n',self.file_parameters,
                '\nbecause its value is : \n',self.TMAX,'\n and is not recognized as timestamp\n','='*60)

        ###### DATA FOLDER PKL ######
        if self.FOLDERPKL=='default':self.FOLDERPKL=os.path.join(self.project_folder,project_name+'_daily')
        create_folder_if_not(self.FOLDERPKL)
        ###### LOG FOLDER ######
        if self.LOG_FOLDER=='default':self.LOG_FOLDER=os.path.join(self.project_folder,'log/')
        create_folder_if_not(self.LOG_FOLDER)


        ###### load the rest of the Conf
        self._load_conf()

    def generate_conf(self):
        f = open(self._file_conf_pkl,'wb')
        start=time.time()
        print('generating configuration files and store it in :',self._file_conf_pkl)
        conf_objs=self._function_generator()

        is_dfplc=False
        #### make sure the user has created a dfplc attribute.
        #### if not try to create it from modbus maps.
        if 'dfplc' not in conf_objs.keys():
            if 'modbus_maps' in conf_objs.keys():
                from sylfenUtils.comUtils import dfplc_from_modbusmap
                plcs_mb={device_name:dfplc_from_modbusmap(map) for device_name,map in conf_objs['modbus_maps'].items()}

                if not 'plcs' in conf_objs.keys():
                    conf_objs['plcs']={}

                conf_objs['plcs'].update(plcs_mb)
                conf_objs['dfplc']=pd.concat(conf_objs['plcs'].values())
            else:
                print('-'*60,'\nIt looks like your function_generator does not include a valid dfplc attribute or modbus_maps attribute.')
                print('A standard dfplc attribute is mandatory to be able to use all the methods and features.\n','-'*60)
                return
        conf_objs['listUnits'] = conf_objs['dfplc'].UNITE.dropna().unique().tolist()
        pickle.dump(conf_objs,f)
        f.close()
        print('configuration file generated in  : '+ str(time.time()-start)+' seconds.')
        return conf_objs

    ####### private ####
    def _load_conf(self):
        _appdir    = os.path.dirname(os.path.realpath(__file__))
        exists_conf=False
        if os.path.exists(self._file_conf_pkl):
            print('configuration file',self._file_conf_pkl,'found!')
            exists_conf=True
            try:
                conf_objs= pickle.load(open(self._file_conf_pkl,'rb'))
                print('configuration file loaded !')
            except:
                print('-'*60,'\nIMPOSSIBLE to load the configuration pkl file ',self._file_conf_pkl,'!\n','-'*60,'\n')
                exists_conf=False
        if not exists_conf:
            conf_objs=self.generate_conf()

        for k,v in conf_objs.items():
            setattr(self,k,v)

    def _loadcolorPalettes(self):
        # colPalettes = Utils().colorPalettes
        colPalettes = pickle.load(open(os.path.join(os.path.dirname(__file__),'conf','palettes.pkl'),'rb'))
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

    def _load_material_dfConstants(self):
        dfConstants = pd.read_excel(os.path.join(os.path.dirname(__file__),'conf','data_values.ods'),
            sheet_name='physical_constants',index_col=1)
        cst = {}
        for k in dfConstants.index:
            cst[k]=dfConstants.loc[k].value
        return cst,dfConstants

    def _buildColorCode(self,user_tag_color,dfplc,unitDefaultColors,verbose=False):
        '''
        assign styles for tags in dfplc using the principle of Guillaume Preaux. One color per unit
        Parameters
        ----------
            - user_tag_color:Dataframe with tag in index and columns colorName with the Name of the color ton. See self.palettes.
            - dfplc:plc dataframe with tags in index.
            - unitDefaultColors: pd.Series with units in index and color. see self.palettes
        '''
        ###### load palettes of color
        self.colorPalettes=self._loadcolorPalettes()

        #### standard styles
        from plotly.validators.scatter.marker import SymbolValidator
        raw_symbols = pd.Series(SymbolValidator().values[2::3])
        listLines = pd.Series(["solid", "dot", "dash", "longdash", "dashdot", "longdashdot"])
        allHEXColors=pd.concat([k['hex'] for k in self.colorPalettes.values()])
        ### remove dupplicates index (same colors having different names)
        allHEXColors=allHEXColors[~allHEXColors.index.duplicated()]

        alltags = list(dfplc.index)
        dfplc.UNITE=dfplc.UNITE.fillna('u.a.')
        def assignRandomColor2Tag(tag):
            if verbose:print(tag)
            unitTag  = dfplc.loc[tag,'UNITE'].strip()
            shadeTag = unitDefaultColors.loc[unitTag]
            if not isinstance(shadeTag,str):
                shadeTag = unitDefaultColors.loc[unitTag].squeeze()

            color = self.colorPalettes[shadeTag]['hex'].sample(n=1)
            return color.index[0]

        # generate random color/symbol/line for tags who are not in color_codeTags
        listTags_wo_color=[k for k in alltags if k not in list(user_tag_color.index)]
        d = {tag:assignRandomColor2Tag(tag) for tag in listTags_wo_color}
        dfRandomColorsTag = pd.DataFrame.from_dict(d,orient='index',columns=['colorName'])
        dfRandomColorsTag['symbol'] = pd.DataFrame(raw_symbols.sample(n=len(dfRandomColorsTag),replace=True)).set_index(dfRandomColorsTag.index)
        dfRandomColorsTag['line'] = pd.DataFrame(listLines.sample(n=len(dfRandomColorsTag),replace=True)).set_index(dfRandomColorsTag.index)
        # concatenate permanent color_coded tags with color-random-assinged tags
        user_tag_color = pd.concat([dfRandomColorsTag,user_tag_color],axis=0)
        # assign HEX color to colorname
        user_tag_color['colorHEX'] = user_tag_color.apply(lambda x: allHEXColors.loc[x['colorName']],axis=1)
        user_tag_color['color_appearance']=''
        return user_tag_color

    ####### public useful ####
    def getdaysnotempty(self):
        return FS.get_parked_days_not_empty(self.FOLDERPKL)

    def connect2db(self):
        connReq = ''.join([k + "=" + v + " " for k,v in self.DB_PARAMETERS.items()])
        return psycopg2.connect(connReq)

    def getUsefulTags(self,usefulTag):
        if usefulTag in self.usefulTags.index:
            category = self.usefulTags.loc[usefulTag,'Pattern']
            return self.getTagsTU(category)
        else:
            return []

    def getUnitofTag(self,tag):
        return FS.getUnitofTag(tag,self.dfplc)

    def getTagsTU(self,patTag,units=None,*args,**kwargs):
        if not units : units = self.listUnits
        return FS.getTagsTU(patTag,self.dfplc,units,*args,**kwargs)

class Conf_generator_RT(Conf_generator):
    def __init__(self,*args,**kwargs):
        Conf_generator.__init__(self,*args,**kwargs)
        self.PARKING_TIME=eval(self.PARKING_TIME)
        self.DB_PARAMETERS = {
            'host'     : self.db_host,
            'port'     : self.db_port,
            'dbname'   : self.dbname,
            'user'     : self.db_user,
            'password' : self.db_password
        }
        del self.db_host,self.db_port,self.dbname,self.db_user,self.db_password

        ###### create the REALTIME TABLE in the database if it does not exist
        create_sql_table(self.DB_PARAMETERS,self.DB_TABLE)
