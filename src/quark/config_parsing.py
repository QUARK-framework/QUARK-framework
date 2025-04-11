from typing import Any
from dataclasses import dataclass
import yaml
import uuid

from quark.benchmarking import ModuleInfo, ModuleNode

@dataclass(frozen=True)
class Config:
    plugins: list[str]
    pipeline_trees: list[ModuleNode]
    run_id: str


# ====== Types allowed to use in the configuration file ======
# Explicitly defining these types allows for better type checking and documentation in _init_pipeline_tree and _extract_module_info below
#
# A pipeline module can be specified in two ways:
# -A single string is interpreted as a single module without parameters
# -A dictionary with a single key-value pair is interpreted as a single module where the value is another dictionary containing the parameters
ModuleFormat = str | dict[str, dict[str, Any]]

# If one layer of the pipeline consists of multiple modules, each one describes a separate pipeline
PipelineLayer = ModuleFormat | list[ModuleFormat]
# ============================================================

def _init_module_info(module: ModuleFormat) -> ModuleInfo:
    match module:
        case str():  # Single module
            return ModuleInfo(name=module, params={})
        case dict():  # Single module with parameters
            name = next(iter(module))
            params = module[name]
            return ModuleInfo(name=name, params=params)


def _init_pipeline_trees(pipeline: list[PipelineLayer]) -> list[ModuleNode]:
    def imp(pipeline: list[list[ModuleFormat]], parent: ModuleNode) -> None:
        match pipeline:
            case []:
                return
            case [layer, *_]:
                for module in layer:
                    module_info = _init_module_info(module)
                    node = ModuleNode(module_info, parent)
                    imp(pipeline[1:], parent=node)

    pipeline = [layer if isinstance(layer, list) else [layer] for layer in pipeline]
    pipeline_trees = [ModuleNode(_init_module_info(layer)) for layer in pipeline[0]]
    for node in pipeline_trees:
        imp(pipeline[1:], parent=node) # type: ignore
    return pipeline_trees

def parse_config(path:str) -> Config:
    with open(path) as file:
        data = yaml.load(file, Loader=yaml.FullLoader)
        pipeline_layers_lists:list[list[PipelineLayer]] = []
        if "pipelines" in data:
            pipeline_layers_lists = data["pipelines"]
        elif "pipeline" in data:
            pipeline_layers_lists = [data["pipeline"]]
        else:
            raise ValueError("No pipeline found in configuration file")

        pipeline_trees = sum((_init_pipeline_trees(pipeline_layers) for pipeline_layers in pipeline_layers_lists), [])
        return Config(
            plugins=data["plugins"],
            pipeline_trees=pipeline_trees,
            run_id=str(data["run_id"] if "run_id" in data else uuid.uuid4())
        )
