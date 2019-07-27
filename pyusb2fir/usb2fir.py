# This file is part of the pyUSB2FIR project.
#
# Copyright(c) 2018 Thomas Fischl (https://www.fischl.de)
# 
# pyUSB2FIR is free software: you can redistribute it and/or modify
# it under the terms of the GNU LESSER GENERAL PUBLIC LICENSE as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyUSB2FIR is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU LESSER GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
# along with pyUSB2FIR.  If not, see <http://www.gnu.org/licenses/>

import libusb1
import usb1
import numpy as np

USB2FIR_VID = 0x04D8
USB2FIR_PID = 0xEE7D

CMD_GET_CAPABILITY = 0
CMD_ECHO = 1
CMD_START_BOOTLOADER = 2
CMD_READ_MEMORY = 3
CMD_WRITE_MEMORY = 4
CMD_GET_STATUS = 5
CMD_CONFIG_BFMODE = 6

BF_HEADER_REG_ID0 = 0
BF_HEADER_REG_ID1 = 1
BF_HEADER_REG_SUBPAGE = 2
BF_HEADER_REG_TA_VBE = 3
BF_HEADER_REG_CP = 4
BF_HEADER_REG_GAIN = 5
BF_HEADER_REG_TA_PTAT = 6
BF_HEADER_REG_VDDPIX = 7


def uint4_to_int4(i):
    if i > 7:
        return i - 16
    else:
        return i

def uint6_to_int6(i):
    if i > 31:
        return i - 64
    else:
        return i

def uint8_to_int8(i):
    if i > 127:
        return i - 256
    else:
        return i

def uint10_to_int10(i):
    if i > 511:
        return i - 1024
    else:
        return i

def uint16_to_int16(i):
    if i > 32767:
        return i - 65536
    else:
        return i

