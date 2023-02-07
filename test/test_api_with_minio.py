from time import sleep

import requests

api_endpoint = "http://localhost:9203"


res = requests.get(api_endpoint + '/status')
if res.ok:
    print("Endpoint /status ok! ")
else:
    print("Endpoint /status not ok! ")
    exit(1)

model_run_id = None
res = requests.get(api_endpoint + '/model/request')
if res.ok:
    print("Endpoint /model/request ok!")
    result = res.json()
    print(result)
    model_run_id = result['model_run_id']
else:
    print("Endpoint /model/request not ok!")
    exit(1)

post_body = {
    "essim_post_body": {
        "user": "essim",
        "scenarioID": "essim_mmvib_adapter_test",
        "simulationDescription": "ESSIM MMvIB adapter test",
        "startDate": "2019-01-01T00:00:00+0100",
        "endDate": "2019-12-31T23:00:00+0100",
        "influxURL": "http://influxdb:8086",
        "grafanaURL": "http://grafana:3000",
        "natsURL": "nats://nats:4222",
        "kpiModule": {
            "modules": [
                {
                    "id": "TotalEnergyProductionID",
                    "config": {"scope": "Local"}
                },
                {
                    "id": "TotalImportedEnergyID",
                    "config": {"scope": "Local"}
                },
                {
                    "id": "TotalExportedEnergyID",
                    "config": {"scope": "Local"}
                }
            ]
        },
    },
    "base_path": "bedrijventerreinommoord/Scenario_1_II3050_Nationale_Sturing/Trial_1/MM_workflow_run_1/",
    # "input_esdl_file_path": "ESDL_add_price_profile_adapter/Hybrid HeatPump.esdl",
    # "input_esdl_file_path": "ESDL_add_price_profile_adapter/HHP_profile.esdl",
    "input_esdl_file_path": "ESSIM_adapter/Tholen-simple v04-26kW.esdl",
    "output_esdl_file_path": "ESSIM_adapter/Tholen-simple v04-26kW_output.esdl",
    "output_file_path": "ESSIM_adapter/KPIs.json"
}

res = requests.post(api_endpoint + '/model/initialize/' + model_run_id, json=post_body)
if res.ok:
    print("Endpoint /model/initialize ok!")
    result = res.json()
    print(result)
else:
    print("Endpoint /model/initialize not ok!")
    exit(1)

res = requests.get(api_endpoint + '/model/run/' + model_run_id)
if res.ok:
    print("Endpoint /model/run ok!")
    result = res.json()
    print(result)
else:
    print("Endpoint /model/run not ok!")
    exit(1)

succeeded = False
while not succeeded:
    res = requests.get(api_endpoint + '/model/status/' + model_run_id)
    if res.ok:
        print("Endpoint /model/status ok!")
        result = res.json()
        print(result)
        if result['state'] == 'SUCCEEDED':
            succeeded = True
        elif result['state'] == 'ERROR':
            print(result['reason'])
            break
        else:
            sleep(2)
    else:
        print("Endpoint /model/status not ok!")
        exit(1)

res = requests.get(api_endpoint + '/model/results/' + model_run_id)
if res.ok:
    print("Endpoint /model/results ok!")
    result = res.json()
    print(result)
else:
    print("Endpoint /model/results not ok!")
    exit(1)

res = requests.get(api_endpoint + '/model/remove/' + model_run_id)
if res.ok:
    print("Endpoint /model/remove ok!")
    result = res.json()
    print(result)
else:
    print("Endpoint /model/remove not ok!")
    exit(1)
