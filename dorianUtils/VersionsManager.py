# #######################
# #  VERISONS MANAGER    #
# #######################
import collections
from . import comUtils
import glob
import pandas as pd
sort_list=lambda x:list(pd.Series(x).sort_values())
class VersionsManager():
    def __init__(self,folderData,plcDir,buildFiles=[False,False,False],pattern_plcFiles='*plc*.csv'):
        self.streamer     = comUtils.Streamer()
        self.fs           = comUtils.FileSystem()
        self.plcDir       = plcDir
        self.folderData   = folderData
        self.versionFiles = glob.glob(self.plcDir+pattern_plcFiles)
        self.dicVersions  = {f:re.findall('\d+\.\d+',f.split('/')[-1])[0] for f in self.versionFiles}
        self.versions     = sort_list(self.dicVersions.values())
        self.daysnotempty = pd.Series([pd.Timestamp(k) for k in self.fs.get_parked_days_not_empty(folderData)])
        self.tmin,self.tmax = self.daysnotempty.min(),self.daysnotempty.max()
        # self.transitionFile = self.plcDir + 'versionnageTags.xlsx'
        # self.transitionFile = self.plcDir + 'versionnageTags.ods'
        # self.transitions    = pd.ExcelFile(self.transitionFile).sheet_names
        self.file_df_plcs    = self.plcDir + 'alldfsPLC.pkl'
        self.file_df_nbTags  = self.plcDir + 'nbTags.pkl'
        self.file_map_missingTags  = self.plcDir + 'map_missingTags.pkl'
        self.file_map_presenceTags  = self.plcDir + 'map_presenceTags.pkl'
        # self.load_confFiles(buildFiles)
        print('FINISH LOADING VERSION MANAGER\n'+'='*60+'\n')

    def load_confFiles(self,buildFiles):
        loadconfFile = lambda x,y,b:self.fs.load_confFile(x,y,b)
        self.df_plcs,self.all_tags_history = loadconfFile(self.file_df_plcs,self.load_PLC_versions,buildFiles[0])
        self.df_nbTagsFolder = loadconfFile(self.file_df_nbTags,self.load_nbTags_folders,buildFiles[1])
        self.map_missingTags,self.map_missingTags_len = loadconfFile(self.file_map_missingTags,self.load_missingTags_versions,buildFiles[2])
        # self.map_presenceTags = loadconfFile(self.file_map_presenceTags,self.load_presenceTags)

    #######################
    #       UTILS         #
    #######################
    def totime(self,x):
        y=x.split('/')
        return pd.Timestamp(y[0]+' ' +y[1] + ':' + y[2])

    def is_tags_in_PLCs(self,tags,ds=True):
        df_plcs = self.df_plcs
        if not not ds:
            df_plcs = {k:v[v.DATASCIENTISM==ds] for k,v in self.df_plcs.items()}
        tagInplc={}
        for tag in tags:
            tagInplc[tag]=[True if tag in list(v.index) else False for k,v in df_plcs.items()]
        return pd.DataFrame.from_dict(tagInplc,orient='index',columns=df_plcs.keys()).T.sort_index()

    def get_patterntags_inPLCs(self,pattern,ds=True):
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

    def get_listTags_folder(self,folder):
        return self.fs.listfiles_folder(folder)

    def get_lentags(self,folder):
        return len(self.fs.listfiles_folder(folder))

    def get_presenceTags_folder(self,folder,tags=None):
        if tags is None : tags=self.all_tags_history
        # print(folder)
        listTags = [k.split('.pkl')[0] for k in self.fs.listfiles_folder(folder)]
        # print(listTags)
        return {t:True if t in listTags else False for t in tags}

    def get_missing_tags_versions(self,folder):
        # print(folder)
        listTags = [k.split('.pkl')[0] for k in self.get_listTags_folder(folder)]
        # keep only valid tags
        listTags = [k for k in listTags if k in self.all_tags_history]
        dfs, tagNotInVersion, tagNotInFolder={},{},{}
        dayCompatibleVersions = {}
        for version,dfplc in self.df_plcs.items():
            # keep only valid tags
            tagsVersion = list(dfplc.index[dfplc.DATASCIENTISM])
            tagNotInVersion[version] = [k for k in listTags if k not in tagsVersion]
            tagNotInFolder[version] = [k for k in tagsVersion if k not in listTags]
            dfs[version] = tagsVersion
            dayCompatibleVersions[version] = tagNotInFolder[version]
        return dayCompatibleVersions


    #######################
    # GENERATE DATAFRAMES #
    #######################
    def load_PLC_versions(self):
        print('Start reading plc files....')
        df_plcs = {}
        for f,v in self.dicVersions.items():
            print(f)
            df_plcs[v] = pd.read_csv(f,index_col=0)

        print('')
        print('concatenate tags of all dfplc verion')
        all_tags_history = list(pd.concat([pd.Series(dfplc.index[dfplc.DATASCIENTISM]) for dfplc in df_plcs.values()]).unique())
        return df_plcs,all_tags_history

    ######################
    # MAKE IT COMPATIBLE #
    ######################
    ##### load the right version to version correspondance
    def getCorrectVersionCorrespondanceSheet(self,transition):
        if transition not in self.transitions:
            return pd.DataFrame({'old tag':[],'new tag':[]})
        else:
            return pd.read_excel(self.transitionFile,sheet_name=transition)

    def get_renametagmap_transition(self,transition):
        patternsMap = self.getCorrectVersionCorrespondanceSheet(transition)
        if len(patternsMap)>0:
            dfRenameTagsMap = patternsMap.apply(lambda x:self._getReplaceTagPatternMap(x[0],x[1],transition),axis=1,result_type='expand')
            ## remove empty lists for old Tags
            dfRenameTagsMap = dfRenameTagsMap[dfRenameTagsMap[0].apply(len)>0]
            ## flatten lists
            dfRenameTagsMap = dfRenameTagsMap.apply(lambda x:self.flattenList(x))
        else:
            dfRenameTagsMap=pd.DataFrame([[],[]]).T
        dfRenameTagsMap.columns=['oldTags','newTags']

        vold,vnew=transition.split('_')
        plcold = self.df_plcs[vold]
        plcold = plcold[plcold.DATASCIENTISM==True]
        plcnew = self.df_plcs[vnew]
        plcnew = plcnew[plcnew.DATASCIENTISM==True]

        tagsAdded = [t for t in list(plcnew.TAG) if t not in list(plcold.TAG)]
        # tags that were renamed should not be added
        tagsAdded = [k for k in tagsAdded if k not in list(dfRenameTagsMap.newTags)]
        return dfRenameTagsMap,tagsAdded

    def get_renametagmap_transition_v2(self,transition):
        patternsMap = self.getCorrectVersionCorrespondanceSheet(transition)
        patternsMap = patternsMap.set_index('old tag').squeeze(axis=1).to_dict()
        vold,vnew=transition.split('_')
        plcold  = self.df_plcs[vold]
        oldtags = list(plcold[plcold.DATASCIENTISM==True].index)
        plcnew  = self.df_plcs[vnew]
        newtags = list(plcnew[plcnew.DATASCIENTISM==True].index)
        df_renametagsmap = {}
        for oldtag in oldtags:
            newtag = oldtag
            for oldpat,newpat in patternsMap.items():
                newtag= newtag.replace(oldpat,newpat)
            df_renametagsmap[oldtag] = newtag
        df_renametagsmap=pd.DataFrame({'oldtag':df_renametagsmap.keys(),'newtag':df_renametagsmap.values()})
        df_renametagsmap = df_renametagsmap[df_renametagsmap.apply(lambda x:not x['oldtag']==x['newtag'],axis=1)]

        # brand_newtags = [t for t in newtags if t not in list(df_renametagsmap['newtag'])]
        # brand_newtags = pd.DataFrame([(None,k) for k in brand_newtags],columns=['oldtag','newtag'])
        # df_renametagsmap = pd.concat([df_renametagsmap,brand_newtags])
        return df_renametagsmap

    def get_rename_tags_newpattern(self,oldPattern,newPattern,df_plc,debug=False):
        ''' replace only pattern occurence '''
        df_renametagsmap=pd.DataFrame(df_plc.index,columns=['oldtag'])
        df_renametagsmap['newtag']=df_renametagsmap.apply(lambda x : x.replace(oldPattern,newPattern))
        return df_renametagsmap

    def removeInvalidTags(self,folderminute):
        listTags = [k.split('.pkl')[0] for k in os.listdir(folderminute)]
        list_invalidTags = [k for k in listTags if k not in self.all_tags_history]
        try:
            [os.remove(folderminute + tag + '.pkl') for tag in list_invalidTags]
        except:
            print('not removed')
            # print('could not remove tags in',list_invalidTags)

    def get_replace_tags_folder(self,folder,tag2replace):
        # print(folder)
        result={}
        for oldtag,newtag in zip(tag2replace['oldtag'],tag2replace['newtag']):
            try:
                os.rename(folder + oldtag+'.pkl',folder+newtag+'.pkl')
                result[oldtag]='replace by ' + newtag
            except:
                result[oldtag]=' not in folder'
        return result

    def get_createnewtags_folder(self,folder,alltagsversion):
        # print(folder)
        df = pd.Series(name='value')
        df_tagAdded={}
        for tag in alltagsversion:
            tagpkl=folder + tag + '.pkl'
            if os.path.exists(tagpkl):
                df_tagAdded[tag] = False
            else:
                df.to_pickle(folder + tag + '.pkl')
                df_tagAdded[tag] = True
        return df_tagAdded

    ###################
    #       GRAPHS    #
    ###################
    def show_map_of_compatibility(self,binaire=False,zmax=None):
        testdf=self.map_missingTags_len.T
        if zmax is None:
            zmax = testdf.max().max()
        reverse_scale=True
        # testdf=testdf.applymap(lambda x:np.random.randint(0,zmax))
        if binaire:
            testdf=testdf.applymap(lambda x:1 if x==0 else 0)
            zmax=1
            reverse_scale=False

        fig=go.Figure(go.Heatmap(z=testdf,x=['v' + k for k in testdf.columns],
            y=testdf.index,colorscale='RdYlGn',reversescale=reverse_scale,
            zmin=0,zmax=zmax))
        fig.update_xaxes(side="top",tickfont_size=35)
        fig.update_layout(font_color="blue",font_size=15)
        fig.show()
        return fig

    def show_nbFolder(self):
        dfshow = self.df_nbTagsFolder
        dfshow.columns=['nombre tags']
        dfshow.index=[self.totime(x) for x in dfshow.index]
        fig = px.line(dfshow,x=dfshow.index,y='nombre tags')
        fig.show()
        return fig

    def show_map_presenceTags(self,tags):
        dfshow = self.map_presenceTags[tags]
        dfshow=dfshow.astype(int)
        fig=go.Figure(go.Heatmap(z=dfshow,x=dfshow.columns,
                        y=dfshow.index,colorscale='RdYlGn',reversescale=False,
                        zmin=0,zmax=1))
        fig.update_xaxes(side="top",tickfont_size=10)
        fig.update_layout(font_color="blue",font_size=15)
        fig.show()
        return fig

