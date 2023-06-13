import numpy as np
import pandas as pd
import sys
from scadaUtils.utils import Utils
from scadaUtils import physics
thermics=physics.thermics
import numpy as np
import pandas as pd
import plotly.express as px

ureg=physics.ureg
ureg.default_format='~P'
q = ureg.Quantity


def flux_conductif(T1,T0,S=1):
    sigma = q(5.67e-8 ,'W/m**2/K**4').m
    return sigma*(T1**4-T0**4)*S


def flux_convectif(T1,T0,h,S=1):
    return h*(T1-T0)*S

def flux_ext(T1,T0,h,S=1):
    return flux_conductif(T1,T0,S)+flux_convectif(T1,T0,h,S)

### flux conductif vs flux convectif
T1 = q(np.arange(0,150),'degC')
T0 = q(25,'degC')
S = q(1,'m**2')
h = q(7,'W/m**2/K')

cd = flux_conductif(T1.to('K').m,T0.to('K').m,S.m)
cv = flux_convectif(T1.to('K').m,T0.to('K').m,h.m,S.m)
df = pd.DataFrame({'flux convectif':cv,'flux conductif':cd},index=T1)
fig = px.scatter(df)
params = {'T0':T0,'h':h,'S':S}
physics.build_layout_figure(fig,
    params=params,
    xaxis_title_text='Temperature [degC]',
    yaxis_title_text='Power [W]'
    ).show()
