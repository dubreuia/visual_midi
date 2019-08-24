import argparse
import os
import sys

import bokeh
import bokeh.plotting
from bokeh.colors.groups import purple as colors
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


class Preset:
  PRESET_DEFAULT = {
    "plot_width": 1200,
    "plot_height": 400,
    "row_height": 25,
    "show_bar": True,
    "show_beat": True,
    "title_text_font_size": "14px",
    "axis_label_text_font_size": "12px",
    "axis_x_major_tick_out": 5,
    "axis_y_major_tick_out": 25,
    "label_y_axis_offset_x": -18,
    "label_y_axis_offset_y": 0.1,
    "axis_y_label_standoff": 0,
    "label_text_font_size": "10px",
    "label_text_font_style": "normal",
    "toolbar_location": "right",
    "stop_live_reload_button": True,
  }

  PRESET_SMALL = {
    "title_text_font_size": "0px",
    "label_text_font_size": "8px",
    "axis_label_text_font_size": "0px",
    "label_y_axis_offset_y": 0,
    "plot_width": 500,
    "plot_height": 200,
    "toolbar_location": None,
    "stop_live_reload_button": False,
  }

  PRESET_4K = {
    "title_text_font_size": "65px",
    "label_text_font_size": "60px",
    "axis_label_text_font_size": "55px",
    "plot_width": 3840,
    "row_height": 125,
    "axis_x_major_tick_out": 25,
    "axis_y_major_tick_out": 100,
    "label_y_axis_offset_x": -85,
    "label_y_axis_offset_y": 0.075,
    "axis_x_label_standoff": 20,
    "axis_y_label_standoff": 20,
    "toolbar_location": None,
  }

  PRESETS = {
    "PRESET_DEFAULT": PRESET_DEFAULT,
    "PRESET_4K": PRESET_4K,
    "PRESET_SMALL": PRESET_SMALL,
  }

  def __init__(self, config=None):
    self.config = {key: value for key, value in self.PRESET_DEFAULT.items()}
    if isinstance(config, dict):
      self.config = {key: value for key, value in config.items()}
    elif config:
      self.config = {key: value for key, value in self.PRESETS[config].items()}

  def __getitem__(self, item):
    return self.config.get(item, self.PRESET_DEFAULT.get(item))

  def is_defined(self, item):
    return self.config.get(item, None)


