import argparse
import os
import sys

import bokeh
import bokeh.plotting
from bokeh.colors.groups import purple as colors
from bokeh.core.enums import FontStyle
from bokeh.embed import file_html
from bokeh.io import output_file, show, save
from bokeh.layouts import column
from bokeh.models import BoxAnnotation, ColumnDataSource, Title
from bokeh.models import Range1d, Label
from bokeh.models.callbacks import CustomJS
from bokeh.models.widgets.buttons import Button
from bokeh.resources import CDN
from pretty_midi import PrettyMIDI


def _frange(x, y, jump):
  while x < y:
    yield x
    x += jump


class Plotter:
  """A plotter class with plot size, time scaling and live reload
  configuration.

  TODO args
  """

  _MAX_PITCH = 127
  _MIN_PITCH = 0

  # TODO calculate
  _PITCH_OFFSET_DEFAULT = 0.2
  _PITCH_OFFSETS = {
    1: 0.45,
    2: 0.45,
    3: 0.40,
    4: 0.40,
    5: 0.35,
    6: 0.30,
    7: 0.25,
    8: 0.25,
  }

  def __init__(self,
               qpm=None,
               plot_pitch_min=None,
               plot_pitch_max=None,
               plot_max_length_time=16,
               plot_width=1200,
               # TODO this will break the offsets
               plot_height=400,
               show_bar=True,
               show_beat=True,
               title_text_font_size="14px",
               axis_label_text_font_size="12px",
               label_text_font_size="10px",
               label_text_font_style="normal",
               toolbar_location="right",
               live_reload=False):
    """TODO doc"""
    self._qpm = qpm
    self._plot_pitch_min = plot_pitch_min
    self._plot_pitch_max = plot_pitch_max
    self._plot_max_length_time = plot_max_length_time
    self._plot_width = plot_width
    self._plot_height = plot_height
    self._show_bar = show_bar
    self._show_beat = show_beat
    self._title_text_font_size = title_text_font_size
    self._axis_label_text_font_size = axis_label_text_font_size
    self._label_text_font_size = label_text_font_size
    self._label_text_font_style = getattr(FontStyle, label_text_font_style)
    self._toolbar_location = toolbar_location
    self._live_reload = live_reload
    self._show_counter = 0

  def _get_qpm(self, pretty_midi):
    """Returns the first tempo change that is not zero, raises exception
    if not found or multiple tempo present."""
    if self._qpm:
      return self._qpm
    qpm = None
    for tempo_change in pretty_midi.get_tempo_changes():
      if tempo_change.min() > 0 \
        and tempo_change.max() > 0 \
        and tempo_change.min() == tempo_change.max():
        if qpm:
          raise Exception("Multiple tempo changes are not supported "
                          + str(pretty_midi.get_tempo_changes()))
        qpm = tempo_change.min()
    if not qpm:
      raise Exception("Unknown qpm in: "
                      + str(pretty_midi.get_tempo_changes()))
    return qpm

  def _scale_time(self, qpm):
    return qpm / 120

  def plot(self, pretty_midi):
    """Plots the pretty midi object as a plot object."""

    # Calculates the QPM from the MIDI file, might raise exception if confused
    qpm = self._get_qpm(pretty_midi)

    # Initialize the tools, those are present on the right hand side
    plot = bokeh.plotting.figure(
      tools="reset,hover,previewsave,wheel_zoom,pan",
      toolbar_location=self._toolbar_location)

    # Setup the hover and the data dict for bokeh,
    # each property must match a property in the data dict
    plot.select(dict(type=bokeh.models.HoverTool)).tooltips = (
      {"pitch": "@top",
       "velocity": "@velocity",
       "duration": "@duration",
       "start_time": "@left",
       "end_time": "@right"})
    data = dict(
      top=[],
      bottom=[],
      left=[],
      right=[],
      duration=[],
      velocity=[],
      color=[],
    )

    # Puts the notes in the dict for bokeh
    # and saves first and last note time, bigger and smaller pitch
    pitch_min = None
    pitch_max = None
    first_note_start = None
    last_note_end = None
    for instrument in pretty_midi.instruments:
      for note in instrument.notes:
        pitch_min = min(pitch_min or self._MAX_PITCH, note.pitch)
        pitch_max = max(pitch_max or self._MIN_PITCH, note.pitch)
        color_index = (note.pitch - 36) % len(colors)
        note_start = note.start / self._scale_time(self._get_qpm(pretty_midi))
        note_end = (note.start + (note.end - note.start)) / \
                   self._scale_time(self._get_qpm(pretty_midi))
        data["top"].append(note.pitch)
        data["bottom"].append(note.pitch + 1)
        data["left"].append(note_start)
        data["right"].append(note_end)
        data["duration"].append(note_end - note_start)
        data["velocity"].append(note.velocity)
        data["color"].append(colors[color_index])
        if not first_note_start:
          first_note_start = note_start
        last_note_end = note_end

    # Shows an empty plot even if there are no notes
    if not first_note_start \
      or not last_note_end \
      or not pitch_min \
      or not pitch_max:
      pitch_min = self._MIN_PITCH
      pitch_max = pitch_min + 5
      first_note_start = 0
      last_note_end = 0

    # Stretch the plot to pitch min and pitch max if provided in constructor
    pitch_min = min(self._plot_pitch_min or self._MAX_PITCH, pitch_min)
    pitch_max = max(self._plot_pitch_max or self._MIN_PITCH, pitch_max)

    # Draws the rectangles on the splot from the data
    source = ColumnDataSource(data=data)
    plot.quad(left="left",
              right="right",
              top="top",
              bottom="bottom",
              line_alpha=1,
              line_color="black",
              color="color",
              source=source)

    # Draws the y grid by hand, because the grid has label on the ticks, but
    # for a plot like this, the labels needs to fit in between the ticks.
    # Also useful to change the background of the grid each line
    for pitch in range(pitch_min, pitch_max + 1):
      # Draws the background box and contours, on the underlay layer, so
      # that the rectangles and over the box annotations
      fill_alpha = (0.15 if pitch % 2 == 0 else 0.00)
      box = BoxAnnotation(bottom=pitch,
                          top=pitch + 1,
                          fill_color="gray",
                          fill_alpha=fill_alpha,
                          line_alpha=0.5,
                          level="underlay")
      plot.add_layout(box)
      # Draws the label on the left which is the pitch (36, 37, etc.)
      pitch_range = pitch_max + 1 - pitch_min
      offset = self._PITCH_OFFSETS.get(pitch_range, self._PITCH_OFFSET_DEFAULT)
      # TODO that doesn't work
      label = Label(x=-22 if self._label_text_font_size >= "15px" else -20,
                    y=pitch + offset,
                    x_units="screen",
                    text=str(pitch),
                    render_mode="css",
                    text_font_size=self._label_text_font_size,
                    text_font_style=self._label_text_font_style)
      plot.add_layout(label)

    # Calculates the number of seconds per bar, this is only useful to draw the
    # back of the grid
    quarter_per_seconds = qpm / 60
    seconds_per_quarter = 1 / quarter_per_seconds
    seconds_per_bar = seconds_per_quarter * 4

    # Calculates the plot start and end time, the start time can start after
    # notes or truncate notes if the plot is too long (we left truncate the
    # plot with the bounds)
    # The plot start and plot end are a multiple of seconds per bar (closest
    # smaller value for the start time, closest higher value for the end time)
    plot_end_time = int((last_note_end) / seconds_per_bar) * seconds_per_bar
    # If the last note end is exactly on a multiple of seconds per bar,
    # we don't start a new one
    if last_note_end % seconds_per_bar != 0:
      plot_end_time += seconds_per_bar
    plot_start_time = max(plot_end_time - self._plot_max_length_time,
                          int(first_note_start / seconds_per_bar) *
                          seconds_per_bar)

    # Draws the vertical bar grid, with a different background color
    # for each bar
    if self._show_bar:
      bar_count = 0
      for bar_time in _frange(plot_start_time, plot_end_time,
                              seconds_per_bar):
        fill_alpha = (0.25 if bar_count % 2 == 0 else 0.05)
        box = BoxAnnotation(left=bar_time,
                            right=bar_time + seconds_per_bar,
                            fill_color="gray",
                            line_color="black",
                            fill_alpha=fill_alpha,
                            line_alpha=0.25,
                            level="underlay")
        plot.add_layout(box)
        bar_count += 1

    # Draws the vertical beat grid, those are only grid lines
    if self._show_beat:
      for beat_time in _frange(plot_start_time, plot_end_time,
                               seconds_per_quarter):
        box = BoxAnnotation(left=beat_time,
                            right=beat_time + seconds_per_quarter,
                            fill_color=None,
                            line_color="black",
                            line_alpha=0.10,
                            level="underlay")
        plot.add_layout(box)

    # Configure x axis
    plot.xaxis.bounds = (plot_start_time, plot_end_time)
    plot.xaxis.axis_label = "time (SEC)"
    plot.xaxis.axis_label_text_font_size = self._axis_label_text_font_size
    plot.xaxis.ticker = bokeh.models.SingleIntervalTicker(interval=1)
    plot.xaxis.minor_tick_line_alpha = 0
    plot.xaxis.major_label_text_font_size = self._label_text_font_size
    plot.xaxis.major_label_text_font_style = self._label_text_font_style

    # Configure y axis
    plot.yaxis.bounds = (pitch_min, pitch_max + 1)
    plot.yaxis.axis_label = "pitch (MIDI)"
    plot.yaxis.axis_label_text_font_size = self._axis_label_text_font_size
    plot.yaxis.major_label_text_alpha = 0
    plot.yaxis.major_tick_line_alpha = 0
    plot.yaxis.minor_tick_line_alpha = 0

    # The x grid is deactivated because is draw by hand (see x grid code)
    plot.xgrid.grid_line_color = None

    # The y grid is deactivated because is draw by hand (see y grid code)
    plot.ygrid.grid_line_color = None

    # Configure the plot size and range
    plot.title = Title(text="Visual MIDI (QPM: " + str(qpm) + ")",
                       text_font_size=self._title_text_font_size)
    plot.plot_width = self._plot_width
    plot.plot_height = self._plot_height
    plot.x_range = Range1d(plot_start_time, plot_end_time)
    plot.y_range = Range1d(pitch_min, pitch_max + 1)

    if self._live_reload:
      callback = CustomJS(code="clearInterval(liveReloadInterval)")
      button = Button(label="stop live reload")
      button.js_on_click(callback)
      layout = column(button, plot)
    else:
      layout = column(plot)

    return layout

  def save(self, pretty_midi, plot_file):
    """Saves the pretty midi object as a plot file (html)
    in the provided file."""
    plot = self.plot(pretty_midi)
    output_file(plot_file)
    save(plot)
    return plot

  def show(self, pretty_midi, plot_file):
    """Shows the pretty midi object as a plot file (html) in the browser. If
    the live reload option is activated, the opened page will periodically
    refresh."""
    plot = self.plot(pretty_midi)
    if self._live_reload:
      html = file_html(plot, CDN)
      html = html.replace("</head>", """
              <script type="text/javascript">
                var liveReloadInterval = window.setInterval(function(){
                  location.reload();
                }, 2000);
              </script>
              </head>""")
      with open(plot_file, 'w') as file:
        file.write(html)
      if self._show_counter == 0:
        import webbrowser
        webbrowser.open("file://" + os.path.realpath(plot_file), new=2)
    else:
      output_file(plot_file)
      show(plot)
    self._show_counter += 1
    return plot


