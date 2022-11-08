from enum import Enum
from typing import Dict, Optional, Any, ClassVar, Type, List
from marshmallow_dataclass import dataclass
from dataclasses import field

from marshmallow import Schema, fields


class ModelState(str, Enum):
    UNKNOWN = "UNKNOWN"
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    QUEUED = "QUEUED"
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    ERROR = "ERROR"


@dataclass
class ESSIMAdapterConfig:
    essim_post_body: Dict[str, Any]
    input_esdl_file_path: Optional[str] = None
    output_file_path: Optional[str] = None
    base_path: Optional[str] = None


@dataclass
class ModelRun:
    state: ModelState
    config: ESSIMAdapterConfig
    result: dict


@dataclass(order=True)
class ModelRunInfo:
    model_run_id: str
    state: ModelState = field(default=ModelState.UNKNOWN)
    result: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None

    # support for Schema generation in Marshmallow
    Schema: ClassVar[Type[Schema]] = Schema


@dataclass
class MonitorKPIResult:
    still_calculating: bool
    results: List[Dict[str, Any]]
