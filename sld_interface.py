#------------------------------------------------------------------------------
#
#   sld_interface.py - 4/16/14
#
#   A Python interface to SLD Controller & nodes via USB-Blaster
#
#------------------------------------------------------------------------------

import ctypes as c
from time import sleep
import subprocess

from ftdi import *

#------------------------------------------------------------------------------
#
# Create a write buffer from a list of bytes

def tx_buffer(byte_list):
    return (c.c_ubyte * len(byte_list))(*byte_list)

#------------------------------------------------------------------------------
#
# Generate CSV output - For testing with 245_decode.py

class CSV_Writer(object):
    
    def __init__(self,file_name):
        
        self.cvs = open(file_name, 'w')
        self.step = 1
        self.fn = file_name
    
    #----

    def write(self, buff):
               
        for i in range(c.sizeof(buff)):
            bits = reversed(list('000000' + bin(buff[i])[2:]) + [str(self.step)])
            print >>self.cvs, ','.join(bits)
            
            self.step +=  1
    
    #----
    
    def close(self):
        self.cvs.close()
        print '%s closed' % self.fn

#-------------------------------------------------------------------------------
#
# Create a tx_buffer to send the data (A string of ones and zeros)

def dataBits(bit_string):
    
    data_bytes = []
    for i in reversed(range(len(bit_string))):        
        if i:
            # LSB bits
            if bit_string[i] == '1':
                data_bytes += M0D1
            else:
                data_bytes += M0D0       
        else:
            # MSB bit of string
            if bit_string[i] == '1':
                data_bytes += M1D1
            else:
                data_bytes += M1D0                
    return tx_buffer(data_bytes)

#-------------------------------------------------------------------------------

# FT245 Bit definitions
OFF = 0x00
TCK = 0x01
TMS = 0x02
TDI = 0x10
LED = 0x20
RD  = 0x40
sHM = 0x80

# Bit-mode - Two byte codes
M0D0R = [LED       | RD , LED             | TCK]
M0D1R = [LED | TDI | RD , LED       | TDI | TCK]

M0D0 = [LED             , LED             | TCK]
M0D1 = [LED | TDI       , LED       | TDI | TCK]
M1D0 = [LED | TMS       , LED | TMS       | TCK]
M1D1 = [LED | TMS | TDI , LED | TMS | TDI | TCK]

# TAP controller Reset
TAP_RESET = tx_buffer(M1D0 + M1D0 + M1D0 + M1D0 + M1D0)

# TAP controller Reset to Idle
TAP_IDLE = tx_buffer(M0D0)

# TAP controller Idle to Shift_DR 
TAP_SHIFT_DR = tx_buffer(M1D0 + M0D0 + M0D0)

# TAP controller Idle to Shift_IR 
TAP_SHIFT_IR = tx_buffer(M1D0 + M1D0 + M0D0 + M0D0)

# TAP controller Exit1 to Idle 
TAP_END_SHIFT = tx_buffer(M1D0 + M0D0)

# IR values

SELECT_VIR = tx_buffer(M0D0 + M0D1 + M0D1 + M0D1 + M0D0 +
                       M0D0 + M0D0 + M0D0 + M0D0 + M1D0)

SELECT_VDR = tx_buffer(M0D0 + M0D0 + M0D1 + M0D1 + M0D0 +
                       M0D0 + M0D0 + M0D0 + M0D0 + M1D0)

NODE_SHIFT_INST  = tx_buffer(M0D1 + M0D0 + M0D0 + M0D0 + M1D1)

NODE_UPDATE_INST = tx_buffer(M0D0 + M0D0 + M0D0 + M0D0 + M1D1)

# Node Data 
NODE_DATA = tx_buffer(M0D0 + M0D1 + M0D1 + M0D0 + M0D0 + M0D1 + M1D1)
 
#-------------------------------------------------------------------------------
#
# A class for higher level SLD functions
#
# All start and end in the Run_Test/Idle TAP state

class SLD_Controller(object):
    
    def __init__(self, interface_name, m_width, n_width):
        
        self.interface = open_ex_by_name(interface_name)
        
        self.instruction_width  = 10
        self.virtual_inst_width = m_width
        self.node_adrs_width    = n_width
        
        self.interface.reset_device()
        self.interface.write(TAP_RESET)
        self.interface.write(TAP_IDLE)
        
    #----
            
    def configure(self, m_width, n_width):
        self.instruction_width  = 10
        self.virtual_inst_width = m_width
        self.node_adrs_width    = n_width

    #----

    def TAP_Reset(self):
        self.interface.write(TAP_RESET)
        self.interface.write(TAP_IDLE)
        
    #----
    
    def IR_Write(self, instruction):
        self.interface.write(TAP_SHIFT_IR)
        self.interface.write(dataBits(instruction))
        self.interface.write(TAP_END_SHIFT)
            
    #----
    
    def VIR_Write(self, node, instruction):
        
        #  load the JTAG IR with USER1 to select the Virtual IR
        self.interface.write(TAP_SHIFT_IR)
        self.interface.write(dataBits('0000001110'))
        self.interface.write(TAP_END_SHIFT)
        
        # Load node 1 virtual IR with SHIFT instruction
        self.interface.write(TAP_SHIFT_DR)
        self.interface.write(dataBits(instruction))
        self.interface.write(TAP_END_SHIFT)
            
    #----
    
    def VDR_Write(self, data):

        #  load the JTAG IR with USER0 to select the Virtual DR
        self.interface.write(TAP_SHIFT_IR)
        self.interface.write(dataBits('0000001100'))
        self.interface.write(TAP_END_SHIFT)
        
        # Load node 1 virtual DR with data
        self.interface.write(TAP_SHIFT_DR)
        self.interface.write(dataBits(data))
        self.interface.write(TAP_END_SHIFT)
            
    #----
    
    def close(self):
        self.interface.close()

#===============================================================================
#
# Main

# Program the DE0-Nano

print 'Programming ...'
command_line = 'quartus_pgm -c USB-Blaster -m JTAG -o p;InitialTest.sof'
retcode = subprocess.call(command_line)

print
print 'return code:', retcode

print
print 'Testing'
sld = SLD_Controller('USB-Blaster', 4, 1)
sld.TAP_Reset()

d = 0
while True:
    
    s = bin(d)[2:]
    s = (7-len(s)) * '0' + s
    
    sld.VIR_Write(1, '10001')
    sld.VDR_Write(s)
    sld.VIR_Write(1, '10000')
    
    if d == 127:
        d = 0
        break
    else:
        d += 1
        
    sleep(0.1)
    
sld.TAP_Reset()
sld.close()
print 
print 'closed'
print 'Done'

#-------------------------------------------------------------------------------
#
# dev = list_devices()
# print 'devices:', dev
#  
# result = get_device_info_list()
# print 'info:'
# for info in result:
#     for k,v in info.items():
#         print '  %12s : %s' % (k, v)
#          
# result = get_device_info_detail()
# print
# print 'detail:'
# for k,v in result.items():
#     print '  %12s : %s' % (k, v)
#              
