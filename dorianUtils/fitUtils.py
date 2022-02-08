import scipy
from scipy.optimize import curve_fit
# ==========================================================================
#                           FITTING FUNCTIONS
# ==========================================================================

def expDown(self,x, a, b, c):
    return a * np.exp(-b * x) + c

def expUp(self,x,a,b,c):
    return a *(1- np.exp(-b * x)) + c

def poly2(self,x,a,b,c):
    return a*x**2 +b*x + c

def expUpandDown(self,x,a1,b1,c1,a2,b2,c2):
    return self.expUp(x,a1,b1,c1) + self.expDown(x,a2,b2,c2)

def generateSimuData(self,func='expDown'):
    x = np.linspace(0, 2, 150)
    y = eval(func)(x, 5.5, 10.3, 0.5)
    np.random.seed(1729)
    y_noise = 0.2 * np.random.normal(size=x.size)
    ydata = y + y_noise
    return x,ydata

def fitSingle(self,dfx,func='expDown',plotYes=True,**kwargs):
    x = dfx.index
    y = dfx.iloc[:,0]
    if isinstance(dfx.index[0],pd._libs.tslibs.timestamps.Timestamp):
        xdata=np.arange(len(x))
    else :
        xdata=x
    popt, pcov = curve_fit(eval('self.'+func), xdata, y,**kwargs)
    if plotYes:
        plt.plot(x, y, 'bo', label='data')
        plt.plot(x, eval('self.'+func)(xdata, *popt), 'r-',
            label='fit: a=%.2f, b=%.2f, c=%.2f' % tuple(popt))
        plt.xlabel('x')
        plt.title(list(dfx.columns)[0])
        # plt.ylabel()
        plt.gcf().autofmt_xdate()
        plt.legend()
        plt.show()
    return popt
