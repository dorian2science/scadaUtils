import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from dateutil import parser
import re,datetime as dt, numpy as np
from dorianUtils.utilsD import Utils

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

    def timeRangeSlider(self,id,t0=None,t1=None,**kwargs):
        if not t0 :
            t0 = parser.parse('00:00')
        if not t1 :
            t1 = t0+dt.timedelta(seconds=3600*24)
        maxSecs=int((t1-t0).total_seconds())
        rs = dcc.RangeSlider(id=id,
        min=0,max=maxSecs,
        # step=None,
        marks = self.utils.buildTimeMarks(t0,t1,**kwargs)[0],
        value=[0,maxSecs]
        )
        return rs

    def DoubleRangeSliderLayout(self,baseId='',t0=None,t1=None,formatTime = '%d - %H:%M',styleDBRS='small'):
        if styleDBRS=='large':
            style2 = {'padding-bottom' : 50,'padding-top' : 50,'border': '13px solid green'}
        elif styleDBRS=='small':
            style2 = {'padding-bottom' : 10,'padding-top' : 10,'border': '3px solid green'}
        elif styleDBRS=='centered':
            style2 = {'text-align': 'center','border': '3px solid green','font-size':'18'}

        if not t0:
            t0 = parser.parse('00:00')
        if not t1:
            t1 = t0 + dt.timedelta(seconds=3600*24*2-1)
        p0      = html.H5('fixe time t0')
        in_t0   = dcc.Input(id=baseId + 'in_t0',type='text',value=t0.strftime(formatTime),size='75')
        in_t1   = dcc.Input(id=baseId + 'in_t1',type='text',value=t1.strftime(formatTime),size='75')
        p       = html.H5('select the time window :',style={'font-size' : 40})
        ine     = dcc.Input(id=baseId + 'ine',type='text',value=t0.strftime(formatTime))
        rs      = self.timeRangeSlider(id=baseId + 'rs',t0=t0,t1=t1,nbMarks=5)
        ins     = dcc.Input(id=baseId + 'ins',type='text',value=t1.strftime(formatTime))
        pf      = html.H5('timeselect start and end time ', id = 'pf',style={'font-size' : 60})
        dbrsLayout = html.Div([
                            dbc.Row([dbc.Col(p0),
                                    dbc.Col(in_t0),
                                    dbc.Col(in_t1)],style=style2,no_gutters=True),
                            dbc.Row(dbc.Col(p),style=style2,no_gutters=True),
                            dbc.Row([dbc.Col(ine),
                                    dbc.Col(rs,width=9),
                                    dbc.Col(ins)],
                                    style=style2,
                                    no_gutters=True),
                            ])
        return dbrsLayout

    def parseLayoutIds(self,obj,debug=False):
        c = True
        ids,queueList,k = [],[],0
        while c:
            if debug : k=k+1;print(k)
            if isinstance(obj,list):
                if debug : print('listfound')
                if len(obj)>1 : queueList.append(obj[1:])
                obj = obj[0]
            elif hasattr(obj,'id'):
                if debug : print('id prop found')
                ids.append(obj.id)
                obj='idfound'
            elif hasattr(obj,'children'):
                if debug : print('children found')
                obj=obj.children
            elif not queueList:
                if debug : print('queue list empty')
                c=False
            else :
                if debug : print('iterate over queue list')
                obj = queueList.pop()
        return ids

    def autoDictOptions(self,listWidgets):
        dictOpts = {}
        d1 = {k : 'value' for k in listWidgets if bool(re.search('(in_)|(dd_)', k))}
        d2 = {k : 'n_clicks' for k in listWidgets if bool(re.search('btn_', k))}
        d3 = {k : 'figure' for k in listWidgets if bool(re.search('graph', k))}
        d4 = {k : 'children' for k in listWidgets if bool(re.search('fileInCache', k))}
        for d in [d1,d2,d3,d4] :
            if not not d : dictOpts.update(d)
        return dictOpts
