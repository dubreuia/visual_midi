import unittest

import pretty_midi as pm

from midi2plot.midi2plot import Plotter


class TestDefaultPlot(unittest.TestCase):

  def test_empty_plot(self):
    plotter = Plotter()
    pretty_midi = pm.PrettyMIDI()
    pretty_midi.instruments.append(pm.Instrument(0))
    pretty_midi.instruments[0].notes.append(pm.Note(100, 36, 0, 0.125))
    plot = plotter.plot_midi(pretty_midi)
    # print(plot)


if __name__ == '__main__':
  unittest.main()
