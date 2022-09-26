from flask import jsonify
from flask_smorest import Blueprint
from flask.views import MethodView
from tno.shared.log import get_logger
from tno.essim_adapter.types import ModelRunInfo, ESSIMAdapterConfig
from tno.essim_adapter.model.essim import ESSIM


essim = ESSIM()

logger = get_logger(__name__)

api = Blueprint("model", "model", url_prefix="/model")


@api.route("/request")
class Request(MethodView):

    @api.response(200, ModelRunInfo.Schema())
    def get(self):
        res = essim.request()
        return jsonify(res)


@api.route("/initialize/<model_run_id>")
class Initialize(MethodView):

    @api.arguments(ESSIMAdapterConfig.Schema())
    @api.response(201, ModelRunInfo.Schema())
    def post(self, config, model_run_id: str):
        res = essim.initialize(model_run_id=model_run_id, config=config)
        return jsonify(res)


@api.route("/run/<model_run_id>")
class Run(MethodView):

    @api.response(200, ModelRunInfo.Schema())
    def get(self, model_run_id: str):
        res = essim.run(model_run_id=model_run_id)
        return jsonify(res)


@api.route("/status/<model_run_id>")
class Status(MethodView):

    @api.response(200, ModelRunInfo.Schema())
    def get(self, model_run_id: str):
        res = essim.status(model_run_id=model_run_id)
        return jsonify(res)


@api.route("/results/<model_run_id>")
class Results(MethodView):

    @api.response(200, ModelRunInfo.Schema())
    def get(self, model_run_id: str):
        res = essim.results(model_run_id=model_run_id)
        return jsonify(res)


@api.route("/remove/<model_run_id>")
class Remove(MethodView):

    @api.response(200, ModelRunInfo.Schema())
    def get(self, model_run_id: str):
        essim.remove(model_run_id=model_run_id)
        return "REMOVED!", 200
