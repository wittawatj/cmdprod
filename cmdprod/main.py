"""
Main file containing core code
"""

__author__ = 'Wittawat'

from abc import ABCMeta, abstractmethod
from future.utils import with_metaclass
import collections
import cmdprod
import cmdprod.util as util
import itertools
import os
import sys


class Values(object):
    """
    A class representing possible values for a parameter (Param).
    Iterable over the values.
    """
    pass

    @abstractmethod
    def __iter__(self):
        '''
        Return an iterator over possible values.
        '''
        pass

class InGroupValues(Values):
    """
    Values of a parameter which is part of a ParamGroup.
    """
    def __init__(self, values, index):
        '''
        values: a Values where each call to the iterator returns a tuple.
        index: index in the tuple 
        '''
        self.values = values
        self.index = index

    def __iter__(self):
        ind = self.index
        for v in self.values:
            yield v[ind]

class ValFixedIter(Values):
    """
    A Values whose values are directly specified by an iterable object.
    """
    def __init__(self, values):
        """
        values: a list of possible values
        """
        self.values = values

    def __iter__(self):
        return iter(self.values)

class InstanceArgsFormatter(object):
    """
    A string formatter for an InstanceArgs e.g., one full command line.
    """

    @abstractmethod 
    def format(self, instance_args):
        """
        instance_args: an InstanceArgs representing an instance of the command
            line.
        """
        raise NotImplementedError()

    def __call__(self, instance_args):
        return self.format(instance_args)

class ValueFormatter(object):
    """
    An abstract class representing a formatter for one value.
    Each formatting method (e.g., format_*) returns a formmatted value of type
    string.
    """
    @abstractmethod
    def format_float(self, value):
        raise NotImplementedError()

    @abstractmethod 
    def format_list(self, value):
        raise NotImplementedError()

    def __call__(self, value):
        return self.format_value(value)

    def format_value(self, value):
        """
        Classify into its correct type and call the right format_* method.
        If the type is unclear, simply call str(.) and return its value.
        """
        if isinstance(value, float):
            return self.format_float(value)
        elif isinstance(value, list):
            return self.format_list(value)
        else:
            # type is unknown. The following line may fail.
            return str(value)

class VFArgParse(ValueFormatter):
    """
    A ValueFormatter which is suitable for normal use of argparse.
    """
    def __init__(self, float_format='{}', list_open='', list_close='', list_value_sep=', '):
        """
        float_format: string format (used with string.format) for
            floating-point values.
        list_open: a string representing the openning of value of type list.
            Could be '(', or '[' or others.
        list_close: a string representing the closing of value of type list.
            Could be ')', or ']' or others.
        list_value_sep: a string to separate entries in a list
        """
        self.float_format = float_format
        self.list_open = list_open
        self.list_close = list_close
        self.list_value_sep = list_value_sep

    def format_float(self, value):
        return self.float_format.format(value)

    def format_list(self, value):
        if not isinstance(value, list):
            raise ValueError('value should be a list. Was {}'.format(value))
        list_formatted = [self.format_value(v) for v in value]
        s = self.list_open + self.list_value_sep.join(list_formatted) + self.list_close
        return s

class IAFArgparse(InstanceArgsFormatter):
    """
    An InstanceArgsFormatter which renders into a string command line that
    mimics what argparse module takes as an input.
    """
    def __init__(self, pv_sep=' ', pv_prefix='', pv_suffix='',
                 value_formatter=VFArgParse()):
        """
        pv_sep: a string separator between two parameter-value pairs
        pv_prefix: string to print before each parameter-value pair
        pv_suffix: string to print after each parameter-value pair
        value_formatter: a ValueFormatter to format values
        """
        self.pv_sep = pv_sep
        self.pv_prefix = pv_prefix
        self.pv_suffix = pv_suffix
        self.value_formatter = value_formatter

    def format(self, instance_args):
        # list of (Param, value)'s
        pvs = instance_args.pvs
        name_values = []
        for p,v in pvs:
            # not None => user specifies what to output
            out_name = p.output if p.output is not None else '--'+p.key
            formatted_v = self.value_formatter(v)
            entry = '{}{} {}{}'.format(self.pv_prefix, out_name, formatted_v, self.pv_suffix)
            name_values.append(entry)
            
        s = self.pv_sep.join(name_values)
        return s

