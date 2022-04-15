from collections import defaultdict
from typing import List
from streamlit import empty, expander
from generator import CoordinateGenerator
from settings import BaseConfig


class ResultRenderer:
    default_text = ""

    def __init__(self, placeholder_text=None):
        self.container = empty()
        self.container.text(placeholder_text if placeholder_text else self.default_text)

    def render(self, generator: CoordinateGenerator):
        pass


class PlotRenderer(ResultRenderer):
    default_text = "plot shown here.."

    def render(self, generator: CoordinateGenerator):
        self.container.plotly_chart(generator.get_plot_figure(), True)


class GCODETextRenderer(ResultRenderer):
    default_text = "GCODE text shown here.."

    def render(self, generator: CoordinateGenerator):
        self.container.download_button("Download GCODE", generator.gcode(as_bytes=True), file_name=".gcode")


class ConfigRenderer:

    def __init__(self, configs: List[BaseConfig]):
        self.configs = configs
        # order configs by section name
        self.configs = configs
        self._input_widgets = {}

    def render(self, callback_function, callback_args=None):
        # group configs by section
        config_groups = defaultdict(list)
        for config in self.configs:
            config_groups[config.section].append(config)

        for section_name, configs in config_groups.items():
            container = expander(section_name, expanded=False)
            with container:
                for config in configs:
                    self._input_widgets[config.get_name()] = config.render_class(
                        on_change=callback_function, args=callback_args if callback_args else (),
                        **config.get_render_params())


def get_renderer_factory(render_type, render_text=None):
    if render_type == "plot":
        return PlotRenderer(render_text)
    elif render_type == "gcode":
        return GCODETextRenderer(render_text)
    else:
        raise ValueError(f"{render_type} renderer type is not configured in the application")
