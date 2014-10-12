import os
import pandas as pd
import nmrglue as ng
import numpy as np
import scipy as sp


def load_bruker_fid(fn, pc_init=None, config={}):

    try:
        print("Reading %s" % fn)
        # read in the bruker formatted data
        dic, data = ng.bruker.read(fn, read_prog=False)
    except Exception as e:
        print(fn, e)
        return None, None, None
    else:

        # remove the digital filter
        if config.get('remove_digital_filter'):
            data = ng.bruker.remove_digital_filter(dic, data)

        # process the spectrum
        original_size = data.shape[-1]

        if config.get('zero_fill'):
            data = ng.proc_base.zf_size(data, config.get('zero_fill_to'))    # zero fill to 32768 points
        #data = ng.process.proc_bl.sol_boxcar(data, w=16, mode='same')  # Solvent removal

        data = ng.proc_base.fft(data)               # Fourier transform

        if config.get('autophase_algorithm') != False:
            print config.get('autophase_algorithm')
            data, pc = autophase(data, pc_init, config.get('autophase_algorithm'))  # Automatic phase correction
        else:
            pc = 0, 0

        if config.get('delete_imaginaries'):
            data = ng.proc_base.di(data)                # discard the imaginaries

        if config.get('reverse_spectra'):
            data = ng.proc_base.rev(data)               # reverse the data

        #data = data / 10000000.
        dic['PATHOMX_PHASE_CORRECT'] = pc
        dic['PATHOMX_ORIGINAL_SIZE'] = original_size
        return dic, data, pc


def autophase(nmr_data, pc_init=None, algorithm='Peak_minima'):
    if pc_init == None:
        pc_init = [0, 0]

    fn = {
        'ACME': autophase_ACME,
        'Peak_minima': autophase_PeakMinima,
    }[algorithm]

    opt = sp.optimize.fmin(fn, x0=pc_init, args=(nmr_data.reshape(1, -1)[:500], ))
    print("Phase correction optimised to: %s" % opt)
    return ng.process.proc_base.ps(nmr_data, p0=opt[0], p1=opt[1]), opt


def autophase_ACME(x, s):
    # Based on the ACME algorithm by Chen Li et al. Journal of Magnetic Resonance 158 (2002) 164–168

    stepsize = 1

    n, l = s.shape
    phc0, phc1 = x

    s0 = ng.process.proc_base.ps(s, p0=phc0, p1=phc1)
    s = np.real(s0)
    maxs = np.max(s)

    # Calculation of first derivatives
    ds1 = np.abs((s[2:l] - s[0:l - 1]) / (stepsize * 2))
    p1 = ds1 / np.sum(ds1)

    # Calculation of entropy
    m, k = p1.shape

    for i in range(0, m):
        for j in range(0, k):
            if (p1[i, j] == 0):  # %in case of ln(0)
                p1[i, j] = 1

    h1 = -p1 * np.log(p1)
    h1s = np.sum(h1)

    # Calculation of penalty
    pfun = 0.0
    as_ = s - np.abs(s)
    sumas = np.sum(as_)

    if (sumas < 0):
        pfun = pfun + np.sum((as_ / 2) ** 2)

    p = 1000 * pfun

    # The value of objective function
    return h1s + p


def autophase_PeakMinima(x, s):
    # Based on the ACME algorithm by Chen Li et al. Journal of Magnetic Resonance 158 (2002) 164–168

    stepsize = 1

    phc0, phc1 = x

    s0 = ng.process.proc_base.ps(s, p0=phc0, p1=phc1)
    s = np.real(s0).flatten()

    i = np.argmax(s)
    peak = s[i]
    mina = np.min(s[i - 100:i])
    minb = np.min(s[i:i + 100])

    return np.abs(mina - minb)

# We should have a folder name; so find all files named fid underneath it (together with path)
# Extract the path, and the parent folder name (for sample label)
nmr_data = []
nmr_dic = []
sample_labels = []
_ppm_real_scan_folder = False
fids = []
for r, d, files in os.walk(config['filename']):  # filename contains a folder for Bruker data
    if 'fid' in files:
        scan = os.path.basename(r)
        print('Read Bruker:', r, scan)
        if scan == '99999' or scan == '9999':  # Dummy Bruker thing
            continue
        # The following is a hack; need some interface for choosing between processed/raw data
        # and for various formats of NMR data input- but simple
        fids.append(r)

total_fids = len(fids)
pc_init = None
pc_history = []
for n, fid in enumerate(fids):
    dic, data, pc = load_bruker_fid(fid, pc_init, config)

    if data is not None:

        # Store previous phase correction outputs to speed up subsequent runs
        pc_history.append(pc)
        pc_init = np.median(np.array(pc_history), axis=0)

        label = os.path.basename(fid)
        #if 'AUTOPOS' in dic['acqus']:
        #    label = label + " %s" % dic['acqus']['AUTOPOS']
        sample_labels.append(label)
        nmr_data.append(data)
        nmr_dic.append(dic)
        _ppm_real_scan_folder = fid

    progress(float(n) / total_fids)  # Emit progress update

if _ppm_real_scan_folder:
    # Nothing worked

    # Generate the ppm for these spectra
    # read in the bruker formatted data// use latest
    dic, data_unp = ng.bruker.read(_ppm_real_scan_folder, read_prog=False)
    # Calculate ppms
    # SW total ppm 11.9877
    # SW_h total Hz 7194.244
    # SF01 Hz of 0ppm 600
    # TD number of data points 32768

    # Offset (not provided but we have:
    # O1 Hz offset (shift) of spectra 2822.5 centre!
    # BF ? 600Mhz
    # O1/BF = centre of the spectra
    # OFFSET = (SW/2) - (O1/BF)

    # What we need to calculate is start, end, increment
    offset = (float(dic['acqus']['SW']) / 2) - (float(dic['acqus']['O1']) / float(dic['acqus']['BF1']))
    start = float(dic['acqus']['SW']) - offset
    end = -offset
    step = float(dic['acqus']['SW']) / 32768

    nmr_ppms = np.arange(start, end, -step)[:32768]
    experiment_name = '%s (%s)' % (dic['acqus']['EXP'], config['filename'])

    print("Processing spectra to Pandas DataFrame...")
    output_data = pd.DataFrame(nmr_data)
    output_data.index = pd.MultiIndex.from_tuples([(l, None) for l in sample_labels], names=['Sample', 'Class'])
    output_data.columns = pd.MultiIndex.from_tuples([(s, ) for s in nmr_ppms], names=['Scale'])

    # Export the dictionary parameters for all sets
    output_dic = nmr_dic

    # Generate simple result figure (using pathomx libs)
    from pathomx.figures import spectra

    View = spectra(output_data, styles=styles)
    

else:
    raise Exception("No valid data found")