class MLXCommonParameters:


    def __init__(self, eepromdata):


        # extract VDD sensor parameters

        self.kVdd = uint8_to_int8(eepromdata[0x33] >> 8) * 32
        self.vdd25 = ((eepromdata[0x33] & 0xff) - 256) * 32 - 8192


        # extract Ta sensor parameters

        self.KvPTAT = eepromdata[0x32] >> 10
        if self.KvPTAT > 31:
            self.KvPTAT = self.KvPTAT - 64
        self.KvPTAT = self.KvPTAT / 4096.0

        self.KtPTAT = eepromdata[0x32] & 0x03FF
        if self.KtPTAT > 511:
            self.KtPTAT = self.KtPTAT - 1024
        self.KtPTAT = self.KtPTAT / 8.0

        self.vPTAT25 = uint16_to_int16(eepromdata[0x31])

        self.alphaPTAT = (eepromdata[0x10] >> 12) / 4.0 + 8.0


        # extract offset

        offsetAverage = uint16_to_int16(eepromdata[0x11])
        occRowScale = (eepromdata[0x10] & 0x0F00) >> 8;
        occColumnScale = (eepromdata[0x10] & 0x00F0) >> 4;
        occRemScale = eepromdata[0x10] & 0x000F;

        occRow = []
        for i in range(24):
            occRow.append(uint4_to_int4((eepromdata[0x12 + i // 4] >> ((i % 4) * 4)) & 0xF))

        occColumn = []
        for i in range(32):
            occColumn.append(uint4_to_int4((eepromdata[0x18 + i // 4] >> ((i % 4) * 4)) & 0xF))

        self.offset = []
        for i in range(24):
            for j in range(32):
                pixelid = i * 32 + j
                o = uint6_to_int6((eepromdata[0x40 + pixelid] & 0xFC00) >> 10)
                o = o * (1 << occRemScale) + offsetAverage + (occRow[i] << occRowScale) + (occColumn[j] << occColumnScale)
                self.offset.append(o)


        # extract sensitivity
        
        alphaRef = eepromdata[0x21]
        alphaScale = (eepromdata[0x20] >> 12) + 30
        accColumnScale = (eepromdata[0x20] & 0x00F0) >> 4;
        accRowScale = (eepromdata[0x20] & 0x0F00) >> 8;
        accRemScale = eepromdata[0x20] & 0x000F;

        accRow = []
        for i in range(24):
            accRow.append(uint4_to_int4((eepromdata[0x22 + i // 4] >> ((i % 4) * 4)) & 0xF))

        accColumn = []
        for i in range(32):
            accColumn.append(uint4_to_int4((eepromdata[0x28 + i // 4] >> ((i % 4) * 4)) & 0xF))

        self.alpha = []
        for i in range(24):
            for j in range(32):
                pixelid = i * 32 + j
                a = uint6_to_int6((eepromdata[0x40 + pixelid] & 0x03F0) >> 4)
                a = alphaRef + (accRow[i] << accRowScale) + (accColumn[j] << accColumnScale) + a * (1 << accRemScale)
                a = (a + 0.0) / (int(1) << alphaScale)
                self.alpha.append(a)


        # extract the Kv(i,j) coefficient

        kvScale = (eepromdata[0x38] & 0x0F00) >> 8

        kV = []
        kV.append([uint4_to_int4((eepromdata[0x34] & 0xF000) >> 12), uint4_to_int4((eepromdata[0x34] & 0x00F0) >> 4)])
        kV.append([uint4_to_int4((eepromdata[0x34] & 0x0F00) >> 8), uint4_to_int4(eepromdata[0x34] & 0x000F)])

        self.kv = []
        for i in range(24):
            for j in range(32):
                pixelid = i * 32 + j
                v = kV[i & 1][j & 1]
                v = (v + 0.0) / (1 << kvScale)
                self.kv.append(v)

        # extract the Kta(i,j) coefficient

        kTaRC = []
        kTaRC.append([uint8_to_int8(eepromdata[0x36] >> 8), uint8_to_int8(eepromdata[0x37] >> 8)])  # row 0, 2, 4, ...
        kTaRC.append([uint8_to_int8(eepromdata[0x36] & 0xff), uint8_to_int8(eepromdata[0x37] & 0xff)])  # row 1, 3, 5, ...

        kTaScale1 = ((eepromdata[0x38] & 0x00F0) >> 4) + 8
        kTaScale2 = eepromdata[0x38] & 0x000F

        self.kta = []
        for i in range(24):
            for j in range(32):
                pixelid = i * 32 + j
                k = ((eepromdata[0x40 + pixelid] & 0x000E) >> 1)
                if k > 3:
                    k = k - 8
                k = k * (1 << kTaScale2) + kTaRC[i & 1][j & 1]
                k = (k + 0.0) / (1 << kTaScale1)
                self.kta.append(k)


        # extract the GAIN coefficient

        self.gainEE = uint16_to_int16(eepromdata[0x30])


        # extract the KsTa coefficient

        self.KsTa = uint8_to_int8(eepromdata[0x3C] >> 8) / 8192.0


        # extract corner temperatures

        step = ((eepromdata[0x3F] & 0x3000) >> 12) * 10;
        self.ct = [-40, 0, 0, 0]
        self.ct[2] = ((eepromdata[0x3F] & 0x00F0) >> 4) * step
        self.ct[3] = ((eepromdata[0x3F] & 0x0F00) >> 8) * step + self.ct[2]

        # extract the KsTo coefficient
        ksToScale = (eepromdata[0x3F] & 0x000F) + 8
        ksToScale = (1 << ksToScale)     
        ksToScale += 0.0

        self.ksTo = [uint8_to_int8(eepromdata[0x3D] & 0x00FF) / ksToScale, uint8_to_int8(eepromdata[0x3D] >> 8) / ksToScale, uint8_to_int8(eepromdata[0x3E] & 0x00FF) / ksToScale, uint8_to_int8(eepromdata[0x3E] >> 8) / ksToScale]


        # extract the sensitivity alphaCP

        alphaScale = ((eepromdata[0x20] & 0xF000) >> 12) + 27
        self.cpAlpha = [0.0, 0.0]
        self.cpAlpha[0] = (uint10_to_int10(eepromdata[0x39] & 0x03FF) + 0.0) / (1 << alphaScale)
        self.cpAlpha[1] = uint6_to_int6((eepromdata[0x39] & 0xFC00) >> 10) + 0.0
        self.cpAlpha[1] = (1 + self.cpAlpha[1] / 128) * self.cpAlpha[0]


        # extract offset of the compensation pixel
        self.cpOffset = [0, 0]
        self.cpOffset[0] = uint10_to_int10(eepromdata[0x3A] & 0x03FF)
        self.cpOffset[1] = uint6_to_int6((eepromdata[0x3A] & 0xFC00) >> 10) + self.cpOffset[0]


        # extract the Kv CP coefficient

        kvScale = (eepromdata[0x38] & 0x0F00) >> 8;
        self.cpKv = uint8_to_int8((eepromdata[0x3B] & 0xFF00) >> 8)
        self.cpKv = (self.cpKv + 0.0) / (1 << kvScale)

        # extract the Kta CP coefficient        
        self.cpKta = uint8_to_int8(eepromdata[0x3B] & 0x00FF)
        self.cpKta = (self.cpKta + 0.0) / (1 << kTaScale1)

        # extract the TGC coefficient

        self.tgc = uint8_to_int8(eepromdata[0x3C] & 0x0ff) / 32.0

        # extract resolution setting
        self.resolutionEE = (eepromdata[0x38] & 0x3000) >> 12;    
    

        self.alphaCorrR = [0] * 4
        self.alphaCorrR[0] = 1 / (1 + self.ksTo[0] * 40)
        self.alphaCorrR[1] = 1
        self.alphaCorrR[2] = (1 + self.ksTo[2] * self.ct[2]);
        self.alphaCorrR[3] = self.alphaCorrR[2] * (1 + self.ksTo[3] * (self.ct[3] - self.ct[2]));



class USB2FIR(object):
    def __init__(self, i2caddress=0x33, refreshRate=3):
        """
        Initialize and open connection to USB2FIR.
        """
        ctx = usb1.LibUSBContext()
        self.usbdev = ctx.getByVendorIDAndProductID(USB2FIR_VID, USB2FIR_PID)
        self.usbhandle = self.usbdev.open()
        self.usbhandle.claimInterface(0)
        self.i2caddress = i2caddress

        data = self.read_memory(0x2400, 832 * 2)
        eepromdata = np.frombuffer(data, '>u2')
        self.commonParameters = MLXCommonParameters(eepromdata)

        self.start_bfmode(refreshRate)

    def echo_test(self, echovalue):
        """
        Transmit echo test values.
        :rtype: int
        :param echovalue: value to echo
        :type echovalue: int
        :return: Echoed value
        """
        data = self.usbhandle.controlRead(libusb1.LIBUSB_TYPE_CLASS, CMD_ECHO, echovalue, 0, 2)
        return data[0] | (data[1] << 8)

    def get_capability(self):
        """
        Get capability. Every bit represents a function.
        :rtype: list
        :return: Capability
        """
        data = self.usbhandle.controlRead(libusb1.LIBUSB_TYPE_CLASS, CMD_GET_CAPABILITY, 0, 0, 4)
        return data


    def get_status(self):
        """
        Get status of last transaction.
        :rtype: int
        :return: Status
        """
        data = self.usbhandle.controlRead(libusb1.LIBUSB_TYPE_CLASS, CMD_GET_STATUS, 0, 0, 1)
        return data[0]


    def start_bootloader(self):
        """
        Jump to bootloader.
        """
        self.usbhandle.controlWrite(libusb1.LIBUSB_TYPE_CLASS, CMD_START_BOOTLOADER, 0x5237, 0, [])        


    def read_memory(self, startaddress, length):
        """
        Read a block of byte data from memory.
        :param startaddress: memory start address
        :type startaddress: int
        :param length: Desired block length
        :type length: int
        :return: List of bytes
        :rtype: list
        """
        data = self.usbhandle.controlRead(libusb1.LIBUSB_TYPE_CLASS, CMD_READ_MEMORY, self.i2caddress, startaddress, length)
        return data   

    def write_memory(self, startaddress, data):
        """
        Write a block of byte data to memory.
        :param startaddress: memory start address
        :type startaddress: int
        :param data: List of bytes
        :type data: list
        :rtype: None
        """
        self.usbhandle.controlWrite(libusb1.LIBUSB_TYPE_CLASS, CMD_WRITE_MEMORY, self.i2caddress, startaddress, data)

    def bulkread(self):
        data = self.usbhandle.bulkRead(0x81, 64, 1000)
        return data

    def start_bfmode(self, refreshRate=3):
        self.usbhandle.controlWrite(libusb1.LIBUSB_TYPE_CLASS, CMD_CONFIG_BFMODE, self.i2caddress, refreshRate, [])        

    def stop_bfmode(self):
        self.usbhandle.controlWrite(libusb1.LIBUSB_TYPE_CLASS, CMD_CONFIG_BFMODE, 0xff, 0, [])        

    def initializeFrame(self, defaulttemp = 0.0):
        return np.array([defaulttemp] * 768)

    def updateFrame(self, frame):
        
        emissivity = 0.95

        while True:
            data = self.bulkread()
            regdata = np.frombuffer(data, '>u2')
            if regdata[BF_HEADER_REG_ID0] == 0xffff and regdata[BF_HEADER_REG_ID1] == 0x0000:
                break

        subpage = regdata[BF_HEADER_REG_SUBPAGE]
 
        vdd = uint16_to_int16(regdata[BF_HEADER_REG_VDDPIX]) + 0.0
        vdd = (vdd - self.commonParameters.vdd25) / self.commonParameters.kVdd + 3.3

        ptat = uint16_to_int16(regdata[BF_HEADER_REG_TA_PTAT]) + 0.0
        ptatArt = uint16_to_int16(regdata[BF_HEADER_REG_TA_VBE]) + 0.0
        ptatArt = (ptat / (ptat * self.commonParameters.alphaPTAT + ptatArt)) * (1 << 18)
        ta = (ptatArt / (1 + self.commonParameters.KvPTAT * (vdd - 3.3)) - self.commonParameters.vPTAT25)
        ta = ta / self.commonParameters.KtPTAT + 25

        tr = ta - 8;

        ta4 = np.power((ta + 273.15), 4)
        tr4 = np.power((tr + 273.15), 4)        
        taTr = tr4 - (tr4 - ta4) / emissivity
 
        gain = (self.commonParameters.gainEE + 0.0) / uint16_to_int16(regdata[BF_HEADER_REG_GAIN])

        irDataCP = uint16_to_int16(regdata[BF_HEADER_REG_CP]) - self.commonParameters.cpOffset[subpage] * (1 + self.commonParameters.cpKta * (ta -25)) * (1 + self.commonParameters.cpKv * (vdd - 3.3))


        pixelidx = subpage
        for segment in range(12):
            data = self.bulkread()
            pixeldata = np.frombuffer(data, '>u2')
            for irData in pixeldata:
                irData = uint16_to_int16(irData) + 0.0                
                irData = irData * gain
                irData = irData - self.commonParameters.offset[pixelidx] * (1 + self.commonParameters.kta[pixelidx] * (ta - 25)) * (1 + self.commonParameters.kv[pixelidx] * (vdd - 3.3))
                irData = irData / emissivity;
                
                irData = irData - self.commonParameters.tgc * irDataCP

                alphaCompensated = (self.commonParameters.alpha[pixelidx] - self.commonParameters.tgc * self.commonParameters.cpAlpha[subpage]) * (1 + self.commonParameters.KsTa * (ta - 25));

                Sx = np.power(alphaCompensated, 3) * (irData + alphaCompensated * taTr);
                Sx = np.sqrt(np.sqrt(Sx)) * self.commonParameters.ksTo[1];

                To = np.sqrt(np.sqrt(irData / (alphaCompensated * (1 - self.commonParameters.ksTo[1] * 273.15) + Sx) + taTr)) - 273.15;

                if To < self.commonParameters.ct[1]:
                    r = 0
                elif To < self.commonParameters.ct[2]:
                    r = 1
                elif To < self.commonParameters.ct[3]:
                    r = 2
                else:
                    r = 3
            
                To = np.sqrt(np.sqrt(irData / (alphaCompensated * self.commonParameters.alphaCorrR[r] * (1 + self.commonParameters.ksTo[r] * (To - self.commonParameters.ct[r]))) + taTr)) - 273.15;
                frame[pixelidx] = To
                pixelidx = pixelidx + 2
                

            
