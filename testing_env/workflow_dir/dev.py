#!/usr/bin/python
# encoding: utf-8
#
# Copyright © 2014 stephen.margheim@gmail.com
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 11-07-2014
#
from __future__ import unicode_literals
# Standard Library
import re
import sys
import os.path

from workflow import Workflow
from workflow.workflow import MATCH_ALL, MATCH_ALLCHARS
from config import Pandoc

"mdfind 'kMDItemFSName=pandoc-citeproc && kMDItemContentType=public.unix-executable'"

README = 'http://johnmacfarlane.net/pandoc/README.html'

DELIMITER = '➣'

KEYS = (
    'in_path',
    'in_fmt',
    'out_fmt'
)

#DEMO = "pandoc -s -S --toc -c pandoc.css -A footer.html README -o example3.html"
DEMO = "pandoc -N --template=mytemplate.tex --variable mainfont=Georgia --variable sansfont=Arial --variable monofont=\"Bitstream Vera Sans Mono\" --variable fontsize=12pt --variable version=1.10 README --latex-engine=xelatex --toc -o example14.pdf"




def main(wf):
    """testing area.
    """
    cmd = DEMO
    arg_options = re.findall(r'(--|-[^\s]*?)\s([^-](?:[^\s]*?".*?"|[^\s]*?))(?=\s|$)', cmd)
    data = Pandoc(wf).arg_options

    # Iterate thru possible short-form option + arg items
    for arg_opt in arg_options:
        search_str = ' '.join(arg_opt)

        # Prepare `flag` for precise searching
        if '--' in arg_opt[0]:
            flag = arg_opt[0]
        else:
            flag = arg_opt[0] + ' '
        long_opt = next((item for item in data if flag in item), None)

        # Is there a possible long-form option?
        if long_opt is not None:
            re_opts = long_opt.split(', ')
            # Get the long-form option format
            full_opt = next((opt for opt in re_opts if ' ' not in opt), None)

            opt_flag = full_opt.split('=')[0]
            # Prepare and format the arg for the long-form option
            if '.' in arg_opt[1]: # is it a file?
                if opt_flag == '--output':
                    input_ext = os.path.splitext(arg_opt[1])[1]
                    replace_path = "{input_name}" + input_ext
                    replace_str = '='.join([opt_flag, replace_path])
                else:
                    replace_path = '{input_dir}/' + arg_opt[1]
                    replace_str = '='.join([opt_flag, replace_path])
            else:
                the_arg = arg_opt[1]
                if '=' in arg_opt[1]:
                    the_arg = arg_opt[1].replace('=', ':')
                    
                replace_str = '='.join([opt_flag, the_arg])
        else: # no long-form option
            replace_str = search_str

        cmd = re.sub(search_str, replace_str, cmd)

    # Split options into list
    cmd_list = splitter(cmd)
    # Clean up list for template
    if cmd_list[0] == 'pandoc':
        cmd_list = cmd_list[1:]
    cmd_list = ["{input_file}" if '-' not in x else x for x in cmd_list]
    print cmd_list






def splitter(s):
    """Split ``s`` by spaces, except for text in quotes.
    """
    parts = re.sub('".+?"',
                   lambda m: m.group(0).replace(" ", "\x00"),
                   s).split()
    parts = [p.replace("\x00", " ") for p in parts]
    return parts

        

    

if __name__ == '__main__':
    WF = Workflow(libraries=[os.path.join(os.path.dirname(__file__), 'lib')])
    sys.exit(WF.run(main))
