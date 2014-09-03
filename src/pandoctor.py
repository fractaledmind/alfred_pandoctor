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

# Standard Library
import re
import sys
import os.path
import subprocess

# Workflow Library
import utils
from workflow import Workflow, web
from workflow.workflow import MATCH_ALL, MATCH_ALLCHARS

# Dependencies Library
sys.path.insert(0, Workflow().workflowfile('lib/'))
from bs4 import BeautifulSoup
from docopt import docopt


__version__ = '1.0.5'

__usage__ = """
PanDoctor -- An Alfred GUI for `pandoc`

Usage:
    pandoctor.py config
    pandoctor.py store <flag> <argument>
    pandoctor.py search <flag> <argument>
    pandoctor.py launch <flag> <argument>
    pandoctor.py run <flag>
    pandoctor.py help <flag>

Arguments:
    <flag>      Determines which specific code-path to follow
    <argument>  The value to be stored, searched, or passed on

Options:
    -h, --help  Show this message

This script is meant to be called from Alfred.
"""

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
    'mmd': 'markdown_phpextra',
    'rest': 'rst',
    'tex': 'latex',
    'txt': 'markdown'
}

RUNNER_KEYS = (
    'in_path',
    'in_format',
    'out_format'
)

DEFAULT_OPTIONS = (
    "parse-raw", 
    "smart", 
    "normalize", 
    "standalone"
)


##################################################
# Applescript Helpers
##################################################


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


################################################################################
#     Pandoc Object
################################################################################

class Pandoc(object):
    """All relevant information about user's `pandoc` installation.
    """
    
    def __init__(self, wf):
        """Initialize `pandoc` object.
        """
        self.wf = wf
        self.data = self.get_stored()


    def config(self):
        """Save `pandoc` info to data storage.
        """
        self.store('pandoc', 'outputs', self._formats('output'))
        self.store('pandoc', 'inputs', self._formats('input'))
        self.store('pandoc', 'options', self._options)
        self.store('pandoc', 'arg_options', self._arg_option_flags)
        return 1


    #-----------------------------------------------------------------
    ## Pandoc properties
    #-----------------------------------------------------------------


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
        version = self._pandoc_info('--version').splitlines()[0]
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


    @property
    def arg_options(self):
        """All possible options for `pandoc`.
        """
        return self.data['arg_options']


    #-----------------------------------------------------------------
    ## Pandoc Storage methods
    #-----------------------------------------------------------------


    def get_stored(self):
        """Get pandoc info from cache file.
        """
        return self.wf.cached_data('pandoc', max_age=0)


    def store(self, name, key, data):
        """Updates `name` cache file with the `data`.
        """
        if hasattr(data, '__call__'):
            wrapper = data
            data = data()
        else:
            def wrapper(): return {key: data}

        stored = self.wf.cached_data(name, wrapper, max_age=0)

        if not stored.has_key(key): # new `key:value` pair
            stored.update({key: data})
            self.wf.cache_data(name, stored)
        else: # update `value` of `key`
            stored[key] = data
            self.wf.cache_data(name, stored)
        return True


    #-------------------------------------------------------
    ## Sub-methods
    #-------------------------------------------------------


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

        d_outputs = [{'arg': 'pdf', 'description': 'Portable Document Format'}]
        for out in outputs:
            d_outputs.append({'arg': out[0], 'description': out[1]})
        d_inputs = []
        for inp in inputs:
            d_inputs.append({'arg': inp[0], 'description': inp[1]})

        if kind == 'output':
            return d_outputs
        elif kind == 'input':
            return d_inputs


    def _pandoc_info(self, flag):
        """Get man/help page for `pandoc`.
        """
        try:
            return subprocess.check_output([self.path, flag]).decode()
        except OSError:
            raise OSError("You probably do not have pandoc installed.")


    def _options(self):
        """Get all possible options for `pandoc`.
        """
        man_page = self._pandoc_info('--help').splitlines(False)
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
    def _arg_option_flags():
        """Get short and long form of all `pandoc` argument options.
        """
        # Soupify the HTML of pandoc README
        req = web.get('http://johnmacfarlane.net/pandoc/README.html')
        req.raise_for_status()
        soup = BeautifulSoup(req.text)

        cli_arg_options = []
        # Get all the sub-sections under "Options"
        option_types = soup.find_all('dl')
        for option_set in option_types:
            # Get all the options under that sub-section
            options = option_set.find_all('dt')
            for opt in options:
                if '=' in opt.text:
                    cli_arg_options.append(opt.text)
        return cli_arg_options


