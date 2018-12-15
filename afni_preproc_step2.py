"""
Post-tedana steps:
1. Use T2* map (from t2smap workflow) to coregister functional to structural
2. Normalize structural to functional
3. Concatenate transforms
4. Apply transforms to denoised data to move to standard space in one go
"""
from os import mkdir, chdir, makedirs
import os.path as op
from glob import glob
from shutil import copyfile
from bids.layout import BIDSLayout


def gen_fname(fname, **kwargs):
    """
    Generate BIDS derivatives-compatible filename from components.

    Parameters
    ----------
    basefile : :obj:`str`
        Name of file from which to derive BIDSRawBase prefix and datatype
        suffix.
    extension : :obj:`str`, optional
        Extension for file. Includes the datatype suffix. Default is
        "_bold.nii.gz".
    kwargs : :obj:`str`
        Additional keyword arguments are added to the filename in the order
        they appear.

    Returns
    -------
    out_file : :obj:`str`
        BIDS derivatives-compatible filename
    """
    fname = op.basename(fname)

    if not all([isinstance(v, str) for k, v in kwargs.items()]):
        raise ValueError("All keyword arguments must be strings")

    # Get prefix
    prefix = fname[:fname.rfind('_')]
    suffix = fname[fname.rfind('_'):]

    # Create string with description-field pairs
    add_str = ''
    for k, v in kwargs.items():
        add_str += '_{0}-{1}'.format(k, v)

    out_file = prefix+add_str+suffix
    return out_file


if __name__ == '__main__':
    # Initiate workflow with name and base directory
    in_dir = '/home/data/nbc/external-datasets/ds001491/'
    step1_dir = '/home/data/nbc/external-datasets/ds001491/derivatives/afni-step1/'
    t2smap_dir = '/home/data/nbc/external-datasets/ds001491/derivatives/t2smap/'
    step2_dir = '/home/data/nbc/external-datasets/ds001491/derivatives/afni-step2/'
    echo_times = np.array([8.02, 22.03, 36.03])
    
    # out_dir = '/scratch/tsalo006/afni-test/'
    task = 'images'
    subjects = sorted([op.basename(s) for s in glob(op.join(step1_dir, 'sub-*'))])
    for sub in subjects:
        in_files = sorted(glob(op.join(step1_dir, sub, 'func/{0}*realign_bold.nii.gz'.format(sub))))
        out_dir = op.join(t2smap_dir, sub, 'func')
        if not op.isdir(out_dir):
            makedirs(out_dir)
        

