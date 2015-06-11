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
from ctypes import cdll, c_int, c_char_p, byref, Structure, c_double, c_uint, POINTER
from numpy import asarray, average, ndarray, zeros, float32

comedi = cdll.LoadLibrary("libcomedi.so")

class comedi_range(Structure):
    _fields_ = [("min", c_double),
                ("max", c_double),
                ("unit", c_uint)]

lsampl_t = c_uint

comedi.comedi_get_range.restype = POINTER(comedi_range)
comedi.comedi_get_board_name.restype = c_char_p
comedi.comedi_to_phys.restype = c_double
comedi.comedi_from_phys.restype = lsampl_t

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
        self._device = comedi.comedi_open(id)
        self._boardname = comedi.comedi_get_board_name(self._device)
        self._nsubdevices = comedi.comedi_get_n_subdevices(self._device)
        print('This device has %i subdevices.' % self._nsubdevices)
        self._nchannels = []
        for subdevice in range(self._nsubdevices):
            self._nchannels.append(comedi.comedi_get_n_channels(self._device, subdevice))
        print self._nchannels

        if self._device is None:
            logging.warning('USB_DUX not created successfully')

        for ch_in in range(self._nchannels[0]):
            # get the first range for the channels, should be [-4.096, 4.096]
            range_struct = comedi.comedi_get_range(self._device, 0, ch_in, 0)
            self.add_parameter(('ai%i'%ch_in),
                flags=Instrument.FLAG_GET,
                type=ndarray,
                units='V',
                tags=['measure'],
                get_func=self.do_get_input,
                channel=ch_in,
                minval=range_struct.contents.min,
                maxval=range_struct.contents.max
                )

        for ch_in in range(self._nchannels[1]):
            # get the first range for the channels, should be [-4.096, 4.096]
            range_struct = comedi.comedi_get_range(self._device, 1, ch_in, 0)
            self.add_parameter(('ao%i'%ch_in),
                flags=Instrument.FLAG_GETSET,
                type=types.FloatType,
                units='V',
                tags=['measure'],
                get_func=self.do_get_output,
                set_func=self.do_set_output,
                channel=ch_in,
                minval=range_struct.contents.min,
                maxval=range_struct.contents.max
                )

        self._default_input_range = comedi.comedi_get_range(self._device, 0, 0, 0)
        self._default_input_maxdata = lsampl_t(4095)

        self._default_output_range = comedi.comedi_get_range(self._device, 1, 0, 0)
        self._default_output_maxdata = lsampl_t(4095)

        self.get_all()

    def do_get_input(self, channel, samples=1, averaged=False):
        '''Get the value of the analog input'''
        if samples == 1:
            raw_data = c_uint()
            rc = comedi.comedi_data_read(self._device, 
                                                0, channel, 0, 0,
                                                byref(raw_data))
            data = comedi.comedi_to_phys(lsample_t(raw_data.value),
                                    self._default_input_range,
                                    self._default_input_maxdata)
        elif samples > 1:
            raw_data_type = c_uint * samples
            raw_data = raw_data_type()
            rc = comedi.comedi_data_read_n(self._device,
                                                0, channel, 0, 0, 
                                                byref(raw_data),
                                                samples)
            # make a numpy array from the c array
            if rc == 0: # success
                data = zeros((samples),dtype=float32)
                for idx, value in enumerate(raw_data):
                    data[idx] = comedi.comedi_to_phys(value,
                                        self._default_input_range,
                                        self._default_input_maxdata)
                if averaged:
                    return average(data)
            else:
                logging.warning('Reading of multiple samples failed.')
                return False
        else:
            logging.warning('Invalid number of samples requested')
            return False
        return data

    def do_get_output(self, channel):
        raw_data = c_uint()
        rc = comedi.comedi_data_read(self._device, 1, channel, 0, 0,
                                                byref(raw_data))
        data = comedi.comedi_to_phys(lsample_t(raw_data.value),
                                    self._default_output_range,
                                    self._default_output_maxdata)
        return float(data)

    def do_set_output(self, output_value, channel):
        '''Set the output of an analog channel'''
        set_value = comedi.comedi_from_phys(c_double(output_value),
                                    self._default_output_range,
                                    self._default_output_maxdata)             
        rc = comedi.comedi_data_write(self._device, 1, channel, 0, 0, set_value)
        if rc == 1: 
            return True
        else:
            return False
        

        
    def get_all(self):
        ch_in = ['ai0','ai1','ai2','ai3','ai4','ai5','ai6','ai7']
        self.get(ch_in)
        ch_out = ['ao0','ao1','ao2','ao3']
        self.get(ch_out)
