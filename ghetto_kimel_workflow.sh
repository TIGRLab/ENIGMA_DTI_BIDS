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

# kimel lab all the things

# module load R FSL ENIGMA-DTI/2015.01
# module load ciftify

session="ses-01"
STUDY="TAY"

OUTPUT_RESOLUTION="1.7"

SING_CONTAINER=/archive/code/containers/QSIPREP/pennbbl_qsiprep_0.16.0RC3-2022-06-03-9c3b9f2e4ac1.simg

BIDS_DIR=/archive/data/${STUDY}/data/bids
QSIPREP_DIR=/archive/data/${STUDY}/pipelines/in_progress/baseline/qsiprep
TMP_DIR=/scratch/edickie/TAY_engimaDTI/tmp
WORK_DIR=${TMP_DIR}/${STUDY}/qsiprep_work
FS_LICENSE=${TMP_DIR}/freesurfer_license/license.txt
OUT_DIR=/scratch/edickie/TAY_engimaDTI/data

mkdir -p $WORK_DIR $OUT_DIR

THIS_DWI=`ls -1d ${QSIPREP_DIR}/sub-*/ses-01/dwi/*desc-preproc_dwi.nii.gz | head -n ${SLURM_ARRAY_TASK_ID} | tail -n 1`
subject=$(basename $(dirname $(dirname $(dirname ${THIS_DWI}))))
subject_id=$(echo $subject | sed 's/sub-//g')

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

QSIRECON_OUT=/scratch/edickie/TAY_engimaDTI/data/qsirecon/sub-${subject_id}/ses-01/dwi/sub-${subject_id}_${session}_space-T1w_desc-preproc_fslstd
DTIFIT_OUT=/scratch/edickie/TAY_engimaDTI/data/dtifit/sub-${subject_id}/ses-01/dwi/sub-${subject_id}_${session}_space-T1w_desc-dtifit

mkdir -p $(dirname ${DTIFIT_OUT})

dtifit -k ${QSIRECON_OUT}_dwi.nii.gz \
  -m ${QSIRECON_OUT}_mask.nii.gz \
  -r ${QSIRECON_OUT}_dwi.bvec \
  -b ${QSIRECON_OUT}_dwi.bval \
  --save_tensor --sse \
  -o ${DTIFIT_OUT}



ENIGMA_DTI_OUT=/scratch/edickie/TAY_engimaDTI/data/engimaDTI

mkdir -p ${ENIGMA_DTI_OUT}

python /scratch/edickie/TAY_engimaDTI/ENIGMA_DTI_BIDS/run_participant_enigma_extract.py --calc-all --debug \
  ${ENIGMA_DTI_OUT}/sub-${subject_id}_${session} ${DTIFIT_OUT}_FA.nii.gz

# ####### group steps

# python /scratch/edickie/TAY_engimaDTI/ENIGMA_DTI_BIDS/run_group_enigma_concat.py \
#  ${ENIGMA_DTI_OUT} FA ${ENIGMA_DTI_OUT}/group_engimaDTI_FA.csv
