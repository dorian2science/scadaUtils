#!/bin/python
import sys, glob, re, os, time, datetime as dt,importlib,pickle,glob
import pandas as pd,numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sylfenUtils.utils import Utils
from sylfenUtils import comUtils
from sylfenUtils.comUtils import (
    SuperDumper_daily,
    ModbusDevice,Meteo_Client,
    VisualisationMaster_daily,
)
from sylfenUtils.VersionsManager import VersionsManager_daily
import os,pandas as pd,numpy as np,glob,sys,time
import textwrap
from sylfenUtils.comUtils import print_file
from scipy import integrate
from pandas.tseries.frequencies import to_offset
import plotly.express as px, plotly.graph_objects as go

class Monitoring_dumper(SuperDumper_daily):
    def __init__(self,conf,log_file_name):
        DEVICES={}
        for device_name in conf.ACTIVE_DEVICES:
            device=conf.DF_DEVICES.loc[device_name]
            if device.protocole=='modebus':
                DEVICES[device_name] = ModbusDevice(
                    device_name=device_name,ip=device['IP'],port=device['port'],
                    dfplc=conf.PLCS[device_name],
                    modbus_map=conf.MODEBUS_MAPS[device_name],
                    freq=device['freq'],
                    bo=device['byte_order'],
                    wo=device['word_order'],
                    log_file=log_file_name)
            elif device_name=='meteo':
                DEVICES['meteo'] = Meteo_Client(conf.DF_DEVICES.loc['meteo'].freq,log_file=log_file_name)
        self.dfplc = pd.concat([v for k,v in conf.PLCS.items() if k in conf.ACTIVE_DEVICES])
        self.alltags = list(self.dfplc.index)
        SuperDumper_daily.__init__(self,DEVICES,conf.FOLDERPKL,conf.DB_PARAMETERS,conf.PARKING_TIME,
            tz_record=conf.TZ_RECORD,dbTable=conf.DB_TABLE,log_file=log_file_name)

