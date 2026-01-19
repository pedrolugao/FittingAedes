import numpy as np
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt 
from scipy.special import erf


vetDias = [0,30,60,90,120,150,180,210,240,270,300,330,360,390,420,450,480,510,540,570,600,630,660,690]
vetTemp = [26.86,25.7,25.8714285714,25.0333333333,25.9285714286,27.22,28.8285714286,30.1285714286,29.2666666667,27.6666666667,26.7142857143,25.6285714286,25.77857143,25.83571429,26.03571429,26.93571429,26.38571429,27.56428571,27.44285714,27.60714286,27.09285714,27.98571429,26.55,25.73571429]
temperature = interp1d(vetDias,np.array(vetTemp)*1.1, kind='linear', fill_value='extrapolate')
pluviosity = interp1d(vetDias, [46.5,169,84.3,73.1,9,25.4,5.5,0,20,63.2,17.5,133.7,100.9,128.3,41.6,33.6,13.6,17.1,13.9,4.2,0.7,0,28.4,26.2], kind='linear', fill_value='extrapolate')




#some functions:
def normal(R,mu,T):
    return np.e**(-(T-mu)**2/(2*R))

def plateau(R,mu,T):
    return np.e**(-(T-mu)**8/(2*R)**5)

def phi(P):
    return (erf((P-10)/40) + 0.3)/1.2

