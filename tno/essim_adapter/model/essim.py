import base64
import json
import requests
from datetime import datetime
from time import sleep, time

from esdl import esdl
from esdl.esdl_handler import EnergySystemHandler

from tno.essim_adapter.model.model import Model, ModelState
from tno.essim_adapter.settings import EnvSettings
from tno.essim_adapter.types import ESSIMAdapterConfig, ModelRunInfo, MonitorKPIResult
from tno.essim_adapter import executor
from tno.shared.log import get_logger

logger = get_logger(__name__)

ESSIM_URL = EnvSettings.essim_url()
ESSIM_HEADERS = {'Content-Type': 'application/json', 'Accept': 'application/json'}
PROGRESS_UPDATE_INTERVAL = 1


class ESSIM(Model):

    def start_essim(self, config: ESSIMAdapterConfig, model_run_id):
        input_esdl_bytes = self.load_from_minio(config.input_esdl_file_path)
        input_esdl_b64_bytes = base64.b64encode(input_esdl_bytes)
        input_esdl_b64_string = input_esdl_b64_bytes.decode('utf-8')

        essim_post_body = config.essim_post_body
        essim_post_body['esdlContents'] = input_esdl_b64_string

        while True:
            logger.info('Trying to start ESSIM...')
            r = requests.post(url=ESSIM_URL, data=json.dumps(essim_post_body), headers=ESSIM_HEADERS)
            response = r.json()
            status_code = r.status_code
            print('start: ', status_code)
            if status_code == 201:
                simulation_id = response['id']
                logger.info(
                    'Successfully started ESSIM Simulation with id {id}'.format(id=simulation_id))
                return ModelRunInfo(
                    model_run_id=model_run_id,
                    state=ModelState.RUNNING,
                ), simulation_id
            elif status_code == 503:
                logger.info('The ESSIM Engine is busy. Retrying in 5 seconds...')
                sleep(5)
            else:
                logger.error(f'ESSIM Simulation failed because: {response["description"]}')
                return ModelRunInfo(
                    model_run_id=model_run_id,
                    state=ModelState.ERROR,
                    reason=f'ESSIM Simulation failed because: {response["description"]}',
                ), None

    @staticmethod
    def monitor_essim_progress(simulation_id, model_run_id):
        if simulation_id is None:
            logger.error('No simulation is started yet!')
            return ModelRunInfo(
                model_run_id=model_run_id,
                state=ModelState.ERROR,
                reason='No simulation is started yet!',
            )

        logger.info("Start monitoring ESSIM progress...")
        status_path = f'{ESSIM_URL}/{simulation_id}/status'
        while True:
            r = requests.get(url=status_path, headers=ESSIM_HEADERS)
            response = r.json()
            status_code = r.status_code
            print('monitor ', status_code)
            if status_code == 200:
                if response['State'] == 'RUNNING':
                    logger.info('{:.1f}% complete'.format(100 * float(response['Description'])))
                    sleep(PROGRESS_UPDATE_INTERVAL)
                elif response['State'] == 'COMPLETE':
                    logger.info('Simulation {}'.format(response['Description']))
                    return ModelRunInfo(
                        model_run_id=model_run_id,
                        state=ModelState.RUNNING,       # for now keep RUNNING here, as KPIs still needs to be queried
                    )
                elif response['State'] == 'ERROR':
                    logger.error(f'ESSIM Simulation failed because: {response["Description"]}')
                    return ModelRunInfo(
                        model_run_id=model_run_id,
                        state=ModelState.ERROR,
                        reason=f'ESSIM Simulation failed because: {response["Description"]}',
                    )
            elif status_code == 404:
                logger.error(response['Description'])
                return ModelRunInfo(
                    model_run_id=model_run_id,
                    state=ModelState.ERROR,
                    reason=f'ESSIM progress monitoring API error (404): {response["Description"]}',
                )
            else:
                logger.error(response['Description'])
                return ModelRunInfo(
                    model_run_id=model_run_id,
                    state=ModelState.ERROR,
                    reason=f'ESSIM progress monitoring API error ({status_code}): {response["Description"]}',
                )

    @staticmethod
    def get_kpi_list():
        kpi_list = []

        status_path = f'{ESSIM_URL}/kpiModules'
        r = requests.get(url=status_path, headers=ESSIM_HEADERS)
        response = r.json()
        status_code = r.status_code

        if status_code == 200:
            # only communicate unique KPI-modules (because they are deployed multiple times)
            already_added_kpi_modules = []
            for kpi in response:
                if not kpi["calculator_id"] in already_added_kpi_modules:
                    kpi_list.append({
                        "id": kpi["calculator_id"],
                        "name": kpi["title"],
                        "descr": kpi["description"]
                    })
                    already_added_kpi_modules.append(kpi["calculator_id"])

        return kpi_list

    @staticmethod
    def process_kpi_results(kpi_result_array, kpi_list):
        kpis_this_sim_run = []
        one_still_calculating = False

        for kpi_result_item in kpi_result_array:
            kpi_id = list(kpi_result_item.keys())[0]
            kpi_result = kpi_result_item[kpi_id]

            kpi_info = dict()
            kpi_info['id'] = kpi_id
            kpi_info['name'] = None
            kpi_info['descr'] = None
            for kpi in kpi_list:
                if kpi['id'] == kpi_id:
                    kpi_info['name'] = kpi['name']
                    kpi_info['descr'] = kpi['descr']

            kpi_info['calc_status'] = kpi_result['status']
            if kpi_info['calc_status'] == 'Not yet started':
                one_still_calculating = True
            if kpi_info['calc_status'] == 'Calculating':
                kpi_info['progress'] = kpi_result['progress']
                one_still_calculating = True
            if kpi_info['calc_status'] == 'Success':
                kpi_info['kpi'] = kpi_result['kpi']
                if 'unit' in kpi_info:
                    kpi_info['unit'] = kpi_result['unit']

            kpis_this_sim_run.append(kpi_info)

        return MonitorKPIResult(
            still_calculating=one_still_calculating,
            results=kpis_this_sim_run
        )

    @staticmethod
    def monitor_kpi_progress(simulation_id, model_run_id):
        if simulation_id is None:
            logger.error('No simulation is started yet!')
            return ModelRunInfo(
                model_run_id=model_run_id,
                state=ModelState.ERROR,
                reason='No simulation is started yet!',
            )

        logger.info("Retrieving KPI list...")
        kpi_list = ESSIM.get_kpi_list()  # contains id, name and description

        logger.info("Start monitoring KPI progress...")
        kpi_path = f'{ESSIM_URL}/{simulation_id}/kpi'
        while True:
            r = requests.get(url=kpi_path, headers=ESSIM_HEADERS)
            response = r.json()
            status_code = r.status_code
            print('kpi ', status_code)
            if status_code == 200:
                kpis_info = ESSIM.process_kpi_results(response, kpi_list)

                if kpis_info.still_calculating:
                    logger.info(kpis_info.results)
                    sleep(PROGRESS_UPDATE_INTERVAL)
                else:
                    logger.info('KPI modules finished')
                    return ModelRunInfo(
                        model_run_id=model_run_id,
                        state=ModelState.SUCCEEDED,
                        result=kpis_info.results
                    )
            else:
                logger.error(f'Monitor KPI modules API error ({status_code})')
                return ModelRunInfo(
                    model_run_id=model_run_id,
                    state=ModelState.ERROR,
                    reason=f'Monitor KPI modules API error ({status_code})',
                )

    def threaded_run(self, model_run_id, config):
        print("Threaded_run:", config)

        # start ESSIM run
        start_essim_info, simulation_id = self.start_essim(config, model_run_id)
        if start_essim_info.state == ModelState.RUNNING:
            # monitor ESSIM progress
            monitor_essim_progress_info = ESSIM.monitor_essim_progress(simulation_id, model_run_id)
            if monitor_essim_progress_info.state == ModelState.ERROR:
                return monitor_essim_progress_info
        else:
            return start_essim_info

        # Monitor KPI progress
        monitor_kpi_progress_info = ESSIM.monitor_kpi_progress(simulation_id, model_run_id)
        return monitor_kpi_progress_info

    def run(self, model_run_id: str):
        res = Model.run(self, model_run_id=model_run_id)

        if model_run_id in self.model_run_dict:
            config: ESSIMAdapterConfig = self.model_run_dict[model_run_id].config

            executor.submit_stored(model_run_id, self.threaded_run, model_run_id, config)
            res.state = ModelState.RUNNING
            return res
        else:
            return ModelRunInfo(
                model_run_id=model_run_id,
                state=ModelState.ERROR,
                reason="Error in ESSIM.run(): model_run_id unknown"
            )

    def status(self, model_run_id: str):
        if model_run_id in self.model_run_dict:
            if not executor.futures.done(model_run_id):
                print("executor.futures._state: ", executor.futures._state(model_run_id))
                return ModelRunInfo(
                    state=self.model_run_dict[model_run_id].state,
                    model_run_id=model_run_id,
                )
            else:
                print("executor.futures._state: ", executor.futures._state(model_run_id))   # FINISHED
                future = executor.futures.pop(model_run_id)
                executor.futures.add(model_run_id, future)   # Put it back on again, so it can be retreived in results
                model_run_info = future.result()
                if model_run_info.result is not None:
                    print(model_run_info.result)
                else:
                    logger.warning("No result in model_run_info variable")
                return model_run_info
        else:
            return ModelRunInfo(
                model_run_id=model_run_id,
                state=ModelState.ERROR,
                reason="Error in ESSIM.status(): model_run_id unknown"
            )

    def process_results(self, result):
        return json.dumps(result)

    def results(self, model_run_id: str):
        # Issue: if status already runs executor.future.pop, future does not exist anymore
        if executor.futures.done(model_run_id):
            if model_run_id in self.model_run_dict:
                future = executor.futures.pop(model_run_id)
                model_run_info = future.result()
                if model_run_info.result is not None:
                    print(model_run_info.result)
                else:
                    logger.warning("No result in model_run_info variable")

                self.model_run_dict[model_run_id].state = model_run_info.state
                if model_run_info.state == ModelState.SUCCEEDED:
                    self.model_run_dict[model_run_id].result = model_run_info.result

                    Model.store_result(self, model_run_id=model_run_id, result=model_run_info.result)
                else:
                    self.model_run_dict[model_run_id].result = {}

                return Model.results(self, model_run_id=model_run_id)
            else:
                return ModelRunInfo(
                    model_run_id=model_run_id,
                    state=ModelState.ERROR,
                    reason="Error in ESSIM.results(): model_run_id unknown"
                )
        else:
            return Model.results(self, model_run_id=model_run_id)
