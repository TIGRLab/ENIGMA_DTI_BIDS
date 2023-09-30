#!/usr/bin/env python
"""
This run ENIGMA DTI pipeline on one FA map.
This was made to be called from dm-proc-enigmadti.py.

Usage:
  run_participant_enigma_extract.py [options] <outputdir> <FAmap>

Arguments:
    <outputdir>        Top directory for the output file structure
    <FAmap>            Full path to input FA map to process

Options:
  --calc-MD                Option to process MD image as well
  --calc-all               Option to process MD, AD and RD
  -v,--verbose             Verbose logging
  --debug                  Debug logging in Erin's very verbose style
  -n,--dry-run             Dry run
  -h,--help                Print this help

DETAILS
This run ENIGMA DTI pipeline on one FA map.
This was made to be called from dm-proc-enigmadti.py - which runs enigma-dti protocol
for a group of subjects (or study) - then creates a group csv output and QC.
We recommend specifying an outputdir that doesn't yet exist (ex. enigmaDTI/<subjectID/).
This script will create the ouputdir and copy over the relevant inputs.
Why? Because this meant to work in directory with only ONE FA image!! (ex. enigmaDTI/<subjectID/).
Having more than one FA image in the outputdir would lead to crazyness during the TBSS steps.
So, the script will not run if more than one FA image (or the wrong FAimage) is present in the outputdir.
By default, this extracts FA values for each ROI in the atlas.
To extract MD as well, call with the "--calc-MD" option.
To extract FA, MD, RD and AD, call with the "--calc-all" option.
Requires ENIGMA dti enviroment to be set (for example):
module load FSL/5.0.7 R/3.1.1 ENIGMA-DTI/2015.01
also requires datman python enviroment.
Written by Erin W Dickie, July 30 2015
Adapted from ENIGMA_MASTER.sh - Generalized October 2nd David Rotenberg Updated Feb 2015 by JP+TB
Runs pipeline outlined by enigma-dti:
http://enigma.ini.usc.edu/protocols/dti-protocols/
"""
from docopt import docopt
import pandas as pd
import nilearn.plotting
import glob
import os
import sys
import subprocess

DRYRUN = False
DEBUG = False

### Erin's little function for running things in the shell
def docmd(cmdlist):
    "sends a command (inputed as a list) to the shell"
    if DEBUG: print(' '.join(cmdlist))
    if not DRYRUN: subprocess.call(cmdlist)

##############################################################################
## Now process the MD if that option was asked for
## if processing MD also set up for MD-ness
def run_non_FA(DTItag, outputdir, FAmap, FAskel):
    """
    The Pipeline to run to extract non-FA values (MD, AD or RD)
    """
    O_dir = os.path.join(outputdir,DTItag)
    image_noext = os.path.basename(FAmap.replace('_FA.nii.gz',''))
    ROIoutdir = os.path.join(outputdir, 'ROI')

    O_dir_orig = os.path.join(O_dir, 'origdata')
    os.makedirs(O_dir_orig, exist_ok=True)

    if DTItag == 'MD':
        image_i = FAmap.replace('FA.nii.gz','MD.nii.gz')
        image_o = os.path.join(O_dir_orig,image_noext + '_' + DTItag + '.nii.gz')
        # copy over the MD image if not done already
        if os.path.isfile(image_o) == False:
            docmd(['cp',image_i,image_o])

    if DTItag == 'AD':
        image_i = FAmap.replace('FA.nii.gz','L1.nii.gz')
        image_o = os.path.join(O_dir_orig,image_noext + '_' + DTItag + '.nii.gz')
        # copy over the AD image - this is _L1 in dti-fit
        if os.path.isfile(image_o) == False:
            docmd(['cp',image_i,image_o])

    if DTItag == 'RD':
        imageL2 = FAmap.replace('FA.nii.gz','L2.nii.gz')
        imageL3 = FAmap.replace('FA.nii.gz','L3.nii.gz')
        image_o = os.path.join(O_dir_orig,image_noext + '_' + DTItag + '.nii.gz')
        # create the RD image as an average of '_L2' and '_L3' images from dti-fit
        if os.path.isfile(image_o) == False:
            docmd(['fslmaths', imageL2, '-add', imageL3, '-div', "2", image_o])

    masked =    os.path.join(O_dir,image_noext + '_' + DTItag + '.nii.gz')
    to_target = os.path.join(O_dir,image_noext + '_' + DTItag + '_to_target.nii.gz')
    skel =      os.path.join(O_dir, image_noext + '_' + DTItag +'skel.nii.gz')
    skelqa =      os.path.join(O_dir, image_noext + '_' + DTItag +'skel.png')
    csvout1 =   os.path.join(ROIoutdir, image_noext + '_' + DTItag + 'skel_ROIout')
    csvout2 =   os.path.join(ROIoutdir, image_noext + '_' + DTItag + 'skel_ROIout_avg')

    ## mask with subjects FA mask
    docmd(['fslmaths', image_o, '-mas', \
      os.path.join(outputdir,'FA', image_noext + '_FA_mask.nii.gz'), \
      masked])

    # applywarp calculated for FA map
    docmd(['applywarp', '-i', masked, \
        '-o', to_target, \
        '-r', os.path.join(outputdir,'FA', 'target'),\
        '-w', os.path.join(outputdir,'FA', image_noext + '_FA_to_target_warp.nii.gz')])

    ## tbss_skeleton step
    docmd(['tbss_skeleton', \
          '-i', tbss_skeleton_input, \
          '-s', tbss_skeleton_alt, \
          '-p', str(skel_thresh), distancemap, search_rule_mask,
           FAskel, skel, '-a', to_target])

    ## ROI extract
    docmd([os.path.join(ENIGMAROI,'singleSubjROI_exe'),
              os.path.join(ENIGMAROI,'ENIGMA_look_up_table.txt'), \
              os.path.join(ENIGMAHOME, 'ENIGMA_DTI_FA_skeleton.nii.gz'), \
              os.path.join(ENIGMAROI, 'JHU-WhiteMatter-labels-1mm.nii.gz'), \
              csvout1, skel])

    ## ROI average
    docmd([os.path.join(ENIGMAROI, 'averageSubjectTracts_exe'), csvout1 + '.csv', csvout2 + '.csv'])

    if not DRYRUN:
        overlay_skel(skel_nii = skel, 
                    overlay_png_path = skelqa)
        

