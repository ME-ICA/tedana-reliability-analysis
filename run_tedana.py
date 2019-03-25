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


def run_tedana(files, tes, seed, dset, source, kind):
    """
    Run tedana workflow with a reasonable number of iterations and no
    restarts. The number of iterations is used to allow for convergence
    failures.

    The workflow should be run on data which have been only minimally
    preprocessed (e.g., slice timing and motion correction), but which have not
    yet been subjected to spatial normalization, smoothing, or denoising.

    Parameters
    ----------
    files : list of str
        Echo-specific preprocessed data files
    tes : list of floats
        Echo times in seconds
    seed : int
        Random seed
    dset : str
        Name of the OpenNeuro dataset being analyzed
    source : {'fmriprep', 'afni'}
        Preprocessing pipeline used
    kind : {'simple', 'duration'}
        Whether to allow a large number of iterations (for estimating duration
        and number of iterations required for convergence) or a reasonable
        number of iterations (for evaluating convergence under typical
        parameters)
    """
    if kind == 'simple':
        maxit = 500
    elif kind == 'duration':
        maxit = 100000
    else:
        raise Exception('Unrecognized kind argument: {0}'.format(kind))

    # Constants
    ds_dir = '/home/data/nbc/external-datasets/{0}'.format(dset)
    out_base_dir = '/scratch/tsalo006/reliability_analysis/'

    # Output directory for collected derivatives
    out_dir = op.join(
        out_base_dir,
        '{0}_tedana_outputs_{1}_{2}'.format(dset, source, kind))
    tes = [te * 1000 for te in tes]
    sub = re.findall('sub-[0-9a-zA-Z]+_', files[0])[0][:-1]

    # BIDS-structured derivatives folders
    name = 'tedana_{0}_{1}_seed-{2:04d}'.format(source, kind, seed)
    ted_dir = op.join(ds_dir, 'derivatives', name, sub, 'func')
    if op.isdir(ted_dir):
        rmtree(ted_dir)
    makedirs(ted_dir)

    # Use an EPI mask
    mask = op.join(ted_dir, 'nilearn_epi_mask.nii')
    mask_img = compute_epi_mask(files[0])
    mask_img.to_filename(mask)

    tedana_workflow(data=files, tes=tes, fixed_seed=seed, tedpca='mle',
                    mask=mask, out_dir=ted_dir, gscontrol=None,
                    maxit=maxit, maxrestart=1, debug=True, verbose=False)
    # Grab the files we care about
    log_file = sorted(op.join(ted_dir, 'runlog*.tsv'))[::-1][0]
    out_log_file = op.join(out_dir, '{0}_seed-{1:04d}_log.tsv'.format(sub, seed))
    ct_file = op.join(ted_dir, 'comp_table_ica.txt')
    out_ct_file = op.join(out_dir, '{0}_seed-{1:04d}_comptable.txt'.format(sub, seed))
    mmix_file = op.join(ted_dir, 'meica_mix.1D')
    out_mmix_file = op.join(out_dir, '{0}_seed-{1:04d}_mmix.1D'.format(sub, seed))
    dn_file = op.join(ted_dir, 'dn_ts_OC.nii')
    out_dn_file = op.join(out_dir, '{0}_seed-{1:04d}_denoised.nii'.format(sub, seed))
    copyfile(log_file, out_log_file)
    copyfile(ct_file, out_ct_file)
    copyfile(mmix_file, out_mmix_file)
    copyfile(dn_file, out_dn_file)
    if seed != 0:  # keep first seed for t2s map
        rmtree(ted_dir)


if __name__ == '__main__':
    dset = sys.argv[1]
    fixed_seed = int(sys.argv[2])

    # Run analysis with fMRIPrep-preprocessed data
    with open('{0}_reliability_files.json'.format(dset), 'r') as fo:
        info = json.load(fo)

    info = info[dset]
    subjects = sorted(list(info.keys()))
    subjects_to_run = []
    for subj in subjects:
        # If final output exists, skip subject
        output_dir = ('/scratch/tsalo006/reliability_analysis/'
                      '{0}_tedana_outputs_afni_long'.format(dset))
        output_file = op.join(output_dir, '{0}_seed-{1:04d}_denoised.nii'.format(subj, fixed_seed))
        if not op.isfile(output_file):
            subjects_to_run.append(subj)

    for subj in subjects_to_run:
        files_fmriprep = info[subj]['files_fmriprep']
        files_afni = info[subj]['files_afni']
        tes = info[subj]['echo_times']
        run_tedana(files_fmriprep, tes, fixed_seed, dset, 'fmriprep', 'short')
        run_tedana(files_fmriprep, tes, fixed_seed, dset, 'fmriprep', 'long')
        run_tedana(files_afni, tes, fixed_seed, dset, 'afni', 'short')
        run_tedana(files_afni, tes, fixed_seed, dset, 'afni', 'long')
