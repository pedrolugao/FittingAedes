import numpy as np
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt 
from scipy.special import erf
import pandas as pd


inmet_dados = pd.read_csv('inmetDados.csv')
def pluviosity(i):
    return np.interp(i, np.arange(len(inmet_dados)), inmet_dados['precipitacao_total_diaria'])

def temperature(i):
    return np.interp(i, np.arange(len(inmet_dados)), inmet_dados['temperatura_media_geral'])


def plotData(ax):
    ax.plot(np.arange(365*2),pluviosity(np.arange(365*2)),label='Precipitação')
    #ax.plot(np.arange(365*2),temperature(np.arange(365*2)),label='Temperatura')
    ax.legend()
    
def plotDataTemp(ax):
    #ax.plot(np.arange(365*2),pluviosity(np.arange(365*2)),label='Precipitação')
    ax.plot(np.arange(365*2),temperature(np.arange(365*2)),label='Temperatura')
    ax.legend()

#Cálculo de K:
days = [0,30,60,90,120,150,180,210,240,270,300,330,360,390,420,450,480,510,540,570,600,630,660,690]
H = np.zeros((len(days)))
Kmax = 212
Hmax = 24
Hum = 85
l = 3.9E-5
Evap = [l*(25+temperature(day))**2*(100-Hum) for day in days]
for i in range(1,len(days)):
    H[i] = H[i-1] + (pluviosity(days[i-1]) - Evap[i-1])
    if H[i] > Hmax:
        H[i] = Hmax
    if H[i] < 0:
        H[i] = 0
K = [Kmax*H[i]/Hmax + 1 for i in range(len(days))]
Kf = interp1d(days,K,kind='linear',fill_value='extrapolate')

#plt.plot(days,Kf(days),label='K(t)')
#plt.legend()
#plt.show()


eulerNumber = 2.71828
#some functions:
def normal(R,mu,T):
    return eulerNumber**(-(T-mu)**2/(2*R))

# def plateau(R,mu,T):
#     return eulerNumber**(-(T-mu)**8/(2*R)**5)

def plateau(R,mu,T):
    # Usando erf para criar um plateau com transições suaves
    # R controla a largura do plateau, mu é o centro
    left_edge = erf(10*(T - (mu - R))/R)
    right_edge = erf(10*((mu + R) - T)/R)
    return (left_edge * right_edge + 1) / 2

#c=10, s=40
def phi(c,s,P):
    return (erf((P-c)/s) + 1.2)/2.2
