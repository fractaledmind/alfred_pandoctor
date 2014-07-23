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
import json
import os.path
import subprocess

import utils
from workflow import Workflow, web

WF = Workflow()

DEFAULT_OPTIONS = (
    "parse-raw", 
    "smart", 
    "normalize", 
    "standalone"
)

class Pandoc(object):
    """A `pandoc` instance
    """
    
    def __init__(self):
        """Initialize `pandoc` object.
        """
        self.data = self.get_stored()

    def config(self):
        """Save `pandoc` info to data storage.
        """
        self.store('pandoc', 'outputs', self._formats('output'))
        self.store('pandoc', 'inputs', self._formats('input'))
        self.store('pandoc', 'options', self._options)
        return 1
        

    @property
    def path(self):
        """Find path to `pandoc` executable.
        """
        if os.path.exists('/usr/local/bin/pandoc'):
            return '/usr/local/bin/pandoc'
        else:
            from distutils.spawn import find_executable
            pandoc_path = find_executable('pandoc')
            if pandoc_path:
                return pandoc_path
            else:
                raise RuntimeError("Pandoc is not installed!")

    @property
    def version(self):
        """Get version of installed `pandoc`.
        """
        version = self._info('--version').splitlines()[0]
        return version.replace('pandoc ', '').strip()

    @property
    def outputs(self):
        """All possible output formats for `pandoc`.
        """
        return self.data['outputs']

    @property
    def inputs(self):
        """All possible input formats for `pandoc`.
        """
        return self.data['inputs']

    @property
    def options(self):
        """All possible options for `pandoc`.
        """
        return self.data['options']

    @staticmethod
    def get_stored():
        """Get pandoc info from cache file.
        """
        return WF.cached_data('pandoc', max_age=0)

    @staticmethod
    def _formats(kind):
        """Get all possible input and/or output formats for `pandoc`.
        """
        format_re = re.compile(r'<code>(.*?)</code>\s\((.*?)\)')
        req = web.request('GET', 'http://johnmacfarlane.net/pandoc/README.html')
        lines = req.text.splitlines()
        for i, line in enumerate(lines):
            if '<dt><code>-f</code>' in line:
                inputs = re.findall(format_re, lines[i+1])
            elif '<dt><code>-t</code>' in line:
                outputs = re.findall(format_re, lines[i+1])

        d_outputs = []
        for out in outputs:
            d_outputs.append({'arg': out[0], 'description': out[1]})
        d_inputs = []
        for inp in inputs:
            d_inputs.append({'arg': inp[0], 'description': inp[1]})

        if kind == 'output':
            return d_outputs
        elif kind == 'input':
            return d_inputs

    def _info(self, flag):
        """Get man/help page for `pandoc`.
        """
        try:
            return subprocess.check_output([self.path, flag]).decode()
        except OSError:
            raise OSError("You probably do not have pandoc installed.")


    def _options(self):
        """Get all possible options for `pandoc`.
        """
        man_page = self._info('--help').splitlines(False)
        idx = man_page.index('Options:') + 1
        options = man_page[idx:]
        args = []
        for option in options:
            long_option = re.search(r'--(.*?)(?=\s|,)', option).group()
            status = False
            for default in DEFAULT_OPTIONS:
                default = "--" + default
                if default == long_option:
                    status = True

            if '=' in long_option:
                if '[=' in long_option:
                    opt, arg = long_option.split('[=')
                    opt = opt.replace('--', '')
                    arg = arg.replace(']', '')
                    args.append({'type': 'Argument (optional)',
                                 'full': long_option,
                                 'flag': opt,
                                 'arg_type': arg,
                                 'status': status})
                else:
                    opt, arg = long_option.split('=')
                    opt = opt.replace('--', '')
                    args.append({'type': 'Argument (required)',
                                 'full': long_option,
                                 'flag': opt,
                                 'arg_type': arg,
                                 'status': status})
            else:
                opt = long_option.replace('--', '')
                args.append({'type': 'Boolean  (on/off)  ',
                             'full': long_option,
                             'flag': opt,
                             'arg_type': None,
                             'status': status})
        return args

    @staticmethod
    def store(name, key, data):
        """Updates `name` cache file with the `data`.
        """
        if hasattr(data, '__call__'):
            wrapper = data
            data = data()
        else:
            def wrapper(): return {key: data}

        stored = WF.cached_data(name, wrapper, max_age=0)

        if not stored.has_key(key): # new `key:value` pair
            stored.update({key: data})
            WF.cache_data(name, stored)
        else: # update `value` of `key`
            stored[key] = data
            WF.cache_data(name, stored)
        return True

    

def config(wf_obj):
    """Save `pandoc` info and create default settings.
    """
    # Save `pandoc` info to `settings.json`
    Pandoc().config()

    if not os.path.exists(wf_obj.datafile('pandoc_defaults.json')):
        defaults = utils.path_read(wf_obj.workflowfile('pandoc-config.json'))
        utils.path_write(defaults, wf_obj.datafile('pandoc_defaults.json'))

if __name__ == '__main__':
    WF = Workflow()
    sys.exit(WF.run(config))
