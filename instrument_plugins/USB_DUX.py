# USB_DUX.py 
# Gabriele de Boo <ggdeboo@gmail.com>
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

import types
from instrument import Instrument
import qt
import comedi
import logging

class USB_DUX(Instrument):

    def __init__(self, name, id):
        Instrument.__init__(self, name, tags=['physical'])

        self._id = id
        self._device = comedi.comedi_open(id)
        self._boardname = comedi.comedi_get_board_name(self._device)
        self._nsubdevices = comedi.comedi_get_n_subdevices(self._device)
        print('This device has %i subdevices.' % self._nsubdevices)
        self._nchannels = []
        for subdevice in range(self._nsubdevices):
            self._nchannels.append(comedi.comedi_get_n_channels(self._device, subdevice))
        print self._nchannels

        print comedi.comedi_get_range(self._device, 0, 0, 0)

        if self._device is None:
            logging.warning('USB_DUX not created successfully')

        for ch_in in range(self._nchannels[0]):
            range_struct = comedi.comedi_get_range(self._device, 0, ch_in, 0)
            self.add_parameter(('input_%i'%ch_in),
                flags=Instrument.FLAG_GET,
                type=types.IntType,
                units='V',
                tags=['measure'],
                get_func=self.do_get_input,
                channel=ch_in,
                minval=range_struct.min,
                maxval=range_struct.max)

        for ch_in in range(self._nchannels[1]):
            range_struct = comedi.comedi_get_range(self._device, 1, ch_in, 0)
            self.add_parameter(('output_bipolar_%i'%ch_in),
                flags=Instrument.FLAG_GET,
                type=types.IntType,
                units='V',
                tags=['measure'],
                get_func=self.do_get_output_unipolar,
                channel=ch_in,
                minval=range_struct.min,
                maxval=range_struct.max)

        for ch_in in range(self._nchannels[3]):
            range_struct = comedi.comedi_get_range(self._device, 3, ch_in, 0)
            self.add_parameter(('output_unipolar_%i'%ch_in),
                flags=Instrument.FLAG_GET,
                type=types.IntType,
                units='V',
                tags=['measure'],
                get_func=self.do_get_output_bipolar,
                channel=ch_in,
                minval=range_struct.min,
                maxval=range_struct.max)

    def do_get_input(self, channel):
        rc, raw_data = comedi.comedi_data_read(self._device, 0, channel, 0, 0)
        return data

    def do_get_output(self, subdevice, channel):
        rc, data = comedi.comedi_data_read(self._device, 1, channel, 0, 0)
        return data

    def do_get_output_bipolar(self, channel):
        rc, data = comedi.comedi_data_read(self._device, 1, channel, 0, 0)
        return data

    def do_get_output_unipolar(self, channel):
        rc, data = comedi.comedi_data_read(self._device, 3, channel, 0, 0)
        return data
        
#    def get_all(self):
#        ch_in = [_get_channel(ch) for ch in self._get_input_channels()]
#        self.get(ch_in)

#    def reset(self):
#        '''Reset device.'''
#        nidaq.reset_device(self._id)

#    def _get_input_channels(self):
#        return nidaq.get_physical_input_channels(self._id)

#    def _get_output_channels(self):
#        return nidaq.get_physical_output_channels(self._id)

#    def _get_counter_channels(self):
#        return nidaq.get_physical_counter_channels(self._id)

#    def do_get_input(self, channel):
#        devchan = '%s/%s' % (self._id, channel)
#        return nidaq.read(devchan, config=self._chan_config)

#    def do_set_output(self, val, channel):
#        devchan = '%s/%s' % (self._id, channel)
#        return nidaq.write(devchan, val)

#    def do_set_chan_config(self, val):
#        self._chan_config = val

#    def do_set_count_time(self, val):
#        self._count_time = val

#    def do_get_counter(self, channel):
#        devchan = '%s/%s' % (self._id, channel)
#        src = self.get(channel + "_src")
#        if src is not None and src != '':
#            src = '/%s/%s' % (self._id, src)
#        return nidaq.read_counter(devchan, src=src, freq=1/self._count_time)

#    def read_counters(self, channels):
#        chans = []
#        srcs = []
#        for chan in channels:
#            chans.append('%s/%s' % (self._id, chan))
#            srcs.append(self.get(chan + "_src"))
#        return nidaq.read_counters(chans, src=srcs, freq=1.0/self._count_time)

#    # Dummy
#    def do_set_counter_src(self, val, channel):
#        return True
#
#    def digital_out(self, lines, val):
#        devchan = '%s/%s' % (self._id, lines)
#        return nidaq.write_dig_port8(devchan, val)

#def detect_instruments():
#    '''Refresh NI DAQ instrument list.'''
#
#    for name in nidaq.get_device_names():
#        qt.instruments.create('NI%s' % name, 'NI_DAQ', id=name)

