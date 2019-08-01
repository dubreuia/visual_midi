import os
import sys
from enum import Enum

import bokeh
import bokeh.plotting
from bokeh.colors.groups import purple as colors
from bokeh.embed import file_html
from bokeh.io import output_file, show
from bokeh.layouts import column
from bokeh.models import BoxAnnotation, ColumnDataSource
from bokeh.models import Range1d, Label
from bokeh.models.callbacks import CustomJS
from bokeh.models.widgets.buttons import Button
from bokeh.resources import CDN
from pretty_midi import PrettyMIDI

BOX_HORIZONTAL_FILL_ALPHA_EVEN = 0.15
BOX_HORIZONTAL_FILL_ALPHA_ODD = 0.0
BOX_HORIZONTAL_LINE_ALPHA = 0.5

BOX_VERTICAL_FILL_ALPHA_EVEN = 0.15
BOX_VERTICAL_FILL_ALPHA_ODD = 0.0
BOX_VERTICAL_LINE_ALPHA = 0.75

BOX_BEAT_VERTICAL_FILL_ALPHA = 0
BOX_BEAT_VERTICAL_LINE_ALPHA = 0.3


class TimeScaling(Enum):
  SEC = 1
  BAR = 2

  def __str__(self):
    return self.name


class Plotter:
  MAX_PITCH = 127
  MIN_PITCH = 0

  def __init__(self,
               qpm=120,
               beat_per_bar=4,
               plot_bar_min=1,
               plot_bar_max=8,
               plot_pitch_min=None,
               plot_pitch_max=None,
               time_scaling=TimeScaling.SEC,
               live_reload=False):
    self._qpm = qpm
    self._beat_per_bar = beat_per_bar
    self._plot_bar_min = plot_bar_min
    self._plot_bar_max = plot_bar_max
    self._plot_pitch_min = plot_pitch_min
    self._plot_pitch_max = plot_pitch_max
    self._time_scaling = time_scaling
    self._live_reload = live_reload
    self._show_counter = 0

  def _is_note_filtered(self, pretty_midi, note):
    if not self._plot_bar_max:
      return True
    min_time = int(pretty_midi.get_end_time() - self._plot_bar_max + 1)
    if note.start < min_time:
      return False
    return True

  def plot_midi(self, pretty_midi):
    plot = bokeh.plotting.figure(tools="reset,hover,previewsave,wheel_zoom,pan")

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

    pitch_min = None
    pitch_max = None
    first_note = None
    last_note = None
    for instrument in pretty_midi.instruments:
      for note in instrument.notes:
        if self._is_note_filtered(pretty_midi, note):
          pitch_min = min(pitch_min or self.MAX_PITCH, note.pitch)
          pitch_max = max(pitch_max or self.MIN_PITCH, note.pitch)
          color_index = (note.pitch - 36) % len(colors)
          start_beat = note.start
          end_beat = note.start + (note.end - note.start)
          data["top"].append(note.pitch)
          data["bottom"].append(note.pitch + 1)
          data["left"].append(start_beat)
          data["right"].append(end_beat)
          data["duration"].append(end_beat - start_beat)
          data["velocity"].append(note.velocity)
          data["color"].append(colors[color_index].lighten(0))
          if not first_note:
            first_note = note
          last_note = note

    if not first_note or not last_note or not pitch_min or not pitch_max:
      # TODO show empty plot
      raise Exception("No note in the file")

    pitch_min = min(self._plot_pitch_min or self.MAX_PITCH, pitch_min)
    pitch_max = max(self._plot_pitch_max or self.MIN_PITCH, pitch_max)

    source = ColumnDataSource(data=data)
    plot.quad(left="left",
              right="right",
              top="top",
              bottom="bottom",
              line_alpha=1,
              line_color="black",
              color="color",
              source=source)

    # Vertical axis
    for pitch in range(pitch_min, pitch_max + 1):
      if pitch % 2 == 0:
        fill_alpha = BOX_HORIZONTAL_FILL_ALPHA_EVEN
      else:
        fill_alpha = BOX_HORIZONTAL_FILL_ALPHA_ODD
      box = BoxAnnotation(bottom=pitch,
                          top=pitch + 1,
                          fill_color="gray",
                          fill_alpha=fill_alpha,
                          line_alpha=BOX_HORIZONTAL_LINE_ALPHA)
      box.level = "underlay"
      plot.add_layout(box)
      label = Label(x=-20,
                    # TODO calculate with plot height / number of sep
                    y=pitch + (300 / 350 / (pitch_max + 1 - pitch_min)),
                    x_units="screen",
                    text=str(pitch),
                    render_mode="css",
                    text_font_size="8pt")
      plot.add_layout(label)

    qpm = 120
    quarter_per_seconds = qpm / 60
    seconds_per_quarter = 1 / quarter_per_seconds
    seconds_per_bar = seconds_per_quarter * 4

    plot_start = int(first_note.start / seconds_per_bar) * seconds_per_bar
    plot_end = int(last_note.end / seconds_per_bar) * seconds_per_bar \
               + seconds_per_bar

    for bar in frange(plot_start, plot_end, seconds_per_bar):
      bar_count = bar / seconds_per_bar
      if bar_count % 2 == 0:
        fill_alpha = BOX_VERTICAL_FILL_ALPHA_EVEN
      else:
        fill_alpha = BOX_VERTICAL_FILL_ALPHA_ODD
      box = BoxAnnotation(left=bar,
                          right=bar + seconds_per_bar,
                          fill_color="gray",
                          fill_alpha=fill_alpha,
                          line_alpha=BOX_VERTICAL_FILL_ALPHA_EVEN)
      box.level = "underlay"
      plot.add_layout(box)

    for beat in frange(plot_start, plot_end, seconds_per_quarter):
      box = BoxAnnotation(left=beat,
                          right=beat + seconds_per_quarter,
                          fill_color=None,
                          fill_alpha=BOX_BEAT_VERTICAL_FILL_ALPHA,
                          line_alpha=BOX_BEAT_VERTICAL_LINE_ALPHA)
      box.level = "underlay"
      plot.add_layout(box)

    plot.xgrid.grid_line_color = "black"
    plot.ygrid.grid_line_color = None

    plot.xgrid.grid_line_alpha = 0.30
    plot.xgrid.grid_line_width = 1
    plot.xgrid.grid_line_color = "black"

    plot.xaxis.bounds = (plot_start, plot_end)
    plot.yaxis.bounds = (pitch_min, pitch_max + 1)

    plot.yaxis.major_label_text_alpha = 0
    plot.yaxis.major_tick_line_alpha = 0
    plot.yaxis.minor_tick_line_alpha = 0

    plot.xaxis.ticker = bokeh.models.SingleIntervalTicker(interval=1)
    plot.xaxis.minor_tick_line_alpha = 0

    plot.plot_width = 1200
    plot.plot_height = 300
    plot.xaxis.axis_label = "time (" + str(self._time_scaling) + ")"
    plot.yaxis.axis_label = "pitch (MIDI)"

    plot.x_range = Range1d(plot_start, plot_end)
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
    plot = self.plot_midi(pretty_midi)
    if self._live_reload:
      html = file_html(plot, CDN, template_variables={'plot_script': 'lol'})
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


def frange(x, y, jump):
  while x < y:
    yield x
    x += jump


if __name__ == "__main__":
  for midi_file in sys.argv[1:]:
    plot_file = midi_file.replace(".mid", ".html")
    print("Plotting midi file " + midi_file + " to " + plot_file)
    pretty_midi = PrettyMIDI(midi_file)
    plotter = Plotter(time_scaling=TimeScaling.SEC)
    plotter.show(pretty_midi, plot_file)
  sys.exit(0)
