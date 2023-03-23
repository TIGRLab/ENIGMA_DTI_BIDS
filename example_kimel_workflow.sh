#!/bin/bash -l

#SBATCH --partition=low-moby
#SBATCH --array=1-188
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=4096
#SBATCH --time=2:00:00
#SBATCH --job-name enigmaDTI
#SBATCH --output=enigmaDTI_%j.out
#SBATCH --error=enigmaDTI_%j.err

# these kimel lab modules are required
module load R FSL ENIGMA-DTI/2015.01
module load ciftify

# the project name
STUDY="TAY"

# the BIDS session id
session="ses-01"

# for QSIPREP output resolution - set this to the resolution of the input files
OUTPUT_RESOLUTION="1.7"

# set this to the location of the QSIPREP container
SING_CONTAINER=/archive/code/containers/QSIPREP/pennbbl_qsiprep_0.16.0RC3-2022-06-03-9c3b9f2e4ac1.simg

# set this to the local locaton of the ENIGMA_DTI_BIDS repo
CODE_DIR=/scratch/edickie/TAY_enigmaDTI/ENIGMA_DTI_BIDS

## set this to the original BIDS dataset location
BIDS_DIR=/archive/data/${STUDY}/data/bids

## set this to the QSIPREP outputs location
QSIPREP_DIR=/archive/data/${STUDY}/pipelines/in_progress/baseline/qsiprep

## any tempdir and workdir location will do
TMP_DIR=/scratch/edickie/TAY_enigmaDTI/tmp
WORK_DIR=${TMP_DIR}/${STUDY}/qsiprep_work

# set this to the location of a freesurfer license
FS_LICENSE=${TMP_DIR}/freesurfer_license/license.txt

# set this to the location to write the outputs to
OUT_DIR=/scratch/edickie/TAY_enigmaDTI/data

mkdir -p $WORK_DIR $OUT_DIR

THIS_DWI=`ls -1d ${QSIPREP_DIR}/sub-*/ses-01/dwi/*desc-preproc_dwi.nii.gz | head -n ${SLURM_ARRAY_TASK_ID} | tail -n 1`
subject=$(basename $(dirname $(dirname $(dirname ${THIS_DWI}))))
subject_id=$(echo $subject | sed 's/sub-//g')

##### STEP 1 - if not done - qsiprep fslstd step ###################

singularity run \
  -H ${TMP_DIR} \
  -B ${BIDS_DIR}:/bids \
  -B ${QSIPREP_DIR}:/qsiprep_in \
  -B ${OUT_DIR}:/out \
  -B ${WORK_DIR}:/work \
  -B ${FS_LICENSE}:/li \
  ${SING_CONTAINER} \
  /bids /out participant \
  --skip-bids-validation \
  --participant_label ${subject_id} \
  --n_cpus 4 --omp-nthreads 2 \
  --recon-only \
  --recon-spec reorient_fslstd \
  --recon-input /qsiprep_in \
  --output-resolution ${OUTPUT_RESOLUTION} \
  --fs-license-file /li \
  -w /work \
  --notrack

######### STEP 2 - running DTIFIT - with BIDS names ##########################

QSIRECON_OUT=${OUT_DIR}/qsirecon/sub-${subject_id}/ses-01/dwi/sub-${subject_id}_${session}_space-T1w_desc-preproc_fslstd
DTIFIT_OUT=${OUT_DIR}/dtifit/sub-${subject_id}/ses-01/dwi/sub-${subject_id}_${session}_space-T1w_desc-dtifit

mkdir -p $(dirname ${DTIFIT_OUT})

dtifit -k ${QSIRECON_OUT}_dwi.nii.gz \
  -m ${QSIRECON_OUT}_mask.nii.gz \
  -r ${QSIRECON_OUT}_dwi.bvec \
  -b ${QSIRECON_OUT}_dwi.bval \
  --save_tensor --sse \
  -o ${DTIFIT_OUT}


##### STEP 3 - run the ENIGMA DTI participant workflow ########################

ENIGMA_DTI_OUT=${OUT_DIR}/enigmaDTI

mkdir -p ${ENIGMA_DTI_OUT}

python ${CODE_DIR}/run_participant_enigma_extract.py --calc-all --debug \
  ${ENIGMA_DTI_OUT}/sub-${subject_id}_${session} ${DTIFIT_OUT}_FA.nii.gz


