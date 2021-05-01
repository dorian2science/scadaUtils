def doubleGraphLayout(self,baseId,widthG=80,heightGraph=400,timeSelect='rs_time'):
   listWidgets = ['dd_listFiles','dd_typeTags1','dd_typeTags2',
                   'btn_legend','in_step','dd_cmap','rs_time']

   if timeSelect == 'in_time' :
       listWidgets.append('in_time')

   DG_html = self.buildLayout(listWidgets,baseId,widthG=widthG,cacheFile=True,nbGraphs=2)

   @self.cache.memoize()
   def storeDF(filename):
       return self.cfg.loadFile(filename,self.skipEveryHours)

   @self.app.callback(Output(baseId + 'fileInCache','children'),
   Input(baseId + 'dd_listFiles','value'))
   def computeDF(filename):
       storeDF(filename)
       return filename

   @self.app.callback(Output(baseId + 'btn_legend', 'children'),
   Input(baseId + 'btn_legend','n_clicks'))
   def updateBtnState(legendType):
       return self.changeLegendBtnState(legendType)

   @self.app.callback(Output(baseId + 'rs_time','marks'),
   Input(baseId + 'fileInCache','children'))
   def updateTimeMarks(filename):
       df = storeDF(filename)
       marks = self.cfg.utils.buildTimeMarks(df.timestamp[0])
       return marks

   if timeSelect == 'in_time' :
       @self.app.callback(Output(baseId + 'rs_time','value'),
       Input(baseId + 'in_timeStart','value'),
       Input(baseId + 'in_timeEnd','value'),
       State(baseId + 'fileInCache','children'))
       def updateTime(startTime,endTime,filename):
           df = storeDF(filename)
           return self.cfg.utils.convertToSecs([startTime,endTime],df.timestamp[0])

       @self.app.callback(
       Output(baseId + 'in_timeStart','value'),
       Output(baseId + 'in_timeEnd','value'),
       Input(baseId + 'rs_time','value'),
       State(baseId + 'fileInCache','children'))
       def updateTimeValue(rsTime,filename):
           df = storeDF(filename)
           return self.cfg.utils.convertSecstoHHMM(rsTime,df.timestamp[0])

   def updateGraph(filename,timeRange,keyDD,step,cmapName,legendType):
       unit    = self.cfg.usefulTags[keyDD][1]
       tagPat  = self.cfg.usefulTags[keyDD][0]
       df = storeDF(filename)
       dfT = self.cfg.getDFTime(df,timeRange).iloc[::step]
       dfT = self.cfg.getDFTagsTU(dfT,tagPat,unit,printRes=0)
       fig = self.updateTUGraph(filename,tagPat,unit,step,cmapName,legendType,df=dfT,heightGraph=heightGraph,breakLine=60)
       return fig

   inPutList1 = {'fileInCache' : 'children','rs_time':'value','dd_typeTags1':'value',
                   'in_step':'value','dd_cmap':'value','btn_legend':'n_clicks'}
   inPutList2 = {'fileInCache' : 'children','rs_time':'value','dd_typeTags2':'value',
                   'in_step':'value','dd_cmap':'value','btn_legend':'n_clicks'}


   @self.app.callback(Output(baseId + 'graph1', 'figure'),[Input(baseId+k,v) for k,v in inPutList1.items()])
   def updateGraph1(filename,timeRange,keyDD,step,cmapName,legendType):
       return updateGraph(filename,timeRange,keyDD,step,cmapName,legendType)

   @self.app.callback(Output(baseId + 'graph2', 'figure'),[Input(baseId+k,v) for k,v in inPutList2.items()])
   def updateGraph2(filename,timeRange,keyDD,step,cmapName,legendType):
       return updateGraph(filename,timeRange,keyDD,step,cmapName,legendType)

   return DG_html
