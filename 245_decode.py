#------------------------------------------------------------------------------
#
#   245_decode.py
#
#   Decode captured FT245 data
#
#   Version 0.0.1  -  4/25/14

#------------------------------------------------------------------------------

import csv

#------------------------------------------------------------------------------
#
# Globals

signal_names = [
    'step',
    'tck',      # D0
    'tms',      # D1
    'nCE',      # D2
    'nCS',      # D3
    'tdi',      # D4
    'LED',      # D5
    'read',     # D6
    'mode',     # D7
    'SDR',
    'UDR',
    'WR'
    ]

cpld_tck = 0
cpld_tdi = 0
cpld_tms = 0

# Named CPLD mode constants
CPLD_START = 0
CPLD_BIT   = 1
CPLD_BYTE  = 2

RISING  = 1
FALLING = 0

#------------------------------------------------------------------------------
#
# A generator of captured data

def cvs(file_name):

    csvfile = open(file_name, 'rb')
    csv_reader = csv.reader(csvfile, delimiter=',', quotechar='|')
    for row in csv_reader:
        
        # Get this into a more usable format
        dc = DataContainer(row)
                
        yield dc 
        
    csvfile.close()

#------------------------------------------------------------------------------
#
# A container class for each row of captured data

class DataContainer(object):
    
    def __init__(self, cvs_row):
        
        # Fields of cvs_row become attributes
        d = dict((key, value.strip()) for (key, value) in zip(signal_names, cvs_row))
        self.__dict__.update(d)
        
        self.cvs_row = cvs_row        
               
    #----
    
    @property
    def byte_count(self):
        # Getter property method for self.value
        bits = [s.strip() for s in self.cvs_row[1:7]]
        bits.reverse()
        return int(''.join(bits), 2)
               
    #----
    
    @property
    def bits(self):
        # Getter property method for self.value
        return [s.strip() for s in self.cvs_row[1:9]]
               
    #----
    
    @property
    def now(self):
        # Getter property method for self.now
        return float(self.step) - 0.5

#------------------------------------------------------------------------------
#
# CPLD Logic
#
# Process FT245 parallel output for bit & byte mode

class CPLD(object):
    
    def __init__(self, byte_stream, mode):
       
        self.byte_stream = byte_stream
        self.mode        = mode
        
    #----
        
    def run(self):
    
        try:
        
            new_byte   = self.byte_stream.next()
            byte_count = 0
            byte_read  = False
            
            while True:
                
                old_byte = new_byte
                new_byte = self.byte_stream.next()
                t = new_byte.now
                
                if self.mode == CPLD_START:
                    # Wait for tck == 0
                    if new_byte.tck == '0':
                        self.mode = CPLD_BIT
                        print 'EXIT START at ', new_byte.now
                    continue
                
                if self.mode == CPLD_BIT:               
                                        
                    if new_byte.mode == '1':
                        byte_count = new_byte.byte_count
                        
                        if new_byte.read == '1':
                            byte_read = True
                            print 'byte shift read mode %d' % byte_count
                        else:
                            byte_read = False
                            print 'byte shift mode %d' % byte_count
                            
                        self.mode = CPLD_BYTE
                        continue
                
                    if (new_byte.tck, old_byte.tck) == ('1', '0'):
                        yield (RISING, new_byte.tms, new_byte.tdi, new_byte.read, new_byte.now)
                        
                    elif (new_byte.tck, old_byte.tck) == ('0', '1'):
                        yield (FALLING, new_byte.tms, new_byte.tdi, new_byte.read, new_byte.now)
                        
                    
                elif self.mode == CPLD_BYTE:
                    
                    # Byte mode
                    if byte_count > 0:
                                                    
                        shift_bits = new_byte.bits
                        for bit in shift_bits:
                            yield (RISING,  '0', bit, byte_read, new_byte.now) 
                            yield (FALLING, '0', bit, byte_read, new_byte.now)
                        byte_count -= 1                           
                    else:
                        self.mode = CPLD_BIT

                    continue
                        
      
                t = new_byte.now
                if t > 600.5:
                    break
                
        except StopIteration:
            print
            print 'Done'

#------------------------------------------------------------------------------
#
# SLD controller
#
# State

class SLD_Controller(object):
    
    def __init__(self, node_count, start='reset'):
 
        # A dict describing JTAG state transitions
    
        self.jtag_states = {
            'capture_dr': ['shift_dr', 'exit1_dr'],
             'capture_ir': ['shift_ir', 'exit1_ir'],
             'exit1_dr': ['pause_dr', 'update_dr'],
             'exit1_ir': ['pause_ir', 'update_ir'],
             'exit2_dr': ['shift_dr', 'update_dr'],
             'exit2_ir': ['shift_ir', 'update_ir'],
             'idle': ['idle', 'select_dr'],
             'pause_dr': ['pause_dr', 'exit2_dr'],
             'pause_ir': ['pause_ir', 'exit2_ir'],
             'reset': ['idle', 'reset'],
             'select_dr': ['capture_dr', 'select_ir'],
             'select_ir': ['capture_ir', 'reset'],
             'shift_dr': ['shift_dr', 'exit1_dr'],
             'shift_ir': ['shift_ir', 'exit1_ir'],
             'update_dr': ['idle', 'select_dr'],
             'update_ir': ['idle', 'select_dr']
        }
    
        self.state    = start        
        self.ir_shift = ''
        self.dr_shift = ''
        
        self.ir = ''
        self.dr = ''
        
        self.node_count = node_count
        
    #----
        
    def TCK_rise(self, event):
        
        direction, tms, tdi, rd, t = event
        self.new_state = self.jtag_states[self.state][int(tms)]
        
        if self.state == 'shift_ir':
            self.ir_shift = tdi + self.ir_shift
#             print '  ir_shift: %s' % self.ir_shift, int(tms)
            
        elif (self.state == 'shift_dr'):
            
            self.dr_shift = tdi + self.dr_shift
#             print '    dr_shift: %s %s at  %.1f' % (self.dr_shift, tms, t)
                                      
    #----
        
    def TCK_fall(self, event):
               
        direction, tms, tdi, rd, t = event
        
        if self.new_state != self.state:
            self.state = self.new_state
            print '  TAP transition to: %s at %.1f' % (self.state, t)
            
            if self.state == 'capture_dr':
                self.dr_shift = ''
                
            elif self.state == 'update_dr':
                self.dr = self.dr_shift
                print 'UPDATE %d dr bits to %s' % (len(self.dr), self.dr)
                
            elif self.state == 'capture_ir':
                self.ir_shift = ''
                
            elif self.state == 'update_ir':
                self.ir = self.ir_shift
                if len(self.ir):
                    print 'UPDATE %d ir bits to %s' % (len(self.ir), self.ir)
                else:
                    print

                    
#------------------------------------------------------------------------------
#
# Main

# This .csv file is broken!!
#pld = CPLD(cvs('ft_245_data.csv'), CPLD_START)

pld = CPLD(cvs('test2.csv'), CPLD_BIT)

sld = SLD_Controller(1)
    
for event in pld.run():
    direction, tms, tdi, rd, t = event
    
    if direction == RISING:
        sld.TCK_rise(event)
    else:
        sld.TCK_fall(event)
                
