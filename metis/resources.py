import json
from datetime import datetime

import arrow
from flask import make_response, request
from flask_restful import Api, Resource
from loguru import logger
from voluptuous import All, Length, MultipleInvalid, Optional, Required, Schema

from metis.action import ActionCode
from metis.agents.exceptions import OAuthError
from metis.agents.visa_offers import Visa
from metis.auth import authorized
from metis.basic_services import basic_add_card, basic_reactivate_card, basic_remove_card
from metis.celery import celery
from metis.prometheus.metrics import (
    STATUS_FAILED,
    STATUS_SUCCESS,
    spreedly_retain_processing_seconds_histogram,
    status_counter,
)
from metis.services import create_prod_receiver, retain_payment_method_token
from metis.tasks import add_card, reactivate_card, remove_card
from metis.utils import ctx

api = Api()


def process_card(action_code, card_info, x_azure_ref: str | None = None):
    card_info["action_code"] = action_code
    {
        ActionCode.ADD: lambda: add_card.delay(card_info, x_azure_ref=x_azure_ref),
        ActionCode.DELETE: lambda: remove_card.delay(card_info, x_azure_ref=x_azure_ref),
        ActionCode.REACTIVATE: lambda: reactivate_card.delay(card_info, x_azure_ref=x_azure_ref),
    }[action_code]()


card_info_schema = Schema(
    {
        Required("id"): int,
        Required("payment_token"): All(str, Length(min=1)),
        Required("card_token"): All(str, Length(min=1)),
        Required("date"): int,
        Required("partner_slug"): All(str, Length(min=1)),
        Optional("retry_id"): int,
        Optional("activations"): dict,
    }
)


class Healthz(Resource):
    def get(self):
        return {}


api.add_resource(Healthz, "/healthz")


class Livez(Resource):
    def get(self):
        return {}


api.add_resource(Livez, "/livez")


class Readyz(Resource):
    def get(self):
        try:
            celery.control.inspect().ping()
        except Exception as ex:
            logger.exception("failed to connect to celery broker")
            return {"celery": f"failed to connect to celery broker due to error: {ex!r}"}, 500

        return {}


api.add_resource(Readyz, "/readyz")


class CreateReceiver(Resource):
    # FIXME: This endpoint is only ever used to set up a new spreedly environment
    # It is not used in normal journeys and so should probably live in a different
    # module
    @authorized
    def post(self):
        ctx.x_azure_ref = request.headers.get("x-azure-ref")
        req_data = json.loads(request.data.decode())
        if req_data is not None and len(req_data) > 0:
            result = create_prod_receiver(req_data["receiver_type"])
            response_text = result.text
            status_code = result.status_code
        else:
            response_text = str({"Error": "Please provide the hostname url."})
            status_code = 422

        return make_response(response_text, status_code)


api.add_resource(CreateReceiver, "/payment_service/create_receiver")


class PaymentCard(Resource):
    def action(self, action_code):
        ctx.x_azure_ref = request.headers.get("x-azure-ref")
        req_data = json.loads(request.data.decode())

        action_name = {ActionCode.ADD: "add", ActionCode.DELETE: "delete"}[action_code]
        try:
            card_info_schema(req_data)
        except MultipleInvalid:
            logger.error(
                f"{arrow.now()} Received {action_name} payment card request failed " f"- invalid schema: {req_data}"
            )
            return make_response("Request parameters not complete", 400)

        logger.info(f"{arrow.now()} Received {action_name} payment card request: {req_data}")
        if action_code == ActionCode.ADD:
            status_code = 500
            resp_text = " No reply received"
            try:
                response_start_time = datetime.now()
                resp = retain_payment_method_token(req_data["payment_token"], req_data.get("partner_slug"))
                response_total_time = datetime.now() - response_start_time

                status_code = resp.status_code
                reason = resp.reason
                resp_text = resp.text

                spreedly_retain_processing_seconds_histogram.labels(
                    provider=req_data.get("partner_slug"), status=status_code
                ).observe(response_total_time.total_seconds())
            except AttributeError:
                status_code = 504
                reason = "Connection failed after retry"
            except Exception as e:
                status_code = 500
                reason = f"Exception {e}"

            if status_code != 200:
                status_counter.labels(provider=req_data.get("partner_slug"), status=STATUS_FAILED).inc()
                logger.info(
                    f"Retain unsuccessful: HTTP {status_code} {reason} {resp_text}"
                    f'Payment token: {req_data.get("payment_token")} partner: {req_data.get("partner_slug")}'
                )
                return make_response("Retain unsuccessful", 400)

            status_counter.labels(provider=req_data.get("partner_slug"), status=STATUS_SUCCESS).inc()

        process_card(action_code, req_data, x_azure_ref=ctx.x_azure_ref)

        return make_response("Success", 200)

    @authorized
    def post(self):
        return self.action(ActionCode.ADD)

    @authorized
    def delete(self):
        return self.action(ActionCode.DELETE)


