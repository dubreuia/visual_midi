from enum import Enum
from typing import Optional


class Coloring(Enum):
  PITCH = 0
  INSTRUMENT = 1

  @staticmethod
  def from_name(name: str):
    for color in Coloring:
      if color.name == name:
        return color
    raise ValueError("Unknown color name: " + name)


class Preset:
  """
  Preset class to configure the plotter bokeh plot output.
  """

  def __init__(self,
               plot_width: int = 1200,
               plot_height: int = 400,
               row_height: Optional[int] = None,
               show_bar: bool = True,
               show_beat: bool = True,
               title_text_font_size: str = "14px",
               axis_label_text_font_size: str = "12px",
               axis_x_major_tick_out: int = 5,
               axis_y_major_tick_out: int = 25,
               label_y_axis_offset_x: float = -18,
               label_y_axis_offset_y: float = 0.1,
               axis_y_label_standoff: int = 0,
               label_text_font_size: str = "10px",
               label_text_font_style: str = "normal",
               toolbar_location: Optional[str] = "right",
               stop_live_reload_button: bool = True):
    self.plot_width = plot_width
    self.plot_height = plot_height
    self.row_height = row_height
    self.show_bar = show_bar
    self.show_beat = show_beat
    self.title_text_font_size = title_text_font_size
    self.axis_label_text_font_size = axis_label_text_font_size
    self.axis_x_major_tick_out = axis_x_major_tick_out
    self.axis_y_major_tick_out = axis_y_major_tick_out
    self.label_y_axis_offset_x = label_y_axis_offset_x
    self.label_y_axis_offset_y = label_y_axis_offset_y
    self.axis_y_label_standoff = axis_y_label_standoff
    self.label_text_font_size = label_text_font_size
    self.label_text_font_style = label_text_font_style
    self.toolbar_location = toolbar_location
    self.stop_live_reload_button = stop_live_reload_button


PRESET_DEFAULT = Preset()

PRESET_4K = Preset(
  plot_width=3840,
  row_height=100,
  title_text_font_size="65px",
  axis_label_text_font_size="55px",
  axis_x_major_tick_out=25,
  axis_y_major_tick_out=100,
  label_y_axis_offset_x=-77,
  label_y_axis_offset_y=0.1,
  axis_y_label_standoff=20,
  label_text_font_size="40px",
  toolbar_location=None,
)
