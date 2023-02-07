from abc import ABC, abstractmethod
from io import BytesIO
from typing import Dict
from uuid import uuid4

import json
import sys

import esdl
import esdl.esdl_handler

from minio import Minio

from tno.essim_adapter.settings import EnvSettings
from tno.essim_adapter.types import ModelRun, ModelState, ModelRunInfo
from tno.shared.log import get_logger

logger = get_logger(__name__)


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