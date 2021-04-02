import dash_html_components as html
import dash_core_components as dcc
import re,dateutil
from utilsD import Utils

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

    def rangeSliderTime(self,tt,nbMarks = 5,parseYes=0):
        marksT = self.utils.linspace(tt,nbMarks)
        if parseYes :
            marksT = [dateutil.parser.parse(k) for k in marksT]
        values = [round((k-marksT[0]).total_seconds()) for k in marksT]
        labels = [{'label' : k.strftime('%H:%M')} for k in marksT]
        mini = round(values[0])
        maxi = round(values[-1])
        dictMarks = dict(zip(values,labels))
        value = [mini,maxi]
        return mini,maxi,value, dictMarks
        # return min,max,value,dictMarks
