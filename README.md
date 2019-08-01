# Visual MIDI

Converts a [pretty midi](https://craffel.github.io/pretty-midi/) sequence to a [bokeh plot](https://bokeh.pydata.org/en/latest/).

## Installation

```bash
# TODO not published to pythonhosted yet
pip install visual_midi
```

## Usage

### Python

```python
from visual_midi import Plotter
import pretty_midi as pm
pretty_midi = pm.PrettyMIDI()
plotter = Plotter()
plotter.show(pretty_midi, "out.html")
```

### Command line

```bash
visual_midi "midi_file_01.mid" "midi_file_02.mid"
```

## Examples

```python
from visual_midi import Plotter
import pretty_midi as pm

plotter = Plotter(plot_max_length_time=16)
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
[pretty_midi.instruments[0].append(note) for note in notes]
plotter.plot(pretty_midi)
plotter.show(pretty_midi, "output.html")
```

![Example 01](docs/example-01.png)

## Contributing

### Development

```bash
# Install in specific env (using conda)
conda activate env

# Installs the python library (doesn't work with classic install)
python setup.py install_lib
```

### Guidelines

Use this [code style](config/visual-midi-code-style-intellij.xml).

## TODO

See [TODO](TODO.md).

## License

[MIT License](LICENSE).
