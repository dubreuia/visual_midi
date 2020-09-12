import os
import unittest

from setuptools import setup


def read(fname):
  return open(os.path.join(os.path.dirname(__file__), fname)).read()


def tests():
  test_loader = unittest.TestLoader()
  test_suite = test_loader.discover("tests", pattern="test_*.py")
  return test_suite


setup(
  name="Visual MIDI",
  version="1.1.0",
  author="Alexandre DuBreuil",
  author_email="code@alexandredubreuil.com",
  description="Converts a pretty midi sequence to a boket plot",
  license="MIT License",
  keywords="midi, bokeh",
  url="http://packages.python.org/visual_midi",
  packages=["visual_midi", "tests"],
  long_description=read("README_short.md"),
  long_description_content_type="text/markdown",
  test_suite="setup.tests",
  entry_points={
    "console_scripts": [
      "visual_midi = visual_midi.visual_midi:console_entry_point"
    ],
  },
  classifiers=[
    "Development Status :: 3 - Alpha",
    "Topic :: Utilities",
    "License :: OSI Approved :: MIT License",
  ],
  install_requires=[
    "pretty_midi >= 0.2.8",
    "bokeh >= 2.0.2",
  ]
)