def overlay_skel(skel_nii, overlay_png_path, display_mode = "z"):
    '''
    create an overlay image montage of
    skel_nii image in orange on top of the background_nii
    Uses nilearn plotting

    skel_nii        the nifty image to be overlayed in magenta (i.e. "FAskel.nii.gz")
    overlay_png_path     the name of the output (output.png)
    '''
    if display_mode=="x":
        cut_coords = [-36, -16, 2, 10, 42]
    if display_mode=="y":
        cut_coords = [-40, -20, -10, 0, 10, 20]
    if display_mode=="z":
        cut_coords = [-4, 2, 8, 12, 20, 40]

    nilearn.plotting.plot_img(skel_nii, 
        bg_img = skel_nii.replace("skel", "_to_target"),
        threshold = 0.000001, 
        display_mode = display_mode,
        cut_coords = cut_coords, 
        cmap = "Oranges", 
        colorbar = True,
        output_file = overlay_png_path)


def main():

    global DEBUG
    global DRYRUN

    global ENIGMAHOME
    global ENIGMAREPO
    global ENIGMAROI

    global skel_thresh
    global distancemap
    global search_rule_mask
    global tbss_skeleton_input
    global tbss_skeleton_alt

    arguments       = docopt(__doc__)
    outputdir       = arguments['<outputdir>']
    FAmap           = arguments['<FAmap>']
    CALC_MD         = arguments['--calc-MD']
    CALC_ALL        = arguments['--calc-all']
    VERBOSE         = arguments['--verbose']
    DEBUG           = arguments['--debug']
    DRYRUN          = arguments['--dry-run']

    if DEBUG: print(arguments)

    ENIGMAREPO = os.path.dirname(os.path.realpath(__file__))

    # check that ENIGMAHOME environment variable exists
    # or set the ENIGMAHOME to engimaDTI is the correct file found
    ENIGMAHOME = os.getenv('ENIGMAHOME')
    if ENIGMAHOME==None:
        potential_enigmahome = os.path.join(ENIGMAREPO, 'enigmaDTI')
        if os.path.isfile(os.path.join(potential_enigmahome, 'ENIGMA_DTI_FA.nii.gz')):
            ENIGMAHOME=potential_enigmahome
            ENIGMAROI=os.path.join(ENIGMAREPO, 'ROIextraction_info')
        else:
            sys.exit("ENIGMAHOME environment variable is undefined. Try again.")
    else:
         ENIGMAROI=ENIGMAHOME
    
    # check that FSLDIR environment variable exists
    FSLDIR = os.getenv('FSLDIR')
    if FSLDIR==None:
        sys.exit("FSLDIR environment variable is undefined. Try again.")
    
    # check that the input FA map exists
    if os.path.isfile(FAmap) == False:
        sys.exit("Input file {} doesn't exist.".format(FAmap))
    
    # check that the input MD map exists - if MD CALC chosen
    if CALC_MD | CALC_ALL:
        MDmap = FAmap.replace('FA.nii.gz','MD.nii.gz')
        if os.path.isfile(MDmap) == False:
            sys.exit("Input file {} doesn't exist.".format(MDmap))
    # check that the input L1, L2, and L3 maps exists - if CALC_ALL chosen
    
    if CALC_ALL:
        for L in ['L1.nii.gz','L2.nii.gz','L3.nii.gz']:
            Lmap = FAmap.replace('FA.nii.gz', L)
            if os.path.isfile(Lmap) == False:
                sys.exit("Input file {} doesn't exist.".format(Lmap))

    # make some output directories
    outputdir = os.path.abspath(outputdir)

    ## These are the links to some templates and settings from enigma
    skel_thresh = 0.049
    distancemap = os.path.join(ENIGMAHOME,'ENIGMA_DTI_FA_skeleton_mask_dst.nii.gz')
    search_rule_mask = os.path.join(FSLDIR,'data','standard','LowerCingulum_1mm.nii.gz')
    tbss_skeleton_input = os.path.join(ENIGMAHOME,'ENIGMA_DTI_FA.nii.gz')
    tbss_skeleton_alt = os.path.join(ENIGMAHOME, 'ENIGMA_DTI_FA_skeleton_mask.nii.gz')
    ROIoutdir = os.path.join(outputdir, 'ROI')
    os.makedirs(ROIoutdir, exist_ok=True)
    image_noext = os.path.basename(FAmap.replace('_FA.nii.gz',''))
    FAimage = image_noext + '.nii.gz'
    csvout1 = os.path.join(ROIoutdir, image_noext + '_FAskel_ROIout')
    csvout2 = os.path.join(ROIoutdir, image_noext + '_FAskel_ROIout_avg')
    FAskel = os.path.join(outputdir,'FA', image_noext + '_FAskel.nii.gz')
    ###############################################################################
    ## setting up
    ## if teh outputfile is not inside the outputdir than copy is there
    outdir_niis = glob.glob(outputdir + '/*.nii.gz') + glob.glob(outputdir + '*.nii')
    if len(outdir_niis) == 0:
        docmd(['cp',FAmap,os.path.join(outputdir,FAimage)])
    else:
        # if more than one FA image is present in outputdir...we have a problem.
        sys.exit("Ouputdir already contains nii images..bad news..exiting")

    ## cd into the output directory
    os.chdir(outputdir)
    os.putenv('SGE_ON','false')
    ###############################################################################
    print("TBSS STEP 1")

    docmd([os.path.join(ENIGMAREPO,'tbss_1_preproc_noqa.sh'), FAimage])

    ###############################################################################
    print("TBSS STEP 2")
    docmd(['tbss_2_reg', '-t', os.path.join(ENIGMAHOME,'ENIGMA_DTI_FA.nii.gz')])

    ###############################################################################
    print("TBSS STEP 3")
    docmd(['tbss_3_postreg','-S'])

    ###############################################################################
    print("Skeletonize...")
    # Note many of the options for this are printed at the top of this script
    docmd(['tbss_skeleton', \
        '-i', tbss_skeleton_input, \
        '-s', tbss_skeleton_alt, \
        '-p', str(skel_thresh), distancemap, search_rule_mask,
        'FA/' + image_noext + '_FA_to_target.nii.gz',
        FAskel])

    ###############################################################################
    print("Convert skeleton datatype to 'float'...")
    docmd(['fslmaths', FAskel, '-mul', '1', FAskel, '-odt', 'float'])

    ###############################################################################
    print("ROI part 1...")
    ## note - right now this uses the _exe for ENIGMA - can probably rewrite this with nibabel
    docmd([os.path.join(ENIGMAROI,'singleSubjROI_exe'),
            os.path.join(ENIGMAROI,'ENIGMA_look_up_table.txt'), \
            os.path.join(ENIGMAHOME, 'ENIGMA_DTI_FA_skeleton.nii.gz'), \
            os.path.join(ENIGMAROI, 'JHU-WhiteMatter-labels-1mm.nii'), \
            csvout1, FAskel])

    ###############################################################################
    ## part 2 - loop through all subjects to create ROI file
    ##			removing ROIs not of interest and averaging others
    ##          note: also using the _exe files to do this at the moment
    print("ROI part 2...")
    docmd([os.path.join(ENIGMAROI, 'averageSubjectTracts_exe'), csvout1 + '.csv', csvout2 + '.csv'])

    if not DRYRUN:
        overlay_skel(skel_nii = FAskel, 
                    overlay_png_path = FAskel.replace(".nii.gz", ".png"))

    ## run the pipeline for MD - if asked
    if CALC_MD | CALC_ALL:
        run_non_FA('MD', outputdir, FAmap, FAskel)

    ## run the pipeline for AD and RD - if asked
    if CALC_ALL:
        run_non_FA('AD', outputdir, FAmap, FAskel)
        run_non_FA('RD', outputdir, FAmap, FAskel)

    ###############################################################################
    os.putenv('SGE_ON','true')
    print("Done !!")

if __name__ == '__main__':
    main()