################################################################################
#     Pandoctor Object
################################################################################

class PanDoctor(object):
    """PanDoctor object."""
    def __init__(self, wf):
        self.wf = wf
        self.runner = self.wf.cached_data('runner', max_age=0)
        self.pandoc = Pandoc(wf)
        self.flag = None
        self.arg = None


#-----------------------------------------------------------------
## Main API method
#-----------------------------------------------------------------


    def run(self, args):
        """Main API method.
        """
        self.flag = args['<flag>']
        if self.flag != None: 
            self.flag = self.flag.strip()
        self.arg = args['<argument>']
        if self.arg != None:
            self.arg = self.arg.strip()

        actions = ('store', 'search', 'launch', 'run', 'config', 'help')

        for action in actions:
            if args.get(action):
                method_name = '{}_codepath'.format(action)
                method = getattr(self, method_name, None)
                if method:
                    return method()
                else:
                    raise ValueError('Unknown action : {}'.format(action))


#-------------------------------------------------------
### `Help` method
#-------------------------------------------------------


    def help_codepath(self):
        """Access various helpful items.
        """
        if self.flag == 'filter':
            self.help_filter()
        else:
            self.help_run()


    #---------------------------------------------
    #### `Help` main branches
    #---------------------------------------------


    def help_filter(self):
        """Filter for help items.
        """
        self.wf.add_item("Pandoc ReadMe",
                        "Open Pandoc's ReadMe file?", 
                        valid=True, 
                        arg='p:readme')
        self.wf.add_item("Pandoctor ReadMe",
                        "Open Pandoctor's ReadMe file?", 
                        valid=True, 
                        arg='dr:readme')
        self.wf.add_item("Root",
                        "Open Pandoctor's Root Folder?", 
                        valid=True, 
                        arg='workflow:openworkflow')
        self.wf.add_item("Storage",
                        "Open Pandoctor's Storage Folder?", 
                        valid=True, 
                        arg='workflow:opendata')
        self.wf.add_item("Cache",
                        "Open Pandoctor's Cache Folder?", 
                        valid=True, 
                        arg='workflow:opencache')
        self.wf.add_item("Logs",
                        "Open Pandoctor's Logs?", 
                        valid=True, 
                        arg='workflow:openlog')
        
        self.wf.send_feedback()


    def help_run(self):
        """Launch various help items.
        """
        # Workflow will take care of all other help items
        if self.flag == 'dr:readme':
            readme = 'http://hackademic.postach.io/pandoctor-alfred-workflow'
        elif self.flag == 'p:readme':
            readme = self.wf.workflowfile('help/pandoc_readme.html')
        subprocess.check_output(['open', readme])


#-------------------------------------------------------
### `Config` method
#-------------------------------------------------------


    def config_codepath(self):
        """Save all pertinent `pandoc` info to cache.
        """
        self.pandoc.config()
        return "Configuration Complete!"


