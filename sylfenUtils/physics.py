# import time
# start=time.time()
import numpy as np,pandas as pd,os,sys
from sylfenUtils import utils
from sylfenUtils.comUtils import (html_table,print_file)
import plotly.express as px
# print(time.time()-start)
# from conf_modeling import conf as CONF,
from sylfenUtils.utils import inspect_simple
import inspect
import pint
from pint import UnitRegistry
import CoolProp.CoolProp as CP
ureg = UnitRegistry()
ureg.load_definitions(os.path.join(os.path.dirname(__file__),'rsoc_units.txt'))
c = pint.Context('rsoc')
c.add_transformation('[length] ** 3', '[mass]',lambda ureg, x,d:x * d)
c.add_transformation('[length] ** 3/[time]', '[mass]/[time]',lambda ureg, x,d:x * d)
c.add_transformation('[mass]','[length] ** 3',lambda ureg, x,d:x/d)
c.add_transformation('[mass]/[time]','[length] ** 3/[time]',lambda ureg, x,d:x/d)
ureg.add_context(c)
Q_ = ureg.Quantity

def show_pretty(s,p=3):
    return s.apply(lambda x:[round(x.m,p),x.u if isinstance(x,Q) else x])

def show_locals(locs,fa):
    res={k:v for k,v in locs.items() if k not in fa.keys()}
    for k,v in res.items():
        if isinstance(v,Q_):
            res[k]=v.to_root_units()
    res=pd.Series(res).T
    print(res)
    return res
    # res=res.apply(lambda x:[round(x.m,3),x.u if isinstance(x,Q_) else x])


coolProps_Q={
'D':'kg/m**3',
'H':'J/kg',
'Q':'mol/mol',
'S':'J/kg/K',
'U':'K/kg',
'A':'m/s',
'L' :'W/m/K',
'V':'Pa/s',
'C' :'J/kg/K',
'G':'J/kg',
'M':'kg/mol',
}

def get_val(pdf,tag):
    val=pdf.loc[tag]
    return Q_(val.iloc[0],val['unite'])

def get_prop(prop,molecule,T=None,P=None,*args,**kwargs):
    if T is None:T=Q_(273.25,'K')
    if P is None:P=Q_(1,'atm')
    T=T.to('K')
    P=P.to('pascal')
    value=CP.PropsSI(prop,'P',P.m,'T',T.m,molecule,*args,**kwargs)
    return Q_(value,coolProps_Q[prop])

COMMON_UNITS={
    'pressure':'mbarg',
    'time':'s',
    'distance':'m',
    'surface':'m**2',
    'volume':'l',
    'mass flow':'g/h',
    'volumetric flow':'l/min',
    'current':'A',
    "voltage":'V',
    'power':'kW',
    'thermal flow rate':'W/K',
    'heat transfer coefficient':'W/m/K',
    'specific mass capacity':'J/g/K',
    # 'temperature difference':'delta degC',
    'temperature':'degC',
    # "reactive power":'kW VAR',
    "mass":'kg',
    "energy":'kWh',
    "specific energy ":'kWh/kg',
    "force":'kgf',
    'speed':'km/h',
    'substance':'moles',
    "conductance":'siemens',
    "resistance":'ohm',
    "ratio":'percent',
    # "electrical capacity"
    # "consigne",
}
ureg.default_format='~P'
GRANDEURS={f"{ureg.Quantity(1,u).dimensionality}":k for k,u in COMMON_UNITS.items()}
SI_UNITS={k:f"{ureg.Quantity(1,u).to_base_units().units}" for k,u in COMMON_UNITS.items()}

def get_unit(u,what='si'):
    '''
    Parameters:
    -------------
    what:{'si','common','grandeur','label','label_si','label_common'}
    '''
    si_unit=f"{Q_(1,u).to_base_units().units}"
    grandeur=[g for g,unit in SI_UNITS.items() if unit==si_unit]
    if what=='si':
        return si_unit
    else:
        if not len(grandeur)==1:
            print('oups. No physical quantity registered in SI_UNITS for unit :',u)
            return
        grandeur=grandeur[0]
        if what=='grandeur':
            return grandeur
        common_unit=COMMON_UNITS[grandeur]
        if what=='common':
            return common_unit
        else:
            if what=='label_si':unit=si_unit
            elif what=='label_common':unit=common_unit
            elif what=='label':unit=u
            return grandeur.capitalize() + '('+ unit +') '

def convert_u1_to_u2(val,u1,u2,format='~.6fP',**kwargs):
    '''
    Parameters:
    ---------
        format : [str] pint format. Or ['m','m+u'] then only the magnitude or magnitude + units is returned.
    '''
    q=Q_(val,u1)
    q_si=q.to_base_units()
    # q.format_babel(locale='fr_FR')
    if u2.lower()=='si':
        res=q_si
    elif u2.lower()=='common':
        grandeur=GRANDEURS[f"{q_si.dimensionality}"]
        u2=COMMON_UNITS[grandeur]
        grandeur2=GRANDEURS[f"{ureg.Quantity(1,u2).dimensionality}"]
        # res=q.to(u2,'rsoc',**kwargs)
        res=q.to(u2,'rsoc',**kwargs)
    else:
        # print(locals())
        res=q.to(u2,'rsoc',**kwargs)

    if format=='pint':return res
    if format=='m':return res.m
    elif format=='m+u':return {'value':res.m,'unit':res.units}
    else:
        ureg.default_format = format
        return f"{res}"