class Monitoring_visu(VisualisationMaster_daily):
    def __init__(self,conf,**kwargs):
        VisualisationMaster_daily.__init__(self,conf.FOLDERPKL,conf.DB_PARAMETERS,conf.PARKING_TIME,
            tz_record=conf.TZ_RECORD,dbTable=conf.DB_TABLE,**kwargs)

        self.utils = Utils()
        self.conf  = conf

        self.usefulTags = conf.useful_tags
        self.dfplc      = conf.df_plc
        self.alltags    = list(self.dfplc.index)
        self.listUnits  = self.dfplc.UNITE.dropna().unique().tolist()

        tag_cats={cat: self.getTagsTU(self.usefulTags.loc[cat,'Pattern']) for cat in self.usefulTags.index}
        tag_cats['pv meters'] = self.getTagsTU('PV.*JTWH$')
        tag_cats['pv power'] = self.getTagsTU('PV.*JTW$')
        self.tag_categories = tag_cats

        self.listComputation = ['power enveloppe','consumed energy','energyPeriodBarPlot']

    def getUsefulTags(self,tagcat):
        return self.usefulTags.loc[tagcat]

    def get_description_tags_compteurs(self,tags):
        counts=[k.split('-')[1] for k in tags]
        return [self.compteurs.loc[k,'description'] for k in counts]

    # ==========================================================================
    #                       COMPUTATIONS FUNCTIONS
    # ==========================================================================
    def computePowerEnveloppe(self,timeRange,compteur,rs):
        listTags = self.getTagsTU(compteur+'.+[0-9]-JTW','kW')
        df = self.df_loadTimeRangeTags(timeRange,listTags,rs='5s')
        L123min = df.min(axis=1)
        L123max = df.max(axis=1)
        L123moy = df.mean(axis=1)
        L123sum = df.sum(axis=1)
        df = pd.concat([df,L123min,L123max,L123moy,L123sum],axis=1)

        from dateutil import parser
        ts=[parser.parse(t) for t in timeRange]
        deltaseconds=(ts[1]-ts[0]).total_seconds()
        if rs=='auto':rs = '{:.0f}'.format(max(1,deltaseconds/1000)) + 's'
        df = df.resample(rs).apply(np.mean)
        dfmin = L123min.resample(rs).apply(np.min)
        dfmax = L123max.resample(rs).apply(np.max)
        df = pd.concat([df,dfmin,dfmax],axis=1)
        df.columns=['L1_mean','L2_mean','L3_mean','PminL123_mean','PmaxL123_mean',
                    'PmoyL123_mean','PsumL123_mean','PminL123_min','PmaxL123_max']
        return df

    def compute_kWhFromPower(self,timeRange,compteurs,rs):
        generalPat='('+'|'.join(['(' + c + ')' for c in compteurs])+')'
        listTags = self.getTagsTU(generalPat+'.*sys-JTW')

        df = self.df_loadTimeRangeTags(timeRange,listTags,rs=rs,applyMethod='mean',pool=True)
        dfs=[]
        for tag in listTags:
            dftmp = self._integratePowerCol(df,tag,True)
            if not dftmp.empty:dfs.append(dftmp)

        try : df=pd.concat(dfs,axis=1)
        except : df = pd.DataFrame()
        return df.ffill().bfill()

    def compute_kWhFromCompteur(self,timeRange,compteurs):
        generalPat='('+'|'.join(['(' + c + ')' for c in compteurs])+')'
        listTags = self.getTagsTU(generalPat+'.+kWh-JTWH')
        df = self.df_loadTimeRangeTags(timeRange,listTags,rs='raw',applyMethod='mean')
        df = df.drop_duplicates()
        dfs=[]
        for tag in listTags:
            x1=df[df.tag==tag]
            dfs.append(x1['value'].diff().cumsum()[1:])
        try :
            df = pd.concat(dfs,axis=1)
            df.columns = listTags
        except : df = pd.DataFrame()
        return df.ffill().bfill()

    def plot_compare_kwhCompteurvsPower(self,timeRange,compteurs,rs):
        dfCompteur = self.compute_kWhFromCompteur(timeRange,compteurs)
        dfPower = self.compute_kWhFromPower(timeRange,compteurs)
        df = self.utils.prepareDFsforComparison([dfCompteur,dfPower],
                            ['energy from compteur','enery from Power'],
                            group1='groupPower',group2='compteur',
                            regexpVar='\w+-\w+',rs=rs)

        fig=px.line(df,x='timestamp',y='value',color='compteur',line_dash='groupPower',)
        fig=self.utils.quickLayout(fig,'energy consumed from integrated power and from energy counter',ylab='kWh')
        fig.update_layout(yaxis_title='energy consommée en kWh')
        return fig

    def energyPeriodBarPlot(self,timeRange,compteurs,period='1d'):
        dfCompteur   = self.compute_kWhFromCompteur(timeRange,compteurs)
        df = dfCompteur.resample(period).first().diff()[1:]
        fig = px.bar(df,title='répartition des énergies consommées par compteur')
        fig.update_layout(yaxis_title='énergie en kWh')
        fig.update_layout(bargap=0.5)
        return fig
    # ==========================================================================
    #                       for website monitoring
    # ==========================================================================
    # def getListTagsAutoConso(self,compteurs):
    #     pTotal = [self.getTagsTU(k + '.*sys-JTW')[0] for k in compteurs]
    #     pvPower = self.getTagsTU('PV.*-JTW-00')[0]
    #     listTagsPower = pTotal + [pvPower]
    #     energieTotale = [self.getTagsTU(k + '.*kWh-JTWH')[0] for k in compteurs]
    #     pvEnergie = self.getTagsTU('PV.*-JTWH-00')[0]
    #     listTagsEnergy = energieTotale + [pvEnergie]
    #     return pTotal,pvPower,listTagsPower,energieTotale,pvEnergie,listTagsEnergy
    #
    # def computeAutoConso(self,timeRange,compteurs,formula='g+f-e+pv'):
    #     pTotal,pvPower,listTagsPower,energieTotale,pvEnergie,listTagsEnergy = self.getListTagsAutoConso(compteurs)
    #     # df = self.df_loadTimeRangeTags(timeRange,listTagsPower,'600s','mean')
    #     df = self.df_loadTimeRangeTags(timeRange,listTagsPower,'600s','mean')
    #     if formula=='g+f-e+pv':
    #         g,e,f = [self.getTagsTU(k+'.*sys-JTW')[0] for k in ['GENERAL','E001','F001',]]
    #         df['puissance totale'] = df[g] + df[f] - df[e] + df[pvPower]
    #     elif formula=='sum-pv':
    #         df['puissance totale'] = df[pTotal].sum(axis=1) - df[pvPower]
    #     elif formula=='sum':
    #         df['puissance totale'] = df[pTotal].sum(axis=1)
    #
    #     df['diffPV']=df[pvPower]-df['puissance totale']
    #     dfAutoConso = pd.DataFrame()
    #     df['zero'] = 0
    #     dfAutoConso['part rSoc']     = 0
    #     dfAutoConso['part batterie'] = 0
    #     dfAutoConso['part Grid']     = -df[['diffPV','zero']].min(axis=1)
    #     dfAutoConso['Consommation du site']      = df['puissance totale']
    #     dfAutoConso['surplus PV']    = df[['diffPV','zero']].max(axis=1)
    #     dfAutoConso['part PV']       = df[pvPower]-dfAutoConso['surplus PV']
    #     # dfAutoConso['Autoconsommation'] = df[pvPower]-dfAutoConso['PV surplus']
    #     return dfAutoConso
    #
    # def consoPowerWeek(self,timeRange,compteurs,formula='g+f-e+pv'):
    #     pTotal,pvPower,listTagsPower,energieTotale,pvEnergie,listTagsEnergy = self.getListTagsAutoConso(compteurs)
    #     # df = self.df_loadTimeRangeTags(timeRange,listTagsPower,'1H','mean')
    #     df = self.df_loadTimeRangeTags(timeRange,listTagsPower,'1H','mean')
    #
    #     if formula=='g+f-e+pv':
    #         g,e,f = [self.getTagsTU(k+'.*sys-JTW')[0] for k in ['GENERAL','E001','F001',]]
    #         df['puissance totale'] = df[g] + df[f] - df[e] + df[pvPower]
    #     elif formula=='sum-pv':
    #         df['puissance totale'] = df[pTotal].sum(axis=1) - df[pvPower]
    #     elif formula=='sum':
    #         df['puissance totale'] = df[pTotal].sum(axis=1)
    #
    #     df = df[['puissance totale',pvPower]]
    #     df.columns = ['consommation bâtiment','production PV']
    #     return df
    #
    # def compute_EnergieMonth(self,timeRange,compteurs,formula='g+f-e+pv'):
    #     pTotal,pvPower,listTagsPower,energieTotale,pvEnergie,listTagsEnergy = self.getListTagsAutoConso(compteurs)
    #     # df = self.df_loadTimeRangeTags(timeRange,listTagsEnergy,rs='raw',applyMethod='mean')
    #     df = self.df_loadTimeRangeTags(timeRange,listTagsEnergy,rs='raw',applyMethod='mean')
    #     df = df.drop_duplicates()
    #
    #     df=df.pivot(columns='tag',values='value').resample('1d').first().ffill().bfill()
    #     newdf=df.diff().iloc[1:,:]
    #     newdf.index = df.index[:-1]
    #     if formula=='g+f-e+pv':
    #         g,e,f = [self.getTagsTU(k + '.*kWh-JTWH')[0] for k in ['GENERAL','E001','F001',]]
    #         newdf['energie totale'] = newdf[g] + newdf[f] - newdf[e] + newdf[pvEnergie]
    #     elif formula=='sum-pv':
    #         newdf['energie totale'] = newdf[pTotal].sum(axis=1) - newdf[pvEnergie]
    #     elif formula=='sum':
    #         newdf['energie totale'] = newdf[energieTotale].sum(axis=1)
    #
    #     newdf = newdf[['energie totale',pvEnergie]]
    #     newdf.columns = ['kWh consommés','kWh produits']
    #     return newdf
    #
    # def get_compteur(self,timeDate,compteurs,formula='g+f-e+pv'):
        timeRange = [k.isoformat() for k in [timeDate - dt.timedelta(seconds=600),timeDate]]
        pTotal,pvPower,listTagsPower,energieTotale,pvEnergie,listTagsEnergy = self.getListTagsAutoConso(compteurs)
        df = self.df_loadTimeRangeTags(timeRange,listTagsEnergy,rs='20s',applyMethod='mean')
        g,e,f = [self.getTagsTU(k + '.*kWh-JTWH')[0] for k in ['GENERAL','E001','F001',]]
        if formula=='g+f-e+pv':
            df['energie totale'] = df[g] + df[f] - df[e] + df[pvEnergie]
        elif formula=='sum':
            df['energie totale'] = df[energieTotale].sum(axis=1)
        return df.iloc[-1,:]
    # ==============================================================================
    #                   GRAPHICAL FUNCTIONS
    # ==============================================================================
    def multiUnitGraphSB(self,df,tagMapping=None,**kwargs):
        if not tagMapping:tagMapping = {t:self.getUnitofTag(t) for t in df.columns}
        fig = self.utils.multiUnitGraph(df,tagMapping,**kwargs)
        return fig
