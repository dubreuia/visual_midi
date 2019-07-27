# midi2plot

Converts a [pretty midi](https://craffel.github.io/pretty-midi/) sequence to a [bokeh plot](https://bokeh.pydata.org/en/latest/).

## Installation

### Locally

```bash
# Install in specific env (using conda)
conda activate env

# Installs the python library (doesn't work with classic install)
python setup.py install_lib
```

### Usage

```python
from midi2plot import Plotter
import pretty_midi as pm

pretty_midi = pm.PrettyMIDI()
pretty_midi.instruments.append(pm.Instrument(0))
pretty_midi.instruments[0].append(pm.Note(100, 36, 0, 1))

plotter = Plotter()
plotter.show(pretty_midi, "out.html")
```
