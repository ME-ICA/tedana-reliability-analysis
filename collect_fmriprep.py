"""
Collect fMRIPrep outputs from working directory to use with tedana
By Elizabeth DuPre
"""
import os
import glob
import gzip
import pickle

subjs = glob.glob(os.path.join('out', 'work', 'fmriprep_wf',
                               'single_subject_*'))

for s in subjs:
    runs = glob.glob(os.path.join(s, 'func_preproc_task*'))
    for r in runs:
        t2smap_infiles = glob.glob(os.path.join(r, 'join_echos',
                                                'result_join_echos.pklz'))

        with gzip.open(t2smap_infiles[0]) as f:
            echo_list = pickle.load(f).outputs.bold_files

        t2smap_outdir = glob.glob(os.path.join(r, 'bold_t2smap_wf', 't2smap_node',
                                               'result_t2smap_node.pklz'))
        # I need to test this line on a fresh dataset
        with gzip.open(t2smap_outdir[0]) as f:
            (optimal_comb, s0_adaptive_map, s0_map,
             t2star_adaptive_map, t2star_map) = pickle.load(f).outputs

        tfm = glob.glob(os.path.join(r, 'bold_mni_trans_wf', 'mask_merge_tfms',
                                     'result_mask_merge_tfms.pklz'))

        with gzip.open(tfm[0]) as f:
            t1_2_mni, bbreg = pickle.load(f).outputs.out
