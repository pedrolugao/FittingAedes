import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from scipy.special import erf
import os

# Load climate data from NovaIguacu.csv
_script_dir = os.path.dirname(os.path.abspath(__file__))
_csv_path = os.path.join(_script_dir, '..', 'data', 'NovaIguacu.csv')

_df = pd.read_csv(_csv_path)

# Days are calculated as month index * 30
vetDias = [i * 30 for i in range(len(_df))]

# Temperature data (mean_t_med from CSV)
vetTemp = _df['mean_t_med'].values

# Pluviosity data (mean_prec from CSV)
vetPluv = _df['mean_prec'].values

temperature = interp1d(vetDias, np.array(vetTemp), kind='linear', fill_value='extrapolate')
pluviosity = interp1d(vetDias, vetPluv, kind='linear', fill_value='extrapolate')


# Some functions:
def normal(R, mu, T):
    return np.e**(-(T-mu)**2/(2*R))

def plateau(R, mu, T):
    return np.e**(-(T-mu)**8/(2*R)**5)

def phi(P):
    return (erf((P-10)/40) + 0.3)/1.2
