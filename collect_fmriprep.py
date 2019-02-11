"""
Collect fMRIPrep outputs from working directory to use with tedana
By Elizabeth DuPre
"""
import gzip
import pickle
import os.path as op
from glob import glob

from bids.layout import BIDSLayout

layout = BIDSLayout('/scratch/tsalo006/ds001491/', derivatives=False)
subjects = layout.get_subjects()

for sub in subjects:
    sub_dir = '/scratch/tsalo006/work/{0}-fmriprep-work/fmriprep_wf/single_subject_{0}'.format(sub)
    run_dirs = glob(op.join(sub_dir, 'func_preproc_task*'))
    for run_dir in run_dirs:
        t2smap_infiles = glob(op.join(run_dir, 'join_echos', 'result_join_echos.pklz'))

        with gzip.open(t2smap_infiles[0]) as f:
            echo_list = pickle.load(f).outputs.bold_files

        t2smap_outdir = op.join(run_dir, 'bold_t2smap_wf', 't2smap_node',
                                'result_t2smap_node.pklz')
        # I need to test this line on a fresh dataset
        with gzip.open(t2smap_outdir) as f:
            (optimal_comb, s0_adaptive_map, s0_map,
             t2star_adaptive_map, t2star_map) = pickle.load(f).outputs

        tfm = glob(op.join(run_dir, 'bold_mni_trans_wf', 'mask_merge_tfms',
                           'result_mask_merge_tfms.pklz'))

        with gzip.open(tfm[0]) as f:
            t1_2_mni, bbreg = pickle.load(f).outputs.out
