import os

from setuptools import setup


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
  return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
  name="midi2plot",
  version="0.0.1",
  author="Alexandre DuBreuil",
  author_email="code@alexandredubreuil.com",
  description=("Converts a pretty midi sequence to a boket plot"),
  license="MIT License",
  keywords="midi, bokeh",
  url="http://packages.python.org/midi2plot",
  packages=['midi2plot', 'tests'],
  long_description=read('README.md'),
  classifiers=[
    "Development Status :: 3 - Alpha",
    "Topic :: Utilities",
    "License :: OSI Approved :: MIT License",
  ],
  install_requires=[
    "pretty_midi>=0.2.8",
    "bokeh>=1.3.0",
  ]
)
