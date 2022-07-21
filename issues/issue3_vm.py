import os,sys,pickle,re,importlib
import subprocess as sp, pandas as pd,numpy as np,time, pickle, os
import dorianUtils.utilsD as ut
import plotly.express as px
import plotly.graph_objects as go
from dorianUtils.utilsD import Utils
utils=Utils()
from dorianUtils.comUtils import (html_table,timenowstd,print_file,computetimeshow)
import dorianUtils.VersionsManager as vm
from scipy import signal
importlib.reload(vm)

class VersionsManager_extend(vm.VersionsManager_daily):
    def __init__(self,*args,**kwargs):
        vm.VersionsManager_daily.__init__(self,*args,**kwargs)
        _v_start={
            1.0:'2022-07-04 15:00',
            2.0:'2022-07-06 7:00',
            }
        self.versions = pd.concat([self.versions,pd.Series(_v_start,name='start')],axis=1)


file_transition='/home/dorian/data/sylfenData/test_plc_folder/versionnage_tags.ods'
dir_plc='/home/dorian/data/sylfenData/test_plc_folder/'
folderPkl='/home/dorian/data/sylfenData/test_daily_folder/'

svm = VersionsManager_extend(folderPkl,dir_plc,file_transition,pattern_plcFiles='*plc*.xlsx')

# svm.generate_versionning_data(False,True)
svm.generate_versionning_data(True,True)

day='2022-07-06'
######################
# GENERATE THE DATA  #
######################
# def generate_the_data():
data={}
ts=pd.date_range(day+' 8:00',day+' 22:00',freq='30s',tz='CET')
s_empty=pd.Series([],name='value')
phi=np.linspace(0,10,len(ts))
data['tag_FT_01']=pd.Series(signal.square(phi),index=ts,name='value')
data['tag_01_FT']=pd.Series(0.5,index=ts,name='value')
data['tag_02_FT']=pd.Series(signal.sawtooth(phi),index=ts,name='value')
data['tag_FT_03']=s_empty.copy()
data['tag_03_FT']=pd.Series(0.7,index=ts,name='value')
data['tag_FT_04']=pd.Series(np.sin(phi),index=ts,name='value')
data['tag_04_FT']=s_empty.copy()
data['tag1']=pd.Series(phi,index=ts,name='value')/10
data['tag3']=s_empty.copy()
data['tag4']=pd.Series(0.2,index=ts,name='value')
data['tag7']=pd.Series(np.log(0.5+phi),index=ts,name='value')/2

for k,s in data.items():s.to_pickle(folderPkl+'/'+day+'/'+k+'.pkl')
###################### #
# look at THE DATA     #
# and see the presence #
#       of tags        #
###################### #
def show_data(day):
    data2={t.strip('.pkl'):pd.read_pickle(folderPkl+'/'+day+'/'+t) for t in os.listdir(folderPkl+'/'+day)}
    data2={k:v for k,v in data2.items() if not v.empty}
    df=pd.concat(data2,axis=1)
    df=df[df.columns.sort_values()]
    fig=px.line(df)
    colors={}
    colors['tag_01_FT']= 'red'
    colors['tag_FT_01']= 'pink'
    colors['tag_02_FT']= 'purple'
    colors['tag_FT_02']= 'magenta'
    colors['tag_FT_03']= 'blue'
    colors['tag_03_FT']= 'cyan'
    colors['tag_FT_04']= 'orange'
    colors['tag_04_FT']= 'yellow'
    colors['tag1']= 'black'
    colors['tag2']= 'black'
    colors['tag3']= 'black'
    colors['tag4']= 'green'
    colors['tag5']= 'black'
    colors['tag6']= 'black'
    colors['tag7']= 'grey'

    for k in fig.data:
        if k.name in colors:
            k.marker.color=colors[k.name]
            k.line.color=colors[k.name]
    fig.show()

show_data('2022-07-06')
# svm.presence_tags(data.keys(),empty_df=True).show()


#################
# DIAGNOSTIQUER #
# LA SITUATION  #
#################
# df_missing_tags=svm._load_missing_tags_map()
# svm.show_map_of_compatibility(df_missing_tags)

####################
# OBTENIR LA TABLE #
# DE  RENNOMMAGE   #
####################
transition='1_2'
# svm.get_rename_tags_map_from_rules(transition)
# svm.make_period_compatible_from_transition(day,day,transition,False)
# v=1.0;html_table(svm.df_plcs[v].loc[svm.missing_tags_versions('2022-07-06',v)[v]])
# v=2.0;html_table(svm.df_plcs[v].loc[svm.missing_tags_versions('2022-07-06',v)[v]])

####################
# RENDRE COMPATIBE #
####################
svm.create_missing_tags_period_version('2022-07-05','2022-07-10',1.0)
svm.make_period_compatible_from_transition('2022-07-05','2022-07-10',transition,True)
show_data('2022-07-06')

sys.exit()
