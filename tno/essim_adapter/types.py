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
    output_esdl_file_path: Optional[str] = None
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


@dataclass
class InfluxDBInfo:
    database: str
    measurement: str
    field: str
    host: Optional[str] = None
    port: Optional[int] = None
    use_ssl: Optional[bool] = None


@dataclass
class ProfileInfo:
    values: List[Any]
    start_datetime: str
    end_datetime: str
    num_values: int
    quantity_and_unit: Optional[str] = None
    influxdb_info: Optional[InfluxDBInfo] = None


@dataclass
class AssetPortProfileInfo:
    asset_id: str
    port_id: str
    profile_info: List[ProfileInfo]


@dataclass
class AssetCostInformationProfileInfo:
    asset_id: str
    cost_information_type: str
    profile_info: ProfileInfo


@dataclass
class CarrierCostInfo:
    carrier_id: str
    profile_info: ProfileInfo


@dataclass
class EnvironmentalProfileInfo:
    environmental_profile_type: str
    profile_info: ProfileInfo


class InfluxDBProfilesInfo:
    asset_port_profiles_dict: Dict[Any, AssetPortProfileInfo]
    asset_cost_profiles_list: List[AssetCostInformationProfileInfo]
    carrier_cost_profiles_list: List[CarrierCostInfo]
    environmental_profiles_list: List[EnvironmentalProfileInfo]
