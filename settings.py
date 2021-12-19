from collections import OrderedDict
from typing import Dict

from streamlit import select_slider, slider, number_input, checkbox
import json


def label_formatter(name: str):
    return " ".join(map(str.capitalize, name.split("_")))


class BaseConfig:
    render_class = None

    def __init__(self, section, name, initial_value):
        self.section = section
        self.name = name
        self.initial = initial_value

    def get_initial(self):
        return self.initial

    def get_name(self):
        return self.name

    def get_render_params(self):
        return dict(label=label_formatter(self.name), value=self.initial, key=self.name)


class NumericConfig(BaseConfig):
    render_class = slider

    def __init__(self, section, name, initial_value=0, step=1, min_value=0, max_value=10):
        super(NumericConfig, self).__init__(section, name, initial_value)
        type_ = type(initial_value)
        if type_ not in [int, float]:
            raise TypeError(
                f"Initial value for {name} is an unrecognized format. only int and float values are allowed, provided {self.initial}")
        self.step = type_(step)
        self.min = type_(min_value)
        self.max = type_(max_value)
        # lets not use slider for very large numerival values
        if self.max > 150:
            self.render_class = number_input

    def get_initial(self):
        return self.initial

    def get_render_params(self):
        params = super(NumericConfig, self).get_render_params()
        params.update(dict(min_value=self.min, max_value=self.max, step=self.step))
        return params


class BooleanConfig(BaseConfig):
    render_class = checkbox

    def __init__(self, section, name, initial_value=False):
        super(BooleanConfig, self).__init__(section, name, initial_value)
        if not isinstance(initial_value, bool):
            raise ValueError(f"Boolean Config requires a boolean value, got {initial_value}")


class CategoricalConfig(BaseConfig):
    render_class = select_slider

    def __init__(self, section, name, initial_value, choices):
        super(CategoricalConfig, self).__init__(section, name, initial_value)
        self.choices = choices
        if initial_value not in choices:
            raise ValueError(
                f"Initial value `{initial_value}` not included in the choices provided: {','.join(choices)}")

    def get_render_params(self):
        params = super(CategoricalConfig, self).get_render_params()
        params.update(dict(options=self.choices))
        return params


def get_config_factory(config_object: dict):
    type_ = config_object.pop("type", None)
    if type_ == "number":
        return NumericConfig(**config_object)
    elif type_ == "boolean":
        return BooleanConfig(**config_object)
    elif type_ == "category":
        return CategoricalConfig(**config_object)
    else:
        raise ValueError(f"{type_} type is not configured in the application")


class GcodeGeneratorSettings(OrderedDict):
    _session = None

    def __init__(self):
        super().__init__()
        self._config_factories = []

    def attach_session(self, session: Dict):
        # update config with session, then update session with
        # config to add anything that session doesnt have at the moment
        self.update(**session)
        self._session = session

    def __getitem__(self, item):
        # prefer to get from the session first before any other
        if self._session is not None:
            res = self._session[item]
            if res is not None:
                return res
        return super(GcodeGeneratorSettings, self).__getitem__(item)

    def __setitem__(self, key, value):
        super(GcodeGeneratorSettings, self).__setitem__(key, value)
        # add config to streamlit session state
        if self._session is not None:
            map(lambda sess: sess.update({key: value}), self._session)

    def add_config(self, config: BaseConfig):
        self[config.name] = config.initial

    def add_config_from_dict(self, config_object):
        config_factory = get_config_factory(config_object)
        self.add_config(config_factory)
        self._config_factories.append(config_factory)

    def get_factories(self):
        return self._config_factories

    def save_config(self):
        # TODO implement saving configurations for later
        for factory in self._config_factories:
            pass


def load_config_file():
    # import config json file
    with open("config.json", "rb") as f:
        config_file = json.load(f)
    return config_file["data"]
