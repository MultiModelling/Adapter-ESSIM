from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from io import BytesIO
from typing import Dict
from uuid import uuid4

import json
import sys

import esdl
import esdl.esdl_handler
import pytz
from influxdb import InfluxDBClient

from minio import Minio
from pyecore.ecore import EReference

from tno.essim_adapter.settings import EnvSettings
from tno.essim_adapter.types import ModelRun, ModelState, ModelRunInfo, ProfileInfo, AssetPortProfileInfo, \
    AssetCostInformationProfileInfo, EnvironmentalProfileInfo, InfluxDBProfilesInfo, CarrierCostInfo, InfluxDBInfo
from tno.shared.log import get_logger

logger = get_logger(__name__)

ESDL_PROFILES_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
INFLUXDB_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S+0000"
INFLUXDB_QUERY_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
utc = pytz.timezone("UTC")


class Model(ABC):
    def __init__(self):
        self.model_run_dict: Dict[str, ModelRun] = {}

        self.minio_client = None
        if EnvSettings.minio_endpoint():
            logger.info(f"Connecting to Minio Object Store at {EnvSettings.minio_endpoint()}")
            self.minio_client = Minio(
                endpoint=EnvSettings.minio_endpoint(),
                secure=EnvSettings.minio_secure(),
                access_key=EnvSettings.minio_access_key(),
                secret_key=EnvSettings.minio_secret_key()
            )
        else:
            logger.info("No Minio Object Store configured")

    def request(self):
        model_run_id = str(uuid4())
        self.model_run_dict[model_run_id] = ModelRun(
            state=ModelState.ACCEPTED,
            config=None,
            result=None,
        )

        return ModelRunInfo(
            state=self.model_run_dict[model_run_id].state,
            model_run_id=model_run_id,
        )

    def initialize(self, model_run_id: str, config=None):
        if model_run_id in self.model_run_dict:
            self.model_run_dict[model_run_id].config = config
            self.model_run_dict[model_run_id].state = ModelState.READY
            return ModelRunInfo(
                state=self.model_run_dict[model_run_id].state,
                model_run_id=model_run_id,
            )
        else:
            return ModelRunInfo(
                model_run_id=model_run_id,
                state=ModelState.ERROR,
                reason="Error in Model.initialize(): model_run_id unknown"
            )

    def load_from_minio(self, path):
        bucket = path.split("/")[0]
        rest_of_path = "/".join(path.split("/")[1:])

        response = self.minio_client.get_object(bucket, rest_of_path)
        if response:
            return response.data
        else:
            return None

    @staticmethod
    def connect_to_influxdb(esdl_influxdb_profile: esdl.InfluxDBProfile):
        use_ssl = esdl_influxdb_profile.host.startswith('https')
        if esdl_influxdb_profile.host.startswith('http'):     # matches http or https
            host_without_protocol = esdl_influxdb_profile.host.split('://')[1]
        else:
            host_without_protocol = esdl_influxdb_profile.host

        client = InfluxDBClient(
            host=host_without_protocol,
            port=esdl_influxdb_profile.port,
            database=esdl_influxdb_profile.database,
            ssl=use_ssl
        )

        influxdb_info = InfluxDBInfo(
            host=host_without_protocol,
            port=esdl_influxdb_profile.port,
            use_ssl=use_ssl,
            database=esdl_influxdb_profile.database,
            measurement=esdl_influxdb_profile.measurement,
            field=esdl_influxdb_profile.field
        )

        return client, influxdb_info

    def get_quantity_and_unit_information(self, esdl_influxdb_profile: esdl.InfluxDBProfile):
        return None

    def query_esdl_influxdb_profile(self, esdl_influxdb_profile: esdl.InfluxDBProfile):
        client, influxdb_info = self.connect_to_influxdb(esdl_influxdb_profile)

        influxdb_startdate = esdl_influxdb_profile.startDate.astimezone(utc).strftime(INFLUXDB_QUERY_DATETIME_FORMAT)
        influxdb_enddate = esdl_influxdb_profile.endDate.astimezone(utc).strftime(INFLUXDB_QUERY_DATETIME_FORMAT)

        query = 'SELECT ' + esdl_influxdb_profile.field + ' FROM "' + esdl_influxdb_profile.measurement + '" WHERE (time >= \'' + influxdb_startdate + '\' AND time < \'' + influxdb_enddate + '\')'
        logger.debug(query)
        res = client.query(query)

        if res:
            # logger.debug(res)
            keys = res.keys()
            if keys:
                first_key = list(keys)[0]
                series = res[first_key]

                values = list()
                for s in series:
                    values.append(s[esdl_influxdb_profile.field])

                profile_info = ProfileInfo(
                    values=values,
                    start_datetime=influxdb_startdate,
                    end_datetime=influxdb_enddate,
                    num_values=len(values),
                    quantity_and_unit=self.get_quantity_and_unit_information(esdl_influxdb_profile),
                    influxdb_info=influxdb_info
                )
                return profile_info

        return None

    def load_profiles_from_influxdb(self, model_run_id: str):
        path = str(self.model_run_dict[model_run_id].config.base_path) + str(
            self.model_run_dict[model_run_id].config.input_esdl_file_path)

        esh = esdl.esdl_handler.EnergySystemHandler()

        bucket = path.split("/")[0]
        rest_of_path = "/".join(path.split("/")[1:])

        response = self.minio_client.get_object(bucket, rest_of_path)
        es: esdl.EnergySystem = esh.load_from_string(response.data.decode('UTF-8'))

        # Collect all values for all InfluxDBProfiles in the ESDL
        influxdb_profiles = esh.get_all_instances_of_type(esdl.InfluxDBProfile)
        influxdb_profiles_dict = dict()
        for ip in influxdb_profiles:
            influxdb_profiles_dict[ip.id] = self.query_esdl_influxdb_profile(ip)

        # Collect information about profiles attached to asset ports
        asset_port_profiles_dict = dict()
        ports = esh.get_all_instances_of_type(esdl.Port)
        for p in ports:
            for prof in p.profile:
                if isinstance(prof, esdl.ProfileReference):
                    prof = prof.reference
                if isinstance(prof, esdl.InfluxDBProfile):
                    asset = p.eContainer()
                    if asset.id + p.id in asset_port_profiles_dict:
                        asset_port_profiles_dict[asset.id + p.id].profile_info.append(influxdb_profiles_dict[prof.id])
                    else:
                        asset_port_profiles_dict[asset.id + p.id] = (
                            AssetPortProfileInfo(
                                asset_id=asset.id,
                                port_id=p.id,
                                profile_info=[influxdb_profiles_dict[prof.id]]
                            )
                        )

        # Collect information about cost information profiles of assets
        asset_cost_profiles_list = list()
        assets = esh.get_all_instances_of_type(esdl.Asset)
        for a in assets:
            if a.costInformation:
                for ci_attr in a.costInformation.eClass.eAllStructuralFeatures():
                    if isinstance(ci_attr, EReference):
                        referred_obj = a.costInformation.eGet(ci_attr)

                        if isinstance(referred_obj, esdl.InfluxDBProfile):
                            ref_name = ci_attr.name
                            asset_cost_profiles_list.append(
                                AssetCostInformationProfileInfo(
                                    asset_id=a.id,
                                    cost_information_type=ref_name,
                                    profile_info=influxdb_profiles_dict[referred_obj.id]
                                )
                            )

        # Collect information about carrier cost profiles
        carrier_cost_profiles_list = list()
        carrier_list = esh.get_all_instances_of_type(esdl.Carrier)
        for c in carrier_list:
            if c.cost:
                if isinstance(c.cost, esdl.InfluxDBProfile):
                    carrier_cost_profiles_list.append(
                        CarrierCostInfo(
                            carrier_id=c.id,
                            profile_info=influxdb_profiles_dict[c.cost.id]
                        )
                    )

        # Collect information about environmental profiles
        environmental_profiles_list = list()
        environmental_profiles = esh.get_all_instances_of_type(esdl.EnvironmentalProfiles)
        for ep in environmental_profiles:
            for ep_attr in ep.eClass.eAllStructuralFeatures():
                if isinstance(ep_attr, EReference):
                    referred_obj = ep.eGet(ep_attr)

                    if isinstance(referred_obj, esdl.InfluxDBProfile):
                        ref_name = ep_attr.name
                        environmental_profiles_list.append(
                            EnvironmentalProfileInfo(
                                environmental_profile_type=ref_name,
                                profile_info=influxdb_profiles_dict[referred_obj.id]
                            )
                        )

        return InfluxDBProfilesInfo(
            asset_port_profiles_dict=asset_port_profiles_dict,
            asset_cost_profiles_list=asset_cost_profiles_list,
            carrier_cost_profiles_list=carrier_cost_profiles_list,
            environmental_profiles_list=environmental_profiles_list
        )

    @staticmethod
    def save_profile_to_influxdb(profile_info: ProfileInfo):
        client = InfluxDBClient(
            host=profile_info.influxdb_info.host,
            port=profile_info.influxdb_info.port,
            database=profile_info.influxdb_info.database,
            ssl=profile_info.influxdb_info.use_ssl
        )

        values_json = list()
        date = datetime.strptime(profile_info.start_datetime, ESDL_PROFILES_DATETIME_FORMAT)
        for v in profile_info.values:
            fields = dict()
            fields[profile_info.influxdb_info.field] = v

            values_json.append({
                "measurement": profile_info.influxdb_info.measurement,
                "time": date.strftime(INFLUXDB_DATETIME_FORMAT),
                "fields": fields
            })

            date = date + timedelta(hours=1)

        client.write_points(values_json)

    @staticmethod
    def save_profiles_to_influxdb(profiles_info: InfluxDBProfilesInfo):
        asset_port_profiles_dict = profiles_info.asset_port_profiles_dict
        if asset_port_profiles_dict:
            for k, v in asset_port_profiles_dict.items():
                for appi in v.profile_info:
                    Model.save_profile_to_influxdb(appi)

        asset_cost_profiles_list = profiles_info.asset_cost_profiles_list
        if asset_cost_profiles_list:
            for acp in asset_cost_profiles_list:
                Model.save_profile_to_influxdb(acp.profile_info)

        carrier_cost_profiles_list = profiles_info.carrier_cost_profiles_list
        if carrier_cost_profiles_list:
            for ccp in carrier_cost_profiles_list:
                Model.save_profile_to_influxdb(ccp.profile_info)

        environmental_profiles_list = profiles_info.environmental_profiles_list
        if environmental_profiles_list:
            for ep in environmental_profiles_list:
                Model.save_profile_to_influxdb(ep.profile_info)

    @abstractmethod
    def process_results(self, result):
        pass

    def post_process_results(self, model_run_id: str, result) -> esdl.esdl_handler.EnergySystemHandler:

        path = str(self.model_run_dict[model_run_id].config.base_path) + str(
            self.model_run_dict[model_run_id].config.input_esdl_file_path)

        esh = esdl.esdl_handler.EnergySystemHandler()

        bucket = path.split("/")[0]
        rest_of_path = "/".join(path.split("/")[1:])

        response = self.minio_client.get_object(bucket, rest_of_path)
        es: esdl.EnergySystem = esh.load_from_string(response.data.decode('UTF-8'))

        kpi_list = []

        # Quick 'hack' to ease mapping to ESDL types
        kpi_unit_mapping = {
            "PERCENTAGE": "PERCENT"
        }

        for essim_result in result:
            kpi_id = essim_result["id"]
            kpi_description = essim_result["descr"]

            for kpi_result in essim_result["kpi"]:
                for kpi_level in kpi_result:
                    for kpi_selection in kpi_result[kpi_level]:
                        kpi_name = kpi_selection["Name"]
                        kpi_unit = kpi_selection["Unit"].upper()
                        if kpi_unit in kpi_unit_mapping:
                            kpi_unit = kpi_unit_mapping[kpi_unit]
                        kpi_unit_enum = esdl.UnitEnum.from_string(kpi_unit)
                        kpi_unit = esdl.QuantityAndUnitType(id=str(uuid4()), unit=kpi_unit_enum)
                        kpi_values = kpi_selection["Values"]

                        if type(kpi_values) == list:
                            for item in kpi_values:
                                kpi_sub_name = kpi_name + " - " + item["carrier"]
                                kpi_sub_unit = esdl.QuantityAndUnitType(
                                    unit=kpi_unit_enum, description=item["carrier"]
                                )
                                kpi_list.append(
                                    esdl.DoubleKPI(
                                        id=str(uuid4()),
                                        name=kpi_sub_name,
                                        quantityAndUnit=kpi_sub_unit,
                                        value=float(item["value"]),
                                    )
                                )
                        else:
                            kpi_list.append(
                                esdl.DoubleKPI(
                                    id=str(uuid4()),
                                    name=kpi_name,
                                    quantityAndUnit=kpi_unit,
                                    value=float(kpi_values),
                                )
                            )

        kpis = esdl.KPIs(id=kpi_id, description=kpi_description, kpi=kpi_list)
        es.instance.items[0].area.KPIs = kpis

        logger.debug("ESDL-KPI String: " + str(esh.to_string()))

        return esh

    def store_result(self, model_run_id: str, result):
        if model_run_id in self.model_run_dict:
            res = self.process_results(result)

            if self.minio_client:

                # Log output
                logger.debug("KPI Output: " + str(result))

                # Generate ESSIM KPIs
                content = BytesIO(bytes(res, 'ascii'))
                base_path = self.model_run_dict[model_run_id].config.base_path
                path = base_path + self.model_run_dict[model_run_id].config.output_file_path
                bucket = path.split("/")[0]
                rest_of_path = "/".join(path.split("/")[1:])

                if not self.minio_client.bucket_exists(bucket):
                    self.minio_client.make_bucket(bucket)

                self.minio_client.put_object(bucket, rest_of_path, content, content.getbuffer().nbytes)
                self.model_run_dict[model_run_id].result = {
                    "path": path
                }

                # Process ESDL file
                esh = self.post_process_results(model_run_id, result)

                # now save it to MinIO
                path = str(self.model_run_dict[model_run_id].config.base_path) + str(self.model_run_dict[model_run_id].config.output_esdl_file_path)
                bucket = path.split("/")[0]
                rest_of_path = "/".join(path.split("/")[1:])

                content = BytesIO(bytes(esh.to_string(), 'ascii'))

                if not self.minio_client.bucket_exists(bucket):
                    self.minio_client.make_bucket(bucket)

                self.minio_client.put_object(bucket, rest_of_path, content, content.getbuffer().nbytes)
                logger.info("ESSIM data saved to MinIO")

            else:
                self.model_run_dict[model_run_id].result = {
                    "result": res
                }
            return ModelRunInfo(
                model_run_id=model_run_id,
                state=ModelState.SUCCEEDED,
            )
        else:
            return ModelRunInfo(
                model_run_id=model_run_id,
                state=ModelState.ERROR,
                reason="Error in Model.store_result(): model_run_id unknown"
            )

    def run(self, model_run_id: str):
        if model_run_id in self.model_run_dict:
            self.model_run_dict[model_run_id].state = ModelState.RUNNING
            return ModelRunInfo(
                state=self.model_run_dict[model_run_id].state,
                model_run_id=model_run_id,
            )
        else:
            return ModelRunInfo(
                model_run_id=model_run_id,
                state=ModelState.ERROR,
                reason="Error in Model.run(): model_run_id unknown"
            )

    def status(self, model_run_id: str):
        if model_run_id in self.model_run_dict:
            # Dummy behaviour: Query status once, to let finish model
            self.model_run_dict[model_run_id].state = ModelState.SUCCEEDED

            return ModelRunInfo(
                state=self.model_run_dict[model_run_id].state,
                model_run_id=model_run_id,
            )
        else:
            return ModelRunInfo(
                model_run_id=model_run_id,
                state=ModelState.ERROR,
                reason="Error in Model.status(): model_run_id unknown"
            )

    def results(self, model_run_id: str):
        if model_run_id in self.model_run_dict:
            return ModelRunInfo(
                state=self.model_run_dict[model_run_id].state,
                model_run_id=model_run_id,
                result=self.model_run_dict[model_run_id].result,
            )
        else:
            return ModelRunInfo(
                model_run_id=model_run_id,
                state=ModelState.ERROR,
                reason="Error in Model.results(): model_run_id unknown"
            )

    def remove(self, model_run_id: str):
        if model_run_id in self.model_run_dict:
            del self.model_run_dict[model_run_id]
            return ModelRunInfo(
                model_run_id=model_run_id,
                state=ModelState.UNKNOWN,
            )
        else:
            return ModelRunInfo(
                model_run_id=model_run_id,
                state=ModelState.ERROR,
                reason="Error in Model.remove(): model_run_id unknown"
            )