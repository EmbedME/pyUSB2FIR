#!usr/bin/python

import matplotlib
#matplotlib.use('GTKAgg') 
import matplotlib.pyplot as plt
from pyusb2fir import USB2FIR
import numpy as np

u2f = USB2FIR()
frame = u2f.initializeFrame()

plt.ion()

ir = frame.reshape((24, 32))
graph = plt.imshow(ir, interpolation='none')

plt.colorbar()
plt.clim(18, 35)
plt.draw()

try:
    while 1:
        u2f.updateFrame(frame)

        ir = frame.reshape((24, 32))[:, ::-1]

        graph.set_data(ir)
        plt.draw()
        plt.pause(0.0001)

except KeyboardInterrupt:
    u2f.close()
    print("CTRL-C: Program Stopping via Keyboard Interrupt...")

finally:
        print("Exiting Loop") 


