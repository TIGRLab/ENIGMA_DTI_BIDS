#!/usr/bin/env python
"""
Run QC -stuff for enigma dti pipeline.

Usage:
  run_group_qc_enigma.py [options] <outputdir>

Arguments:
    <outputdir>        Top directory for the output file structure

Options:
  --calc-MD                Also run QC for MD values,
  --calc-all               Also run QC for for MD, AD, and RD values.
  --subject-filter         String to filter subject list by
  --index                  Only write index pages and exit
  -v,--verbose             Verbose logging
  --debug                  Debug logging in Erin's very verbose style
  -n,--dry-run             Dry run
  --help                   Print help

DETAILS
This creates some QC outputs from of enigmaDTI pipeline stuff.
QC outputs are placed within <outputdir>/QC.
Right now QC constist of pictures of the skeleton on the registered image, for every subject.
Pictures are assembled in html pages for quick viewing.
This is configured to work for outputs of the enigma dti pipeline (dm-proc-enigmadti.py).

The inspiration for these QC practices come from engigma DTI
http://enigma.ini.usc.edu/wp-content/uploads/DTI_Protocols/ENIGMA_FA_Skel_QC_protocol_USC.pdf

Future plan: add section that checks results for normality and identifies outliers..

Requires datman python enviroment, FSL and imagemagick.

Written by Erin W Dickie, August 14 2015
"""
from docopt import docopt
import pandas as pd
import os
import nilearn.plotting 
from glob import glob
import tempfile
import shutil

### Erin's little function for running things in the shell
def docmd(cmdlist):
    "sends a command (inputed as a list) to the shell"
    if DEBUG: print(' '.join(cmdlist))
    if not DRYRUN: subprocess.call(cmdlist)

def main():

    global DEBUG
    global VERBOSE
    global DRYRUN

    arguments       = docopt(__doc__)
    outputdir       = arguments['<outputdir>']
    subject_filter  = arguments['--subject-filter']
    index_only      = arguments['--index']
    CALC_MD         = arguments['--calc-MD']
    CALC_ALL        = arguments['--calc-all']
    VERBOSE         = arguments['--verbose']
    DEBUG           = arguments['--debug']
    DRYRUN          = arguments['--dry-run']

    if DEBUG: print(arguments)

    ## if no result file is given use the default name
    outputdir = os.path.normpath(outputdir)
    all_FAskels = glob('{}/sub*/FA/*skel*'.format(outputdir))
    all_FAskels.sort()

    if subject_filter:
        FAskels = [x for x in FAskels if test_sub in x]
    else:
        FAskels = all_FAskels

    tags = ['FA']
    if CALC_MD: tags = tags + ['MD']
    if CALC_ALL: tags = tags + ['MD','RD','AD']

    ## find the files that match the resutls tag...first using the place it should be from doInd-enigma-dti.py
    QCdir = os.path.join(outputdir,'QC')
    os.makedirs(QCdir , exist_ok=True)

    for FAskel in FAskels:
        if not index_only:
            build_subject_page(FAskel, QCdir, tags)

    for tag in tags:
        for display_mode in ["z", "x"]:
            build_index(QCdir, tag, display_mode)

def build_subject_page(FAskel, QCdir, tags):
    '''
    builds the images from a single subject
    
    FAskel     path to the participants FAskeletin image
    QCdir      path to the qc images outputdirectory
    tags       list of the tags (FA, MD, RD, AD)
    '''
    subject_session = subject_session = os.path.basename(os.path.dirname(os.path.dirname(FAskel)))

    qc_subdir = os.path.join(QCdir, subject_session)

    if DEBUG: print("Building QC page for {}".format(subject_session))

    os.makedirs(qc_subdir)
    subpics = []
    
    for tag in tags:
        for display_mode in ["z", "x"]:
            pic = os.path.join(qc_subdir, '{}_{}kel_{}.png'.format(
                subject_session, tag, display_mode))
            overlay_skel(FAskel.replace("FA", tag), pic, display_mode = "z")
            subpics.append(pic)

        ## write an html page that shows all the pics
    qchtml = open(os.path.join(qc_subdir, + 'index.html'),'w')
    qchtml.write('<HTML><TITLE>' + subject_session + 'skeleton QC page</TITLE>')
    qchtml.write('<BODY BGCOLOR=#333333>\n')
    qchtml.write('<h1><font color="white">' + subject_session + ' skeleton QC page</font></h1>')
    for pic in subpics:
        relpath = os.path.relpath(pic,QCdir)
        qchtml.write('<a href="'+ relpath + '" style="color: #99CCFF" >')
        qchtml.write('<img src="' + relpath + '" "WIDTH=800" > ')
        qchtml.write(relpath + '</a><br>\n')
    qchtml.write('</BODY></HTML>\n')
    qchtml.close() # you can omit in most cases as the destructor will call it