#-------------------------------------------------------
### `Search` method
#-------------------------------------------------------


    def search_codepath(self):
        """Search/Show data for given scope.
        """
        prop = 'options' if self.flag in ('ignore', 'default') else self.flag
        data = getattr(self.pandoc, prop, None)

        # Ensure each Script Filter has informational header
        self._add_header()
        
        if self.flag in ('inputs', 'outputs'):
            self.search_formats(data)
        
        elif self.flag == 'options':
            self.search_options(data)
        
        elif self.flag == 'ignore':
            self.search_ignores(data)

        elif self.flag == 'default':
            self.search_defaults(data)

        elif self.flag == 'templates':
            self.search_templates()

        elif self.flag == 'set_template_default':
            self.search_booleans()

        # Pass all Alfred items
        self.wf.send_feedback()


    #---------------------------------------------
    #### `Search` main branches
    #---------------------------------------------


    def search_formats(self, data):
        """Search `input` or `output` formats.
        """
        res = self._filter(data, lambda x: ' '.join([x['arg'], x['description']]))
        
        # Prepare Alfred feedback
        for item in res:
            self.wf.add_item(item['arg'],
                             item['description'],
                             arg=item['arg'],
                             valid=True)


    def search_options(self, data):
        """Search `options`.
        """
        results = self._filter(data, lambda x: ' '.join([x['full'], x['type']]))

        # Get all option keys already assigned
        runner_opts = []
        if self.runner is not None:
            runner_opts = [k for k in self.runner.keys()
                            if k not in RUNNER_KEYS]
        
        # Prepare Alfred feedback
        for item in results:
            if self._check_option(item) == False:
                continue

            # Check for user defaults
            # and change status accordingly
            if os.path.exists(self.wf.datafile('user_defaults.json')):
                item['status'] = False
                defs = utils.json_read(self.wf.datafile('user_defaults.json'))
                if item['flag'] in defs:
                    item['status'] = True

            # Catch any pre-set options
            if item['flag'] in runner_opts:
                # get item's pre-set status value
                item['status'] = next((val for key, val in self.runner.items()
                                    if key == item['flag']), None)

            # Prepare item subtitle and icon
            subtitle = 'Type: {}'.format(item['type'])
            icon = 'icons/pandoc.png'
            if item['status'] != False:
                icon = 'icons/pandoc_on.png'

            # Add item to Alfred results
            self.wf.add_item(item['flag'],
                             subtitle,
                             arg=item['flag'],
                             valid=True,
                             icon=icon)


    def search_ignores(self, data):
        """Search thru options user wants to ignore.
        """
        results = self._filter(data, lambda x: ' '.join([x['full'], x['type']]))

        ignored_opts = utils.json_read(self.wf.datafile('user_ignore.json'))
        
        # Prepare Alfred feedback
        for item in results:
            icon = 'icons/pandoc.png'
            
            # Ignore user chosen ignored_opts options
            if item['flag'] in ('to', 'from'):
                continue
            
            elif (ignored_opts is not None 
                    and item['flag'] in ignored_opts
                 ):
                icon = 'icons/pandoc_on.png'

            # Prepare item subtitle and icon
            subtitle = 'Type: {}'.format(item['type'])

            # Add item to Alfred results
            self.wf.add_item(item['flag'],
                        subtitle,
                        arg=item['flag'],
                        valid=True,
                        icon=icon)


    def search_defaults(self, data):
        """Search through options to set as default.
        """
        results = self._filter(data, lambda x: ' '.join([x['full'], x['type']]))

        default_opts = utils.json_read(self.wf.datafile('user_defaults.json'))
        
        # Prepare Alfred feedback
        for item in results:
            icon = 'icons/pandoc.png'
            
            # Ignore user chosen default_opts options
            if item['flag'] in ('to', 'from'):
                continue
            
            elif (default_opts is not None 
                    and item['flag'] in default_opts
                 ):
                icon = 'icons/pandoc_on.png'

            # Prepare item subtitle and icon
            subtitle = 'Type: {}'.format(item['type'])

            # Add item to Alfred results
            self.wf.add_item(item['flag'],
                        subtitle,
                        arg=item['flag'],
                        valid=True,
                        icon=icon)


    def search_templates(self):
        """Display the names of all the user's Pandoc Templates.
        """
        tmps = utils.json_read(self.wf.datafile('user_templates.json'))
        if not tmps:
            # Show default Templates if no user ones created
            tmps = utils.json_read(self.wf.workflowfile('pandoc_templates.json'))

        results = self._filter(tmps, lambda x: x['name'])
        
        # Prepare Alfred feedback
        for item in results:
            sub = "Uses default options? " + str(item['use_defaults'])
            self.wf.add_item(item['name'],
                             sub,
                             arg=item['name'],
                             valid=True)



    def search_booleans(self):
        """Display ``True`` and ``False`` as options.
        """
        booleans = ('True', 'False')
        results = self._filter(booleans, lambda x: x)
        
        # Prepare Alfred feedback
        for item in results:
            self.wf.add_item(item,
                            'Add Default Options to new user template?',
                            arg='Defaults ➣' + item,
                            valid=True)
            


    #---------------------------------------------
    #### `Search` lower-level method
    #---------------------------------------------


    def _add_header(self):
        """Add an info header to the top of the search.
        """

        if self.flag in ('inputs', 'outputs', 'templates'):
            if self.flag in ('inputs', 'outputs'):
                sub_post = " format."
            elif self.flag == 'templates':
                sub_post = " command."

            header = "Pandoc " + self.flag.capitalize()
            header_sub = "Select the proper " + str(self.flag[:-1]) + sub_post
            header_arg = None
            header_valid = False
            header_icon = "icons/pandoc_info.png"

        elif self.flag in ('options', 'ignore', 'default'):
            header = "Done setting " + self.flag.capitalize() + "?"
            header_sub = "Select this item when you've finished all selections."
            header_arg = "[done]"
            header_valid = True
            header_icon = "icons/pandoc_qu.png"

        elif self.flag == 'set_template_default':
            return 0
        
        # Ensure first item explains search or is option to end session.
        self.wf.add_item(header,
                         header_sub,
                         arg=header_arg,
                         valid=header_valid,
                         icon=header_icon)


    def _check_option(self, item):
        """Determine if item should be passed on or not.
        """
        # Get all options user wants ignored
        ignored_opts = utils.json_read(self.wf.datafile('user_ignore.json'))
        
        # Ignore `input` and `output` options
        # or ignore any user selected ignore options
        if (item['flag'] in ('to', 'from')
             or
                (ignored_opts is not None 
                  and item['flag'] in ignored_opts
                )
            ):
            return False
        else:
            return True


    def _filter(self, data, func):
        """Use ``Workflow``'s ``filter`` method.
        """
        results = self.wf.filter(self.arg, data,
                                key=func, 
                                match_on=MATCH_ALL ^ MATCH_ALLCHARS)
        return results


