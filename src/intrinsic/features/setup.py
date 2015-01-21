# python setup.py build_ext --inplace

from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext

import numpy

ext = Extension(
    "line_casting_cython", ["line_casting_cython.pyx"],
    include_dirs=[numpy.get_include()])

setup(ext_modules=[ext],
      cmdclass={'build_ext': build_ext})