def convert_fluid_prop(value,u1,u2,molecule,*args):
    props=CST[CST.index.str.contains(molecule)].T.to_dict()
    props={k.split('_')[0]:v['value'] * ureg(v['unit']) for k,v in props.items()}
    return convert_u1_to_u2(value,u1,u2,*args,**props)

def convert_to_common_units_df(df,u2='common',format='m+u'):
    '''
    Convert a DataFrame of values/units to common or SI units.
    Parameters :
    ---------------
        - df : dataframe with at least 2 columns : value, unit
    '''
    new_df = df.apply(lambda x:convert_u1_to_u2(x['value'],x['unit'],u2,format=format),axis=1)
    return pd.DataFrame(new_df.to_list())
    # return new_df

to_si = lambda v,u:convert_u1_to_u2(v,u,'si',format='m')
from_si = lambda v,u:convert_u1_to_u2(v,get_unit(u,'si'),u,format='m')
def convert_df_units(df,Qs):
    '''Qs:[dictionnary] keys are columns names and values are desired units'''
    new_df=df.copy()
    for g,u in Qs.items():
        # new_df[g]=convert_u1_to_u2(df[g].to_list(),get_unit(u,'si'),u,'m').round(2)
        new_df[g]=from_si(df[g].to_list(),u).round(2)
    return new_df
def update_graph(fig,Qs):
    '''Qs:[dictionnary] keys are columns names and values are desired units'''
    fig.update_traces(mode='lines+markers')
    cur_xaxis=fig.layout.xaxis.title.text
    cur_yaxis=fig.layout.yaxis.title.text
    fig.update_layout(
        xaxis_title=get_unit(Qs[cur_xaxis],'label'),
        yaxis_title=get_unit(Qs[cur_yaxis],'label')
    )
    return fig
units_test=lambda v,u2:v.to_root_units().u==Q_(u2).to_root_units().u

constants=pd.Series({k:convert_u1_to_u2(1,k,'si',format='~eP') for k in dir(ureg) if 'constant' in k }).T

########## MATHS ##########
def show_poly(coeffs,xs=[-10,10],N=100):
    x=np.linspace(*xs,N)
    p=np.poly1d(coeffs)
    px.scatter(pd.DataFrame(p(x.tolist()),index=x)).show()

T0=Q_(293.15,'K')
P0=Q_(1,'atm')
def Nl_to_liter(v,P=None,T=None):
    '''
    v,P,T: [pint.util.Quantity]volume pression temperature
    '''
    if P is None:P=P0
    if T is None:T=T0
    T,P=T.to('K'),P0.to('atm')
    return P0/P*T/T0 * v

def liter_to_Nl(v,P=None,T=None):
    '''
    v,P,T: [pint.util.Quantity]volume pression temperature
    '''
    if P is None:P=P0
    if T is None:T=T0
    T,P=T.to('K'),P0.to('atm')
    return P/P0*T0/T * v

def get_molar_volume(T=None,P=None):
    if T is None:T=T0
    T=T.to_root_units()
    if P is None:P=P0
    P=P.to_root_units()
    vlm=Q_(1,'R')*T/P
    return vlm.to_root_units()

def mass_to_volum_flow(qm,molecule,T,unit2='Nl/min'):
    d=get_prop('D',molecule,T=T)
    return qm.to(unit2,'rsoc',d=d)

def volum_to_mass_flow(qm,molecule,T,unit2='Nl/min'):
    d=get_prop('D',molecule,T=T)
    return qm.to(unit2,'rsoc',d=d)

def convert_flow(q,molecule,u2,verbose=False):
    if molecule.lower()=='h2o_gas':
        molecule='H2O'
        T=Q_(105,'degC')
    else:
        T=Q_(20,'degC')
    d=get_prop('D',molecule,T=T)
    mw=get_prop('M',molecule,T=T)
    vlm=get_molar_volume()

    if units_test(q,'Nl/min'):
        qv=q
        ### volumetric flow to mass flow
        qm=qv*d
        ### volumetric flow to molar flow
        q_molps=qv/vlm
    elif units_test(q,'g/min'):
        qm=q
        ### mass flow to volumetric flow
        qv=qm/d
        ### mass flow to molar flow
        q_molps=qm/mw

    elif units_test(q,'mol/s'):
        q_molps=q
        ### molar flow to volumetric flow
        qv=q_molps*vlm
        ### molar flow to mass flow
        qm=q_molps*mw

    df=pd.Series({'your flow':q,
        'mass flow':qm,
        'volumetric flow':qv,
        'molar flow':q_molps,
    })
    # print(df)
    qv=qv.to('Nl/min')
    qm=qm.to('g/s')
    q_molps=q_molps.to('mol/s')
    if units_test(Q_(1,u2),'Nl/min'):qf=qv.to(u2)
    if units_test(Q_(1,u2),'g/min'):qf=qm.to(u2)
    if units_test(Q_(1,u2),'mol/s'):qf=q_molps.to(u2)
    if verbose:
        df=pd.Series({'your flow':q,
            'mass flow':qm,
            'volumetric flow':qv,
            'molar flow':q_molps,
            'final flow':qf,
            })
        return df
    return qf

