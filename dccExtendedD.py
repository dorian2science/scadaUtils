import dash_html_components as html
import dash_core_components as dcc
import re

class DccExtended:
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

    # def basicLayoutWithFiles(self,idRT,listFilenames,widthG,list)
    #     RTObj = html.Div(
    #     [
    #         html.Div(
    #             self.dropDownFromList(idRT + 'dd_listFiles',listFilenames,'Select your File : ',
    #             labelsPattern='\d{4}-\d{2}-\d{2}',defaultIdx=0) +
    #             self.dropDownFromList(idRT + 'dd_Units',self.cfg.listUnits,'Select units graph : ',value='W') +
    #             self.dropDownFromList(idRT + 'dd_patternCat',self.cfg.listPatterns,'Select pattern for categories : ')+
    #             [html.P('select category: '),dcc.Dropdown(id=idRT+'dd_subcat',multi=True)] +
    #             [html.P('skip points : '),
    #             dcc.Input(id=idRT + 'step_in',placeholder='skip points : ',type='text',value=1)] +
    #             self.dccE.dropDownFromList(idRT + 'dd_cmap',self.cfg.cmaps[0],'select the colormap'),
    #             style={"width": str(100-widthG) + "%", "float": "left"},
    #             ),
    #         # a graph
    #         dcc.Graph(id=idRT + 'graph',style={"width": str(widthG) + "%", "display": "inline-block"}),
    #         #a signal in cache
    #         html.Div(id=idRT + 'cacheVal', style={'display': 'none'})
    #     ])
    #     return RTObj
