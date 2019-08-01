import os
import sys
from enum import Enum

import bokeh
import bokeh.plotting
from bokeh.colors.groups import purple as colors
from bokeh.embed import file_html
from bokeh.io import output_file, show
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


class TimeScaling(Enum):
  SEC = 1
  BAR = 2

  def __str__(self):
    return self.name


class Plotter:
  _MAX_PITCH = 127
  _MIN_PITCH = 0

  _X_FILL_ALPHA_EVEN = 0.15
  _X_FILL_ALPHA_ODD = 0.0
  _X_LINE_ALPHA = 0.5

  _Y_BAR_FILL_ALPHA_EVEN = 0.15
  _Y_BAR_FILL_ALPHA_ODD = 0.0
  _Y_BAR_LINE_ALPHA = 0.75

  _Y_BEAT_FILL_ALPHA = 0
  _Y_BEAT_LINE_ALPHA = 0.3

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
               plot_pitch_min=None,
               plot_pitch_max=None,
               plot_max_length_time=8,
               time_scaling=TimeScaling.SEC,
               live_reload=False):
    self._plot_pitch_min = plot_pitch_min
    self._plot_pitch_max = plot_pitch_max
    self._plot_max_length_time = plot_max_length_time
    self._time_scaling = time_scaling
    self._live_reload = live_reload
    self._show_counter = 0

  def _get_qpm(self, pretty_midi):
    """Returns the first tempo change that is not zero, raises exception
    if not found or multiple tempo present."""
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

  def plot(self, pretty_midi):
    # Calculates the QPM from the MIDI file, might raise exception if confused
    qpm = self._get_qpm(pretty_midi)

    # Initialize the tools, those are present on the right hand side
    plot = bokeh.plotting.figure(tools="reset,hover,previewsave,wheel_zoom,pan")

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
        start_beat = note.start
        end_beat = note.start + (note.end - note.start)
        data["top"].append(note.pitch)
        data["bottom"].append(note.pitch + 1)
        data["left"].append(start_beat)
        data["right"].append(end_beat)
        data["duration"].append(end_beat - start_beat)
        data["velocity"].append(note.velocity)
        data["color"].append(colors[color_index])
        if not first_note_start:
          first_note_start = note.start
        last_note_end = note.end

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
      fill_alpha = (self._X_FILL_ALPHA_EVEN
                    if pitch % 2 == 0
                    else self._X_FILL_ALPHA_ODD)
      box = BoxAnnotation(bottom=pitch,
                          top=pitch + 1,
                          fill_color="gray",
                          fill_alpha=fill_alpha,
                          line_alpha=self._X_LINE_ALPHA,
                          level="underlay")
      plot.add_layout(box)
      # Draws the label on the left which is the pitch (36, 37, etc.)
      pitch_range = pitch_max + 1 - pitch_min
      offset = self._PITCH_OFFSETS.get(pitch_range, self._PITCH_OFFSET_DEFAULT)
      label = Label(x=-20,
                    y=pitch + offset,
                    x_units="screen",
                    text=str(pitch),
                    render_mode="css",
                    text_font_size="8pt")
      plot.add_layout(label)

    # Calculates the number of seconds per bar, this is only useful to draw the
    # back of the grid
    quarter_per_seconds = qpm / 60
    seconds_per_quarter = 1 / quarter_per_seconds
    seconds_per_bar = seconds_per_quarter * 4

    # Calculates the plot start and end time, the start time can start after
    # notes or truncate notes if the plot is too long (we left truncate the
    # plot with the bounds)
    # The adjustment 0.000001 is to make sure a note ending right on the last
    # bar wouldn't force the show of the next bar
    plot_end_time = int((last_note_end - 0.00001) / seconds_per_bar) \
                    * seconds_per_bar + seconds_per_bar
    plot_start_time = max(plot_end_time - self._plot_max_length_time,
                          int(first_note_start / seconds_per_bar) *
                          seconds_per_bar)

    # Draws the vertical bar grid, with a different background color
    # for each bar
    for bar in _frange(plot_start_time, plot_end_time, seconds_per_bar):
      bar_count = bar / seconds_per_bar
      fill_alpha = (self._Y_BAR_FILL_ALPHA_EVEN
                    if bar_count % 2 == 0
                    else self._Y_BAR_FILL_ALPHA_ODD)
      box = BoxAnnotation(left=bar,
                          right=bar + seconds_per_bar,
                          fill_color="gray",
                          fill_alpha=fill_alpha,
                          line_alpha=self._Y_BAR_FILL_ALPHA_EVEN)
      box.level = "underlay"
      plot.add_layout(box)

    # Draws the vertical beat grid, those are only grid lines
    for beat in _frange(plot_start_time, plot_end_time, seconds_per_quarter):
      box = BoxAnnotation(left=beat,
                          right=beat + seconds_per_quarter,
                          fill_color=None,
                          fill_alpha=self._Y_BEAT_FILL_ALPHA,
                          line_alpha=self._Y_BEAT_LINE_ALPHA)
      box.level = "underlay"
      plot.add_layout(box)

    # Configure x axis
    plot.xaxis.bounds = (plot_start_time, plot_end_time)
    plot.xaxis.axis_label = "time (" + str(self._time_scaling) + ")"
    plot.xaxis.ticker = bokeh.models.SingleIntervalTicker(interval=1)
    plot.xaxis.minor_tick_line_alpha = 0

    # Configure y axis
    plot.yaxis.bounds = (pitch_min, pitch_max + 1)
    plot.yaxis.axis_label = "pitch (MIDI)"
    plot.yaxis.major_label_text_alpha = 0
    plot.yaxis.major_tick_line_alpha = 0
    plot.yaxis.minor_tick_line_alpha = 0

    # The x grid is kept as is
    plot.xgrid.grid_line_color = "black"
    plot.xgrid.grid_line_alpha = 0.30
    plot.xgrid.grid_line_width = 1
    plot.xgrid.grid_line_color = "black"

    # The y grid is deactivated because is draw by hand (see y grid code)
    plot.ygrid.grid_line_color = None

    # Configure the plot size and range
    plot.title = Title(text="Visual MIDI (qpm: " + str(qpm) + ")")
    plot.plot_width = 1200
    plot.plot_height = 300
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

  def show(self, pretty_midi, plot_file):
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


if __name__ == "__main__":
  for midi_file in sys.argv[1:]:
    plot_file = midi_file.replace(".mid", ".html")
    print("Plotting midi file " + midi_file + " to " + plot_file)
    pretty_midi = PrettyMIDI(midi_file)
    plotter = Plotter(time_scaling=TimeScaling.SEC)
    plotter.show(pretty_midi, plot_file)
  sys.exit(0)
