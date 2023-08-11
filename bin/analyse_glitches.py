import sys
from glob import glob
import pickle
from joblib import Parallel, delayed

import numpy as np

import jax
import numpyro
from numpyro import infer
import arviz as az

numpyro.set_host_device_count(4)
njobs = 8

from antiglitch import freqs, to_fd, extract_glitch, rfft

# Frequency-domain signal model
from antiglitch import fsignal

# Bayesian model
from antiglitch import glitch_model

sampler = infer.MCMC(
    infer.NUTS(glitch_model),
    num_warmup=3000,
    num_samples=2000,
    num_chains=1,
    progress_bar=False,
)

# Read all glitches of a certain type from the .npz files
datadir = sys.argv[1]

def process(ifo, key, ii, ff):
    npz = np.load(ff)
    invasd, whts, _ = extract_glitch(npz)
    fglitch = to_fd(whts)
    sampler.run(jax.random.PRNGKey(0),
                    freqs[1:], invasd[1:],
                    data=fglitch[1:])

    itrace = az.from_numpyro(sampler)
    summ = az.summary(itrace, kind='stats')
    return ((ifo, key, ii), summ)

simlst = []
for ifo in ['V1']:
    for key in ['tomte','blip','koi']:
        files = sorted(glob(f"{datadir}/{ifo}-{key}-*.npz"))
        for ii, ff in enumerate(files):
            simlst.append((ifo, key, ii, ff))

print(simlst[:10])
            
result = Parallel(n_jobs=njobs, verbose=10)(delayed(process)(*arg) for arg in simlst)

result = dict(result)

with open(f"Jul2023-V1-physical-results.pkl", 'wb') as handle:
    pickle.dump(result, handle, protocol=pickle.HIGHEST_PROTOCOL)