def console_entry_point():
  plot_configuration_keys = [
    ("qpm", int),
    ("plot_pitch_min", int),
    ("plot_pitch_max", int),
    ("plot_max_length_time", int),
    ("plot_width", int),
    ("plot_height", int),
    ("show_bar", bool),
    ("show_beat", bool),
    # TODO use int
    ("title_text_font_size", str),
    # TODO use int
    ("axis_label_text_font_size", str),
    # TODO use int
    ("label_text_font_size", str),
    ("label_text_font_style", str),
    ("toolbar_location", str),
  ]

  parser = argparse.ArgumentParser()
  [parser.add_argument("--" + key[0], type=key[1])
   for key in plot_configuration_keys]
  parser.add_argument("files", nargs='+')
  args = parser.parse_args()

  kwargs = {key[0]: (None if getattr(args, key[0]) == "None"
                     else getattr(args, key[0]))
            for key in plot_configuration_keys
            if getattr(args, key[0], None)}
  plotter = Plotter(**kwargs)

  for midi_file in args.files:
    plot_file = midi_file.replace(".mid", ".html")
    print("Plotting midi file " + midi_file + " to " + plot_file)
    pretty_midi = PrettyMIDI(midi_file)
    plotter.save(pretty_midi, plot_file)
  sys.exit(0)


if __name__ == '__main__':
  console_entry_point()
