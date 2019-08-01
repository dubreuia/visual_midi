import os
import unittest

import pretty_midi as pm

from visual_midi.visual_midi import Plotter

os.makedirs("output", exist_ok=True)

class TestDefaultPlot(unittest.TestCase):

  def test_empty_plot(self):
    plotter = Plotter()
    pretty_midi = pm.PrettyMIDI()
    # pretty_midi.instruments.append(pm.Instrument(0))
    # pretty_midi.instruments[0].notes.append(pm.Note(100, 36, 0, 0.125))
    # plotter.show(pretty_midi, os.path.join("output", "test_empty_plot.html"))

  def test_one_note_plot(self):
    plotter = Plotter()
    pretty_midi = pm.PrettyMIDI()
    pretty_midi.instruments.append(pm.Instrument(0))
    pretty_midi.instruments[0].notes.append(pm.Note(100, 36, 1.5, 1.7))
    pretty_midi.instruments[0].notes.append(pm.Note(100, 37, 1.5, 1.7))
    pretty_midi.instruments[0].notes.append(pm.Note(100, 38, 3.5, 4.1))
    pretty_midi.instruments[0].notes.append(pm.Note(100, 39, 5.5, 6.0))
    pretty_midi.instruments[0].notes.append(pm.Note(100, 40, 6.0, 7.0))
    pretty_midi.instruments[0].notes.append(pm.Note(100, 41, 7.0, 8.0))
    plotter.show(pretty_midi, os.path.join("output", "test_empty_plot.html"))


if __name__ == '__main__':
  unittest.main()
