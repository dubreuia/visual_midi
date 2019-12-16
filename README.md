# Visual MIDI

Converts a [pretty midi](https://craffel.github.io/pretty-midi/) sequence to a [bokeh plot](https://bokeh.pydata.org/en/latest/).

## Installation

```bash
pip install visual_midi
```

## Usage

### Python

```python
from visual_midi import Plotter
from pretty_midi import PrettyMIDI

pm = PrettyMIDI()
plotter = Plotter()
plotter.show(pm, "out.html")
```

### Command line

```bash
visual_midi "midi_file_01.mid" "midi_file_02.mid"
```

## Examples

```python
from visual_midi import Plotter
from pretty_midi import PrettyMIDI
from pretty_midi import Instrument
from pretty_midi import Note

plotter = Plotter(plot_max_length_bar=4)
pm = PrettyMIDI()
pm.instruments.append(Instrument(0))
notes = [Note(100, 36, 1.5, 1.7),
         Note(100, 37, 1.5, 1.7),
         Note(100, 38, 3.5, 4.1),
         Note(100, 39, 5.5, 6.0),
         Note(100, 40, 6.0, 7.0),
         Note(100, 41, 7.0, 8.0),
         Note(100, 36, 9.0, 10.5),
         Note(100, 37, 9.5, 10.0),
         Note(100, 37, 10.0, 10.5),
         Note(100, 37, 10.5, 11.0)]
[pm.instruments[0].append(note) for note in notes]
plotter.plot(pm)
plotter.show(pm, "output.html")
```

![Example 01](docs/example-01.png)

## Contributing

### Development

```bash
# Installs the library, dependencies, and command line scripts
python setup.py install

# Installs the python library (necessary for python imports)
python setup.py install_lib
```

### Guidelines

Use this [code style](config/visual-midi-code-style-intellij.xml).

## TODO

See [TODO](TODO.md).

## License

See [MIT License](LICENSE).