class VersionsManager_minutely(VersionsManager):
    #######################
    # GENERATE DATAFRAMES #
    #######################
    def load_nbTags_folders(self):
        # get_lentags=lambda x:len(self.fs.listfiles_folder(x))
        df_nbtags=self.streamer.actionMinutes_pooled(self.tmin,self.tmax,self.folderData,self.get_lentags)
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
        df = self.streamer.actionMinutes_pooled(tmin,tmax,self.folderData,function,*args,pool=pool)
        # print(df)
        df = pd.DataFrame(df).T
        df.index=[self.totime(x) for x in df.index]
        return df

    def make_it_compatible_with_renameMap(self,map_renametag,period):
        ## from one version to an adjacent version (next or last):
        ## get transition rules
        # self.getCorrectVersionCorrespondanceSheet(transition)
        ## get the corresponding map of tags that should be renamed
        ## rename tags that should be renamed
        '''map_renametag :
            - should be a dataframe with columns ['oldtag','newtag']
            - should have None values in oldtag column for brand newtags
            - should have None values in newtag column for deleted tags
            '''
        tag2replace = map_renametag[map_renametag.apply(lambda x:not x['oldtag']==x['newtag'] and not x['oldtag'] is None and not x['newtag'] is None,axis=1)]
        print()
        print('MAP OF TAGS TO REPLACE '.rjust(75))
        print(tag2replace)
        print()
        replacedmap=self._compute_all_minutefolders(self.get_replace_tags_folder,tag2replace,period=period)
        print()
        print('MAP OF REPLACED TAGS '.rjust(75))
        print(replacedmap)
        return replacedmap

