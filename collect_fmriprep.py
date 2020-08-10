"""
Collect native-space preprocessed data from fMRIPrep working directory and
copy into fMRIPrep derivatives directory, in BIDS format.
"""
import gzip
import pickle
import os.path as op
from os import mkdir
from glob import glob
from shutil import copyfile, rmtree

import nibabel as nib
from nilearn import image
from nipype.interfaces.ants import ApplyTransforms
from niworkflows.interfaces.itk import MultiApplyTransforms
from niworkflows.interfaces.nilearn import Merge

ORDER = ['_from-T1w_to-MNI152NLin2009cAsym_mode-image_xfm.h5',
         '_from-reference_to-T1w_mode-image_xfm.txt',
         '_from-native_to-reference_mode-image_xfm.txt']
XFORM_RENAME = {'bold_reg_wf/bbreg_wf/fsl2itk_fwd/affine.txt': '_from-reference_to-T1w_mode-image_xfm.txt',
                'bold_hmc_wf/fsl2itk/mat2itk.txt': '_from-native_to-reference_mode-image_xfm.txt'}


def collect_fmriprep(deriv_dir, work_dir, subs):
    """
    Collect native-space preprocessed data from fMRIPrep working directory and
    copy into fMRIPrep derivatives directory, in BIDS format.

    Parameters
    ----------
    deriv_dir : str
    work_dir : str
    subs : list
        Cannot include sub- prefix.
    """
    for sub in subs:
        print('Wrangling subject {0}'.format(sub))
        sub_in_dir = op.join(work_dir, 'single_subject_{0}_wf'.format(sub))
        task_dirs = glob(op.join(sub_in_dir, 'func_preproc_task_*_wf'))
        for task_dir in task_dirs:
            # Check for SDC
            sdc_wf_dir = op.join(task_dir, 'sdc_estimate_wf')
            sdc = op.isfile(sdc_wf_dir)
            if sdc:
                bf_dirs = sorted(glob(op.join(task_dir, '_bold_file_*')))
                ORDER.append('_fieldwarp_mode-image_xfm.nii.gz')
                XFORM_RENAME[
                    'sdc_estimate_wf/pepolar_unwarp_wf/cphdr_warp/_warpfieldQwarp_PLUS_WARP_fixhdr.nii.gz'] \
                    = '_fieldwarp_mode-image_xfm.nii.gz'
            else:
                bb_wf_dir = op.join(task_dir, 'bold_bold_trans_wf')
                bf_dirs = sorted(glob(op.join(bb_wf_dir, '_bold_file_*')))
            for bf_dir in bf_dirs:
                # Collect partially preprocessed data
                bf_dir_list = bf_dir.split('..')
                idx = bf_dir_list.index('sub-{0}'.format(sub))
                sub_deriv_dir = op.join(deriv_dir, op.dirname('/'.join(bf_dir_list[idx:])))
                bf_filename = bf_dir_list[-1]
                if sdc:
                    temp_dir = op.join(deriv_dir, 'temp_dir')
                    os.mkdir(temp_dir)
                    os.chdir(temp_dir)
                    split_files = sorted(glob(op.join(bf_dir, 'bold_split/vol*.nii.gz')))
                    hmc_xforms = op.join(task_dir, 'bold_hmc_wf/fsl2itk/mat2itk.txt')

                    bold_transform = MultiApplyTransforms(
                        interpolation='LanczosWindowedSinc', float=True, copy_dtype=True, save_cmd=True)
                    bold_transform.inputs.input_image = split_files
                    bold_transform.inputs.transforms = hmc_xforms
                    bold_transform.inputs.reference_image = split_files[0]
                    bold_transform.run()

                    files2merge = sorted(glob(op.join(temp_dir, 'vol*xform*.nii.gz')))
                    merge = Merge(compress=True)
                    merge.inputs.in_files = files2merge
                    merge.run()

                    in_file = op.join(temp_dir, 'vol0000_xform-00000_merged.nii.gz')
                else:
                    in_file = op.join(bf_dir, 'merge/vol0000_xform-00000_merged.nii.gz')
                orig_fn_list = bf_filename.split('_')
                fn_list = orig_fn_list[:]
                fn_list.insert(-1, 'space-native')
                fn_list.insert(-1, 'desc-partialPreproc')
                out_file = op.join(sub_deriv_dir, '_'.join(fn_list))
                copyfile(in_file, out_file)

            # Collect native-to-T1w and T1w-to-MNI transforms
            out_func_dir = op.dirname(out_file)
            f = op.join(task_dir, 'bold_mni_trans_wf',
                        'bold_to_mni_transform/_inputs.pklz')
            with gzip.open(f, 'rb') as fo:
                data = pickle.load(fo)

            xform_rename2 = {}
            orig_fn_list = [fn for fn in orig_fn_list if 'echo' not in fn]
            orig_fn_list = orig_fn_list[:-1]
            for xform in XFORM_RENAME.keys():
                chosen = [xf for xf in data['transforms'] if xf.endswith(xform)]
                assert len(chosen) == 1
                chosen = chosen[0]
                xform_fn = '_'.join(orig_fn_list) + XFORM_RENAME[xform]
                xform_rename2[chosen] = op.join(out_func_dir, xform_fn)

            for in_xform in xform_rename2.keys():
                copyfile(in_xform, xform_rename2[in_xform])


