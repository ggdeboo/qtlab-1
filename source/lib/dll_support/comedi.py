import ctypes
from numpy import zeros, float32

comedi = ctypes.cdll.LoadLibrary("libcomedi.so")

class comedi_range(ctypes.Structure):
      _fields_ = [("min", ctypes.c_double),
                ("max", ctypes.c_double),
                ("unit", ctypes.c_uint)] 

lsampl_t = ctypes.c_uint

comedi.comedi_get_range.restype = ctypes.POINTER(comedi_range)
comedi.comedi_get_board_name.restype = ctypes.c_char_p
comedi.comedi_to_phys.restype = ctypes.c_double
comedi.comedi_from_phys.restype = lsampl_t

def convert_to_phys(data_value, channel_range, maxdata):
    '''Converts a data_value to a physical value.

    Input:
        data_value 
        channel_range : comedi_range class
        maxdata

    Output:
        float
    '''
    return comedi.comedi_to_phys(lsampl_t(data_value),
                        channel_range, 
                        maxdata)

def convert_from_phys(physical_value, channel_range, maxdata):
    '''returns a c_double with the number that can be used by data_write'''
    return comedi.comedi_from_phys(ctypes.c_double(physical_value),
                                    channel_range,
                                    maxdata)

def data_read(device, subdevice, channel, channel_range, aref):
    '''Return a single reading'''
    raw_data = ctypes.c_uint()
    rc = comedi.comedi_data_read(device,
                                    subdevice,
                                    channel,
                                    channel_range, # int
                                    aref,
                                    ctypes.byref(raw_data))
    if rc == 1:
        return raw_data.value
    else:
        logging.warning('data_read was not successful')
        return False

def data_read_n(device, subdevice, channel, channel_range, aref, samples):
    '''Return multiple reading
    This function returns unevenly spaced readings in a single numpy array
    '''
    raw_data_type = ctypes.c_uint * samples
    raw_data = raw_data_type()
    channel_range_struct = get_range_struct(device,
                                    subdevice,
                                    channel,
                                    channel_range)
    channel_max_data = get_max_data(device,
                                    subdevice,
                                    channel)
    rc = comedi.comedi_data_read_n(device,
                                    subdevice,
                                    channel,
                                    channel_range, # int
                                    aref,
                                    ctypes.byref(raw_data),
                                    samples)
    if rc == 0:
        data = zeros((samples), dtype=float32)
        for idx, value in enumerate(raw_data):
            data[idx] = convert_to_phys(value,
                            channel_range_struct,
                            channel_max_data) 
        return data
    else:
        logging.warning('data_read was not successful')
        return False

def data_write(device, subdevice, channel, channel_range, aref, set_value):
    '''Write a single value to a channel'''
    rc = comedi.comedi_data_write(device, 
                                    subdevice,
                                    channel, 
                                    channel_range, 
                                    aref,
                                    set_value)
    if rc == 1:
        return True
    else:
        logging.warning('data_write was not successful')
        return False
                
def open(device_id):
    return comedi.comedi_open(device_id)

def get_board_name(device):
    return comedi.comedi_get_board_name(device)

def get_n_subdevices(device):
    return comedi.comedi_get_n_subdevices(device)

def get_n_channels(device, subdevice):
    return comedi.comedi_get_n_channels(device, subdevice)

def get_range(device, subdevice, channel, channel_range):
    range_struct =  comedi.comedi_get_range(device,
                                        subdevice,
                                        channel,
                                        channel_range)
    return range_struct.contents

def get_range_struct(device, subdevice, channel, channel_range):
    range_struct =  comedi.comedi_get_range(device,
                                        subdevice,
                                        channel,
                                        channel_range)
    return range_struct

def get_max_data(device, subdevice, channel):
    return comedi.comedi_get_maxdata(device, subdevice, channel)
