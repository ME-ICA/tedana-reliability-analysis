"""
Pre-tedana steps:
- Slice timing correction
- Estimate motion correction parameters for first echo
- Apply parameters to all echoes
"""
from os import mkdir, chdir
import os.path as op
from shutil import copyfile
from bids.layout import BIDSLayout
from nipype.interfaces import afni


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
    out_dir = '/home/data/nbc/external-datasets/ds001491/derivatives/afni-step1/'
    # out_dir = '/scratch/tsalo006/afni-test/'
    task = 'images'

    layout = BIDSLayout(in_dir)
    subjects = layout.get_subjects(task=task)

    for sub in sorted(subjects):
        echoes = layout.get_echoes(subject=sub, task=task)
        sub_out_dir = op.join(out_dir, 'sub-{0}'.format(sub))
        if not op.isdir(sub_out_dir):
            mkdir(sub_out_dir)

        func_out_dir = op.join(sub_out_dir, 'func')
        if not op.isdir(func_out_dir):
            mkdir(func_out_dir)
        
        for echo in echoes:            
            chdir(func_out_dir)

            echo_file = layout.get(subject=sub, task=task, echo=echo,
                                   extensions='nii.gz')[0].path
            metadata = layout.get_metadata(echo_file)

            stc_file = op.join(func_out_dir, gen_fname(echo_file, desc='stc'))
            mc_file = op.join(func_out_dir, gen_fname(echo_file, desc='realign'))
            mat_file = op.join(func_out_dir, 'volreg.1D')
            out_mc_file = op.join(func_out_dir, op.basename(mc_file))

            stc = afni.TShift(tzero=0.)
            stc.inputs.in_file = echo_file
            stc.inputs.outputtype = 'NIFTI_GZ'
            stc.inputs.tr = '{}s'.format(metadata['RepetitionTime'])
            stc.inputs.slice_timing = metadata['SliceTiming']
            stc.inputs.slice_encoding_direction = metadata.get('SliceEncodingDirection', 'k')
            stc.inputs.out_file = stc_file
            stc.run()

            if echo == echoes[0]:
                first_echo_file = stc_file
                mc_est = afni.Volreg(interp='linear')
                mc_est.inputs.in_file = first_echo_file
                mc_est.inputs.out_file = mc_file
                mc_est.inputs.oned_matrix_save = mat_file
                mc_est_res = mc_est.run()
            else:
                mc_app = afni.Allineate(interpolation='linear')
                mc_app.inputs.in_matrix = mc_est_res.outputs.oned_matrix_save
                mc_app.inputs.in_file = stc_file
                mc_app.inputs.out_file = mc_file
                mc_app.run()