def split_4d(in_file, out_dir):
    """
    Split 4D file into 3D files in out_dir
    """
    img_4d = nib.load(in_file)
    if not op.isdir(out_dir):
        mkdir(out_dir)

    out_files = []
    for i, img_3d in enumerate(image.iter_img(img_4d)):
        out_file = op.join(out_dir, 'f{0:05d}.nii.gz'.format(i))
        img_3d.to_filename(out_file)
        out_files.append(out_file)

    return out_files


def collect_xforms(in_file):
    """
    Collect transform files into list based on input file.
    """
    sub = [s for s in in_file.split('/') if s.startswith('sub-')][0]
    sub_dir = in_file.split(sub)[0] + sub
    anat_dir = op.join(sub_dir, 'anat')
    func_dir = op.dirname(in_file)
    echo_regex = re.compile('_echo-[0-9+]_')
    ref_file = re.sub(echo_regex, '_', in_file)
    t1_to_mni = glob(op.join(anat_dir, '*{0}'.format(ORDER[-1])))[0]
    ref_to_t1 = 'i dunno'
    nat_to_ref = 'i dunno'
    return [t1_to_mni, ref_to_t1, nat_to_ref]


def apply_xforms(in_file, out_file, xforms, temp_dir):
    """
    Build miniworkflow to split, apply xforms, and merge

    Split:
    fslsplit /scratch/tsalo006/work/fmriprep_wf/single_subject_ltd_wf/\
        func_preproc_task_checkerboard_echo_1_wf/bold_stc_wf/\
        _bold_file_..scratch..tsalo006..ltd_dset..sub-ltd..func..\
        sub-ltd_task-checkerboard_echo-1_bold.nii.gz/copy_xform/\
        sub-ltd_task-checkerboard_echo-1_bold_tshift_xform.nii.gz -t

    Apply xforms:
    antsApplyTransforms --default-value 0 --float 1 \
        --input /scratch/tsalo006/work/fmriprep_wf/single_subject_ltd_wf/\
        func_preproc_task_checkerboard_echo_1_wf/split_opt_comb/\
        vol0000.nii.gz \
        --interpolation LanczosWindowedSinc \
        --output /scratch/tsalo006/work/fmriprep_wf/single_subject_ltd_wf/\
        func_preproc_task_checkerboard_echo_1_wf/bold_mni_trans_wf/\
        bold_to_mni_transform/vol0000_xform-00000.nii.gz \
        --reference-image /scratch/tsalo006/work/fmriprep_wf/\
        single_subject_ltd_wf/func_preproc_task_checkerboard_echo_1_wf/\
        bold_mni_trans_wf/gen_ref/\
        tpl-MNI152NLin2009cAsym_res-01_T1w_reference.nii.gz \
        --transform /scratch/tsalo006/work/fmriprep_wf/single_subject_ltd_wf/\
        anat_preproc_wf/t1_2_mni/ants_t1_to_mniComposite.h5 \
        --transform /scratch/tsalo006/work/fmriprep_wf/single_subject_ltd_wf/\
        func_preproc_task_checkerboard_echo_1_wf/bold_reg_wf/bbreg_wf/\
        fsl2itk_fwd/affine.txt \
        --transform /scratch/tsalo006/work/fmriprep_wf/single_subject_ltd_wf/\
        func_preproc_task_checkerboard_echo_1_wf/bold_mni_trans_wf/\
        bold_to_mni_transform/tmp-h62vznik/mat2itk_pos-002_xfm-00000.txt

    Merge:
    nilearn
    """
    assert op.isfile(in_file)
    assert not op.isdir(temp_dir)
    assert all([op.isfile(xform) for xform in xforms])

    # Split 4D input file into 3D temporary files
    temp_files = split_4d(in_file, temp_dir)

    # Apply transforms
    ref_file = in_file.replace(
        'native_desc-partialPreproc_bold',
        'MNI152NLin2009cAsym_desc-preproc_bold')
    echo_regex = re.compile('_echo-[0-9+]_')
    ref_file = re.sub(echo_regex, '_', ref_file)
    assert op.isfile(ref_file)

    print('Applying transforms...')
    at = ApplyTransforms(
        default_value=0, float=True, interpolation='LanczosWindowedSinc',
        transforms=xforms,
        reference_image=ref_file)

    temp_xformed_files = []
    for f in temp_files:
        temp_xformed_file = op.join(temp_dir, 'xformed_{0}'.format(op.basename(f)))
        at.inputs.input_image = f
        at.inputs.output_image = temp_xformed_file
        at.run()
        temp_xformed_files.append(temp_xformed_file)

    # Merge transformed 3D files into output 4D file
    img_4d = image.concat_imgs(temp_xformed_files)
    img_4d.to_filename(out_file)

    # Remove temp_dir
    print('Cleaning up temporary directory...')
    rmtree(temp_dir)


if __name__ == '__main__':
    deriv_dir = '/home/data/nbc/external-datasets/ltd_dset/derivatives/fmriprep/'
    work_dir = '/home/data/nbc/external-datasets/ltd_dset/derivatives/fmriprep-work/'
    subs = ['ltd']
    collect_fmriprep(deriv_dir, work_dir, subs)
