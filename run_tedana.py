# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
Run base pipeline on one dataset many times.
"""
import re
import sys
import json
import os.path as op
from os import makedirs
from shutil import copyfile, rmtree

from nilearn.masking import compute_epi_mask
from tedana.workflows import tedana_workflow


def run_tedana(files, tes, seed):
    """
    Run tedana workflow across a range of parameters

    Parameters
    ----------
    files : list of str
        Echo-specific preprocessed data files
    tes : list of floats
        Echo times in seconds
    seed : int
        Random seed
    """
    out_dir = '/scratch/tsalo006/reliability_analysis/tedana_outputs/'
    ds_dir = '/home/data/nbc/external-datasets/ds001491/'
    tes = [te * 1000 for te in tes]
    sub = re.findall('sub-[0-9a-zA-Z]+_', files[0])[0][:-1]
    #ds_dir = files[0][:files[0].index(sub)]
    name = 'tedana_seed-{0:03d}'.format(seed)
    ted_dir = op.join(ds_dir, 'derivatives', name, sub, 'func')
    if op.isdir(ted_dir):
        rmtree(ted_dir)
    makedirs(ted_dir)
    
    mask = op.join(ted_dir, 'nilearn_epi_mask.nii')
    mask_img = compute_epi_mask(files[0])
    mask_img.to_filename(mask)

    tedana_workflow(data=files, tes=tes, fixed_seed=seed, tedpca='mle',
                    mask=mask, out_dir=ted_dir, debug=True, gscontrol=None)
    # Grab the files we care about
    log_file = op.join(ted_dir, 'runlog.tsv')
    out_log_file = op.join(out_dir, '{0}_seed-{1:03d}_log.tsv'.format(sub, seed))
    ct_file = op.join(ted_dir, 'comp_table_ica.txt')
    out_ct_file = op.join(out_dir, '{0}_seed-{1:03d}_comptable.txt'.format(sub, seed))
    dn_file = op.join(ted_dir, 'dn_ts_OC.nii')
    out_dn_file = op.join(out_dir, '{0}_seed-{1:03d}_denoised.nii'.format(sub, seed))
    copyfile(log_file, out_log_file)
    copyfile(ct_file, out_ct_file)
    copyfile(dn_file, out_dn_file)
    if seed != 0:  # keep first seed for t2s map
        rmtree(ted_dir)


if __name__ == '__main__':
    seed = sys.argv[1]
    seed = int(seed)

    with open('reliability_files.json', 'r') as fo:
        info = json.load(fo)
    
    subjects = list(info.keys())
    subjects_to_run = []
    for sub in subjects:
        out_dir = '/scratch/tsalo006/reliability_analysis/tedana_outputs/'
        out_dn_file = op.join(out_dir, '{0}_seed-{1:03d}_denoised.nii'.format(sub, seed))
        if not op.isfile(out_dn_file):
            subjects_to_run.append(sub)

    for sub in subjects_to_run:
        files = info[sub]['files']
        tes = info[sub]['echo_times']
        run_tedana(files, tes, seed)
