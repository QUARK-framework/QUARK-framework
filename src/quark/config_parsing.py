import functools
import operator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from quark.benchmarking import ModuleInfo, ModuleNode


@dataclass(frozen=True)
class Config:
    """A wrapper for the relevant config data, parsed from a config yml file."""

    plugins: list[str]
    # Parsing directly to trees in form of ModuleNodes introduces some unfortunate coupling to the benchmarking module.
    # However, doing so prevents returning pipeline_trees in form of some ugly intermediate type.
    pipeline_trees: list[ModuleNode]


# ====== Types allowed to use in the configuration file ======
# Explicitly defining these types allows for better type checking and documentation in _init_pipeline_tree and
# _extract_module_info below
#
# A pipeline module can be specified in two ways:
# -A single string is interpreted as a single module without parameters
# -A dictionary with a single key-value pair is interpreted as a single module where the value is another dictionary
# containing the parameters
ModuleFormat = str | dict[str, dict[str, Any]]

# If one layer of the pipeline consists of multiple modules, each one describes a separate pipeline
PipelineLayer = ModuleFormat | list[ModuleFormat]
# ============================================================


def _init_module_info(module: ModuleFormat) -> ModuleInfo:
    """Create a ModuleInfo object from data adhering to ModuleFormat.

    :param module: Data adhering to ModuleFormat
    :return: An instance of ModuleInfo containing the given data
    """
    # This function belongs here instead of inside the ModuleInfo class definition because ModuleFormat is only used for
    # parsing the config.
    match module:
        case str():  # Single module
            return ModuleInfo(name=module, params={})
        case dict():  # Single module with parameters
            name = next(iter(module))
            params = module[name]
            return ModuleInfo(name=name, params=params)
        case _:
            msg = "The config file is not in the correct format"
            raise TypeError(msg)


def _init_pipeline_trees(pipeline: list[PipelineLayer]) -> list[ModuleNode]:
    """Create pipeline trees from lists of data adhering to PipelineLayer.

    Each layer of a pipeline defined in the config file can contain one or more modules.
    The function starts by creating a root node for each module in the first layer.
    For each module in the next layer, a child node is created for each of the previous nodes.
    This continues recursively until the last layer is reached.
    # Shouldn't it be "iteratively" instead of "recursively"? A: Logically, yes, this is what is happening. But the
    # implementation works recursively

    :param pipeline: TODO
    :return: TODO
    """

    # TODO rewrite to simple for loop
    def imp(pipeline: list[list[ModuleFormat]], parent: ModuleNode) -> None:
        match pipeline:
            case []:
                return
            case [layer, *_]:
                for module in layer:
                    module_info = _init_module_info(module)
                    # TODO write about the side effect of setting the children and parent variables by AnyTree
                    node = ModuleNode(module_info, parent)
                    imp(pipeline[1:], parent=node)

    pipeline = [layer if isinstance(layer, list) else [layer] for layer in pipeline]  # <- pipeline is converted here
    pipeline_trees = [ModuleNode(_init_module_info(layer)) for layer in pipeline[0]]
    for node in pipeline_trees:
        imp(pipeline[1:], parent=node)  # type: ignore
    # Why "type: ignore"? A: Pyright is not smart enough to realize that pipeline has the required type at this point.
    # A few lines above this, pipeline is converted from a list[PipelineLayer] to a list[list[ModuleFormat]] by the list
    # comprehension. All of those hard-coded types are only here to make type-checking possible at all after reading
    # an arbitrary config file, but maybe this is not the best way of doing things, according to Pyright.
    return pipeline_trees


def parse_config(path: str) -> Config:
    """Parse the config to sync formatting."""
    with Path(path).open() as file:
        data = yaml.load(file, Loader=yaml.FullLoader)  # noqa: S506
        pipeline_layers_lists: list[list[PipelineLayer]] = []
        if "pipelines" in data:
            pipeline_layers_lists = data["pipelines"]
        elif "pipeline" in data:
            pipeline_layers_lists = [data["pipeline"]]
        else:
            message = "No pipeline found in configuration file"
            raise ValueError(message)

        # TODO more documentation for this line in particular or rewrite into more clear syntax with for loop or such
        pipeline_trees = functools.reduce(
            operator.iadd,
            (_init_pipeline_trees(pipeline_layers) for pipeline_layers in pipeline_layers_lists),
            [],
        )
        return Config(plugins=data["plugins"], pipeline_trees=pipeline_trees)
