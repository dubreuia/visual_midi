"""
Converts a pretty midi sequence to a boket plot
"""
import argparse
import ast
import math
import os
import sys
from typing import List
from typing import Tuple

import bokeh
import bokeh.plotting
from bokeh.colors.groups import purple as colors
from bokeh.embed import file_html
from bokeh.io import output_file
from bokeh.io import save
from bokeh.io import show
from bokeh.layouts import column
from bokeh.models import BoxAnnotation
from bokeh.models import ColumnDataSource
from bokeh.models import Label
from bokeh.models import Range1d
from bokeh.models import Title
from bokeh.models.callbacks import CustomJS
from bokeh.models.widgets.buttons import Button
from bokeh.resources import CDN
from pretty_midi import PrettyMIDI
from pretty_midi import TimeSignature

from .presets import Coloring
from .presets import Preset


class Plotter:
  """
  Plotter class with plot size, time scaling and live reload
  configuration.
  """

  _MAX_PITCH = 127
  _MIN_PITCH = 0

  def __init__(self,
               preset: Preset = None,
               qpm: float = None,
               plot_pitch_range_start: int = None,
               plot_pitch_range_stop: int = None,
               plot_bar_range_start: int = None,
               plot_bar_range_stop: int = None,
               plot_max_length_bar: int = 8,
               bar_fill_alphas: List[float] = None,
               coloring: Coloring = Coloring.PITCH,
               show_velocity: bool = False,
               midi_time_signature: str = None,
               live_reload: bool = False):
    if not preset:
      preset = Preset()
    if not bar_fill_alphas:
      bar_fill_alphas = [0.25, 0.05]
    self._preset = preset
    self._qpm = qpm
    self._plot_pitch_range_start = plot_pitch_range_start
    self._plot_pitch_range_stop = plot_pitch_range_stop
    self._plot_bar_range_start = plot_bar_range_start
    self._plot_bar_range_stop = plot_bar_range_stop
    self._plot_max_length_bar = plot_max_length_bar
    self._bar_fill_alphas = bar_fill_alphas
    self._coloring = coloring
    self._show_velocity = show_velocity
    self._midi_time_signature = midi_time_signature
    self._live_reload = live_reload
    self._show_counter = 0

  def _get_qpm(self, pm: PrettyMIDI):
    """
    Returns the first tempo change that is not zero, raises exception
    if not found or multiple tempo present.
    """
    if self._qpm:
      return self._qpm
    qpm = None
    for tempo_change in pm.get_tempo_changes():
      if (tempo_change.min() and tempo_change.max()
        and tempo_change.min() == tempo_change.max()):
        if qpm:
          raise Exception("Multiple tempo changes are not supported "
                          + str(pm.get_tempo_changes()))
        qpm = tempo_change.min()
    if not qpm:
      raise Exception("Unknown qpm in: "
                      + str(pm.get_tempo_changes()))
    return qpm

  def _get_color(self, index_instrument, note):
    """
    Returns the color for the instrument and the note, depends
    on self._coloring.
    """
    if self._coloring is Coloring.PITCH:
      color_index = (note.pitch - 36) % len(colors)
    elif self._coloring is Coloring.INSTRUMENT:
      color_index = ((index_instrument + 1) * 5) % len(colors)
    else:
      raise Exception("Unknown coloring: " + str(self._coloring))
    color = colors[color_index]
    color = color.lighten(0.1)
    return color

  def plot(self, pm: PrettyMIDI):
    """
    Plots the pretty midi object as a plot object.

      :param pm: the PrettyMIDI instance to plot
      :return: the bokeh plot layout
    """
    preset = self._preset

    # Calculates the QPM from the MIDI file, might raise exception if confused
    qpm = self._get_qpm(pm)

    # Initialize the tools, those are present on the right hand side
    plot = bokeh.plotting.figure(
      tools="reset,hover,save,wheel_zoom,pan",
      toolbar_location=preset.toolbar_location)

    # Setup the hover and the data dict for bokeh,
    # each property must match a property in the data dict
    plot.select(dict(type=bokeh.models.HoverTool)).tooltips = ({
      "program": "@program",
      "pitch": "@top",
      "velocity": "@velocity",
      "duration": "@duration",
      "start_time": "@left",
      "end_time": "@right"})
    data = dict(
      program=[],
      top=[],
      bottom=[],
      left=[],
      right=[],
      duration=[],
      velocity=[],
      color=[])

    # Puts the notes in the dict for bokeh and saves first
    # and last note time, bigger and smaller pitch
    pitch_min = None
    pitch_max = None
    first_note_start = None
    last_note_end = None
    index_instrument = 0
    for instrument in pm.instruments:
      for note in instrument.notes:
        pitch_min = min(pitch_min or self._MAX_PITCH, note.pitch)
        pitch_max = max(pitch_max or self._MIN_PITCH, note.pitch)
        color = self._get_color(index_instrument, note)
        note_start = note.start
        note_end = note.start + (note.end - note.start)
        data["program"].append(instrument.program)
        data["top"].append(note.pitch)
        if self._show_velocity:
          data["bottom"].append(note.pitch + (note.velocity / 127))
        else:
          data["bottom"].append(note.pitch + 1)
        data["left"].append(note_start)
        data["right"].append(note_end)
        data["duration"].append(note_end - note_start)
        data["velocity"].append(note.velocity)
        data["color"].append(color)
        first_note_start = min(first_note_start or sys.maxsize, note_start)
        last_note_end = max(last_note_end or 0, note_end)
      index_instrument = index_instrument + 1

    # Shows an empty plot even if there are no notes
    if (first_note_start is None or last_note_end is None
      or pitch_min is None or pitch_max is None):
      pitch_min = self._MIN_PITCH
      pitch_max = pitch_min + 5
      first_note_start = 0
      last_note_end = 0

    # Gets the pitch range (min, max) from either the provided arguments
    # or min and max values from the notes
    if self._plot_pitch_range_start is not None:
      pitch_min = self._plot_pitch_range_start
    else:
      pitch_min = min(self._MAX_PITCH, pitch_min)
    if self._plot_pitch_range_stop is not None:
      pitch_max = self._plot_pitch_range_stop
    else:
      pitch_max = max(self._MIN_PITCH, pitch_max)

    pitch_range = pitch_max + 1 - pitch_min

    # Draws the rectangles on the plot from the data
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
        x=preset.label_y_axis_offset_x,
        y=pitch + preset.label_y_axis_offset_y,
        x_units="screen",
        text=str(pitch),
        render_mode="css",
        text_font_size=preset.label_text_font_size,
        text_font_style=preset.label_text_font_style)
      plot.add_layout(label)

    # Gets the time signature from pretty midi, or 4/4 if none
    if self._midi_time_signature:
      numerator, denominator = self._midi_time_signature.split("/")
      time_signature = TimeSignature(int(numerator), int(denominator), 0)
    else:
      if pm.time_signature_changes:
        if len(pm.time_signature_changes) > 1:
          raise Exception("Multiple time signatures are not supported")
        time_signature = pm.time_signature_changes[0]
      else:
        time_signature = TimeSignature(4, 4, 0)

    # Gets seconds per bar and seconds per beat
    if len(pm.get_beats()) >= 2:
      seconds_per_beat = pm.get_beats()[1] - pm.get_beats()[0]
    else:
      seconds_per_beat = 0.5
    if len(pm.get_downbeats()) >= 2:
      seconds_per_bar = pm.get_downbeats()[1] - pm.get_downbeats()[0]
    else:
      seconds_per_bar = 2.0

    # Defines the end time of the plot in seconds
    if self._plot_bar_range_stop is not None:
      plot_end_time = self._plot_bar_range_stop * seconds_per_bar
    else:
      # Calculates the plot start and end time, the start time can start after
      # notes or truncate notes if the plot is too long (we left truncate the
      # plot with the bounds)
      # The plot start and plot end are a multiple of seconds per bar (closest
      # smaller value for the start time, closest higher value for the end time)
      plot_end_time = int((last_note_end) / seconds_per_bar) * seconds_per_bar
      # If the last note end is exactly on a multiple of seconds per bar,
      # we don't start a new one
      is_on_bar = math.isclose(last_note_end % seconds_per_bar, seconds_per_bar)
      is_on_bar_exact = math.isclose(last_note_end % seconds_per_bar, 0.0)
      if not is_on_bar and not is_on_bar_exact:
        plot_end_time += seconds_per_bar

    # Defines the start time of the plot in seconds
    if self._plot_bar_range_start is not None:
      plot_start_time = self._plot_bar_range_start * seconds_per_bar
    else:
      start_time = int(first_note_start / seconds_per_bar) * seconds_per_bar
      plot_max_length_time = self._plot_max_length_bar * seconds_per_bar
      plot_start_time = max(plot_end_time - plot_max_length_time, start_time)

    # Draws the vertical bar grid, with a different background color
    # for each bar
    if preset.show_bar:
      bar_count = 0
      for bar_time in pm.get_downbeats():
        fill_alpha_index = bar_count % len(self._bar_fill_alphas)
        fill_alpha = self._bar_fill_alphas[fill_alpha_index]
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
    if preset.show_beat:
      for beat_time in pm.get_beats():
        box = BoxAnnotation(left=beat_time,
                            right=beat_time + seconds_per_beat,
                            fill_color=None,
                            line_color="black",
                            line_width=1,
                            line_alpha=0.4,
                            level="underlay")
        plot.add_layout(box)

    # Configure x axis
    plot.xaxis.bounds = (plot_start_time, plot_end_time)
    plot.xaxis.axis_label = "time (SEC)"
    plot.xaxis.axis_label_text_font_size = preset.axis_label_text_font_size
    plot.xaxis.ticker = bokeh.models.SingleIntervalTicker(interval=1)
    plot.xaxis.major_tick_line_alpha = 0.9
    plot.xaxis.major_tick_line_width = 1
    plot.xaxis.major_tick_out = preset.axis_x_major_tick_out
    plot.xaxis.minor_tick_line_alpha = 0
    plot.xaxis.major_label_text_font_size = preset.label_text_font_size
    plot.xaxis.major_label_text_font_style = preset.label_text_font_style

    # Configure y axis
    plot.yaxis.bounds = (pitch_min, pitch_max + 1)
    plot.yaxis.axis_label = "pitch (MIDI)"
    plot.yaxis.axis_label_text_font_size = preset.axis_label_text_font_size
    plot.yaxis.ticker = bokeh.models.SingleIntervalTicker(interval=1)
    plot.yaxis.major_label_text_alpha = 0
    plot.yaxis.major_tick_line_alpha = 0.9
    plot.yaxis.major_tick_line_width = 1
    plot.yaxis.major_tick_out = preset.axis_y_major_tick_out
    plot.yaxis.minor_tick_line_alpha = 0
    plot.yaxis.axis_label_standoff = preset.axis_y_label_standoff
    plot.outline_line_width = 1
    plot.outline_line_alpha = 1
    plot.outline_line_color = "black"

    # The x grid is deactivated because is draw by hand (see x grid code)
    plot.xgrid.grid_line_color = None

    # The y grid is deactivated because is draw by hand (see y grid code)
    plot.ygrid.grid_line_color = None

    # Configure the plot size and range
    plot_title_text = "Visual MIDI (%s QPM, %s/%s)" % (
      str(int(qpm)), time_signature.numerator, time_signature.denominator)
    plot.title = Title(text=plot_title_text,
                       text_font_size=preset.title_text_font_size)
    plot.plot_width = preset.plot_width
    if preset.row_height:
      plot.plot_height = pitch_range * preset.row_height
    else:
      plot.plot_height = preset.plot_height
    plot.x_range = Range1d(plot_start_time, plot_end_time)
    plot.y_range = Range1d(pitch_min, pitch_max + 1)
    plot.min_border_right = 50

    if self._live_reload and preset.stop_live_reload_button:
      callback = CustomJS(code="clearInterval(liveReloadInterval)")
      button = Button(label="stop live reload")
      button.js_on_click(callback)
      layout = column(button, plot)
    else:
      layout = column(plot)

    return layout

  def save(self, pm: PrettyMIDI, filepath: str):
    """
    Saves the pretty midi object as a plot file (html) in the provided file. If
    the live reload option is activated, the opened page will periodically
    refresh.

      :param pm: the PrettyMIDI instance to plot
      :param filepath: the file path to save the resulting plot to
      :return: the bokeh plot layout
    """
    plot = self.plot(pm)
    if self._live_reload:
      html = file_html(plot, CDN)
      html = html.replace("</head>", """
              <script type="text/javascript">
                var liveReloadInterval = window.setInterval(function(){
                  location.reload();
                }, 2000);
              </script>
              </head>""")
      with open(filepath, 'w') as file:
        file.write(html)
    else:
      output_file(filepath)
      save(plot)
    return plot

  def show(self, pm: PrettyMIDI, filepath: str):
    """
    Shows the pretty midi object as a plot file (html) in the browser. If
    the live reload option is activated, the opened page will periodically
    refresh.

      :param pm: the PrettyMIDI instance to plot
      :param filepath: the file path to save the resulting plot to
      :return: the bokeh plot layout
    """
    plot = self.plot(pm)
    if self._live_reload:
      html = file_html(plot, CDN)
      html = html.replace("</head>", """
              <script type="text/javascript">
                var liveReloadInterval = window.setInterval(function(){
                  location.reload();
                }, 2000);
              </script>
              </head>""")
      with open(filepath, 'w') as file:
        file.write(html)
      if self._show_counter == 0:
        import webbrowser
        webbrowser.open("file://" + os.path.realpath(filepath), new=2)
    else:
      output_file(filepath)
      show(plot)
    self._show_counter += 1
    return plot