#-------------------------------------------------------
### `Store` method
#-------------------------------------------------------


    def store_codepath(self):
        """Updates `runner` cache file with the `data`.
        """
        arg_out = ''

        # if a base key
        if self.flag in RUNNER_KEYS:
            arg_out = self.add_runner_base()

        # if option key
        elif self.flag == 'options':
            arg_out = self.add_runner_option()

        # if ignore key
        elif self.flag == 'ignore':
            arg_out = self.add_ignore(self.arg)

        # if default key
        elif self.flag == 'default':
            arg_out = self.add_default(self.arg)


        # if template key
        elif self.flag == 'template':
            arg_out = self.add_template()
        
        return arg_out


    #---------------------------------------------
    #### `Store` main branches
    #---------------------------------------------


    def add_runner_base(self):
        """Add basic info (path, input format, output format)
        to ``runner.cache``.
        """
        self._store(self.flag, self.arg)
        return ''


    def add_runner_option(self):
        """Add an option to ``runner.cache``.
        """
        arg_out = ''

        # if exit item selected
        if self.arg == '[done]':
            self._launch('pandoc_run', 'gui')
            arg_out = '[pause]'
        
        # if boolean option
        elif self._is_boolean_option(self.arg):
            status = self._flip_value(self.arg)
            self._store(self.arg, status)
        
        # or argument option
        else:
            # need to set Argument
            if DELIMITER not in self.arg:
                arg = "{} {} ".format(self.arg, DELIMITER)
                self._launch('pandoc_opt_set', arg)
                arg_out = '[pause]'
            
            # need to save set Argument
            else:
                flag, status = self._parse_query(self.arg)
                self._store(flag, status)

        return arg_out


    def add_ignore(self, value):
        """Store list of options to ignore.
        """
        arg_out = ''

        # If exit item selected
        if self.arg == '[done]':
            arg_out = '[pause]'
        else:
            ignored = utils.json_read(self.wf.datafile('user_ignore.json'))
            if ignored:
                ignored.extend([value])
                clean = list(set(ignored))
                utils.json_write(clean, self.wf.datafile('user_ignore.json'))
            else:
                utils.json_write([value], self.wf.datafile('user_ignore.json'))

        return arg_out


    def add_default(self, value):
        """Store list of options to be defaults.
        """
        arg_out = ''

        # If exit item selected
        if self.arg == '[done]':
            arg_out = '[pause]'
        else:
            defaults = utils.json_read(self.wf.datafile('user_defaults.json'))
            if defaults:
                defaults.extend([value])
                clean = list(set(defaults))
                utils.json_write(clean, self.wf.datafile('user_defaults.json'))
            else:
                utils.json_write([value], self.wf.datafile('user_defaults.json'))

        return arg_out


    def add_template(self):
        """Add a new template in JSON format to `pandoc_templates.json`.
        """
        if DELIMITER in self.arg:
            key, value = self._parse_query(self.arg)
            if key == 'Name':
                self._store_template_info('name', value)
            elif key == 'Defaults':
                bool_v = utils.to_bool(value)
                self._store_template_info('use_defaults', bool_v)
            elif key == 'Command':
                clean_cmd = self._parse_template(value)
                self._store_template_info('options', clean_cmd)
        return 'Template successfully created!'


    #---------------------------------------------
    #### `Store` sub-methods
    #---------------------------------------------


    def _store(self, key, value):
        """Store data to cache.
        """
        if self.runner:
            # new `key:value` pair
            if not self.runner.has_key(key):
                self.runner.update({key: value})
                self.wf.cache_data('runner', self.runner)

            # update `value` of `key`
            else:
                self.runner[key] = value
                self.wf.cache_data('runner', self.runner)
        else:
            self.wf.cache_data('runner', {key: value})
        return True


    def _store_template_info(self, key, value):
        """Store dictionary info for new user template.
        """
        tmps = utils.json_read(self.wf.datafile('user_templates.json'))
        if tmps:
            if key == 'name':
                d = [{key: value}]
                tmps.extend(d)
            else:
                for temp in tmps:
                    if len(temp.keys()) != 3:
                        temp.update({key: value})
                        break
            new = tmps
        else:
            new = [{key: value}]

        utils.json_write(new, self.wf.datafile('user_templates.json'))
        return True


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


    def _flip_value(self, option):
        """Return only options of specified type.
        """
        runner_opts = [k for k in self.runner.keys() if k not in RUNNER_KEYS]
        if option not in runner_opts:
            gen_exp = (opt for opt in self.pandoc.options
                        if opt['flag'] == option)
            dct = next(gen_exp, None)
            return not dct['status']
        else:
            gen_exp = (val for key, val in self.runner.items()
                        if key == option)
            val = next(gen_exp, None)
            return not val


    def _is_boolean_option(self, option):
        """Check if option is Boolean.
        """
        dct = [opt for opt in self.pandoc.options 
                if opt['flag'] == option
                and opt['arg_type'] == None]
        if dct != []:
            return True
        else:
            return False

    # TODO
    def _parse_template(self, cmd):
        """Parse a normal `pandoc` command into a proper Pandoctor command.
        """
        pandoc_re = r'(--|-[^\s]*?)\s([^-](?:[^\s]*?".*?"|[^\s]*?))(?=\s|$)'
        arg_options = re.findall(pandoc_re, cmd)
        data = self.pandoc.arg_options

        # Iterate thru possible short-form option + arg items
        for arg_opt in arg_options:
            search_str = ' '.join(arg_opt)

            # Prepare `flag` for precise searching
            flag = arg_opt[0] if '--' in arg_opt[0] else arg_opt[0] + ' '
            long_opt = next((item for item in data if flag in item), None)

            # Is there a possible long-form option?
            if long_opt is not None:
                re_opts = long_opt.split(', ')
                
                # Get the long-form option format
                full_opt = next((o for o in re_opts if ' ' not in o), None)
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
        cmd_list = self._splitter(cmd)
        
        # Clean up list for template
        if cmd_list[0] == 'pandoc':
            cmd_list = cmd_list[1:]
        cmd_list = ["{input_file}" if '-' not in x else x for x in cmd_list]
        
        return cmd_list


    @staticmethod
    def _splitter(s):
        """Split ``s`` by spaces, except for text in quotes.
        """
        parts = re.sub('".+?"',
                       lambda m: m.group(0).replace(" ", "\x00"),
                       s).split()
        parts = [p.replace("\x00", " ") for p in parts]
        return parts