def build_index(QCdir, tag, display_mode):

        if DEBUG: print("Building index {} {}".format(tag, display_mode))

        pics = glob('{}/*/*{}skel_{}*'.format(QCdir, tag, display_mode))
        ## write an html page that shows all the pics
        qchtml = open(os.path.join(QCdir,tag + '_'+ display_mode + '_qcskel.html'),'w')
        qchtml.write('<HTML><TITLE>' + tag + 'skeleton QC page</TITLE>')
        qchtml.write('<BODY BGCOLOR=#333333>\n')
        qchtml.write('<h1><font color="white">' + tag + ' skeleton QC page</font></h1>')
        for pic in pics:
            relpath = os.path.relpath(pic,QCdir)
            qchtml.write('<a href="'+ relpath + '" style="color: #99CCFF" >')
            qchtml.write('<img src="' + relpath + '" "WIDTH=800" > ')
            qchtml.write(relpath + '</a><br>\n')
        qchtml.write('</BODY></HTML>\n')
        qchtml.close() # you can omit in most cases as the destructor will call it


def overlay_skel(skel_nii, overlay_png_path, display_mode = "z"):
    '''
    create an overlay image montage of
    skel_nii image in orange on top of the background_nii
    Uses nilearn plotting

    skel_nii        the nifty image to be overlayed in magenta (i.e. "FAskel.nii.gz")
    overlay_png_path     the name of the output (output.png)
    '''

    nilearn.plotting.plot_img(skel_nii, 
        bg_img = skel_nii.replace("skel", "_to_target"),
        threshold = 0.000001, 
        display_mode = display_mode, 
        cmap = "Oranges", 
        colorbar = True,
        output_file = overlay_png_path)

def overlay_skel_fsl(background_nii, skel_nii,overlay_gif):
    '''
    create an overlay image montage of
    skel_nii image in magenta on top of the background_nii
    Uses FSL slicer and imagemagick tools

    backgroud_nii   the background image in nifty format (i.e. "FA_to_target.nii.gz")
    skel_nii        the nifty image to be overlayed in magenta (i.e. "FAskel.nii.gz")
    overlay_gif     the name of the output (output.gif)
    '''
    #mkdir a tmpdir for the
    tmpdir = tempfile.mkdtemp()

    docmd(['slices',background_nii,'-o',os.path.join(tmpdir,subid + "to_target.gif")])
    docmd(['slices',skel_nii,'-o',os.path.join(tmpdir,subid + "skel.gif")])
    docmd(['convert', '-negate', os.path.join(tmpdir,subid + "skel.gif"), \
        '+level-colors', 'magenta,', \
        '-fuzz', '10%', '-transparent', 'white', \
        os.path.join(tmpdir,subid + 'skel_mag.gif')])
    docmd(['composite', os.path.join(tmpdir,subid + 'skel_mag.gif'),
        os.path.join(tmpdir,subid + 'to_target.gif'),
        os.path.join(tmpdir,subid + 'cskel.gif')])
    docmd(['convert', os.path.join(tmpdir,subid + 'cskel.gif'),\
        '-crop', '100x33%+0+0', os.path.join(tmpdir,subid + '_sag.gif')])
    docmd(['convert', os.path.join(tmpdir,subid + 'cskel.gif'),\
        '-crop', '82x33%+0+218', os.path.join(tmpdir,subid + '_cor.gif')])
    docmd(['convert', os.path.join(tmpdir,subid + 'cskel.gif'),\
        '-crop', '82x33%+0+438', os.path.join(tmpdir,subid + '_ax.gif')])
    docmd(['montage', '-mode', 'concatenate', '-tile', '3x1', \
        os.path.join(tmpdir,subid + '_sag.gif'),\
        os.path.join(tmpdir,subid + '_cor.gif'),\
        os.path.join(tmpdir,subid + '_ax.gif'),\
        os.path.join(overlay_gif)])

    
    #get rid of the tmpdir
    shutil.rmtree(tmpdir)


if __name__ == '__main__':
    main()