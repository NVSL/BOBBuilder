from setuptools import setup
import os
from codecs import open
import sys

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'DESCRIPTION.rst'), encoding='utf-8') as f:
    long_description = f.read()

with open(os.path.join(here, 'VERSION.txt'), encoding='utf-8') as f:
    version = f.read()


setup(name='BOBBuilder',
      version=version,
      description="A tool for converting break-out boards into Eagle packages",
      long_description=long_description,
      classifiers=[
          "Development Status :: 4 - Beta",
          "Intended Audience :: Science/Research",
          "Operating System :: MacOS",
          "Operating System :: POSIX",
          "Operating System :: POSIX :: Linux",
          "Operating System :: Unix",
          "Programming Language :: Python",
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 2.7",
          "Topic :: Scientific/Engineering",
          "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
          "Topic :: System",
          "Topic :: System :: Hardware",
      ],
      author="NVSL, University of California San Diego",
      author_email="swanson@cs.ucsd.edu",
      #url="http://nvsl.ucsd.edu/BOBBuilder/",
      test_suite="Test",
      packages = ["BOBBuilder"],
      package_dir={
'BOBBuilder' : 'BOBBuilder',
      },
      package_data={
          "" : ["*.rst"],
      },
      install_requires=["lxml==3.6.2"], #EagleUtil
      entry_points={
          'console_scripts': [
            'buildBOB = BOBBuilder.buildBOB:main',
        ]
        },
      keywords = "PCB Eagle CAD printed circuit boards schematic electronics CadSoft",

)


