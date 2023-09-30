# Newer ENIGMA DTI workflow

This is some helper scripts for running ENIGMA DTI on the Kimel system (using the ENIGMA DTI module) after running QSIPREP.

The ENIGMA DTI workflow was developed by Neda Jahanshad, Emma Sprooten, Peter Kochunov
neda.jahanshad@ini.usc.edu, emma.sprooten@yale.edu

The following steps will allow you to register and skeletonize your FA images to the DTI atlas being used for ENIGMA-DTI for tract-based spatial statistics (TBSS; Smith et al., 2006).

Here we assume preprocessing steps including motion/Eddy current correction, masking, tensor calculation, and creation of FA maps has already been performed, along with quality control.

Further instructions for using FSL, particularly TBSS can be found on the website: https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/TBSS

Further detailed instructions of the steps run here are in [docs/ENIGMA_instructions.md].

## Running this workflow on the kimel system

Running this workflow on the kimel system has following steps:

1. Run or locate outputs for QSIPREP
2. modify `example_kimel_workflow.sh` with paths to your data and submit it
3. Run the group concaneating and QC page generating steps
4. Check the QC pages of any large errors

## 1. Running QSIPREP

More guidance in running QSIprep is given in the [kimel docs page](http://imaging-genetics.camh.ca/documentation/#/methods/QSIprep_based_DWI_processing)

This is the most time consuming step - it's worth checking the archive or asking on of the Kimel TIGRCAT team member if this has already been done for you. 

## 2. Running the participant workflow

First - clone this repo to your project or scratch.

Then modify the script [`example_kimel_workflow.sh`](example_kimel_workflow.sh) to fit the study you will be working with.

To submit this script on the kimel system

```sh
# don't forget to run this on KIMEL - i.e. ssh franklin 

#load KIMEL modules
module load R FSL ENIGMA-DTI/2015.01
module load ciftify

# make sure singularity is available
which singularity

# submit the scripts from a location you want logs written to
cd /scratch/edickie/TAY_enigmaDTI/logs

# Note: Erin prefers testing a script by running a few participants first (like the two commands seen below)
sbatch --array=1-2 --export=ALL ../code/example_kimel_workflow.sh 
#sbatch --array=3-187 --export=ALL ../code/example/kimel_workflow.sh 
```

## 3. Running the concatenating scripts

There are other scripts in this repo that are meant to be run AFTER all partipants have been run

the group steps

Note: with teh older version there are some QC scripts change

```sh
module load R FSL 
module load ciftify

# modify this to the location of you output directory
OUT_DIR=/scratch/edickie/TAY_enigmaDTI/data/enigmaDTI

# modify this to the location you cloned the repo to
ENIGMA_DTI_BIDS=/scratch/edickie/TAY_enigmaDTI/ENIGMA_DTI_BIDS

for metric in FA MD RD AD; do
${ENIGMA_DTI_BIDS}/run_group_enigma_concat.py \
  ${OUT_DIR} ${metric} ${OUT_DIR}/enigmaDTI/group_enigmaDTI_${metric}.csv
${ENIGMA_DTI_BIDS}/run_group_qc_index.py ${OUT_DIR} ${metric}skel
done

${ENIGMA_DTI_BIDS}/run_group_enigma_concat.py --output-nVox\
  ${OUT_DIR} FA ${OUT_DIR}/group_engimaDTI_nvoxels.csv

python ${ENIGMA_DTI_BIDS}/run_group_dtifit_qc.py --debug --dry-run --calc-all ${OUT_DIR}/enigmaDTI
```

This is an older version (creates engima DTI QC images - takes a little longer)

```sh
module load R FSL ENIGMA-DTI/2015.01
module load ciftify

# modify this to the location of you output directory
OUT_DIR=/scratch/edickie/TAY_enigmaDTI/data/enigmaDTI

# modify this to the location you cloned the repo to
ENIGMA_DTI_BIDS=/scratch/edickie/TAY_enigmaDTI/ENIGMA_DTI_BIDS

for metric in FA MD RD AD; do
python ${ENIGMA_DTI_BIDS}/run_group_enigma_concat.py \
  ${ENIGMA_DTI_OUT} ${metric} ${OUT_DIR}/enigmaDTI/group_enigmaDTI_${metric}.csv
done

${ENIGMA_DTI_BIDS}/run_group_enigma_concat.py --output-nVox\
  ${OUT_DIR} FA ${OUT_DIR}/group_engimaDTI_nvoxels.csv

python ${ENIGMA_DTI_BIDS}/run_group_qc_enigma.py --debug --dry-run --calc-all ${OUT_DIR}/enigmaDTI
python ${ENIGMA_DTI_BIDS}/run_group_dtifit_qc.py --debug --dry-run --calc-all ${OUT_DIR}/enigmaDTI
```



## 4. check the QC outputs before you move forward!

There's things to check through before you move on:

1. make sure everything finished!
   1. check for any errors in the logs
   2. check that you have output values for all expected input scans
2. The dtifit directions `{output}/dtifit/QC/qc_directions.html`- these are pretty colorful pictures of the dtifit with directions of diffusion plotted as different colours - corpus callosum should be red!
3. The dtifit error `{output}/dtifit/QC/qc_sse.html`- these are image maps of error in the tensor fit - everyone should be dark (fails will jump out at you as much brighter than the rest)
4. The enigma dti qc pages `{output}/enigmaDTI/QC/FA_x_qcskel.html` & `{output}/enigmaDTI/QC/FA_z_qcskel.html` These show your tbss skeleton (i.e. the data you are extracting) on top of your enigma template transformed FA image.
5. Look at the movement and quality metrics from QSIprep

# BONUS - we now have scripts for also extracting the NODDI fit values from the skeleton

This requires that the NODDI fit was run with qsiprep

1. running one participant (this could be submitted to the queue to run in parallel across subjects)

This script required that engima DTI has been run (it requires the warps and FA skeleton in the engima outputs)

The inputs
```
module load R FSL
module load ciftify

${enigma_code}/run_participant_noddi_enigma_extract.py --debug \
    --noddi_outputdir /path/to/qsiprep/qsirecon/noddi/outputs \
    --enigma_outputdir /path/to/engimaDTI/outputs \
    --outputdir /path/for/new/enigmaDTInoddi/ouputs \
    --subject bids_subject_id \
    --session bids_session_id
``` 

and example

```sh
module load R FSL
module load ciftify

### 398 077 151 384 148 303
subject="sub-CMH00000151"
session="ses-01"
noddi_dir=/KIMEL/tigrlab/archive/data/TAY/pipelines/in_progress/jwong/dmri-microstructure/amico/qsirecon/
enigma_dir=/KIMEL/tigrlab/scratch/edickie/TAY_engimaDTI/data/engimaDTI
outputdir=/KIMEL/tigrlab/scratch/edickie/TAY_engimaDTI/data/engimaDTInoddi
enigma_code=/KIMEL/tigrlab/scratch/edickie/TAY_engimaDTI/ENIGMA_DTI_BIDS
dtifit_dir=/KIMEL/tigrlab/scratch/edickie/TAY_engimaDTI/data/dtifit

${enigma_code}/run_participant_noddi_enigma_extract.py --debug \
    --noddi_outputdir ${noddi_dir} \
    --enigma_outputdir ${enigma_dir} \
    --outputdir ${outputdir} \
    --subject ${subject} \
    --session ${session}
```

2. Running the group steps to combine the results and create an html index of the qc images
   
```sh
## the group steps
${enigma_code}/run_group_enigma_concat.py --output-nVox\
  ${outputdir} OD ${outputdir}/group_engimaDTI_nvoxels.csv

for metric in OD ISOVF ICVF; do
${enigma_code}/run_group_enigma_concat.py \
  ${outputdir} ${metric} ${outputdir}/group_engimaDTI_${metric}.csv
${enigma_code}/run_group_qc_index.py ${outputdir} ${metric}skel
done
```