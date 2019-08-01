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
pretty_midi.instruments.append(pm.Instrument(0))
pretty_midi.instruments[0].append(pm.Note(100, 36, 0, 1))

plotter = Plotter()
plotter.show(pretty_midi, "out.html")
```

### Command line

```bash
TODO
```

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

## [TODO](TODO.md)

## [License](LICENSE)
