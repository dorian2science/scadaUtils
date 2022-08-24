import importlib
from sylfenUtils import utils
import pandas as pd
importlib.reload(utils)
import plotly.express as px
df=px.data.stocks().set_index('date')
glib=utils.Graphics()

def test_graphlib():
    fig=glib.multiUnitGraph(df)
    glib.add_drawShapeToolbar(fig).show()
    glib.showPalettes('blues')

# def Physics():
# def test_utils:
lib=utils.Utils()
slib=utils.Structs()
dlib=utils.DataBase()
plib=utils.Physics()
flib=utils.FileSystem()
elib=utils.EmailSmtp()
