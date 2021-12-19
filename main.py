import streamlit as st

from renderer import get_renderer_factory, ConfigRenderer
from settings import GcodeGeneratorSettings, load_config_file
from generator import GcodeProcessor


def main():
    # import config file
    config_data = load_config_file()

    settings = GcodeGeneratorSettings()
    for config_object in config_data:
        settings.add_config_from_dict(config_object)

    # attach settings to session to allow changes when session values are updated on rendered input widgets
    settings.attach_session(st.session_state)

    # render page elements
    # render configurations to page
    processor = GcodeProcessor()
    st.title("ASTM D638 GCODE Generator")
    config_renderer = ConfigRenderer(settings.get_factories())
    config_renderer.render(lambda x: processor.reload(), (None,))

    # render result containers to page
    plot_renderer = get_renderer_factory("plot")
    gcode_renderer = get_renderer_factory("gcode")

    # attach settings and renderers to processor
    processor.attach_settings(settings)
    processor.attach_result_renderers([plot_renderer, gcode_renderer])
    processor.reload()


main()
