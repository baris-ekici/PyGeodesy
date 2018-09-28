
# -*- coding: utf-8 -*-

# Script to run some or all PyGeodesy tests with Python 2 or 3.

# Tested with 64-bit Python 2.6.9, 2.7,13, 3.5.3, 3.6.4, 3.6.5 and
# 3.7.0 on macOS 10.12 Sierra and 10.13 High Sierra and with
# Pythonista 3.1 and 3.2 on iOS 10.3, 11.0, 11.1, 11.3 and 11.4.

from glob import glob
from os import environ, linesep as NL
from os.path import abspath, basename, dirname, join
from time import time
import sys

_test_dir = dirname(abspath(__file__))
# extend sys.path to include the .. directory
if _test_dir not in sys.path:
    sys.path.insert(0, _test_dir)

from base import isiOS, PyGeodesy_dir, PythonX, \
          secs2str, tilde, versions  # PYCHOK expected

__all__ = ('run2',)
__version__ = '18.09.25'

if isiOS:

    try:  # prefer StringIO over io
        from StringIO import StringIO
    except ImportError:  # Python 3+
        from io import StringIO
    from runpy import run_path
    from traceback import format_exception

    def run2(test):
        '''Invoke one test module and return
           the exit status and console output.
        '''
        # Mimick partial behavior of function runner
        # further below because subprocess.Popen is
        # not available on iOS/Pythonista/Python.
        # One issue however, the test script is
        # imported and run in the same process.

        x = None  # no exit, no exception

        sys3 = sys.argv, sys.stdout, sys.stderr
        sys.stdout = sys.stderr = std = StringIO()
        try:
            sys.argv = [test]
            run_path(test, run_name='__main__')
        except:  # PYCHOK have to on Pythonista
            x = sys.exc_info()
            if x[0] is SystemExit:
                x = x[1].code  # exit status
            else:  # append traceback
                x = [t for t in format_exception(*x)
                             if 'runpy.py", line' not in t]
                print(''.join(map(tilde, x)).rstrip())
                x = 1  # count as a failure
        sys.argv, sys.stdout, sys.stderr = sys3

        r = std.getvalue()
        if isinstance(r, bytes):  # Python 3+
            r = r.decode('utf-8')

        std.close()
        std = None  # del std

        if x is None:  # no exit status or exception:
            # count failed tests excluding KNOWN ones
            x = r.count('FAILED, expected')
        return x, r

    Python_O = basename(PythonX)

else:  # non-iOS

    from subprocess import PIPE, STDOUT, Popen

    def run2(test):  # PYCHOK expected
        '''Invoke one test module and return
           the exit status and console output.
        '''
        if __debug__:
            c = [PythonX, test]
        else:
            c = [PythonX, '-O', test]
        p = Popen(c, creationflags=0,
                     executable   =sys.executable,
                   # shell        =True,
                     stdin        =None,
                     stdout       =PIPE,  # XXX
                     stderr       =STDOUT)  # XXX

        r = p.communicate()[0]
        if isinstance(r, bytes):  # Python 3+
            r = r.decode('utf-8')

        # the exit status reflects the number of
        # test failures in the tested module
        return p.returncode, r

    # replace home dir with ~
    Python_O = PythonX.replace(environ.get('HOME', '~'), '~')

if not debug__:
    Python_O += ' -O'
# shorten Python path [-OO]
if len(Python_O) > 32:
    Python_O = Python_O[:16] + '...' + Python_O[-16:]

# command line options
_failedonly = False
_raiser     = False
_results    = False  # or file
_verbose    = False

_T = 0  # total tests
_X = 0  # failed tests


def _exit(last, text, exit):
    '''(INTERNAL) Close and exit.
    '''
    print(last)
    if _results:
        _write(NL + text + NL)
        _results.close()
    sys.exit(exit)


def _run(test):
    '''(INTERNAL) Run a test script and parse the result.
    '''
    global _T, _X

    t = 'running %s %s' % (Python_O, tilde(test))
    print(t)

    x, r = run2(test)
    if _results:
        _write(NL + t + NL)
        _write(r)

    _T += r.count(NL + '    test ')  # number of tests
    _X += x  # failures, excluding KNOWN ones

    if 'Traceback' in r:
        print(r + NL)
        if not x:  # count as failure
            _X += 1
        if _raiser:
            raise SystemExit

    elif _failedonly:
        for t in r.split(NL):
            # print failures, KNOWN ones and totals
            if 'FAILED,' in t or 'passed' in t or 'SKIPPED' in t:
                print(t.rstrip())
        print('')

    elif _verbose:
        print(r + NL)

    elif x:
        for t in r.split(NL):
            # print failures, without KNOWN ones
            if 'FAILED,' in t and 'KNOWN' not in t:
                print(t.rstrip())


def _write(text):
    '''(INTERNAL) Write text to results.
    '''
    _results.write(text.encode('utf-8'))


if __name__ == '__main__':  # MCCABE 16

    argv0, args = tilde(sys.argv[0]), sys.argv[1:]

    while args and args[0].startswith('-'):
        arg = args.pop(0)
        if '-help'.startswith(arg):
            print('usage: %s [-failedonly] [-raiser] [-results] [-verbose] [test/test...py ...]' % (argv0,))
            sys.exit(0)
        elif '-failedonly'.startswith(arg):
            _failedonly = True
        elif '-raiser'.startswith(arg):
            _raiser = True  # break on error
        elif '-results'.startswith(arg):
            _results = True
        elif '-verbose'.startswith(arg):
            _verbose = True
        else:
            print('%s invalid option: %s' % (argv0, arg))
            sys.exit(1)

    if not args:  # no tests specified, get all test*.py
        # scripts in the same directory as this one
        args = sorted(glob(join(_test_dir, 'test[A-Z]*.py')))

    # PyGeodesy and Python versions, size, OS name and release
    v = versions()

    if _results:  # save all test results
        t = '-'.join(['testresults'] + v.split()) + '.txt'
        t = join(PyGeodesy_dir, 'testresults', t)
        _results = open(t, 'wb')  # note, 'b' not 't'!
        _write('%s typical test results (%s)%s' % (argv0, v, NL))

    s = time()
    try:
        for arg in args:
            _run(arg)
    except KeyboardInterrupt:
        _exit('', '^C', 9)
    except SystemExit:
        pass
    s = secs2str(time() - s)

    if _X:
        x = '%d FAILED' % (_X,)
    elif _T > 0:
        x = 'all %s tests OK' % (_T,)
    else:
        x = 'all OK'

    t = '%s %s %s (%s) %s' % (argv0, Python_O, x, v, s)
    _exit(t, t, 0)