class Plotter:
  """A plotter class with plot size, time scaling and live reload
  configuration.

  TODO args
  """

  _MAX_PITCH = 127
  _MIN_PITCH = 0

  def __init__(self,
               qpm=None,
               plot_pitch_min=None,
               plot_pitch_max=None,
               plot_max_length_time=16,
               live_reload=False,
               preset=Preset()):
    """TODO doc"""
    self._qpm = qpm
    self._plot_pitch_min = plot_pitch_min
    self._plot_pitch_max = plot_pitch_max
    self._plot_max_length_time = plot_max_length_time
    self._live_reload = live_reload
    self._show_counter = 0
    self._preset = preset

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
      toolbar_location=self._preset["toolbar_location"])

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
        data["color"].append(colors[color_index].lighten(0.1))
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
    pitch_range = pitch_max + 1 - pitch_min

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
                          line_color="black",
                          line_alpha=0.3,
                          line_width=1,
                          level="underlay")
      plot.add_layout(box)
      label = Label(
        x=self._preset["label_y_axis_offset_x"],
        y=pitch + self._preset["label_y_axis_offset_y"],
        x_units="screen",
        text=str(pitch),
        render_mode="css",
        text_font_size=self._preset["label_text_font_size"],
        text_font_style=self._preset["label_text_font_style"])
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
    if self._preset["show_bar"]:
      bar_count = 0
      for bar_time in _frange(plot_start_time, plot_end_time,
                              seconds_per_bar):
        fill_alpha = (0.25 if bar_count % 2 == 0 else 0.05)
        box = BoxAnnotation(left=bar_time,
                            right=bar_time + seconds_per_bar,
                            fill_color="gray",
                            fill_alpha=fill_alpha,
                            line_color="black",
                            line_width=2,
                            line_alpha=0.5,
                            level="underlay")
        plot.add_layout(box)
        bar_count += 1

    # Draws the vertical beat grid, those are only grid lines
    if self._preset["show_beat"]:
      for beat_time in _frange(plot_start_time, plot_end_time,
                               seconds_per_quarter):
        box = BoxAnnotation(left=beat_time,
                            right=beat_time + seconds_per_quarter,
                            fill_color=None,
                            line_color="black",
                            line_width=1,
                            line_alpha=0.4,
                            level="underlay")
        plot.add_layout(box)

    # Configure x axis
    plot.xaxis.bounds = (plot_start_time, plot_end_time)
    plot.xaxis.axis_label = "time (SEC)"
    plot.xaxis.axis_label_text_font_size = self._preset[
      "axis_label_text_font_size"]
    plot.xaxis.ticker = bokeh.models.SingleIntervalTicker(interval=1)
    plot.xaxis.major_tick_line_alpha = 0.9
    plot.xaxis.major_tick_line_width = 1
    plot.xaxis.major_tick_out = self._preset[
      "axis_x_major_tick_out"]
    plot.xaxis.minor_tick_line_alpha = 0
    plot.xaxis.major_label_text_font_size = self._preset[
      "label_text_font_size"]
    plot.xaxis.major_label_text_font_style = self._preset[
      "label_text_font_style"]

    # Configure y axis
    plot.yaxis.bounds = (pitch_min, pitch_max + 1)
    plot.yaxis.axis_label = "pitch (MIDI)"
    plot.yaxis.axis_label_text_font_size = self._preset[
      "axis_label_text_font_size"]
    plot.yaxis.ticker = bokeh.models.SingleIntervalTicker(interval=1)
    plot.yaxis.major_label_text_alpha = 0
    plot.yaxis.major_tick_line_alpha = 0.9
    plot.yaxis.major_tick_line_width = 1
    plot.yaxis.major_tick_out = self._preset["axis_y_major_tick_out"]
    plot.yaxis.minor_tick_line_alpha = 0
    plot.yaxis.axis_label_standoff = self._preset["axis_y_label_standoff"]
    plot.outline_line_width = 1
    plot.outline_line_alpha = 1
    plot.outline_line_color = "black"

    # The x grid is deactivated because is draw by hand (see x grid code)
    plot.xgrid.grid_line_color = None

    # The y grid is deactivated because is draw by hand (see y grid code)
    plot.ygrid.grid_line_color = None

    # Configure the plot size and range
    plot.title = Title(text="Visual MIDI (QPM: " + str(int(qpm)) + ")",
                       text_font_size=self._preset["title_text_font_size"])
    plot.plot_width = self._preset["plot_width"]
    if self._preset.is_defined("plot_height"):
      plot.plot_height = self._preset["plot_height"]
    else:
      plot.plot_height = pitch_range * self._preset["row_height"]
    plot.x_range = Range1d(plot_start_time, plot_end_time)
    plot.y_range = Range1d(pitch_min, pitch_max + 1)
    plot.min_border_right = 50

    if self._live_reload and self._preset["stop_live_reload_button"]:
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
    # TODO refactor
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
    else:
      output_file(plot_file)
      save(plot)
    return plot

  def show(self, pretty_midi, plot_file):
    """Shows the pretty midi object as a plot file (html) in the browser. If
    the live reload option is activated, the opened page will periodically
    refresh."""
    plot = self.plot(pretty_midi)
    # TODO refactor
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
  plot_conf_keys = [
    ("qpm", int),
    ("plot_pitch_min", int),
    ("plot_pitch_max", int),
    ("plot_max_length_time", int),
    ("live_reload", bool),
  ]

  parser = argparse.ArgumentParser()
  [parser.add_argument("--" + key[0], type=key[1]) for key in plot_conf_keys]
  parser.add_argument("--preset", type=str)
  parser.add_argument("files", type=str, nargs='+')
  args = parser.parse_args()

  preset = Preset(config=(getattr(args, "preset", None)))
  plot_conf_kwargs = {key[0]: (None if getattr(args, key[0]) == "None"
                               else getattr(args, key[0]))
                      for key in plot_conf_keys
                      if getattr(args, key[0], None)}
  plotter = Plotter(preset=preset, **plot_conf_kwargs)

  for midi_file in args.files:
    plot_file = midi_file.replace(".mid", ".html")
    print("Plotting midi file " + midi_file + " to " + plot_file)
    pretty_midi = PrettyMIDI(midi_file)
    plotter.save(pretty_midi, plot_file)
  sys.exit(0)


if __name__ == '__main__':
  console_entry_point()
