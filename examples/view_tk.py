import queue
import threading
import tkinter as tk

from pyUSB2FIR.pyusb2fir.usb2fir import USB2FIR


def rgb(minimum, maximum, value):
    minimum, maximum = float(minimum), float(maximum)
    ratio = 2 * (value-minimum) / (maximum - minimum)
    b = int(max(0, 255*(1 - ratio)))
    r = int(max(0, 255*(ratio - 1)))
    g = 255 - b - r
    return r, g, b


def u2f_fetcher(u2f, queue):
    global tempvalues
    t = threading.currentThread()
    while getattr(t, "do_run", True):
        u2f.updateFrame(tempvalues)
        queue.put(tempvalues)    


class TempView(tk.Tk):

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        self.pixelsize = 15
        self.cursorpos = 32 * 12 + 16

        self.title("USB2FIR - View_TK")

        self.tempmap = tk.Canvas(width=32*self.pixelsize, height=24*self.pixelsize)
        self.tempmap.pack()

        self.tempstr = tk.StringVar()
        self.label_temp = tk.Label(textvariable=self.tempstr)
        self.label_temp.pack()

        self.queue = queue.Queue()
        self.updateMap()

    def updateMap(self):

        try:
            tempvalues = self.queue.get_nowait()
            self.setTempValues(tempvalues)
        except queue.Empty:
            pass

        self.after(100, self.updateMap)


    def setTempValues(self, tempvalues):

        maximum = 0
        maximum_idx = 0
        minimum = 1000
        minimum_idx = 0
        i = 0
        for t in tempvalues:
            if t > maximum:
                maximum = t
                maximum_idx = i
            if t < minimum:
                minimum = t
                minimum_idx = i
            i = i + 1

        self.tempmap.delete("all")
        i = 0
        for t in tempvalues:
            row = i / 32
            column = 31 - i % 32
            x = column * self.pixelsize
            y = row * self.pixelsize
            color = '#%02x%02x%02x' % rgb(minimum, maximum, t)
            outline = color
            if i == self.cursorpos:
                outline = 'white'
            self.tempmap.create_rectangle(x, y, x + self.pixelsize - 1, y + self.pixelsize - 1, fill=color, outline=outline)

            i = i + 1
            
        self.tempstr.set('% 3.1f    % 3.1f    % 3.1f' % (minimum, tempvalues[self.cursorpos], maximum))
        

app = TempView()

u2f = USB2FIR()
tempvalues = u2f.initializeFrame()
t = threading.Thread(target=u2f_fetcher, args=(u2f, app.queue,))
t.start()

app.mainloop()

t.do_run = False

u2f.close()
