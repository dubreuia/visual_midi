import os
import unittest

import pretty_midi as pm
from pretty_midi import TimeSignature

from presets import PRESET_4K
from visual_midi import Coloring
from visual_midi.visual_midi import Plotter

os.makedirs("output", exist_ok=True)


class TestDefaultPlot(unittest.TestCase):

  def test_plotter_preset(self):
    plotter = Plotter(PRESET_4K)
    pretty_midi = pm.PrettyMIDI()
    plotter.plot(pretty_midi)
    output_file = os.path.join("output", "test_plotter_preset.html")
    plotter.save(pretty_midi, output_file)

  def test_empty_plot(self):
    plotter = Plotter()
    pretty_midi = pm.PrettyMIDI()
    plotter.plot(pretty_midi)
    output_file = os.path.join("output", "test_empty_plot.html")
    plotter.save(pretty_midi, output_file)

  def test_one_note_plot(self):
    plotter = Plotter()
    pretty_midi = pm.PrettyMIDI()
    pretty_midi.instruments.append(pm.Instrument(0))
    notes = [pm.Note(100, 36, 1.5, 1.7)]
    [pretty_midi.instruments[0].notes.append(note) for note in notes]
    plotter.plot(pretty_midi)
    output_file = os.path.join("output", "test_one_note_plot.html")
    plotter.save(pretty_midi, output_file)

  def test_two_notes_plot(self):
    plotter = Plotter()
    pretty_midi = pm.PrettyMIDI()
    pretty_midi.instruments.append(pm.Instrument(0))
    notes = [pm.Note(100, 36, 1.5, 1.7),
             pm.Note(100, 37, 3.5, 4.0)]
    [pretty_midi.instruments[0].notes.append(note) for note in notes]
    plotter.plot(pretty_midi)
    output_file = os.path.join("output", "test_two_notes_plot.html")
    plotter.save(pretty_midi, output_file)

  def test_multiple_notes_plot(self):
    plotter = Plotter()
    pretty_midi = pm.PrettyMIDI()
    pretty_midi.instruments.append(pm.Instrument(0))
    notes = [pm.Note(100, 36, 1.5, 1.7),
             pm.Note(100, 37, 1.5, 1.7),
             pm.Note(100, 38, 3.5, 4.1),
             pm.Note(100, 39, 5.5, 6.0),
             pm.Note(100, 40, 6.0, 7.0),
             pm.Note(100, 41, 7.0, 8.0)]
    [pretty_midi.instruments[0].notes.append(note) for note in notes]
    plotter.plot(pretty_midi)
    output_file = os.path.join("output", "test_multiple_notes_plot.html")
    plotter.save(pretty_midi, output_file)

  def test_qpm_plot(self):
    plotter = Plotter()
    pretty_midi = pm.PrettyMIDI(initial_tempo=150)
    pretty_midi.instruments.append(pm.Instrument(0))
    notes = [pm.Note(100, 36, 1.5, 1.7),
             pm.Note(100, 37, 1.5, 1.7),
             pm.Note(100, 38, 3.5, 4.1),
             pm.Note(100, 39, 5.5, 6.0),
             pm.Note(100, 40, 6.0, 7.0),
             pm.Note(100, 41, 7.0, 8.0)]
    [pretty_midi.instruments[0].notes.append(note) for note in notes]
    plotter.plot(pretty_midi)
    output_file = os.path.join("output", "test_qpm_plot.html")
    plotter.save(pretty_midi, output_file)

  def test_overflow_plot(self):
    plotter = Plotter(plot_max_length_bar=4)
    pretty_midi = pm.PrettyMIDI()
    pretty_midi.instruments.append(pm.Instrument(0))
    notes = [pm.Note(100, 36, 1.5, 1.7),
             pm.Note(100, 37, 1.5, 1.7),
             pm.Note(100, 38, 3.5, 4.1),
             pm.Note(100, 39, 5.5, 6.0),
             pm.Note(100, 40, 6.0, 7.0),
             pm.Note(100, 41, 7.0, 8.0),
             pm.Note(100, 36, 9.0, 10.5),
             pm.Note(100, 37, 9.5, 10.0),
             pm.Note(100, 37, 10.0, 10.5),
             pm.Note(100, 37, 10.5, 11.0)]
    [pretty_midi.instruments[0].notes.append(note) for note in notes]
    plotter.plot(pretty_midi)
    output_file = os.path.join("output", "test_overflow_plot.html")
    plotter.save(pretty_midi, output_file)

  def test_time_signature_plot(self):
    plotter = Plotter(plot_bar_range_start=0, plot_bar_range_stop=11)
    pretty_midi = pm.PrettyMIDI()
    pretty_midi.instruments.append(pm.Instrument(0))
    pretty_midi.time_signature_changes.append(TimeSignature(3, 8, 0))
    notes = [pm.Note(100, 36, 1.5, 1.7),
             pm.Note(100, 37, 1.5, 1.7),
             pm.Note(100, 38, 3.5, 4.1),
             pm.Note(100, 39, 5.5, 6.0),
             pm.Note(100, 40, 6.0, 7.0),
             pm.Note(100, 41, 7.0, 8.0)]
    [pretty_midi.instruments[0].notes.append(note) for note in notes]
    plotter.plot(pretty_midi)
    output_file = os.path.join("output", "test_time_signature_plot.html")
    plotter.save(pretty_midi, output_file)

  def test_instrument_color_plot(self):
    plotter = Plotter(coloring=Coloring.INSTRUMENT)
    pretty_midi = pm.PrettyMIDI()
    # Instrument 0
    pretty_midi.instruments.append(pm.Instrument(0))
    notes = [pm.Note(100, 36, 1.5, 1.7),
             pm.Note(100, 37, 1.5, 1.7),
             pm.Note(100, 38, 3.5, 4.1),
             pm.Note(100, 39, 5.5, 6.0),
             pm.Note(100, 40, 6.0, 7.0),
             pm.Note(100, 41, 7.0, 8.0)]
    [pretty_midi.instruments[0].notes.append(note) for note in notes]
    # Instrument 1
    pretty_midi.instruments.append(pm.Instrument(1))
    notes = [pm.Note(100, 50, 1.5, 2.5),
             pm.Note(100, 53, 3.5, 5.0),
             pm.Note(100, 54, 5.0, 7.0)]
    [pretty_midi.instruments[1].notes.append(note) for note in notes]
    plotter.plot(pretty_midi)
    output_file = os.path.join("output", "test_instrument_color_plot.html")
    plotter.save(pretty_midi, output_file)


if __name__ == '__main__':
  unittest.main()
