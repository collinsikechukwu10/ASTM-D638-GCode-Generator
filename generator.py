from enum import IntEnum
import math
from typing import List
import pandas as pd
import datetime as dt
import plotly.graph_objects as go
from settings import GcodeGeneratorSettings
from exceptions import NegativeValueException

CROSS_SECTION_FACTOR_ADJUSTMENT = lambda x: 0.7063 * math.pow(x, -0.652)


class PrinterType(IntEnum):
    REPRAP = 0
    ULTIMAKER = 1


class MicrostructureType(IntEnum):
    SHIFTED = 0
    STRAIGHT = 1


class GCodeCoordinate:
    def __init__(self, x, y, z=0, e=0):
        self.x = x
        self.y = y
        self.z = z
        self.e = e

    def tuple(self):
        return self.x, self.y, self.z, self.e

    def point(self):
        return self.x, self.y, self.z

    def __sub__(self, other):
        return self.x - other.x, self.y - other.y, self.z - other.z


class CoordinateGenerator:
    def __init__(self, app_config: GcodeGeneratorSettings):
        self._kwargs = app_config
        self._coords: List[GCodeCoordinate] = []
        self._counter_idx = 0
        self._init_speed = self._kwargs["initialization_speed"]
        self._print_speed = self._kwargs["print_speed"]

        self._startX = self._kwargs["start_point_x"] or 0
        self._startY = self._kwargs["start_point_y"] or 0
        self._sample_height = self._kwargs["sample_height"]
        self._layer_height = self._kwargs["layer_thickness"]
        self._layer_width = self._kwargs["layer_width"]
        self._layer_length = self._kwargs["layer_length"]
        self._layer_raster_spacing = self._kwargs["layer_raster_spacing"]
        self._filament_size = self._kwargs["filament_size"]

        self._currentZ = 0

        # FILLET SECTION
        self._sample_midsection_width = self._kwargs["sample_midsection_width"]
        self._sample_midsection_height = self._kwargs["sample_midsection_height"]

        # PRINTER SETTINGS
        self._printer_type = self._kwargs["printer_type"]
        self._nozzle_temperature = self._kwargs["nozzle_temperature"]
        self._bed_temperature = self._kwargs["bed_temperature"]
        self._nozzle_diameter = self._kwargs["nozzle_diameter"]

        self._add_adhesion = self._kwargs["add_adhesion"]
        self._adhesion_width = self._kwargs["adhesion_layer_width"]
        self._adhesion_thickness = self._kwargs["adhesion_layer_thickness"]

        self._num_layers = int((self._currentZ + self._sample_height) / self._layer_height)

    def build(self):
        current_z = self._currentZ
        if self._add_adhesion:
            self._build_adhesion_layer(self._startX, self._startY, current_z, self._adhesion_width)

        for layer in range(1, self._num_layers + 1):
            self._build_layer(self._startX, self._startX + self._layer_length, self._startY,
                              current_z + (layer * self._layer_height))

    def _build_layer(self, start_x, end_x, start_y, layer_z):
        # this function shoudl control which part is being created, whether the dogbone or fillet end
        cx = start_x
        end_y = start_y + self._layer_width
        while cx <= end_x:
            cx += self._layer_raster_spacing
            self._add_path(cx, start_y, layer_z)
            self._add_path(cx, end_y, layer_z)
            cx += self._layer_raster_spacing
            self._add_path(cx, end_y, layer_z)
            self._add_path(cx, start_y, layer_z)

    def _get_start_and_end_points(self, layer_z):
        # use this to controll which section it is

        pass

    def _build_adhesion_layer(self, start_x, start_y, z_layer, adhesion_width):
        adhes_end_x = adhes_end_y = adhesion_width
        c_x = start_x - adhes_end_x
        c_y = start_y - adhes_end_y
        if c_x < 0 or c_y < 0:
            raise NegativeValueException()
        self._add_path(c_x, c_y, z_layer, True)
        while adhes_end_x <= 0.4 or adhes_end_y <= 0.4:
            c_y += (adhes_end_y * 2 + self._layer_width)
            self._add_path(c_x, c_y, z_layer, True)
            c_x += (adhes_end_x * 2 + self._layer_length)
            self._add_path(c_x, c_y, z_layer, True)
            c_y -= (adhes_end_y * 2 + self._layer_width)
            self._add_path(c_x, c_y, z_layer, True)
            c_x -= (adhes_end_x * 2 + self._layer_length)
            self._add_path(c_x, c_y, z_layer, True)
            c_x += 0.4765
            c_y += 0.4765
            adhes_end_x -= (2 * 0.4765 / 3)
            adhes_end_x -= (2 * self._layer_raster_spacing / 3)

    def gcode(self, as_bytes: bool = False):
        gcode = f";Generated on {dt.datetime.now()};\n"
        gcode += self._prepare_initialization_code()
        gcode += "".join([
            f"G{(idx == 0) * 0 + (idx != 0) * 1} F{(idx == 0) * self._init_speed + (idx != 0) * self._print_speed} " +
            f"X{coord.x:.4f} Y{coord.y:.4f} Z{coord.z:.4f} E{coord.e:.4f};\n" for idx, coord in
            enumerate(self._coords)])
        gcode += self._prepare_close_code()
        return bytes(gcode.encode("utf8")) if as_bytes else gcode

    def df(self):
        return pd.DataFrame(map(lambda i: i.tuple(), self._coords), columns=["X", "Y", "Z", "E"])

    def get_plot_figure(self):
        df = self.df()
        fig = go.Figure(data=[go.Scatter3d(
            z=df["Z"],
            x=df["X"],
            y=df["Y"],
            marker=dict(
                size=1,
                color="black",
                colorscale='Viridis',
            ),
            line=dict(
                color='green',
                width=2
            )
        )])
        fig.update_layout(title='3D Astm D638 Plot', autosize=True, margin=dict(l=65, r=50, b=65, t=90))
        print(df.head())
        return fig

    def _add_path(self, x, y, z, is_adhesion_layer=False):
        self._coords.append(GCodeCoordinate(x, y, z, self._calculate_extrusion_amount(x, y, z, is_adhesion_layer)))

    def _calculate_extrusion_amount(self, x, y, z, is_adhesion_layer):
        if self._counter_idx == 0:
            return 0
        csa = CROSS_SECTION_FACTOR_ADJUSTMENT(self._layer_raster_spacing)
        csa = self._adhesion_thickness * 0.4 / csa if is_adhesion_layer else self._layer_height * 0.4 / csa
        px, py, pz, pe = self._coords[self._counter_idx - 1].tuple()
        return pe + csa * math.sqrt(math.pow(x - px, 2) + math.pow(y - py, 2) + math.pow(z - pz, 2))

    def _prepare_initialization_code(self):
        if self._printer_type == PrinterType.ULTIMAKER:
            opening_str = f";FLAVOR:UltiGCode\n" + \
                          ";MATERIAL:1795\n" + \
                          ";MATERIAL2:0\n" + \
                          f";NOZZLE_DIAMETER:{self._nozzle_diameter}\n" + \
                          ";ASTM TYPE 5 Design\n" + \
                          f";LAYER COUNT:{self._num_layers}\n" + \
                          "M107 ;FAN OFF\n" + \
                          f"G0 F{self._init_speed} X{self._startX} Y{self._startY} Z0\n" + \
                          "M106 S255 ;FAN ON\n"
        else:
            opening_str = ";REPRAP GCODE ASTM D638 BUILD\n" + \
                          f"M104 S{self._nozzle_temperature}\n" + \
                          f"M190 S{self._bed_temperature}\n" + \
                          f"M109 {self._nozzle_temperature}\n" + \
                          "M82\n" + \
                          "M107\n" + \
                          f"G1 F{self._print_speed} X20 Y20 Z10\n" + \
                          "G92 E0\n" + \
                          f"F1 F{self._print_speed} E3\n" + \
                          "G92 E0\n" + \
                          f"G1 F{self._print_speed} X{self._startX} Y{self._startY} Z0.05\n" + \
                          "G92 X0 Y0 Z0\n" + \
                          "M106 S190\n"
        return opening_str

    def _prepare_close_code(self):
        closing_string = ""
        if self._printer_type == PrinterType.ULTIMAKER:
            closing_string += "G10;\nM107;\n"
        else:
            closing_string += "M104 S0;\nM140 S0;\nG91;\nG1 E-2 F300;\nG28 X0 Y0;\nM84;\nG90;\nM107;\n"
        return closing_string


class GcodeProcessor:
    _generator: CoordinateGenerator = None

    def __init__(self):
        self._settings = None
        self.renderers = []

    def attach_settings(self, settings: GcodeGeneratorSettings):
        self._settings = settings

    def attach_result_renderers(self, renderers=()):
        self.renderers = renderers

    def build_generator(self):
        if not self._settings:
            raise Exception("No settings found to create generator")
        self._generator = CoordinateGenerator(self._settings)
        self._generator.build()

    def reload(self):
        self.load()
        print("............plotting............")
        for renderer in self.renderers:
            renderer.render(self._generator)

    def load(self):
        print("...........building...........")
        self.build_generator()


# lets create the shoulders

