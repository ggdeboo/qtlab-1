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
import logging
from numpy import asarray, average, ndarray

from lib.dll_support import comedi as comedi_lib

class USB_DUX(Instrument):
    '''
    Class implementing the USB_DUX instrument

    The USB-DUX-D operated using the comedi driver has 5 subdevices:
        0 : analog input    8 channels  12 bits
        1 : analog output   4 channels  12 bits
        2 : digital I/O     8 channels
        3 : counter         4 channels  max value 65535
        4 : pwm             8 channels  max value 512

    '''

    def __init__(self, name, id):
        Instrument.__init__(self, name, tags=['physical'])

        self._id = id
        self._device = comedi_lib.open(id)
        self._boardname = comedi_lib.get_board_name(self._device)
        self._nsubdevices = comedi_lib.get_n_subdevices(self._device)

        print('This device has %i subdevices.' % self._nsubdevices)
        self._nchannels = []
        for subdevice in range(self._nsubdevices):
            self._nchannels.append(comedi_lib.get_n_channels(self._device, 
                                                                subdevice))
        if self._device is None:
            logging.warning('USB_DUX not created successfully')

        for ch_in in range(self._nchannels[0]):
            # get the first range for the channels, should be [-4.096, 4.096]
            channel_range = comedi_lib.get_range(self._device, 0, ch_in, 0)
            self.add_parameter(('ai%i'%ch_in),
                flags=Instrument.FLAG_GET,
                type=ndarray,
                units='V',
                tags=['measure'],
                get_func=self.do_get_input,
                channel=ch_in,
                minval=channel_range.min,
                maxval=channel_range.max
                )

        for ch_in in range(self._nchannels[1]):
            # get the first range for the channels, should be [-4.096, 4.096]
            channel_range = comedi_lib.get_range(self._device, 1, ch_in, 0)
            self.add_parameter(('ao%i'%ch_in),
                flags=Instrument.FLAG_GETSET,
                type=types.FloatType,
                units='V',
                tags=['measure'],
                get_func=self.do_get_output,
                set_func=self.do_set_output,
                channel=ch_in,
                minval=channel_range.min,
                maxval=channel_range.max
                )

        # The following settings should be made changeable in the future
        self._default_input_range = comedi_lib.get_range_struct(self._device, 
                                                                0, 0, 0)
        self._default_input_maxdata = comedi_lib.lsampl_t(4095)
        self._default_output_range = comedi_lib.get_range_struct(self._device, 
                                                                1, 0, 0)
        self._default_output_maxdata = comedi_lib.lsampl_t(4095)

        self.get_all()

    def do_get_input(self, channel, samples=1, averaged=False):
        '''Get the value of the analog input'''
        if samples == 1:
            raw_data = comedi_lib.data_read(self._device, 
                                                0, channel, 0, 0)
            data = comedi_lib.convert_to_phys(raw_data,
                                    self._default_input_range,
                                    self._default_input_maxdata)
            return data
        elif samples > 1:
            data =  comedi_lib.data_read_n(self._device,
                                                0, channel, 0, 0, 
                                                samples)
            if averaged:
                return average(data)
            else:
                return data
        else:
            logging.warning('Invalid number of samples requested')
            return False

    def do_get_output(self, channel):
        raw_data = comedi_lib.data_read(self._device, 1, channel, 0, 0)
        data = comedi_lib.convert_to_phys(raw_data,
                                    self._default_output_range,
                                    self._default_output_maxdata)
        return float(data)

    def do_set_output(self, output_value, channel):
        '''Set the output of an analog channel'''
        set_value = comedi_lib.convert_from_phys(output_value,
                                    self._default_output_range,
                                    self._default_output_maxdata)             
        comedi_lib.data_write(self._device, 1, channel, 0, 0, set_value)
        
    def get_all(self):
        ch_in = ['ai0','ai1','ai2','ai3','ai4','ai5','ai6','ai7']
        self.get(ch_in)
        ch_out = ['ao0','ao1','ao2','ao3']
        self.get(ch_out)
