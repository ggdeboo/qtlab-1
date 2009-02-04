# gnuplotpipe.py, class for communicating with gnuplot through a pipe.
# Reinier Heeres <reinier@heeres.eu>
#
# On Windows you will need gnuplot 4.3.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import subprocess
import select
import re
import time
import ctypes

class WinPipe():
    '''
    Class to perform line-based, non-blocking reads from a win32 file.
    '''

    def __init__(self, fd):
        self._peek_named_pipe = ctypes.windll.kernel32.PeekNamedPipe

        self._fd = fd
        self._buf = ''
        self._maxsize = 1024

    def _get_buffer(self):
        try:
            import msvcrt
            handle = msvcrt.get_osfhandle(self._fd.fileno())
            avail = ctypes.c_ulong(0)
            self._peek_named_pipe(handle, None, 0, None, ctypes.byref(avail), None)
            avail = avail.value
            avail = min(avail, self._maxsize)
            if avail > 0:
                data = self._fd.read(avail)
                self._buf += data
                return True
            return False
        except Exception, e:
            print 'Error: %s' % str(e)
            return False

    def readline(self, delay=0):
        '''Return a \n terminated line, if available.'''

        start = time.time()
        firsttime = True

        while firsttime or (time.time() - start) < delay:
            self._get_buffer()
            index = self._buf.find('\n')
            if index != -1:
                ret = self._buf[:index]
                self._buf = self._buf[index+1:]
                ret = ret.rstrip('\r\n')
                ret += '\n'
                return ret
            firsttime = False
            time.sleep(delay / 10.0)

        return None

class GnuplotPipe():
    '''
    Class for a two-way pipe interface with gnuplot.
    '''

    _RE_TERMINAL = re.compile('terminal type is (\w*) (.*)')
    _RE_PALETTE = {
        'type': re.compile('palette is (.*)\n'),
        'gamma': re.compile('gamma is (.*)\n'),
        'rgbformulae': re.compile('rgbformulae are (.*),(.*),(.*)\n'),
        'model': re.compile('Color-Model: (.*)\n'),
        'figure': re.compile('figure is (.*)\n'),
        }
    _RE_RANGE = re.compile('set .*range \[ (.*) : (.*) \] .*\n')
    _RE_LOG = re.compile('(\w+) \(base ([^\)]*)\)')
    _RE_LABEL = re.compile('.*label is "[\"]"')

    def __init__(self, persist=False):
        args = ['gnuplot']
        if persist:
            args.append('-persist')
        self._popen = subprocess.Popen(args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

        if subprocess.mswindows:
            self._winpipe = WinPipe(self._popen.stderr)

        # Wait a bit for gnuplot to start
        self.readline(0.5)
        self.flush_output()

        self._default_terminal = self.get_terminal()

    def is_alive(self):
        '''Check whether the gnuplot instance is alive.'''
        return self._popen.poll() == None

    if subprocess.mswindows:
        def readline(self, delay=0):
            line = self._winpipe.readline(delay)
            return line

    else:
        def readline(self, delay=0):
            rlist = [self._popen.stderr]
            elist = []
            lists = select.select(rlist, elist, elist, delay)
            if len(lists[0]) == 0:
                return None
            line = self._popen.stderr.readline()
            return line

    def get_output(self, delay=0.05):
        '''Read output from gnuplot, waiting at most <delay> seconds.'''

        ret = ''
        i = 0
        while i < 1000:
            line = self.readline(delay)
            if line is None:
                break
            ret += line
            i += 1

        return ret

    def flush_output(self, delay=0):
        '''Flush gnuplot stdout.'''
        self.get_output(delay)

    def cmd(self, cmd, retoutput=False, delay=0.05):
        '''Execute a gnuplot command, optionally returning output.'''

        # End with newline
        if len(cmd) > 0 and cmd[-1] != '\n':
            cmd += '\n'

        if retoutput:
            self.flush_output()
        self._popen.stdin.write(cmd)
        if retoutput:
            return self.get_output()
        return None

    def is_responding(self, delay=0.01):
        self.flush_output()
        ret = self.cmd('print 0', True, delay)
        if ret is None or len(ret) == 0:
            return False
        return True

    def get_terminal(self):
        '''Set terminal info as (type, options) tuple.'''

        output = self.cmd('show terminal\n', True)
        m = self._RE_TERMINAL.search(output)
        if m is not None:
            return m.groups()
        return None

    def set_terminal(self, termtype, options=''):
        '''Set a terminal.'''
        output = self.cmd('set terminal %s %s\n' % (termtype, options))
        return None

    def get_default_terminal(self):
        '''Return default terminal info as (type, options) tuple.'''
        return self._default_terminal

    def get_palette_info(self):
        '''Return a dictionary with info about the current palette.'''

        ret = {}
        output = self.cmd('show palette\n', True)
        for key, regexp in self._RE_PALETTE.iteritems():
            m = regexp.search(output)
            if m is not None:
                if len(m.groups()) == 1:
                    ret[key] = m.group(1)
                else:
                    ret[key] = m.groups()
        return ret

    def get_range(self, axis):
        '''
        Return the range for a given axis as a tuple.
        '*' indicates auto-range.
        '''

        cmd = 'show %srange\n' % axis
        output = self.cmd(cmd, True)
        m = self._RE_RANGE.search(output)
        if m is not None:
            return m.groups()
        return None

    def get_label(self, axis):
        '''Return the label for a given axis.'''

        cmd = 'show %slabel\n' % axis
        output = self.cmd(cmd, True)
        m = self._RE_LABEL.search(output)
        if m is not None:
            return m.groups()
        return None

    def get_log_axes(self):
        '''
        Return which axes are logarithmic. The result is a dictionary with the
        axes as the key and the logarithm base in the value.
        '''

        cmd = 'show log\n'
        output = self.cmd(cmd, True)
        ret = {}
        for m in self._RE_LOG.finditer(output):
            ret[m.group(1)] = m.group(2)
        return ret

    def is_log_axis(self, axis):
        '''Return whether axis <axis> has a logarithmic scale.'''

        logaxes = self.get_log_axes()
        if logaxes is None:
            return False
        return (axis in logaxes)

    def set_var(self, var, val):
        self.cmd('var=%s' % val)

    def get_var(self, var):
        output = self.cmd('print %s' % var)
        if output is None:
            return None
        return output.rstrip('\r\n')

    def live(self):
        print 'Entering gnuplot live mode, enter "q(uit)" or CTRL-d to quit'
        exit_cmds = ('q', 'quit', 'exit')
        while True:
            try:
                input = raw_input('>>>')
            except EOFError:
                return
            if input in exit_cmds:
                return
            reply = self.cmd(input, True)
            print reply