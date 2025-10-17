from flask import Flask, request, jsonify, Response, Request
from .common.utils import convert_json_to_snake


def build_api():

    app = Flask("calculation_engine")

    app.config["JSON_SORT_KEYS"] = False
    app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True
    app.config["JSONIFY_MIMETYPE"] = "application/json"

    @app.route("/", methods=["GET"])
    def index():
        """
        Endpoint to check if the server is running.
        Returns
        -------
        Response
            JSON response indicating the server is running.
        """
        return jsonify({"status": "running"}), 200

    @app.route("/api/simulation", methods=["POST"])
    def simulation():
        """
        Endpoint to run the simulation.
        Returns
        -------
        Response
            JSON response containing the simulation results.
        """
        from .commands import RunSimulationCommand

        command = RunSimulationCommand.model_validate(convert_json_to_snake(request.json))
        result = command.handle()
        return jsonify(result.model_dump()), 200

    return app