#-------------------------------------------------------
## `Launch` method
#-------------------------------------------------------


    def launch_codepath(self):
        """Run Alfred filter.
        """
        self._launch(self.flag, self.arg)


    #---------------------------------------------
    #### `Launch` sub-methods
    #---------------------------------------------


    def _launch(self, trigger, arg):
        """Launch appropriate Alfred action via External Trigger.
        """
        trigger = _applescriptify(trigger)
        check = self._check_query(arg)

        if check is not None:
            n_arg = _applescriptify(check)
            scpt = TRIGGER_ALFRED.format(trigger, n_arg)
            run_applescript(scpt)


    #---------------------------------------------
    ##### `Launch` lower-level methods
    #---------------------------------------------


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
            return None
        else:
            return query


#-------------------------------------------------------
## `Run` method
#-------------------------------------------------------


    def run_codepath(self):
        """Run `pandoc` with all chosen options.
        """
        if self.flag == 'gui':
            return self.run_gui_cmd()
        else:
            return self.run_template_cmd(self.flag)


    #---------------------------------------------
    ## `Run` main branches
    #---------------------------------------------


    def run_template_cmd(self, template):
        """Run user-selected template command.
        """
        tmps = utils.json_read(self.wf.datafile('user_templates.json'))
        if tmps == None:
            tmps = utils.json_read(self.wf.workflowfile('pandoc_templates.json'))

        for temp in tmps:
            if temp['name'] == template.strip():
                args = temp['options']

                if temp['use_defaults'] == True:
                    defaults = [opt['full'] for opt in self.pandoc.options
                                if opt['status'] == True]
                    args.extend(defaults)

                args = self._format_template(args)
                
        return self.run_pandoc(args)


    def run_gui_cmd(self):
        """Run `pandoc` on command created via Pandoctor GUI.
        """
        pandoc_args = []
        pandoc_args.extend(self._get_input_format())
        pandoc_args.extend(self._get_output_format())
        pandoc_args.extend(self._get_options())
        pandoc_args.extend(self._get_input_path())
        
        return self.run_pandoc(pandoc_args)


    #-------------------------------------------------
    ### `Run` sub-methods
    #-------------------------------------------------


    def run_pandoc(self, extra_args):
        """Run `pandoc` with all arguments.
        """
        args = [self.pandoc.path]
        args.extend(extra_args)
        self.wf.logger.debug(args)
        try:
            subprocess.check_output(args).decode('utf-8')
            self.clean_codepath()
            return 'File successfully created!'
        except subprocess.CalledProcessError as e:
            self.wf.logger.debug(e.output)
            return e.output


    #---------------------------------------------
    # `Run` lower-level method
    #---------------------------------------------


    def _get_input_path(self):
        """Get path of input file.
        """
        in_path = self._runner_val('in_path')
        return [in_path]


    def _get_input_format(self):
        """Get format of input file.
        """
        in_fmt = self._runner_val('in_format')
        return ["--from=" + in_fmt]


    def _get_output_format(self):
        """Get format of output file.
        """
        out_fmt = self._runner_val('out_format')
        if out_fmt == 'pdf':
            out_fmt = 'latex'
        return ["--to=" + out_fmt]


    def _get_options(self):
        """Get all chosen options.
        """
        runner_opts = [k for k in self.runner.keys() if k not in RUNNER_KEYS]

        on_opts = []
        for opt in self.pandoc.options:
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
            out_fmt = self._runner_val('out_format')
            for ext, fmt in FORMATS.items():
                if fmt == out_fmt:
                    out_fmt = ext
            input_path = self._get_input_path()[0]
            input_file = os.path.splitext(input_path)[0]
            output = '.'.join([input_file, out_fmt])
            output = "--output={}".format(output)
            on_opts.extend([output])
        return on_opts


    def _runner_val(self, key):
        """Get the value for ``key`` from ``runner.cache``.
        """
        val = next((v for k, v in self.runner.items() if k == key), None)
        return val


    def _format_template(self, args):
        """Format the variables in a Template.
        """
        input_path = self._get_input_path()[0]
        input_name = os.path.splitext(input_path)[0]
        input_dir = os.path.dirname(input_path)

        for i, arg in enumerate(args):
            # Replace any and all variables with correct data
            arg = arg.replace('{input_file}', input_path)
            arg = arg.replace('{input_name}', input_name)
            arg = arg.replace('{input_dir}', input_dir)
            args[i] = arg
        return args


    #-------------------------------------------------------
    ## `Clean` methods
    #-------------------------------------------------------


    def clean_codepath(self):
        """Clean up cache for next run.
        """
        runner = self.wf.cachefile('runner.cache')
        os.remove(runner)

    


def main(wf):
    """main"""
    args = wf.args
    args = docopt(__usage__, argv=args, version=__version__)
    wf.logger.debug(args)
    pd = PanDoctor(wf)
    res = pd.run(args)
    if res:
        print res.strip()

    

if __name__ == '__main__':
    WF = Workflow()
    sys.exit(WF.run(main))
