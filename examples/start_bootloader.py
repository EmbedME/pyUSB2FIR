#!/usr/bin/env python

from pyusb2fir import USB2FIR

u2f = USB2FIR()
u2f.start_bootloader()
u2f.close()
