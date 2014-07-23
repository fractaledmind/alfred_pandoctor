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

import sys
import os.path
import subprocess

from config import Pandoc
from workflow import Workflow
from workflow.workflow import MATCH_ALL, MATCH_ALLCHARS


__version__ = '0.5'

__usage__ = """
PanDoctor -- An Alfred GUI for `pandoc`

Usage:
    pandoctor.py store <key> <value>
    pandoctor.py search <scope> <query>
    pandoctor.py launch <trigger> <query>
    pandoctor.py run

Arguments:
    <key>       Dictionary key to save <value> data under in cache
    <value>     Data to be saved in cache
    <scope>     Scope of searchable data
    <query>     Search query
    <trigger>   Trigger name for Alfred's "External Trigger"

Options:
    -h, --help  Show this message

This script is meant to be called from Alfred.

"""

README = 'http://johnmacfarlane.net/pandoc/README.html'

DELIMITER = '➣'

TRIGGER_ALFRED = """tell application "Alfred 2" \
                to run trigger "{}" \
                in workflow "com.hackademic.pandoctor" \
                with argument "{}"
"""

FORMATS = {
    'dbk': 'docbook',
    'hs': 'native',
    'md': 'markdown',
    'rest': 'rst',
    'tex': 'latex',
    'txt': 'markdown'
}

KEYS = (
    'in_path',
    'in_fmt',
    'out_fmt'
)

def _applescriptify(text):
    """Replace double quotes in `text` for Applescript.
    """
    return text.replace('"', '" & quote & "')

def run_applescript(scpt_str):
    """Run an applescript.
    """
    proc = subprocess.Popen(['osascript', '-e', scpt_str],
                                stdout=subprocess.PIPE)
    out = proc.communicate()[0]
    return out.strip()





