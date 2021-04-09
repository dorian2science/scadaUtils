import dash_html_components as html
import dash_core_components as dcc
import re,dateutil,datetime as dt
from utilsD import Utils
import numpy as np
class DccExtended:
    utils=Utils()
    ''' dropdown with a list or dictionnary. Dictionnary doesn"t work for the moment '''
    def dropDownFromList(self,idName,listdd,pddPhrase = None,defaultIdx=None,labelsPattern=None,**kwargs):
        if not pddPhrase :
            pddPhrase = 'Select your ... : ' + idName
        p = html.P(pddPhrase)
        if labelsPattern :
            ddOpt= [{'label': re.findall(labelsPattern,t)[0], 'value': t} for t in listdd]
        else :
            ddOpt =[{'label': t, 'value': t} for t in listdd]

        if 'value' in list(kwargs.keys()):
            dd = dcc.Dropdown(id=idName,options=ddOpt,clearable=False,**kwargs)
        else :
            if not defaultIdx:
                defaultIdx = 0
            if 'value' in list(kwargs.keys()):
                del kwargs['value']
            dd = dcc.Dropdown(id=idName,options=ddOpt,value=listdd[defaultIdx],clearable=False,**kwargs)
        return [p,dd]

    def dropDownFromDict(self,idName,listdd,pddPhrase = None,valIdx=None,**kwargs):
        if not pddPhrase :
            pddPhrase = 'Select your ... : ' + idName
        p = html.P(pddPhrase)
        if isinstance(listdd,dict):
            keysDict= list(listdd.keys())
            valDict = list(listdd.values())
            ddOpt =[{'label': k, 'value': v} for k,v in listdd.items()]

        if 'value' in list(kwargs.keys()):
            dd = dcc.Dropdown(id=idName,options=ddOpt,clearable=False,**kwargs)
        elif valIdx:
            valSel = [list(listdd.values())[k] for k in valIdx]
            print(valSel)
            dd = dcc.Dropdown(id=idName,options=ddOpt,value=valSel,clearable=False,**kwargs)
        else :
            print('here')
            dd = dcc.Dropdown(id=idName,options=ddOpt,clearable=False,**kwargs)
        return [p,dd]

    def quickInput(self,idName,typeIn='text',pddPhrase = 'input',dftVal=0,**kwargs):
        p = html.P(pddPhrase),
        inp = dcc.Input(id=idName,placeholder=pddPhrase,type=typeIn,value=dftVal,**kwargs)
        return [p,inp]

    def timeRangeSlider(self,idName,mini=0,maxi=3600*24-1,t0=None):
        if not isinstance(t0,dt.datetime):
            t0 = dt.datetime(2021,1,1,0,0)
        p = html.H5('select the time window')
        rs = dcc.RangeSlider(id=idName,allowCross=False,min = mini,max = maxi,
                    marks = self.utils.buildTimeMarks(t0,maxi=maxi,mini=mini),
                    value = [mini,maxi],
                    tooltip={'always_visible' : False,'placement':'bottom'})
        return [p,rs]

    def buildTimeMarks(t0,t1,nbMarks=8,fontSize='20px'):
        maxSecs=int((t1-t0).total_seconds())
        listSeconds = [int(t) for t in np.linspace(0,maxSecs,nbMarks)]
        dictTimeMarks = {k : {'label':(t0+dt.timedelta(seconds=k)).strftime('%H:%M'),
                                'style' :{'font-size': fontSize}
                                } for k in listSeconds}
        return dictTimeMarks,maxSecs

    def buildTimeRangeSlider(id,t0,t1=None,**kwargs):
        if not t1 :
            t1 = t0+dt.timedelta(seconds=3600*24)
        maxSecs=int((t1-t0).total_seconds())
        rs = dcc.RangeSlider(id=id,
        min=0,max=maxSecs,
        # step=None,
        marks = buildTimeMarks(t0,t1,**kwargs)[0],
        value=[0,maxSecs]
        )
        return rs
