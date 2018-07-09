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

from setuptools import setup

def readme():
    with open("README.rst") as f:
        return f.read()

setup(name='pyusb2fir',
      version='1.0',
      description='USB2FIR - Interface for far infrared thermal sensor array MLX90640',
      long_description=readme(),
      classifiers=[
          "Development Status :: 3 - Alpha",
          "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
          "Programming Language :: Python :: 2.7",
      ],
      url='https://github.com/EmbedME/pyUSB2FIR',
      author='Thomas Fischl',
      author_email='tfischl@gmx.de',
      license="LGPL-3.0",
      packages=['pyusb2fir'],
      install_requires=[
          'libusb1',
          'numpy'
      ],
      zip_safe=False)