#!/usr/bin/python
# encoding: utf-8
#
# Copyright © 2014 stephen.margheim@gmail.com
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 29-07-2014
#
from __future__ import unicode_literals
import sys

from workflow import Workflow
from pandoctor import PanDoctor

sys.path.insert(0, Workflow().workflowfile('lib/'))
from docopt import docopt

__version__ = '1.1'

__usage__ = """
PanDoctor -- An Alfred GUI for `pandoc`

Usage:
    testing.py config
    testing.py store <flag> <argument>
    testing.py search <flag> <argument>
    testing.py launch <flag> <argument>
    testing.py run <flag>
    testing.py help <flag>

Arguments:
    <flag>      Determines which specific code-path to follow
    <argument>  The value to be stored, searched, or passed on

Options:
    -h, --help  Show this message

This script is meant to be called from Alfred.
"""

def main(wf):
    """main"""
    args = ['search', 'options']
    args = docopt(__usage__, argv=args, version=__version__)
    print args 
    pd = PanDoctor(wf)
    res = pd.run(args)
    if res:
        print res.strip()
 

if __name__ == '__main__':
    WF = Workflow()
    sys.exit(WF.run(main))