class ArgsProcessor(object):
    """
    Abstract class.  A processor that iterates over all InstanceArgs in an Args
    and outputs them in some way.
    """
    @abstractmethod
    def process_args(self, args):
        '''
        args: an instance of Args
        '''
        raise NotImplementedError('Subclasses should implement this method')

    def __call__(self, args):
        return self.process_args(args)


class APPrint(ArgsProcessor):
    """
    An ArgsProcessor that prints each command (InstanceArgs) to the stdout.
    """
    def __init__(self, iaf=IAFArgparse(), prefix='', suffix='\n'):
        '''
        iaf: an InstanceArgsFormatter to format each line
        prefix: string to prepend to each output line
        suffix: string to append to each output line
        '''
        self.iaf = iaf
        self.prefix = prefix
        self.suffix = suffix

    def process_args(self, args):
        for ar in args:
            assert isinstance(ar, InstanceArgs)
            line = self.prefix + self.iaf(ar) + self.suffix
            sys.stdout.write(line)

class APPerBashFile(ArgsProcessor):
    """
    An ArgsProcessor that prints each command (InstanceArgs) to one Bash script
    file. One use is for creating submission files to a computing cluster.
    """
    def __init__(self, dirpath, create_run_token=False, iaf=IAFArgparse(),
                 file_begin='', file_end='', line_begin='', line_end='',
                 fname_func=None):
        '''
        dirpath: string denoting the path to a directory to contain the
            generated files.
        create_run_token: if True, wrap the command with if ... fi so that the
            command is run only when its token file does not exist. A token
            file is created when the command is successfully executed.
        iaf: an InstanceArgsFormatter to format each InstanceArgs (line)
        file_begin: string to include at the beginning of each file.
        file_end: string to include at the end of each file.
        line_begin: string to include at the beginning of each line
        line_end: string to include at the end of each line
        fname_func: a callable InstanceArgs -> string which turns an
            InstanceArgs into string for naming each file. If not specified,
            use SHA1 to hash InstanceArgs. Set extension to .sh.
        '''
        if os.path.isfile(dirpath):
            raise ValueError('The specified dirpath is a file: {}. Has to be a directory'.format(dirpath))
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

        self.dirpath = dirpath
        self.create_run_token = create_run_token
        self.iaf = iaf
        self.file_begin = file_begin
        self.file_end = file_end
        self.line_begin = line_begin
        self.line_end = line_end
        if fname_func is None:
            def hash_instanceargs(ia, extension='.sh'):
                # turn the InstanceArgs into string
                ia_str = iaf.format(ia)
                # hash
                h = util.simple_object_hash(ia_str)
                h = h[:14]
                return h + extension
            fname_func = hash_instanceargs

        self.fname_func = fname_func

    def _wrap_bash_token_block(self, content, token_fname):
        """
        Wrap the string content with  the token block (i.e., only execute if
        the token file does not exist).
        Return a string
        """
        template =  \
        '''
if [ ! -f {} ]; then

{}

    if [ $? -eq 0 ]; then
        touch {}
    fi
fi
        '''
        wrap = template.format(token_fname, content, token_fname)
        return wrap

    # def _get_file_content(self, ia):
    #     """
    #     ia: InstanceArgs
    #     """
    #     # form the file content
    #     cmd = self.iaf(ia)
    #     line = self.line_begin + cmd + self.line_end
    #     # print(cmd)
    #     content = self.file_begin + os.linesep + line + os.linesep + self.file_end
    #     return content

    def process_args(self, args):
        '''
        args: an instance of Args

        Write a file for each InstanceArgs in args.
        '''
        for ia in args:
            assert isinstance(ia, InstanceArgs)
            cmd = self.iaf(ia)
            line = self.line_begin + cmd + self.line_end

            # get the file name to write to
            fname = self.fname_func(ia)
            if self.create_run_token:
                token_fname = fname + '.token'
                token_fpath = os.path.abspath( os.path.join(self.dirpath, token_fname) )
                line = self._wrap_bash_token_block(line, token_fpath)

            content = self.file_begin + os.linesep + line + os.linesep + self.file_end
            # write to file
            fpath = os.path.join(self.dirpath, fname)
            with open(fpath, 'w') as f:
                f.write(content)