class VersionsManager_daily(VersionsManager):
    def __init__(self,*args,**kwargs):
        VersionsManager.__init__(self,*args,**kwargs)
        self.streamer.actiondays(self.tmin,self.tmax,self.folderData,self.streamer.create_dayfolder,pool=False)

    #######################
    # GENERATE DATAFRAMES #
    #######################
    def _compute_all_dayfolders(self,function,*args,period=None,pool=False):
        '''-period : [tmin,tmax] timestamps'''
        if period is None:
            tmin = self.tmin
            tmax = self.tmax
        else :
            tmin,tmax=period
        if tmax - tmin - dt.timedelta(days=20)<pd.Timedelta(seconds=0):
            pool=False
        df = self.streamer.actiondays(tmin,tmax,self.folderData,function,*args,pool=pool)
        # print(df)
        df = pd.DataFrame(df).T
        df.index=[pd.Timestamp(x,tz='CET') for x in df.index]
        return df

    def load_nbTags_folders(self):
        df_nbtags=self.streamer.actiondays(self.tmin,self.tmax,self.folderData,self.get_lentags,pool=False)
        return pd.DataFrame.from_dict(df_nbtags,orient='index')

    def load_missingTags_versions(self,period=None,pool=False):
        '''-period : [tmin,tmax] timestamps'''
        map_missingTags = self._compute_all_dayfolders(self.get_missing_tags_versions,period=period,pool=pool)
        map_missingTags = pd.DataFrame(map_missingTags).T.sort_index()
        map_missingTags_len = map_missingTags.applymap(lambda x:len(x))
        return map_missingTags,map_missingTags_len

    def load_presenceTags(self,period=None,pool=False):
        return self._compute_all_dayfolders(self.get_presenceTags_folder,period=period,pool=pool)

    ###########################
    # COMPATIBILITY FUNCTIONS #
    ###########################
    def make_it_compatible_with_renameMap(self,map_renametag,period):
        ## from one version to an adjacent version (next or last):
        ## get transition rules
        # self.getCorrectVersionCorrespondanceSheet(transition)
        ## get the corresponding map of tags that should be renamed
        ## rename tags that should be renamed
        '''map_renametag :
            - should be a dataframe with columns ['oldtag','newtag']
            - should have None values in oldtag column for brand newtags
            - should have None values in newtag column for deleted tags
            '''
        tag2replace = map_renametag[map_renametag.apply(lambda x:not x['oldtag']==x['newtag'] and not x['oldtag'] is None and not x['newtag'] is None,axis=1)]
        print()
        print('MAP OF TAGS TO REPLACE '.rjust(75))
        print(tag2replace)
        print()
        replacedmap=self._compute_all_dayfolders(self.get_replace_tags_folder,tag2replace,period=period)
        print()
        print('MAP OF REPLACED TAGS '.rjust(75))
        print(replacedmap)
        return replacedmap

    def create_emptytags_version(self,period,dfplc):
        ## add tags as emptydataframes in folder if they are missing
        print('---------------------------------------------------------------')
        print();print();print()
        alltags = list(dfplc[dfplc.DATASCIENTISM==True].index)
        map_createTags   = self._compute_all_dayfolders(self.get_createnewtags_folder,alltags,period=period)
        return map_createTags