class ReUtils(utils.Utils):
    def sample_colorscale(self,N,colorscale='jet'):
        if colorscale=='Alphabet':
            return [c for k,c in zip(range(N),px.colors.qualitative.Alphabet)]
        return px.colors.sample_colorscale(colorscale,np.linspace(0,1,N))

    def getLayoutMultiUnit(self,*args,**kwargs):
        colormap='Alphabet'
        return utils.Utils.getLayoutMultiUnit(self,*args,colormap=colormap,**kwargs)

class Thermics():
    def get_gibbs_free_energy_reaction(self,reaction,T=293):
        dH0=1
        dH=1
        dS=1
        return dH-T*dS

    def get_power_phase_change(self,q,molecule='H2O',x=1):
        '''
        - q : volumetric flow in m3/s
        - x : fraction of molecule vaporised
        '''
        ch_latente=CST['cl_'+molecule]
        qm=self.v_flow_to_mass_flow(q,molecule)
        return ch_latente*qm*x

    def get_simple_heat_flow(self,q,molecule,Tc,Th,Nl=False,integral=False,dT=1,P=None,verbose=False):
        '''
        Compute the heat flow of a fluid between 2 temperatures.
        - molecule[str] : (valid coolprops molecule) for example water,h2...
        - q[pint] : volumetric or mass flow.
        - Nl : [bool] if True it means that the flow is in normal liters.
        - Th,Tc[pint]: bound temperatures ideally Th>Tc(otherwise <0)
        '''
        fa=locals().copy();fa['fa']=''

        if P is None:P=P0
        P=P.to_root_units()
        Tc,Th=Tc.to_root_units(),Th.to_root_units()
        if Tc>Th:
            tmp=Tc
            Tc=Th
            Th=tmp

        ### if using normal liters convert to liters
        qi = q
        qm = convert_flow(q,molecule,'g/s')
        ###### should integrate the Cp instead #####
        if integral:
            heat_flows=[]
            T=Q_(np.arange(Tc.m,Th.m,dT),'K')
            for tt in T:
                cp=get_prop('C',molecule,P=P,T=tt)
                heat_flows+=[qm*cp*Q_(dT,'K')]
            heat_flow=sum(heat_flows).to('W')
        else:
            cp=get_prop('C',molecule,P=P,T=Tc)
            heat_flow = (qm*cp*(Th-Tc)).to('W')

        if verbose:print_file('debugging here');return show_locals(locals(),fa)
        return heat_flow

    def get_heat_flow(self,q,composition,Tc,Th,*args,**kwargs):
        '''
        Compute the heat flow of a fluid between 2 temperatures.
        - composition : dictionnary of molecules[str]:fraction[float]
        - q[pint] : volumetric flow in normal units like Nl/min
        - Tc,Th[pint]: bound temperatures.
        *args,**kwargs : see get_simple_heat_flow
        '''
        heat_flows={}
        for molecule,frac in composition.items():
            qx=frac*q
            heat_flows[molecule]=self.get_simple_heat_flow(qx,molecule,Tc,Th,*args,**kwargs)
        return sum(heat_flows.values())

thermics=Thermics()

def stack_production(I,molecule,nbCells,unit='g/h',verbose=False):
    '''
    - I[pint array]:current.
    - molecule[str]:the molecule that is produced : {H2,O2}
    '''
    if molecule=='O2' or molecule=='air':z=4
    elif molecule=='H2':z=2
    else:
        print_file('molecule should be H2 or O2')
        return
    q_molps=(I/(z*Q_('faraday_constant'))*nbCells).to('mol/s')

    # mw=get_prop('M',molecule)
    # q_gs=(q_molps/mw).to('g/s')
    q_nlpm=(q_molps*get_molar_volume()).to('Nl/min')
    d=get_prop('D',molecule)
    qm=q_nlpm.to('g/s','rsoc',d=d)

    if units_test(Q_(1,unit),Q_(1,'g/s')):
        qf=qm.to(unit)
    elif units_test(Q_(1,unit),Q_(1,'mol/s')):
        qf=q_molps.to(unit)
    else:
        qf=q_nlpm.to(unit)
    if verbose:
        df=pd.DataFrame([I,q_molps,q_nlpm,qm,qf]).T
        df.columns=['current','molar flow','volumetric flow','mass flow','unit selected']
        return df
    return qf