# class PV(object):
#     """
#     A Param-Values pair. This forms the basis of everything. A PV completely
#     specifies a parameter and its candidate values to vary.
#     """
#     def __init__(self, param, values):
#         if not isinstance(param, Param):
#             raise ValueError('param has to be of type {}'.format(str(Param)))
#         if not isinstance(values, Values):
#             raise ValueError('values has to be of type {}'.format(str(Values)))
#         self.param = param
#         self.values = values


# class RenderUnit(object):
#     """
#     One unit to render with a formatter. A typical example is a Param-value
#     pair.
#     """
#     @abstractmethod
#     def render(self, *args, **kwargs):
#         pass

class ParamUnit(object):
    '''
    The smallest meaningful unit to be rendered.  An example is a Param-value
    pair.
    '''
    @abstractmethod
    def __iter__(self):
        '''
        An iterable whose iterator returns a list [(p, v)] where p is a 
        ParamUnit and v is one value (not Values). Iterate over all candidate
        values.
        '''
        pass


class ParamGroup(ParamUnit):
    """
    A group of parameters. Values are specified jointly so no permutation
    within the values of the parameters in this group.
    """
    def __init__(self, keys, values, outputs=None):
        '''
        keys: a list of names (strings) for referring to ths parameters.
        values: a Values. Each returned object from the iterator has to be a
            tuple. The length of each tuple is the same as the length of keys.
        outputs: the names of the parameters to output.
        '''
        if not keys:
            raise ValueError('keys cannot be empty. Was {}'.format(keys))
        self.keys = keys
        self.values = values
        if not isinstance(values, collections.Iterable):
            raise ValueError('values has to be iterable. Was {}'.format(values))
        if outputs is not None:
            assert len(keys)==len(outputs)
        self.outputs = outputs

    def __iter__(self):
        n = len(self.keys)
        for v in self.values:
            # v is a tuple of values
            if len(v) != n:
                raise ValueError('Number of keys ({}) does not match the lenght of tuple of values ({})'.format(n, len(v)))
            l = []
            for i in range(n):
                valuesi = InGroupValues(self.values, i)
                outi = None if self.outputs is None else self.outputs[i]
                parami = Param(self.keys[i], valuesi, output=outi)
                l.append( (parami, v[i]) )
            yield l



class Param(ParamUnit):
    """
    A parameter in a list of arguments.
    """
    def __init__(self, key, values, output=None):
        '''
        key: a name for referring to this parameter 
        values: a Values object representing possible values for this parameter.
            If values is a list, automatically wrap it with ValFixedIter
        output: the name to output. 
        '''
        if isinstance(values, list):
            values = ValFixedIter(values)
        if not key:
            raise ValueError('key cannot be empty. Was {}'.format(key))
        self.key = key
        if not isinstance(values, collections.Iterable):
            raise ValueError('values has to be iterable. Was {}'.format( values))
        
        self.values = values
        self.output = output

    def __iter__(self):
        for v in self.values:
            yield [(self, v)]

    # def render(self, value, formatter):
    #     '''
    #     Render this parameter and its value with the formatter.
    #     Return a string.
    #     '''
    #     pass


class Args(object):
    """
    A list of parameter (string)-Values pairs in order.
    """
    def __init__(self, param_units):
        '''
        param_units: a list of ParamUnit's (e.g., Param, ParamGroup)
        '''
        self.param_units = param_units

    @staticmethod
    def flatten(*lists):
        L = []
        for l in lists:
            L.extend(l)
        
        return L

    def __iter__(self):
        """
        Return an iterator where each call to next() returns an InstanceArgs.
        """
        # iterate over all the ParamUnit's
        # iter_list = itertools.zip_longest(*self.param_units)
        iter_list = itertools.product(*self.param_units)
        # Each next() returns a tuple of lists. Flatten everything into a single list
        # print('check iter_list')
        # for x in iter_list:
        #     print(x)
        iter_flat = itertools.starmap(Args.flatten, iter_list)
        for L in iter_flat:
            # L is a flat list
            # print('yielding ia')
            ia = InstanceArgs(L)
            yield ia

class InstanceArgs(object):
    """
    A list of parameter-value pairs. Specifically, represent [(p, v)] where p
    is a Param and v is one value supported by the ParamUnit.
    """
    def __init__(self, pvs):
        '''
        pvs: the list [(p,v)]
        '''
        # print(pvs)
        self.pvs = pvs


#---------------------------------------