api.add_resource(PaymentCard, "/payment_service/payment_card")


class PaymentCardUpdate(Resource):
    @authorized
    def post(self):
        req_data = json.loads(request.data.decode())
        ctx.x_azure_ref = request.headers.get("x-azure-ref")

        logger.info(f"{arrow.now()} Received reactivate payment card request: {req_data}")

        try:
            card_info_schema(req_data)
        except MultipleInvalid:
            return make_response("Request parameters not complete", 400)

        process_card(ActionCode.REACTIVATE, req_data, x_azure_ref=ctx.x_azure_ref)

        return make_response("Success", 200)


api.add_resource(PaymentCardUpdate, "/payment_service/payment_card/update")


class VisaActivate(Resource):
    @staticmethod
    def post():
        ctx.x_azure_ref = request.headers.get("x-azure-ref")
        visa = Visa()
        response_status, status_code, agent_response_code, agent_message, other_data = visa.activate_card(request.json)
        response = make_response(
            json.dumps(
                {
                    "response_status": response_status,
                    "agent_response_code": agent_response_code,
                    "agent_response_message": agent_message,
                    "activation_id": other_data.get("activation_id", ""),
                }
            ),
            status_code,
        )
        response.headers["Content-Type"] = "application/json"
        return response


api.add_resource(VisaActivate, "/visa/activate/")


class VisaDeactivate(Resource):
    @staticmethod
    def post():
        ctx.x_azure_ref = request.headers.get("x-azure-ref")
        visa = Visa()
        response_status, status_code, agent_response_code, agent_message, _ = visa.deactivate_card(request.json)
        response = make_response(
            json.dumps(
                {
                    "response_status": response_status,
                    "agent_response_code": agent_response_code,
                    "agent_response_message": agent_message,
                }
            ),
            status_code,
        )
        response.headers["Content-Type"] = "application/json"
        return response


api.add_resource(VisaDeactivate, "/visa/deactivate/")

"""
    Foundation interface is intended to be used by data correction scripts in the first instance
    It does basic actions without any background processing and returns a json dict
    Note it does not map the called service response code to http return codes; 200 if api call is success even if
    the called service returns an error.  The response data has a status_code field which should be checked
"""


foundation_retain_schema = Schema({Required("id"): int, Required("payment_token"): All(str, Length(min=1))})


foundation_add_schema = Schema(
    {
        Required("id"): int,
        Required("payment_token"): All(str, Length(min=1)),
        Required("card_token"): All(str, Length(min=1)),
        Optional("status_map"): dict,
    }
)


foundation_delete_schema = Schema(
    {
        Required("id"): int,
        Required("payment_token"): All(str, Length(min=1)),
        Required("partner_slug"): All(str, Length(min=1)),
        Optional("status_map"): dict,
    }
)


def foundation_response(ret, status_code):
    response = make_response(json.dumps(ret), status_code)
    response.headers["Content-Type"] = "application/json"
    return response


def set_ret():
    return {
        "status_code": 0,
        "resp_text": "",
        "reason": "",
        "bink_status": "",
        "agent_response_code": "",
        "agent_retry_status": "",
    }


class InvalidParams(Exception):
    pass


