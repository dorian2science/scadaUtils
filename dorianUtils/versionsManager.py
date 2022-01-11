import pandas as pd, glob,os,sys
import pickle,re,time
from functools import reduce

class VersionsManager():
    def __init__(self,folderData,baseDir=None,pattern_plcFiles='*plc*.pkl'):
        self.scriptDir    = os.path.dirname(os.path.realpath(__file__))
        if baseDir is None:baseDir=self.scriptDir
        self.baseDir      = baseDir
        self.plcDir       = self.baseDir + 'PLC_config/'
        self.folderData   = folderData
        self.versionFiles = glob.glob(self.plcDir+pattern_plcFiles)
        self.dicVersions  = {f:re.findall('\d+\.\d+',f)[0] for f in self.versionFiles}
        self.listVersions = list(self.dicVersions.values())
        self.listVersions.sort()
        self.allDays      = [k.split('/')[-1] for k in glob.glob(self.folderData+'*')]
        self.allDays.sort()
        self.pkldf_plcs = self.plcDir + 'alldfsPLC.pkl'
        self.pkldf_missingTagsmap  = self.plcDir + 'mapMissingTags_map.pkl'
        self.transitionFile = self.plcDir + 'versionnageTags.ods'
        self.transitions = pd.ExcelFile(self.transitionFile).sheet_names


        # self.load_dfPLCs()
        # self.load_misingTagsMap()

    def flattenList(self,l):
        return [item for sublist in l for item in sublist]

    def readAll_PLC_versions(self):
        print('Start reading all .xlsm files....')
        sheetnames ={f:pd.ExcelFile(f).sheet_names for f in self.versionFiles}
        confJulesNotInV = {f:False if 'FichierConf_Jules' in v else True for f,v in sheetnames.items()}
        confJulesNotInV = pd.DataFrame.from_dict(confJulesNotInV,orient='index').squeeze()
        confJulesNotInV = list(confJulesNotInV[confJulesNotInV].index)
        if len(confJulesNotInV)>0:
            oldDir = self.plcDir + 'old/'
            if not os.path.exists(oldDir):os.mkdir(oldDir)
            print('no FichierConf_Jules sheet in files : ')
            print()
            for k in confJulesNotInV:
                print(k)
                os.rename(k,oldDir+k.split('/')[-1])
            print()
            print('those files were moved in directory ',oldDir)
            print('==============================================')

        df_plcs = {}
        for f,v in self.dicVersions.items():
            print(f)
            df_plcs[v] = pd.read_excel(f,sheet_name='FichierConf_Jules')
        pickle.dump(df_plcs,open(self.pkldf_plcs,'wb'))
        print(self.pkldf_plcs + ' saved')
        print('==============================================')
        print('')

    def computeMapOfCompatibleVersions(self):
        dayCompatibleVersions={jour:{} for jour in self.allDays}
        # for jour in self.allDays:
        listLengths={}
        # for jour in self.allDays[-2:]:
        for jour in self.allDays:
            folderJour = self.folderData+jour+'/'
            print('\n=====================',jour,'===============\n')
            listDayTags = [k.split('/')[-1][:-4] for k in glob.glob(folderJour + '*')]
            listDayTags.sort()
            #               remove all pkl files that are
            #           not a datascientism file(cleaning a bit)
            listTagsNotDs=[k for k in listDayTags if k not in self.all_ds_tags_history]
            [os.remove(folderJour + tag + '.pkl') for tag in listTagsNotDs]

            #     check if all tag_files are found in day_folder
            listTags_ds = [k for k in listDayTags if k in self.all_ds_tags_history]
            dfs, tagNotInVersion, tagNotInDay={},{},{}
            for version,dfplc in self.df_plcs.items():
                listTagsVersion = list(dfplc.TAG[dfplc.DATASCIENTISM])
                listTagsVersion.sort()
                tagNotInVersion[version] = [k for k in listTags_ds if k not in listTagsVersion]
                tagNotInDay[version] = [k for k in listTagsVersion if k not in listTags_ds]
                dfs[version] = listTagsVersion
                dayCompatibleVersions[jour][version] = tagNotInDay[version]

            dfs = pd.DataFrame.from_dict({**dfs,'daytags':listTags_ds},orient='index').T
            # listLengths[jour] = dfs.apply(lambda x:len(x.dropna())).sort_values()

        df_missingTags_map = pd.DataFrame.from_dict(dayCompatibleVersions,orient='index')
        df_missingTags_map = df_missingTags_map[df_missingTags_map.columns.sort_values()]
        dfmapLen = df_missingTags_map.applymap(lambda x:len(x))
        # reduce(self.intersec,list(tagNotInVersion.values())[:3])
        # reduce(set,list(tagNotInVersion.values()))
        pickle.dump([df_missingTags_map,dfmapLen],open(self.pkldf_missingTagsmap,'wb'))
        print(self.pkldf_missingTagsmap + ' saved')
        print('==============================================')
        print('')

    def load_dfPLCs(self):
        try:
            self.df_plcs = pickle.load(open(self.pkldf_plcs,'rb'))
            self.all_ds_tags_history = list(pd.concat([dfplc.TAG[dfplc.DATASCIENTISM] for dfplc in self.df_plcs.values()]).unique())
        except:
            print('self.df_plcs could not be loaded because file ',self.pkldf_plcs,' does not exist')
            print('start reading allfiles with function readAll_PLC_versions')
            self.readAll_PLC_versions()
            self.load_dfPLCs()
            print('==============================================')

    def load_misingTagsMap(self):
        try:
            self.df_missingTags_map,self.df_missingTags_lenmap_ = pickle.load(open(self.pkldf_missingTagsmap,'rb'))
        except:
            print('df_plcs could not be loaded because file ',self.pkldf_plcs,' does not exist')
            print()
            print('run first computeMapOfCompatibleVersions')
            self.computeMapOfCompatibleVersions()
            self.load_misingTagsMap()
            print('==============================================')

    def intersec(self,a,b):
        return set(a)&set(b)
    ##### load the right version to version correspondance
    def getCorrectVersionCorrespondanceSheet(self,transition):
        if transition not in self.transitions:
            return pd.DataFrame({'old tag':[],'new tag':[]})
        else:
            return pd.read_excel(self.transitionFile,sheet_name=transition)

    ##### look for occurence of tags in all plc versions(map)
    def look4Tags_inPLCs(self,tags,ds=True):
        df_plcs = self.df_plcs
        if not not ds:
            df_plcs = {k:v[v.DATASCIENTISM==ds] for k,v in self.df_plcs.items()}
        tagInplc={}
        for tag in tags:
            tagInplc[tag]=[True if tag in list(v.TAG) else False for k,v in df_plcs.items()]
        return pd.DataFrame.from_dict(tagInplc,orient='index',columns=df_plcs.keys()).T.sort_index()

    def getTagsofPattern_inPLCs(self,pattern,ds=True):
        df_plcs = self.df_plcs
        if not not ds:
            df_plcs = {k:v[v.DATASCIENTISM==ds] for k,v in self.df_plcs.items()}
        tagsofPattern_Inplc={}
        # print(df_plcs.keys())
        for v,dfplc in df_plcs.items():
            # return pd.DataFrame.from_dict(tagInplc,orient='index',columns=df_plcs.keys()).T.sort_index()
            tagsofPattern_Inplc[v]=list(dfplc.TAG[dfplc.TAG.str.contains(pattern)])
        return pd.DataFrame.from_dict(tagsofPattern_Inplc,orient='index').sort_index()

    ##### build map of tag to change
    def _getReplaceTagPatternMap(self,oldPattern,newPattern,transition,ds=True,debug=False):
        ''' deal only with pattern=tag or pat has xxx to replace '''
        vold,vnew=transition.split('_')
        # oldPattern = oldPattern.strip()
        # newPattern = newPattern.strip()
        oldPattern = oldPattern
        newPattern = newPattern
        plcold = self.df_plcs[vold]
        plcnew = self.df_plcs[vnew]
        if ds:
            plcold = plcold[plcold.DATASCIENTISM==True]
            plcnew = plcnew[plcnew.DATASCIENTISM==True]
        # start = time.time()
        if 'xxx' in oldPattern:
            oldTags,newTags={},{}
            for tag in list(plcold.TAG):
                regexp = oldPattern.replace('.','\.').replace('xxx','(.*)')
                m=re.search(regexp,tag)
                if m:
                    oldTags[m.group(0)]=m.group(1)
            for tag in list(plcnew.TAG):
                regexp = newPattern.replace('.','\.').replace('xxx','(.*)')
                m=re.search(regexp,tag)
                if m:
                    newTags[m.group(0)]=m.group(1)
            # how should be the new tags with their extensions
            newTagsWithExtensions = [newPattern.replace('xxx',k) for k in oldTags.values()]
            oldTags = list(oldTags.keys())

            # compare to new tags found
            dicTags,dicTagsNotds = {},{}
            oldTags = pd.Series(oldTags)
            newTagsWithExtensions = pd.Series(newTagsWithExtensions)
            newTags = pd.Series(newTags.keys())
            newTagsinWithExt = newTagsWithExtensions[newTagsWithExtensions.isin(newTags)]
            newTagsExtAdded  = newTags[~newTags.isin(newTagsWithExtensions)]
            df = pd.concat([oldTags,newTagsWithExtensions,newTags,newTagsinWithExt,newTagsExtAdded],axis=1)
            df.columns=['oldTags','newTagsWithExtensions','newTags','newTagsInWithExt','newTagsExtAdded']

            oldTagsRemoved = df.oldTags[df['newTagsInWithExt'].isna()]
            oldTagsRemoved.name='oldTagsRemoved'
            dfRenameTagsMap=df[df['newTagsInWithExt'].isin(df.newTagsInWithExt)][['oldTags','newTagsInWithExt']].dropna()

            df = pd.concat([df,oldTagsRemoved],axis=1)
            if debug:
                return df
            oldTags = list(dfRenameTagsMap['oldTags'])
            newTags = list(dfRenameTagsMap['newTagsInWithExt'])
        else:
            oldTags = [oldPattern] if oldPattern in list(plcold.TAG) else []
            newTags = [newPattern] if newPattern in list(plcnew.TAG) else []
        return oldTags,newTags

    def getMapRenameTags(self,transition):
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

    def makeDayTagsCompatible(self,jour,transition):
        tags2add, tagsAlreadyIn, tagsAdded = [],[],[]
        tagsReplaced = {}
        dfRenameTagsMap,addedNewVersion = self.getMapRenameTags(transition)

        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        #                          rename tags
        ljsT = 45
        ljsb = 20
        folderJour = self.folderData + jour + '/'
        print('\n=====================',jour,'===============\n')
        listTagsDay = [k.split('/')[-1][:-4] for k in glob.glob(folderJour+ '*')]
        for t1,t2 in zip(list(dfRenameTagsMap['oldTags']),list(dfRenameTagsMap['newTags'])):
            if t1 in listTagsDay:
                if t2 not in listTagsDay:
                    oldTagpkl  = folderJour + t1 + '.pkl'
                    newTagpkl  = folderJour + t2 + '.pkl'
                    os.rename(oldTagpkl,newTagpkl)
                    print(oldTagpkl.split('/')[-1].ljust(ljsT),' replaced by '.ljust(ljsb),newTagpkl.split('/')[-1])
                    tagsReplaced[t1] = t2
                else :
                    print(t2.ljust(ljsT),' already in '.ljust(ljsb),jour)
                    tagsAlreadyIn.append(t2)
            else :
                print(t1.ljust(ljsT),' not in folder '.ljust(ljsb),jour)
                tags2add.append(t1)
        # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        #                          add missing tags
        print('\n          ','adding file now ','                 \n')
        listTagsToAdd = addedNewVersion + tags2add
        for t in listTagsToAdd:
            if not t in listTagsDay:
                pickle.dump(pd.DataFrame(),open(folderJour + t + '.pkl','wb'))
                print(t.ljust(ljsT),' added in '.ljust(ljsb),folderJour)
                tagsAdded.append(t)
            else :
                print(t.ljust(ljsT),' already in '.ljust(ljsb),folderJour)
                tagsAlreadyIn.append(t)

        return tagsAdded, tagsAlreadyIn, tagsReplaced

    def makeDayTagsCompatibleToLastVersion(self,jour):
        for k in range(len(self.listVersions)-1):## because listVersions are sorted
            transition = self.listVersions[k] + '_' + self.listVersions[k+1]
            print(transition)
            self.makeDayTagsCompatible(jour,transition)

class Monitoring_VM(VersionsManager):
    def readAll_PLC_versions(self):
        print('Start reading all .csv files....')
        df_plcs = {}
        for f,v in self.dicVersions.items():
            print(f)
            # df_plcs[v] = pickle.load(open(f,'rb'))
            df_plcs[v] = pd.read_csv(f)
        pickle.dump(df_plcs,open(self.pkldf_plcs,'wb'))
        print(self.pkldf_plcs + ' saved')
        print('==============================================')
        print('')
        try:
            self.df_plcs = pickle.load(open(self.pkldf_plcs,'rb'))
            self.all_ds_tags_history = list(pd.concat([dfplc.TAG[dfplc.DATASCIENTISM] for dfplc in self.df_plcs.values()]).unique())
        except:
            print('self.df_plcs could not be loaded because file ',self.pkldf_plcs,' does not exist')
            print('start reading allfiles with function readAll_PLC_versions')
            self.readAll_PLC_versions()
            self.load_dfPLCs()
            print('==============================================')
