# #######################
# #  VERISONS MANAGER    #
# #######################
import collections
from . import comUtils
from .comUtils import (print_file)
from .utilsD import Utils
import glob,re,pandas as pd,os,time,pickle
sort_list=lambda x:list(pd.Series(x).sort_values())
import plotly.express as px
import plotly.graph_objects as go
import subprocess as sp

class VersionsManager():
    def __init__(self,folderPkl,dir_plc,file_transition,pattern_plcFiles='*plc*.csv',ds=None):
        '''
        plc versions filenames should be of the form x.y or x with the letter v or version in front of it.
        '''
        self._streamer     = comUtils.Streamer()
        self._fs           = comUtils.FileSystem()
        self.dir_plc       = dir_plc
        self._versionFiles = glob.glob(self.dir_plc+pattern_plcFiles)
        self.versions      = {re.search(r'\d+(\.\d+)?',f.split('/')[-1]).group():f for f in self._versionFiles}
        self.folderPkl     = folderPkl
        self.file_transitions = file_transition
        self.transitions    = pd.ExcelFile(self.file_transitions).sheet_names
        self._file_versionning = self.dir_plc+'versions_data.pkl'
        self.versions = pd.DataFrame([{'file':f,'version':v} for v,f in self.versions.items()]).set_index('version').sort_index()
        self.versions.index=self.versions.index.astype(float)
        self._ds=ds
        if not os.path.exists(self._file_versionning):self.generate_versionning_data()
        [self.df_plcs,self.df_transition_rules] = Utils().loads_pickle(self._file_versionning)

    ##########################
    # private init functions #
    ##########################
    def _load_transition_rules(self):
        rules={}
        for t in self.transitions:
            tmp=pd.read_excel(self.file_transitions,sheet_name=t)
            idx_nana = tmp[tmp.isna().all(axis=1)].index.min()
            rules[t]=tmp.iloc[:idx_nana,:]
        return rules

    def _load_PLC_versions(self):
        print_file('Start reading all .xlsm files....')
        df_plcs = {}
        for v,f in self.versions['file'].to_dict().items():
            print_file(f)
            df_plcs[v] = pd.read_excel(f,index_col=0)
        print_file('')
        print_file('concatenate tags of all dfplc verion')
        return df_plcs

    def _load_missing_tags_map(self,d0=None,d1=None,v0=None,v1=None):
        list_days=self._fs.listfiles_folder(self.folderPkl)
        list_days.sort()

        if d0 is None:d0=list_days[0]
        if d1 is None:d1=list_days[-1]
        vi=self.versions.index
        if v0 is None:v0=vi[0]
        if v1 is None:v1=vi[-1]

        versions=[k for k in vi[(vi>=float(v0))&(vi<=float(v1))]]
        list_days=[d for d in list_days if d in pd.date_range(d0,d1)]

        df={}
        for d in list_days:
            tmp=self.missing_tags_versions(d,versions)
            df[d]=pd.Series({k:len(v) for k,v in tmp.items()})
        return pd.concat(df,axis=1).T


    #####################
    # public methods    #
    #####################
    def generate_versionning_data(self,plcs=True,transition_rules=True):
        print('generating versionning data and store in :'+self._file_versionning)
        if os.path.exists(self._file_versionning):[dfplcs,df_transition_rules] = Utils().loads_pickle(self._file_versionning)

        start=time.time()

        if plcs:dfplcs=self._load_PLC_versions()

        if transition_rules:transition_rules=self._load_transition_rules()

        f = open(self._file_versionning,'wb')
        pickle.dump(dfplcs,f)
        pickle.dump(transition_rules,f)
        # self.df_nbTagsFolder = loadconfFile(self.file_df_nbTags,self.load_nbTags_folders,buildFiles[1])
        # self.map_missingTags,self.map_missingTags_len = loadconfFile(self.file_map_missingTags,self.load_missingTags_versions,buildFiles[2])
        f.close()
        [self.df_plcs,self.df_transition_rules] = Utils().loads_pickle(self._file_versionning)
        print('finish loading versionning data \n'+'='*60+'\n')

    def get_rename_tags_map_from_rules(self,transition,show_diagnostique=True):
        def pattern_to_regexp(s,back_ref=False):
            if back_ref:
                return s.apply(lambda x:x.replace('xxx','\\1'))
            else:
                return s.apply(lambda x:x.replace('xxx','(.*)'))

        vold,vnew=[float(k) for k in transition.split('_')]
        df_rules_transition=self.df_transition_rules[transition]

        patterns_new = pattern_to_regexp(df_rules_transition[df_rules_transition['old_pattern'].isna()]['new_pattern']).to_list()
        patterns_old = pattern_to_regexp(df_rules_transition[df_rules_transition['new_pattern'].isna()]['old_pattern']).to_list()


        df_compare=self.compare_plcs(vold,vnew)
        if df_compare.empty:
            print('='*60,'\nLes 2 versions',vold,'et', vnew,'ont exactement les même tags.\n Rien à faire mon ami.')
            sys.exit()
        r=df_compare[[k for k in df_compare.columns if 'removed' in k]].dropna().squeeze(1)
        a=df_compare[[k for k in df_compare.columns if 'added' in k]].dropna().squeeze(1)

        ################################
        #  find tags to add and remove #
        #       from  patterns         #
        ################################
        if len(patterns_new)>0:
            tags_added=pd.concat([a[a.str.contains(pat)] for pat in patterns_new])
        else:
            tags_added=pd.Series([],name=a.name)
        if len(patterns_old)>0:
            tags_removed=pd.concat([r[r.str.contains(pat)] for pat in patterns_old])
        else:
            tags_removed=pd.Series([],name=r.name)

        ##### find tags to rename from patterns
        a2 = a[~a.isin(tags_added)]
        r2 = r[~r.isin(tags_removed)]
        dd=df_rules_transition.dropna()
        patternMap_rename = pd.concat([pattern_to_regexp(dd['old_pattern']),pattern_to_regexp(dd['new_pattern'],True)],axis=1)


        dfs={}
        for x in range(len(patternMap_rename)):
            pat_old,pat_new=patternMap_rename.iloc[x]
            # print(pat_old,'+',pat_new)
            tags2rename=r2[r2.str.contains(pat_old)].to_list()
            dfs[pat_old]=pd.DataFrame({'old_names':tags2rename,'new_names_from_rules':[re.sub(pat_old,pat_new,t) for t in tags2rename]})

        if len(dfs)>0:
            tags_renamed_map=pd.concat(dfs.values())
        else:
            tags_renamed_map=pd.DataFrame({'old_names':[],'new_names_from_rules':[]})


        t1=tags_added.to_frame()
        t1.columns=['new_names_from_rules']
        t1['old_names']=''
        t2=tags_removed.to_frame()
        t2.columns=['old_names']
        t2['new_names_from_rules']=''
        tags_renamed_map=pd.concat([tags_renamed_map,t1,t2])
        tags_renamed_map['in_new_plc']=tags_renamed_map['new_names_from_rules'].isin(a)

        ##### still to explain
        a3 = pd.Series([t for t in a2 if t not in tags_renamed_map['new_names_from_rules'].to_list()],name='still in '+str(vnew))
        r3 = pd.Series([t for t in r2 if t not in tags_renamed_map['old_names'].to_list()],name='still in '+str(vold))
        still2explain=pd.concat([r3,a3],axis=1)


        ######################
        ## show diagnostique #
        ######################
        if show_diagnostique:
            def std_div(h,t,color=None):
                return '<div style="margin:10px;background-color:None">'+'<h2 style="text-align:center">'+h+'</h2>' + t + '</div>\n'

            t1=df_compare.to_html()
            h1='comparaison des fichiers PLCS'
            t2=tags_renamed_map.to_html()
            h2='table de renommage à partir des règles'
            t3=still2explain.to_html()
            h3='tags restants non trouvés par les règles de renommage'

            f=open('/tmp/table.html','w')
            text='<div style="display:flex">\n'+std_div(h1,t1)+std_div(h2,t2)+std_div(h3,t3)+'</div>'
            f.write(text)
            f.close()
            sp.run('firefox /tmp/table.html',shell=True)

        return tags_renamed_map
        sys.exit()

    def compare_plcs(self,vold,vnew):
        plc_old  = self.df_plcs[vold]
        plc_new  = self.df_plcs[vnew]
        if self._ds is None:
            oldtags = list(plc_old.index)
            newtags = list(plc_new.index)
        else:
            oldtags = list(plc_old[plc_old.DATASCIENTISM==self._ds].index)
            newtags = list(plc_new[plc_new.DATASCIENTISM==self._ds].index)

        print(plc_new)
        r = pd.Series([t for t in oldtags if t not in newtags],name='removed_from_' + str(vold))
        a = pd.Series([t for t in newtags if t not in oldtags],name='added_in_' + str(vnew))
        return pd.concat([r,a],axis=1)

    def _find_presence_tags(self,tags,empty_df=True):
        '''
        empty_df : [boolean] if true will return -1 if not in 0 if empty or 1 if in
        '''
        listDays=os.listdir(self.folderPkl)
        df=pd.DataFrame()
        if empty_df:
            for t in tags:
                vals={}
                for d in listDays:
                    vals[d]=-1
                    if t+'.pkl' in os.listdir(self.folderPkl+d):
                        vals[d]=pd.read_pickle(self.folderPkl+d + '/' + t + '.pkl').empty
                df[t]=vals.values()
        else:
            for t in tags:
                df[t] = [True if t+'.pkl' in os.listdir(self.folderPkl+d) else False for d in listDays]
        df=df.mask(df==False,1).mask(df==True,0)
        df.index=listDays
        df=df.sort_index().astype(int)
        return df

    def presence_tags(self,*args,**kwargs):
        df=self._find_presence_tags(*args,**kwargs)

        fig=px.line(df);fig.update_traces(line_shape='hv',mode='lines+markers')
        for k,t in enumerate(fig.data):t['y']=t['y']+0.01*float((k+1)//2)*((-1)**k)

        return fig

    def presence_tags_transition(self,transition,**kwargs):
        tags_renamed_map=self.get_rename_tags_map_from_rules(transition,False)
        df_rename_tags=tags_renamed_map.iloc[:,:-1]
        df_rename_tags.columns=['old_tag','new_tag']

        df_tags_new = self._find_presence_tags(df_rename_tags[(df_rename_tags['old_tag']=='')]['new_tag'].to_list(),**kwargs).melt(ignore_index=False)
        df_tags_new['group'] = 'tag v2(added)'
        df_tags_removed = self._find_presence_tags(df_rename_tags[(df_rename_tags['new_tag']=='')]['old_tag'].to_list(),**kwargs).melt(ignore_index=False)
        df_tags_removed['group']       = 'tag v1(deleted)'
        df_tags_v2_from_v1    = df_rename_tags[df_rename_tags.all(axis=1)]
        df_v2_renamed_from_v1 = self._find_presence_tags(df_tags_v2_from_v1['new_tag'],**kwargs).melt(ignore_index=False)
        df_v2_renamed_from_v1['group'] = 'tag v2 renamed from v1'
        df_v1_renamed_to_v2   = self._find_presence_tags(df_tags_v2_from_v1['old_tag'],**kwargs).melt(ignore_index=False)
        df_v1_renamed_to_v2['group']   = 'tag v1 renamed to v2'

        df = pd.concat([df_tags_new,df_tags_removed,df_v2_renamed_from_v1,df_v1_renamed_to_v2])
        ######### make graph
        col_dis_map={
        'tag v2(added)':'blue',
        'tag v1(deleted)':'yellow',
        'tag v2 renamed from v1':'green',
        'tag v1 renamed to v2':'red'
        }
        fig=px.line(df,y='value',color='group',symbol='variable',color_discrete_map=col_dis_map);
        fig.update_traces(line_shape='hv',mode='lines+markers')
        v_old,v_new=[float(k) for k in transition.split('_')]
        v1_start=self.versions.loc[v_old,'start']
        v2_start=self.versions.loc[v_new,'start']
        fig.add_vline(x=v1_start)
        fig.add_vline(x=v2_start)

        add_v_number= lambda x,y,t,ax,fig: fig.add_annotation(
                x=x,y=y,text='start of v' + str(t),
                font=dict(family="Courier New, monospace",size=16,color="#000000"),
                align="center",arrowhead=2,arrowsize=1,arrowwidth=2,arrowcolor="#000000",showarrow=True,
                bordercolor="#c7c7c7",borderwidth=2,borderpad=4,bgcolor="#ffffff",opacity=0.8,
                ax=ax,ay=130,
                )

        fig=add_v_number(v1_start,0,v_old,-60,fig)
        fig=add_v_number(v2_start,0.25,v_new,-60,fig)
        try:
            v_next=self.versions.index[[k for k,v in enumerate(self.versions.index) if v==v_new][0]+1]
            v3_start=self.versions.loc[v_next,'start']
            fig.add_vline(x=v3_start)
            fig.add_vrect(x0=v2_start, x1=v3_start, line_width=0, fillcolor="red", opacity=0.2)
            fig=add_v_number(v3_start,0.5,v_next,60,fig)
        except:
            print('v_new :v ',v_new,'is the last version available.')
        ### separate a bit the traces
        for k,t in enumerate(fig.data):t['y']=t['y']+0.01*float((k+1)//2)*((-1)**k)
        return fig

    def get_lines(self):
        lines=[]
        for v in self.versions.index:
            s=pd.Series(self.df_plcs[v].index)
            tmp=(s[s.str.contains('L\d+')]).apply(lambda x:re.findall('L\d+',x)[0])
            lines+=[pd.Series(tmp.unique(),name=v).sort_values().reset_index()[v]]

        l=pd.concat(lines,axis=1)
        all_lines=pd.Series(pd.concat([l[v] for v in l.columns]).unique()).sort_values().dropna()
        l.index=all_lines
        # return l
        d=pd.DataFrame()
        for v in l.columns:
            # d[v]=all_lines.apply(lambda x:x if x in l[v].to_list() else np.nan)
            d[v]=all_lines.apply(lambda x:1 if x in l[v].to_list() else 0)
        d.index=l.index
        d=d.T
        d=d.iloc[[len(d)-k-1 for k in range(len(d))],:]
        return d

    def missing_tags_versions(self,day,versions=None):
        folder=self.folderPkl+day+'/'
        print(folder)
        listTags = [k.split('.pkl')[0] for k in self._fs.listfiles_folder(folder)]
        dfs, tagNotInVersion, tagNotInFolder={},{},{}
        dayCompatibleVersions = {}

        if versions is None:versions=self.df_plcs.keys()
        if isinstance(versions,str) or isinstance(versions,float):versions=[versions]
        for version,dfplc in {v:df for v,df in self.df_plcs.items() if v in versions}.items():
            # keep only valid tags
            if self._ds is None:
                tagsVersion = list(dfplc.index)
            else:
                tagsVersion = list(dfplc.index[dfplc.DATASCIENTISM==self._ds])

            tagNotInVersion[version] = [k for k in listTags if k not in tagsVersion]
            tagNotInFolder[version] = [k for k in tagsVersion if k not in listTags]
            dfs[version] = tagsVersion
            dayCompatibleVersions[version] = tagNotInFolder[version]
        return dayCompatibleVersions

    def show_map_of_compatibility(self,missing_tags_map,binaire=False,zmax=None):
        if zmax is None:
            zmax = missing_tags_map.max().max()
        reverse_scale=True
        # missing_tags_map=missing_tags_map.applymap(lambda x:np.random.randint(0,zmax))
        if binaire:
            missing_tags_map=missing_tags_map.applymap(lambda x:1 if x==0 else 0)
            zmax=1
            reverse_scale=False

        fig=go.Figure(go.Heatmap(z=missing_tags_map,x=['v' + str(k) for k in missing_tags_map.columns],
            y=missing_tags_map.index,colorscale='RdYlGn',reversescale=reverse_scale,
            zmin=0,zmax=zmax))
        fig.update_xaxes(side="top",tickfont_size=35)
        fig.update_layout(font_color="blue",font_size=15)
        fig.show()
        return fig

    ######################
    # make it compatible #
    ######################
    def _create_newtags_folder(self,day,tags):
        folder=self.folderPkl+day+'/'
        if not os.path.exists(folder):os.mkdir(folder)
        df = pd.Series(name='value')
        for tag in tags:
            tagpkl=folder + tag + '.pkl'
            if not os.path.exists(tagpkl):
                df.to_pickle(tagpkl)

    def _replace_tags_folder(self,day,tags2replace):
        folder=self.folderPkl+day+'/'
        for oldtag,newtag in zip(tags2replace['old_tag'],tags2replace['new_tag']):
            oldpath=folder + oldtag+'.pkl'
            newpath=folder + newtag+'.pkl'
            if not os.path.exists(newpath):
                os.rename(oldpath,newpath)
            else:
                s=pd.read_pickle(newpath)
                if s.empty and os.path.exists(oldpath):
                    os.rename(oldpath,newpath)

    def _apply_map_rename_tags(self,d0,d1,transition):
        #### get map of tags that should be renamed
        tags_renamed_map=self.get_rename_tags_map_from_rules(transition)
        df_rename_tags=tags_renamed_map.iloc[:,:-1]
        df_rename_tags.columns=['old_tag','new_tag']
        df_replace_tags=df_rename_tags[df_rename_tags.all(axis=1)]
        #### get map of tags that should be added
        tags_to_add=df_rename_tags[df_rename_tags['old_tag']=='']['new_tag'].to_list()
        for d in pd.date_range(d0,d1):
            day=d.strftime('%Y-%m-%d')
            self._replace_tags_folder(day,df_replace_tags)
            self._create_newtags_folder(day,tags_to_add)

    def make_period_compatible_from_transition(self,d0,d1,transition,execute=True):
        range_days=[(pd.Timestamp(t)+pd.Timedelta(days=d)).strftime('%Y-%m-%d') for t,d in zip([d0,d1],[-2,2])]
        v_old,vnew=[float(k) for k in transition.split('_')]
        idx_v = [k for k,v in enumerate(self.versions.index) if v==v_old][0]
        idx_v0=max(0,idx_v-1)
        v0=self.versions.index[idx_v0]

        fig=self.presence_tags_transition(transition)
        fig.update_xaxes(range=range_days).show()
        fig.update_layout(title_text='before remapping')
        df_missing_tags=self._load_missing_tags_map(d0,d1,v0=v0)

        self.show_map_of_compatibility(df_missing_tags)

        if not execute:return
        #########################
        # execute the remapping #
        #########################
        self._apply_map_rename_tags(d0,d1,transition)
        #### check that the transformation is correct and there are no tags missing

        fig=self.presence_tags_transition(transition)
        fig.update_layout(title_text='after remapping')
        fig.update_xaxes(range=range_days).show()

        df_missing_tags=self._load_missing_tags_map(d0,d1,v0=v0)
        self.show_map_of_compatibility(df_missing_tags)

    def create_missing_tags_period_version(self,d0,d1,version):
        dfplc=self.df_plcs[version]
        if self._ds is None:
            list_tags=dfplc.index.to_list()
        else:
            list_tags=dfplc[dfplc.DATASCIENTISM==self._ds].index.to_list()
        for d in pd.date_range(d0,d1):
            day=d.strftime('%Y-%m-%d')
            # print(day)
            self._create_newtags_folder(day,list_tags)

    #######################
    #       UTILS         #
    #######################
    def _totime(self,x):
        y=x.split('/')
        return pd.Timestamp(y[0]+' ' +y[1] + ':' + y[2])

    def are_tags_in_PLCs(self,tags,ds=True):
        df_plcs = self.df_plcs
        if not not ds:
            df_plcs = {k:v[v.DATASCIENTISM==ds] for k,v in self.df_plcs.items()}
        tagInplc={}
        for tag in tags:
            tagInplc[tag]=[True if tag in list(v.index) else False for k,v in df_plcs.items()]
        return pd.DataFrame.from_dict(tagInplc,orient='index',columns=df_plcs.keys()).T.sort_index()

    def patterntags_inPLCs(self,pattern,ds=True):
        df_plcs = self.df_plcs
        if not not ds:
            df_plcs = {k:v[v.DATASCIENTISM==ds] for k,v in self.df_plcs.items()}
        patterntags_plcs={}
        # print(df_plcs.keys())
        for v,dfplc in df_plcs.items():
            # return pd.DataFrame.from_dict(tagInplc,orient='index',columns=df_plcs.keys()).T.sort_index()
            patterntags_plcs[v]=list(dfplc.index[dfplc.index.str.contains(pattern)])
            patterntags_plcs = collections.OrderedDict(sorted(patterntags_plcs.items()))
        return patterntags_plcs

class VersionsManager_minutely(VersionsManager):
    #######################
    # GENERATE DATAFRAMES #
    #######################
    def load_nbTags_folders(self):
        # get_lentags=lambda x:len(self._fs.listfiles_folder(x))
        df_nbtags=self._streamer.actionMinutes_pooled(self.tmin,self.tmax,self.folderData,self.get_lentags)
        return pd.DataFrame.from_dict(df_nbtags,orient='index')

    def load_missingTags_versions(self,period=None,pool=True):
        '''-period : [tmin,tmax] timestamps'''
        map_missingTags = self._compute_all_minutefolders(self.get_missing_tags_versions,period=period)
        map_missingTags = pd.DataFrame(map_missingTags).T
        map_missingTags_len = map_missingTags.applymap(lambda x:len(x))
        return map_missingTags,map_missingTags_len

    def load_presenceTags(self,period=None,frequence='daily'):
        if frequence=='daily':
            return self._compute_all_minutefolders(self.get_presenceTags_folder,period=period)
        elif frequence=='minutely':
            return self._compute_all_minutefolders(self.get_presenceTags_folder,period=period)

    def _compute_all_minutefolders(self,function,*args,period=None,pool=True):
        '''-period : [tmin,tmax] timestamps'''
        if period is None:
            tmin = self.tmin
            tmax = self.tmax
        else :
            tmin,tmax=period
        if tmax - tmin -dt.timedelta(days=2)<pd.Timedelta(seconds=0):
            pool=False
        df = self._streamer.actionMinutes_pooled(tmin,tmax,self.folderData,function,*args,pool=pool)
        # print(df)
        df = pd.DataFrame(df).T
        df.index=[self.totime(x) for x in df.index]
        return df

    def make_it_compatible_with_renameMap(self,map_renametag,period):
        ## from one version to an adjacent version (next or last):
        ## get transition rules
        # self.get_transition_rename_rules(transition)
        ## get the corresponding map of tags that should be renamed
        ## rename tags that should be renamed
        '''map_renametag :
            - should be a dataframe with columns ['oldtag','newtag']
            - should have None values in oldtag column for brand newtags
            - should have None values in newtag column for deleted tags
            '''
        tags2replace = map_renametag[map_renametag.apply(lambda x:not x['oldtag']==x['newtag'] and not x['oldtag'] is None and not x['newtag'] is None,axis=1)]
        print()
        print('MAP OF TAGS TO REPLACE '.rjust(75))
        print(tags2replace)
        print()
        replacedmap=self._compute_all_minutefolders(self.get_replace_tags_folder,tags2replace,period=period)
        print()
        print('MAP OF REPLACED TAGS '.rjust(75))
        print(replacedmap)
        return replacedmap

class VersionsManager_daily(VersionsManager):
    def __init__(self,*args,**kwargs):
        VersionsManager.__init__(self,*args,**kwargs)
        # self._streamer.actiondays(self.tmin,self.tmax,self.folderData,self._streamer.create_dayfolder,pool=False)
