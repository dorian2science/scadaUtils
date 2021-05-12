def typeGraph(self,baseId,widthG=80):
    listTG=list(self.cfg.typeGraphs.keys())
    listTGDisabled = list(self.cfg.typeGraphs.values())
    AGVL_html = html.Div([
        html.Div(
            self.dccE.dropDownFromList(baseId + 'dd_listFiles',self.cfg.listFilesPkl,'Select your File : ',
                                        labelsPattern = '\d{4}-\d{2}-\d{2}-\d{2}',defaultIdx=5)+
            [html.P('Select the type of Graph : '),
            dcc.Dropdown(id=baseId + 'dd_typeGraph',options = [{'label' : t, 'value' : t, 'disabled' : d}
                                    for t,d in zip(listTG,listTGDisabled)],value=listTG[0])]+
            # self.dccE.dropDownFromList(baseId + 'dd_graphOption',['percent',''],'select the graph option :',value='percent')+
            [html.P('select the graph option :'),
            dcc.Dropdown(id=baseId + 'dd_graphOption',options=[{'label' : 'standard','value' : ''},
                                                            {'label' : 'percent','value' : 'percent'}]
                                                            ,value='')]+
            [html.P('time resolution in seconds : '),
            dcc.Input(id=baseId + 'in_time',placeholder=' time resolution in seconds : ',type='number',value=60)]+
            self.dccE.dropDownFromList(baseId + 'dd_cmap',self.cfg.cmaps[0],'select the colormap',value='jet'),
            style={"width": str(100-widthG) + "%", "float": "left"},
        ),
        dcc.Graph(id=baseId + 'graph',style={"width": str(widthG) + "%", "display": "inline-block"}),
        html.Div(id=baseId + 'cacheVal', style={'display': 'none'})
    ])
    @self.cache.memoize()
    def storeDF(value):
        filename,typeGraph,stepTime = value
        df = self.cfg.loadFile(filename,self.skipEveryHours)
        # dfPower=pd.concat([cfg.getDFsameCat(df,'A'),cfg.getDFsameCat(df,'W')])
        return self.cfg.getDFtypeGraph(df,typeGraph,timeWindow=stepTime)

    @self.app.callback(
    Output(baseId + 'cacheVal', 'children'),
    Input(baseId + 'dd_listFiles','value'),
    Input(baseId + 'dd_typeGraph','value'),
    Input(baseId + 'in_time','value'),
    )
    def computeDf(filename,typeGraph,stepTime):
        value = [filename,typeGraph,stepTime]
        storeDF(value)
        return value

    @self.app.callback(
    Output(baseId + 'graph', 'figure'),
    Input(baseId + 'cacheVal','children'),
    Input(baseId + 'dd_cmap','value'),
    Input(baseId + 'dd_graphOption','value'),
    State(baseId + 'dd_graphOption',"options"),
    )
    def update_graph(value,cmapName,graphOpt,opt):
        df = storeDF(value)
        if value[1] == 'Bilan système en puissance' :
            fig = px.area(df, x="timestamp", y="value", color="groupPower",
                    line_group="Tag",groupnorm=graphOpt,height=900,title=value[0])
            labelOpt = [x['label'] for x in opt if x['value'] == graphOpt]
            figname=self.cfg.utils.makeFigureName(value[0],'-Real',['P_aux',labelOpt[0]])+'.png'
        # print(self.cfg.folderFig + figname)
        fig.write_image(self.cfg.folderFig + figname,width=1500,height=400)
        return fig
    return AGVL_html
