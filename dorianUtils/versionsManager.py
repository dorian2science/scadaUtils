import pandas as pd, glob,os,sys,datetime as dt
import pickle,re,time
from functools import reduce
from .comUtils import Streamer
sort_list=lambda x:list(pd.Series(x).sort_values())
class VersionsManager():
    def __init__(self,folderData,plcDir=None,pattern_plcFiles='*plc*.csv'):
        self.streamer     = Streamer()
        self.plcDir       = plcDir
        self.folderData   = folderData
        self.versionFiles = glob.glob(self.plcDir+pattern_plcFiles)
        self.dicVersions  = {f:re.findall('\d+\.\d+',f)[0] for f in self.versionFiles}
        self.listVersions = sort_list(self.dicVersions.values())
        self.tmin,self.tmax = self.get_tminmax()
        self.transitionFile = self.plcDir + 'versionnageTags.ods'
        self.transitions = pd.ExcelFile(self.transitionFile).sheet_names

    def get_tminmax(self):
        minFolder=lambda x:pd.Series(os.listdir(x)).min()
        maxFolder=lambda x:pd.Series(os.listdir(x)).max()

        dmin=minFolder(self.folderData)
        hmin=minFolder(self.folderData+dmin)
        mmin=minFolder(self.folderData+dmin+'/'+hmin)
        tmin=pd.Timestamp(dmin + ' '+hmin+':'+mmin)
        dmax=maxFolder(self.folderData)
        hmax=maxFolder(self.folderData+dmax)
        mmax=maxFolder(self.folderData+dmax+'/'+hmax)
        tmax=pd.Timestamp(dmax + ' '+hmax+':'+mmax)
        return tmin,tmax

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
