"""Add phase for two obs on Vela pulsar from CTA DC-1"""
import numpy as np
import astropy.units as u
from astropy.time import Time
from astropy.coordinates import SkyCoord
from gammapy.data import DataStore

###########################################################################
#######################  Extracting Vela files  ###########################
###########################################################################

# Load the data store (contains the information about all the DC1 data)
# Assumes you have an environment variable CTADATA set pointing to the DC1 folder
data_store = DataStore.from_dir('$CTADATA/index/gps')
table = data_store.obs_table

# Defining the offset as the angular separation between the observation position and the target position
pos_obs = SkyCoord(table['GLON_PNT'], table['GLAT_PNT'], frame='galactic', unit='deg')
pos_target = SkyCoord.from_name('vela')
offset = pos_target.separation(pos_obs)

# Defining a mask to select all runs targeting Vela with an offset < 2 deg
mask = (offset < 2 * u.deg)


# Applying the mask
table = table[mask]

# Getting the list of observation indices of Vela
obs_ids = table['OBS_ID']

# Here we just keep the first two observations
obs_ids = obs_ids[:2]

###########################################################################
########################  Phasing the times  ##############################
###########################################################################


def time2phase(t, t0, f0, f1, f2, phi_0=0):
    """Convert time to phase following frequency derivatives.

    Parameters:
    -----------
    t : `~astropy.time.core.Time`
         input times
    phi_0 : `~float`
         offset in the phasogram, 0 by default
    t0 : `~astropy.time.Time`
        origin of the times in mjd
    f0 : `~astropy.units.Quantity`
        frequency of pulsar in Hz
    f1 : `~astropy.units.Quantity`
        derivative of frequency in Hz / s
     f2 : `~astropy.units.Quantity`
        second derivative of frequency in Hz /s /s
    """
    tt = (t - t0).sec * u.s  # conversion in seconds
    phi_1 = f0 * tt  # first phasing term
    phi_2 = 0.5 * f1 * (tt ** 2)  # second phasing term
    phi_3 = (1. / 6) * f2 * (tt ** 3)  # third phasing term
    ph = phi_0 + phi_1 + phi_2 + phi_3  # phase not yet bounded between 0 and 1
    return ph - ph.astype('int')  # explanations here under


# Parameters for the Vela pulsar model for the DC1 found in model_galactic_pulsars.xml
f0_vela = 11.19 * u.Hz
f1_vela = -1.55e-11 * u.Hz / u.s
f2_vela = 6.46e-23 * u.Hz / ((u.s) ** 2)
t0_vela = Time(54686.2, format='mjd', scale='utc')

# Loop over all Vela observations
for obs_id in obs_ids:
    events = data_store.obs(obs_id).events
    times = events.time
    phases = np.fromiter((time2phase(times, t0_vela, f0_vela, f1_vela, f2_vela)), np.float)
    events.table['PHASE'] = phases

    filename = "gps_baseline_{:06d}.fits".format(obs_id)
    print('Writing {}'.format(filename))
    events.table.write(filename, overwrite=True)
