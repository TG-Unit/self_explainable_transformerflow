import dataclasses
from dataclasses import dataclass
from typing import List
from pathlib import Path

from ..ArtificalGateDefinition import ArtificalGateDefinition
from .outlierhandlerconfig import OutlierHandlerConfig

from .dataloaderconfig import DataLoaderConfig


@dataclass
class CacheDataCreationConfig:
    source_datasets: List[DataLoaderConfig]
    blacklist_path: Path
    output_location: Path
    gate_defintions: List[ArtificalGateDefinition]
    outlier_handler_config: OutlierHandlerConfig
    polygon_points: List[int] = dataclasses.field(default_factory=lambda : list([20]))
    ignore_blacklist: bool = False
