import os
import pandas as pd
import nmrglue as ng

total_fids = len(dic_list)

for n, dic in enumerate(dic_list):
    data = input_data.values[n, :].flatten()

    data = ng.proc_base.rev(data)               # reverse the data
    data = ng.proc_base.ifft(data)   # Inverse Fourier transform

    # Check if we're short on data (allows re-export after binning)
    if data.shape[-1] < 16384:
        data = ng.proc_base.zf(data, 16384)

    if 'acqus' not in dic:
        raise ValueError("dictionary does not contain acqus parameters")
    if 'DECIM' not in dic['acqus']:
        raise ValueError("dictionary does not contain DECIM parameter")
    decim = dic['acqus']['DECIM']
    if 'DSPFVS' not in dic['acqus']:
        raise ValueError("dictionary does not contain DSPFVS parameter")
    dspfvs = dic['acqus']['DSPFVS']
    if 'GRPDLY' not in dic['acqus']:
        grpdly = 0
    else:
        grpdly = dic['acqus']['GRPDLY']


    if grpdly > 0:  # use group delay value if provided (not 0 or -1)
        phase = grpdly
    # determind the phase correction
    else:
        if dspfvs >= 14:  # DSPFVS greater than 14 give no phase correction.
            phase = 0.
        else:  # loop up the phase in the table
            if dspfvs not in ng.bruker.bruker_dsp_table:
                raise ValueError("dspfvs not in lookup table")
            if decim not in ng.bruker.bruker_dsp_table[dspfvs]:
                raise ValueError("decim not in lookup table")
            phase = ng.bruker.bruker_dsp_table[dspfvs][decim]


    # Remove phase correcton
    if 'PATHOMX_PHASE_CORRECT' in dic:
        data = ng.process.proc_base.ps(data, p0=-dic['PATHOMX_PHASE_CORRECT'][0], p1=-dic['PATHOMX_PHASE_CORRECT'][1])

    data = ng.proc_base.fsh2(data, -phase)
    data = data[0:16384]

    ng.bruker.write(os.path.join(config['filename'], str(n + 1)), dic, data, overwrite=True)

    progress(float(n) / total_fids)  # Emit progress update    