class PanDoctor(object):
    """PanDoctor object."""
    def __init__(self, wf):
        self.wf = wf
        self.runner = self.wf.cached_data('runner', max_age=0)
        self.key = None
        self.value = None
        self.scope = None
        self.query = None
        self.trigger = None

    ##################################################
    ##################################################
    ##
    ##   Main API method
    ##
    ##################################################
    ##################################################

    def run(self, args):
        """Main API method.
        """
        self.key = args['<key>']
        self.value = args['<value>']
        self.scope = args['<scope>']
        self.query = args['<query>']
        self.trigger = args['<trigger>']

        actions = ('store', 'search', 'launch', 'run', 'clean')

        for action in actions:
            if args.get(action):
                methname = 'do_{}'.format(action)
                meth = getattr(self, methname, None)
                if meth:
                    return meth()
                else:
                    raise ValueError('Unknown action : {}'.format(action))


    ##################################################
    ## `Search` methods
    ##################################################

    def do_search(self):
        """Search/Show data for given scope.
        """
        data = getattr(Pandoc(), self.scope, None)
        
        if self.scope in ('inputs', 'outputs'):
            self.search_formats(data)
        elif self.scope == 'options':
            self.search_options(data)

    #-------------------------------------------------
    # `Search` sub-methods
    #-------------------------------------------------

    def search_formats(self, data):
        """Search `input` or `output` formats.
        """
        # Ensure first item is header explaining option.
        header = "Pandoc " + self.scope.capitalize()
        header_sub = "Please select the proper " + str(self.scope[:-1]) + " format"
        self.wf.add_item(header,
                         header_sub,
                         valid=False,
                         icon="icons/pandoc_qu.png")

        # Function to generate search string
        func = lambda x: ' '.join([x['arg'], x['description']])
        
        # Filter or show all if `query` = '.'
        results = self._filter(data, func)
        
        # Prepare Alfred feedback
        for item in results:
            self.wf.add_item(item['arg'],
                             item['description'],
                             arg=item['arg'],
                             valid=True)
        self.wf.send_feedback()

    def search_options(self, data):
        """Search `options`.
        """
        # Ensure first item is always option to end session.
        self.wf.add_item("Done?",
                         "Finished setting all Pandoc options?",
                         arg="[done]",
                         valid=True,
                         icon="icons/pandoc_qu.png")
        
        # Function to generate search string
        func = lambda x: ' '.join([x['full'], x['type']])
        
        # Filter or show all if `query` = '.'
        results = self._filter(data, func)
        
        # Get all option keys already assigned
        runner_opts = []
        if self.runner is not None:
            runner_opts = [k for k in self.runner.keys() if k not in KEYS]
        
        # Prepare Alfred feedback
        for item in results:
            # Ignore `input` and `output` options
            if item['flag'] in ('to', 'from'):
                continue

            # Catch any pre-set options
            elif item['flag'] in runner_opts:
                item['status'] = next((val for key, val in self.runner.items()
                                        if key == item['flag']), None)

            # Prepare item subtitle and icon
            subtitle = 'Type: {} || Status: {}'.format(
                                                    item['type'],
                                                    str(item['status']))
            if item['status'] != False:
                icon = 'icons/pandoc_on.png'
            else:
                icon = 'icons/pandoc.png'

            # Add item to Alfred results
            self.wf.add_item(item['flag'],
                             subtitle,
                             arg=item['flag'],
                             valid=True,
                             icon=icon)
        self.wf.send_feedback()

    #-------------------------------------------------
    # `Search` lower-level method
    #-------------------------------------------------

    def _filter(self, data, func):
        """Filter the ``data`` by the ``query`` using ``func``
        to create a searchable string.
        """
        if self.query in ('.', ' '):
            filtered = data
        else:
            filtered = self.wf.filter(self.query, data,
                                      key=func, 
                                      match_on=MATCH_ALL ^ MATCH_ALLCHARS)
        return filtered


    ##################################################
    ## `Store` methods
    ##################################################

    def do_store(self):
        """Updates `runner` cache file with the `data`.
        """
        arg_out = '.'
        # if a base key
        if self.key in KEYS:
            self.store(self.value.strip())

        # if option key
        elif self.key == 'options':
            flag = self.value.strip()

            # if final options selection
            if flag == '[done]':
                # TODO
                self.launch('pandoc_run', '[blank]')
                arg_out = '[pause]'
            
            # if boolean option
            elif self.boolean_option(flag):
                status = self.flip_value(flag)
                self.key = flag
                self.store(status)
            # or argument option
            else:
                # need to set Argument
                if DELIMITER not in flag:
                    arg = "{} {} ".format(flag, DELIMITER)
                    self.launch('pandoc_opt_set', arg)
                    arg_out = '[pause]'
                # need to save set Argument
                else:
                    flag, status = self._parse_query(flag)
                    self.key = flag
                    self.store(status)
        return arg_out

    #-------------------------------------------------
    # `Store` sub-method
    #-------------------------------------------------

    def store(self, value):
        """Store data to cache.
        """
        # new `key:value` pair
        if self.runner:
            if not self.runner.has_key(self.key):
                self.runner.update({self.key: value})
                self.wf.cache_data('runner', self.runner)

            # update `value` of `key`
            else:
                self.runner[self.key] = value
                self.wf.cache_data('runner', self.runner)
        else:
            self.wf.cache_data('runner', {self.key: value})
        return True

    #-------------------------------------------------
    ## `Store` lower-level methods
    #-------------------------------------------------

    @staticmethod
    def _parse_query(query):
        """Split ``query`` into ``flag`` and ``value``.

        :returns: ``(flag, value)`` where either may be empty
        """

        components = query.split(DELIMITER)
        if not len(components) == 2:
            raise ValueError('Too many components in : {!r}'.format(query))
        flag, value = [s.strip() for s in components]
        return (flag, value)


    def flip_value(self, option):
        """Return only options of specified type.
        """
        runner_opts = [k for k in self.runner.keys() if k not in KEYS]
        if option not in runner_opts:
            gen_exp = (opt for opt in Pandoc().options if opt['flag'] == option)
            dct = next(gen_exp, None)
            return not dct['status']
        else:
            gen_exp = (val for key, val in self.runner.items()
                        if key == option)
            val = next(gen_exp, None)
            return not val

    @staticmethod
    def boolean_option(option):
        """Check if option is Boolean.
        """
        dct = [opt for opt in Pandoc().options 
                if opt['flag'] == option
                and opt['arg_type'] == None]
        if dct != []:
            return True
        else:
            return False


    ##################################################
    ## `Launch` methods
    ##################################################

    def do_launch(self):
        """Run Alfred filter.
        """
        self.launch(self.trigger, self.query.strip())

    #-------------------------------------------------
    # `Launch` sub-methods
    #-------------------------------------------------

    def launch(self, trigger, arg):
        """Launch appropriate Alfred action via External Trigger.
        """
        trigger = _applescriptify(trigger)
        check = self._check_query(arg)

        if check:
            n_arg = _applescriptify(check)
            scpt = TRIGGER_ALFRED.format(trigger, n_arg)
            run_applescript(scpt)

    #-------------------------------------------------
    # `Launch` lower-level methods
    #-------------------------------------------------

    def _check_query(self, query):
        """Get proper `pandoc` name of format from file extension.
        """
        if query == "[path]":
            input_path = self.runner['in_path']
            if os.path.exists(input_path):
                input_ext = os.path.splitext(input_path)[1].strip('.')
                for ext, fmt in FORMATS.items():
                    if ext == input_ext:
                        return fmt
                return input_ext
        elif query == "[pause]":
            return False
        else:
            return query


    ##################################################
    ## `Run` methods
    ##################################################

    def do_run(self):
        """Run `pandoc` with all chosen options.
        """
        pandoc_args = []
        pandoc_args.extend(self.get_input_format())
        pandoc_args.extend(self.get_output_format())
        pandoc_args.extend(self.get_opts())
        pandoc_args.extend(self.get_input_path())
        
        self.run_pandoc(pandoc_args)

        self.do_clean()

        return 'File successfully created!'

    #-------------------------------------------------
    # `Run` sub-methods
    #-------------------------------------------------

    def get_input_path(self):
        """Get path of input file.
        """
        in_path = self.get_run_val('in_path')
        return [in_path]

    def get_input_format(self):
        """Get format of input file.
        """
        in_fmt = self.get_run_val('in_fmt')
        return ["--from=" + in_fmt]

    def get_output_format(self):
        """Get format of output file.
        """
        out_fmt = self.get_run_val('out_fmt')
        return ["--to=" + out_fmt]

    def get_opts(self):
        """Get all chosen options.
        """
        runner_opts = [k for k in self.runner.keys() if k not in KEYS]

        on_opts = []
        for opt in Pandoc().options:
            if opt['flag'] in ('to', 'from'):
                continue
            # Catch any pre-set options
            elif opt['flag'] in runner_opts:
                opt['status'] = next((val for key, val in self.runner.items()
                                        if key == opt['flag']), None)
            
            if opt['status'] == True:
                on_opts.append(opt['full'])
            elif opt['status'] != False:
                arg_opt = "--{}={}".format(opt['flag'], opt['status'])
                on_opts.append(arg_opt)

        # Check if explicit output file is specified
        check = next((opt for opt in on_opts if '--output' in opt), None)
        if check == None:
            fmt = self.get_output_format()[0].split('=')[1]
            input_path = self.get_input_path()[0]
            input_file = os.path.splitext(input_path)[0]
            output = '.'.join([input_file, fmt])
            output = "--output={}".format(output)
            on_opts.extend([output])
        return on_opts

    @staticmethod
    def run_pandoc(extra_args):
        """Run `pandoc` with all arguments.
        """
        args = [Pandoc().path]
        args.extend(extra_args)
        proc = subprocess.check_output(args)

        return proc.decode('utf-8')

    #-------------------------------------------------
    # `Run` lower-level method
    #-------------------------------------------------

    def get_run_val(self, key):
        """Get the value for ``key`` from ``runner.cache``.
        """
        val = next((v for k, v in self.runner.items() if k == key), None)
        return val


    ##################################################
    ## `Clean` methods
    ##################################################

    def do_clean(self):
        """Clean up cache for next run.
        """
        runner = self.wf.cachefile('runner.cache')
        os.remove(runner)

    

    




def main(wf):
    """main"""
    from docopt import docopt
    args = wf.args
    #args = ['run']
    args = docopt(__usage__, argv=args, version=__version__)
    pd = PanDoctor(wf)
    res = pd.run(args)
    if res:
        print res.strip()

    

if __name__ == '__main__':
    WF = Workflow(libraries=[os.path.join(os.path.dirname(__file__), 'lib')])
    sys.exit(WF.run(main))
