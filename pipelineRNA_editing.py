##############################################################################
#
#   MRC FGU CGAT
#
#   $Id$
#
#   Copyright (C) 2009 Andreas Heger
#
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License
#   as published by the Free Software Foundation; either version 2
#   of the License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
###############################################################################
"""===========================
Pipeline Germline Variant Calling
===========================

:Author: Jacob Parker
:Release: $Id$
:Date: |today|
:Tags: Python

.. Replace the documentation below with your own description of the
   pipeline's purpose

Overview
========

This pipeline computes the word frequencies in the configuration
files :file:``pipeline.ini` and :file:`conf.py`.

Usage
=====

See ref`PipelineSettingUp` and :ref:`PipelineRunning` on general
information how to use CGAT pipelines.

Configuration
-------------

The pipeline requires a configured :file:`pipeline.ini` file.
CGATReport report requires a :file:`conf.py` and optionally a
:file:`cgatreport.ini` file (see :ref:`PipelineReporting`).

Default configuration files can be generated by executing:

   python <srcdir>/pipeline_rnaseqmismatches.py config

Input files
-----------

None required except the pipeline configuration files.

Requirements
------------

The pipeline requires the results from
:doc:`pipeline_annotations`. Set the configuration variable
:py:data:`annotations_database` and :py:data:`annotations_dir`.

On top of the default CGAT setup, the pipeline requires the following
software to be in the path:

.. Add any additional external requirements such as 3rd party software
   or R modules below:

Requirements:

* samtools >= 1.1

Pipeline output
===============

.. Describe output files of the pipeline here

Glossary
========

.. glossary::


Code
====

"""

from ruffus import *

import sys
import os
import sqlite3
import shutil
import cgatcore.experiment as E
from cgatcore import pipeline as P
import re
import glob
import collections
import cgat.GTF as GTF
import cgatcore.iotools as iotools
import cgat.BamTools as bamtools
import cgatpipelines.tasks.geneset as PipelineGeneset
import cgatpipelines.tasks.mapping as PipelineMapping
import cgatpipelines.tasks.mappingqc as PipelineMappingQC

# load options from the config file
PARAMS = P.get_parameters(
    ["%s/pipeline.yml" % os.path.splitext(__file__)[0],
     "../pipeline.yml",
     "pipeline.yml"])

PARAMS["projectsrc"] = os.path.dirname(__file__)
#for key, value in PARAMS.iteritems():
#    print "%s:\t%s" % (key,value)


# add configuration values from associated pipelines
#
# 1. pipeline_annotations: any parameters will be added with the
#    prefix "annotations_". The interface will be updated with
#    "annotations_dir" to point to the absolute path names.

PARAMS.update(P.peek_parameters(
    PARAMS["annotations_dir"],
    'genesets',
    prefix="annotations_",
    update_interface=True,
    restrict_interface=True))

# if necessary, update the PARAMS dictionary in any modules file.
# e.g.:
#
# import CGATPipelines.PipelineGeneset as PipelineGeneset
# PipelineGeneset.PARAMS = PARAMS
#
# Note that this is a hack and deprecated, better pass all
# parameters that are needed by a function explicitely.

# -----------------------------------------------
# Utility functions
def connect():
    '''utility function to connect to database.

    Use this method to connect to the pipeline database.
    Additional databases can be attached here as well.

    Returns an sqlite3 database handle.
    '''

    dbh = sqlite3.connect(PARAMS["database"])
    statement = '''ATTACH DATABASE '%s' as annotations''' % (
        PARAMS["annotations_database"])
    cc = dbh.cursor()
    cc.execute(statement)
    cc.close()

    return dbh


# ---------------------------------------------------
# Specific pipeline tasks

@follows(mkdir("genome.dir"))
@transform(PARAMS["mapfasta"],formatter(),r"genome.dir/reference.fasta")
def reference_creation(infile, outfile):

    dirs = "genome.dir"
    name = PARAMS["name"]
    statement = '''ln -s %(infile)s %(dirs)s &&
                  mv genome.dir/%(name)s genome.dir/reference.fasta &&
                  sprint prepare genome.dir/reference.fasta bwa'''
    job_threads = 3
    job_memory = "16G"
    P.run(statement,job_condaenv="py2")


# --------------------------------------------------
@follows(reference_creation,mkdir("RNA_editingsites.dir"))
@transform("input.dir/*.fastq.gz", regex(r"input.dir/(.+).fastq.gz"),
           add_inputs("genome.dir/reference.fasta"),
           r"RNA_editingsites.dir/\1.dir")

def RES(infiles,outfile):
    samtools = PARAMS["samtool"]
    fastq,reference=infiles
    fas = os.path.basename(fastq).split(".gz")[0]
    
    statement = ''' gunzip -c %(fastq)s > input.dir/%(fas)s  &&
                   sprint main -1 input.dir/%(fas)s %(reference)s %(outfile)s bwa %(samtools)s &&
                   rm input_fastq.dir/%(fas)s && 
                   cd %(outfile)s &&
                   rename SPRINT %(fas)s && mv *.res ../  '''
    
    job_threads = 3
    job_memory = "16G"
    P.run(statement,job_condaenv="py2")



# Generic pipeline tasks
@follows(reference_creation,RES)
def full():
    pass


@follows(mkdir("report"))
def build_report():
    '''build report from scratch.

    Any existing report will be overwritten.
    '''

    E.info("starting report build process from scratch")
    P.run_report(clean=True)


@follows(mkdir("report"))
def update_report():
    '''update report.

    This will update a report with any changes inside the report
    document or code. Note that updates to the data will not cause
    relevant sections to be updated. Use the cgatreport-clean utility
    first.
    '''

    E.info("updating report")
    P.run_report(clean=False)


@follows(update_report)
def publish_report():
    '''publish report in the CGAT downloads directory.'''

    E.info("publishing report")
    P.publish_report()

def main(argv=None):
    if argv is None:
        argv = sys.argv
    P.main(argv)


if __name__ == "__main__":
    sys.exit(P.main(sys.argv))