def foundation_check_request(schema, agent, req_data, ret):
    try:
        schema(req_data)
    except MultipleInvalid as e:
        ret["reason"] = f"Invalid/Missing Request Parameters: {e}"
        ret["agent_retry_status"] = "Failed"
        raise InvalidParams from None
    if agent not in ("visa", "mastercard", "amex"):
        ret["reason"] = "Invalid Agent"
        ret["agent_retry_status"] = "Failed"
        raise InvalidParams


def map_response(resp, ret):
    ret["status_code"] = resp["status_code"]
    ret["bink_status"] = resp.get("bink_status")
    ret["resp_text"] = resp.get("response_state")
    ret["reason"] = resp["message"]
    ret["agent_response_code"] = resp.get("agent_status_code")
    ret["agent_retry_status"] = resp.get("response_state")


class FoundationSpreedlyRetain(Resource):
    @authorized
    def post(self, agent):
        req_data = request.json
        ret = set_ret()
        try:
            foundation_check_request(foundation_retain_schema, agent, req_data, ret)
            resp = retain_payment_method_token(req_data["payment_token"], agent)
            ret["status_code"] = resp.status_code
            ret["resp_text"] = resp.text
            ret["reason"] = resp.reason
        except AttributeError:
            ret["status_code"] = 504
            ret["reason"] = "Connection failed after retry"
            ret["agent_retry_status"] = "Failed"
        except InvalidParams:
            pass
        except Exception as e:
            ret["status_code"] = 500
            ret["reason"] = f"Exception {e}"
            ret["agent_retry_status"] = "Failed"

        return foundation_response(ret, 200)


class FoundationSpreedlyAdd(Resource):
    @authorized
    def post(self, agent):
        req_data = request.json
        ret = set_ret()
        try:
            foundation_check_request(foundation_add_schema, agent, req_data, ret)
            resp = basic_add_card(agent, req_data)
            map_response(resp, ret)

        except OAuthError:
            ret["reason"] = "OAuthError"
            ret["agent_retry_status"] = "Failed"
        except InvalidParams:
            pass
        except Exception as e:
            ret["status_code"] = 500
            ret["reason"] = f"Exception {e}"
            ret["agent_retry_status"] = "Failed"

        return foundation_response(ret, 200)


class FoundationRemove(Resource):
    @authorized
    def post(self, agent):
        req_data = request.json
        ret = set_ret()
        try:
            foundation_check_request(foundation_delete_schema, agent, req_data, ret)
            response_status, api_code, agent_error_code, agent_message, other = basic_remove_card(agent, req_data)
            ret["status_code"] = api_code
            ret["resp_text"] = ""
            ret["reason"] = agent_message
            ret["bink_status"] = other.get("bink_status", "unknown")
            ret["agent_response_code"] = agent_error_code
            ret["agent_retry_status"] = response_status
        except OAuthError:
            ret["reason"] = "OAuthError"
            ret["agent_retry_status"] = "Failed"
        except InvalidParams:
            pass
        except Exception as e:
            ret["status_code"] = 500
            ret["reason"] = f"Exception {e}"
            ret["agent_retry_status"] = "Failed"

        return foundation_response(ret, 200)


class FoundationSpreedlyMCReactivate(Resource):
    @authorized
    def post(self):
        req_data = request.json
        ret = set_ret()
        agent = "mastercard"
        try:
            foundation_check_request(foundation_add_schema, agent, req_data, ret)
            # response_status, status_code, agent_response_code, agent_message, _
            resp = basic_reactivate_card(agent, req_data)
            map_response(resp, ret)

        except OAuthError:
            ret["reason"] = "OAuthError"
            ret["agent_retry_status"] = "Failed"
        except InvalidParams:
            pass
        except Exception as e:
            ret["status_code"] = 500
            ret["reason"] = f"Exception {e}"
            ret["agent_retry_status"] = "Failed"

        return foundation_response(ret, 200)


api.add_resource(FoundationSpreedlyRetain, "/foundation/spreedly/<agent>/retain")
api.add_resource(FoundationSpreedlyAdd, "/foundation/spreedly/<agent>/add")
api.add_resource(FoundationSpreedlyMCReactivate, "/foundation/spreedly/mastercard/reactivate")
api.add_resource(FoundationRemove, "/foundation/<agent>/remove")