def console_entry_point():
  flags_plot = [
    ("qpm", int),
    ("plot_pitch_range_start", int),
    ("plot_pitch_range_stop", int),
    ("plot_bar_range_start", int),
    ("plot_bar_range_stop", int),
    ("plot_max_length_bar", int),
    ("bar_fill_alphas", str, ast.literal_eval),
    ("coloring", str, Coloring.from_name),
    ("show_velocity", str, ast.literal_eval),
    ("midi_time_signature", str),
    ("live_reload", str, ast.literal_eval),
  ]
  flags_preset = [
    ("plot_width", int),
    ("plot_height", int),
    ("row_height", int),
    ("show_bar", str, ast.literal_eval),
    ("show_beat", str, ast.literal_eval),
    ("title_text_font_size", str),
    ("axis_label_text_font_size", str),
    ("axis_x_major_tick_out", int),
    ("axis_y_major_tick_out", int),
    ("label_y_axis_offset_x", float),
    ("label_y_axis_offset_y", float),
    ("axis_y_label_standoff", int),
    ("label_text_font_size", str),
    ("label_text_font_style", str),
    ("toolbar_location", str),
    ("stop_live_reload_button", str, ast.literal_eval),
  ]
  parser = argparse.ArgumentParser()
  [parser.add_argument("--" + flag[0], type=flag[1]) for flag in flags_plot]
  [parser.add_argument("--" + flag[0], type=flag[1]) for flag in flags_preset]
  parser.add_argument("files", type=str, nargs='+')
  args = parser.parse_args()

  def _eval_parser_arg(flag: Tuple):
    value = None if getattr(args, flag[0]) == "None" else getattr(args, flag[0])
    if not value:
      return None
    if len(flag) == 3:
      try:
        return flag[2](value)
      except ValueError:
        raise Exception("Cannot transform flag '" + str(flag[0])
                        + "' of type '" + str(flag[1])
                        + "' with value '" + str(value) + "'")
    return value

  kwargs_preset = {flag[0]: _eval_parser_arg(flag)
                   for flag in flags_preset
                   if getattr(args, flag[0], None)}
  preset = Preset(**kwargs_preset)

  kwargs_plotter = {flag[0]: _eval_parser_arg(flag)
                    for flag in flags_plot
                    if getattr(args, flag[0], None)}
  plotter = Plotter(preset=preset, **kwargs_plotter)

  for midi_file in args.files:
    plot_file = midi_file.replace(".mid", ".html")
    print("Plotting midi file " + midi_file + " to " + plot_file)
    pretty_midi = PrettyMIDI(midi_file)
    plotter.save(pretty_midi, plot_file)
  sys.exit(0)


if __name__ == '__main__':
  console_entry_point()
