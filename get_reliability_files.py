# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
Compile list of files in datasets for processing
"""
import json
import os.path as op
from bids.layout import BIDSLayout


def get_files():
    DSET_DIR = op.abspath('/home/data/nbc/external-datasets/ds001491/')

    layout = BIDSLayout(DSET_DIR)
    layout.add_derivatives('/home/data/nbc/external-datasets/ds001491/derivatives/afni-step1/')
    task = 'images'
    info = {}
    for sub in sorted(layout.get_subjects()):
        print(sub)
        sub_info = {'files': [], 'echo_times': []}
        for echo in sorted(layout.get_echoes(subject=sub, task=task)):
            raw_files = layout.get(subject=sub, task=task, echo=echo,
                                   extensions='.nii.gz')
            preproc_files = layout.get(subject=sub, task=task, root='afni-step1',
                                       extensions='.nii.gz')
            # For some reason pybids doesn't index echo in derivatives
            preproc_files = [p for p in preproc_files if 'echo-{0}'.format(echo) in p.filename]
            if len(preproc_files) != 1:
                print(preproc_files)
                raise Exception('BAD')

            # Replace filename with path when using new version of bids
            sub_info['files'].append(preproc_files[0].path)
            metadata = raw_files[0].metadata
            sub_info['echo_times'].append(metadata['EchoTime'])
        info[sub] = sub_info

    with open('reliability_files.json', 'w') as fo:
        json.dump(info, fo, indent=4, sort_keys=True)


if __name__ == '__main__':
    get_files()
