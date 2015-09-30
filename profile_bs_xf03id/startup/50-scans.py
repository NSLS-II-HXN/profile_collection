# vim: sw=4 ts=4 sts expandtab smarttab
# HXN step-scan configuration

import hxntools.scans
from hxntools.detectors.master_detector import MasterDetector

# TODO: figure out olog issues
olog_client = None
# TODO

# Set up regular ascans/dscans to work with HXN detector triggering methods:
hxntools.scans.setup()

# default_detectors = [sclr1, det_beamstatus,
#                      sclr1_ch2, sclr1_ch3, sclr1_ch4,
#                      ssx_rbv, ssy_rbv, ssz_rbv, t_base, t_sample, t_vlens,
#                      t_hlens]

# When the scaler is triggered, the xspress3 is externally triggered with this
# MasterDetector:
master_sclr1 = MasterDetector(sclr1, slaves=[xspress3.filestore])

# NOTE: master_sclr1 has SUB-detectors which are not in this list (see above)
gs.DETS = [zebra, master_sclr1, ssx, ssy, ssz, t_base, t_sample,
           t_vlens, t_hlens]

gs.TABLE_COLS = ['sclr1_chan1', 'sclr1_chan4', 'ssx', 'ssy', 'ssz',
                 't_base', 't_sample', 't_vlens', 't_hlens']
gs.PLOT_Y = 'sclr1_chan4'
