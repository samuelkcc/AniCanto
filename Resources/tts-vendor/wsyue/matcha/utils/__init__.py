"""Inference utilities; training helpers are imported only when requested."""
from matcha.utils.pylogger import get_pylogger


def __getattr__(name):
    import importlib
    modules = {
        'instantiate_callbacks': 'instantiators', 'instantiate_loggers': 'instantiators',
        'log_hyperparameters': 'logging_utils', 'enforce_tags': 'rich_utils',
        'print_config_tree': 'rich_utils', 'extras': 'utils',
        'get_metric_value': 'utils', 'task_wrapper': 'utils',
    }
    if name not in modules:
        raise AttributeError(name)
    return getattr(importlib.import_module('matcha.utils.' + modules[name]), name)
