-------------------------------------------------------------------------------
---                                                                         ---
---                  Readme file for open_sld project                       ---
---                                                                         ---
-------------------------------------------------------------------------------
  
4/16/2014 - Vern Muhr (vernm10@comcast.net)  

The goal of this project is to create a python module that performs USB
communication with the nodes of an SLD (System Level Debug) mega-function
within an Altera FPGA.

This project is at the proof of concept stage. The python module can write to
to the InitialTest design created by Chris Zeh. Google:
   "Talking to the DE0-Nano using the Virtual JTAG interface"
   
The project targets Windows. It should also be easy to target Linux.
   
Requirements:

	FTD2XX.dll: The dll file must be in the same directory as sld_interface.py
	  http://www.ftdichip.com/Drivers/D2XX.htm)
	  
	Altera Quartus:
	  http://www.altera.com/products/software/sfw-index.jsp)

	pyftdi: 
	  http://fluidmotion.dyndns.org/zenphoto/uploaded/ftdi/pyftdi.tar.gz
	  
	This project communicates with a DE0-Nano FPGA board via USB.
	  http://www.terasic.com.tw/en/ Also available from Digikey, Mouser, Etc.		

The files of this project are:

sld_interface.py:

    The high level interface to the FTD2XX routines, as well as the main
    function that loads and drives the LEDs of the InitialTest FPGA design
    Note: this file also contains a class that writes commands to a .CSV
    file instead of the USB driver. This is useful for debugging, see 
    245_decode.py.
    
245_decode.py:

    A debug tool that emulates the SLD controller, and prints a log of TAP
    controller states, and register values.
    
ft_245_data.csv:
    A .cvs (comma seperated value) file of data captured on the FT245 parallel
    interface pins. Open it with 245_decode.py to see a log of how the
    captured data is processed by the SLD controller.

ftdi.py:
	The low-level python interface to FTD2XX.dll using ctypes. From the pyftdi
	project. Named ftdi2.py in that project.
	
InitialTest.sof:
    The programming file for the DE0-Nano FPGA. Loaded by sld_interface.py.
	
The details of how the FT245 parallel interface is used to control the JTAG
pins of Altera FPGAs is documented here:
  http://sourceforge.net/p/ixo-jtag/code/HEAD/tree/usb_jtag/

