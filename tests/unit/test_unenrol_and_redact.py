import json
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
import responses
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from requests import ConnectionError, Response

from metis import create_app
from metis.action import ActionCode
from metis.enums import RetryTypes
from metis.tasks import remove_and_redact

auth_key = (
    "Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjMyL"
    "CJpYXQiOjE0NDQ5ODk2Mjh9.N-0YnRxeei8edsuxHHQC7-okLoWKfY6uE6YmcOWlFLU"
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("redact_only", "priority", "expected_route"),
    (
        pytest.param(False, 4, "metis.tasks.low", id="unenroll and redact, low priority"),
        pytest.param(True, 6, "metis.tasks.high", id="redact only, high priority"),
    ),
)
@pytest.mark.parametrize(
    "partner_slug",
    (
        "visa",
        "amex",
        "mastercard",
    ),
)
def test_unenroll_and_redact_resource(
    client: TestClient, mocker: MockerFixture, redact_only: bool, priority: int, expected_route: str, partner_slug: str
) -> None:
    mock_task = mocker.patch("metis.api.resources.remove_and_redact")

    card_info = {
        "id": 1,
        "payment_token": "1111111111111111111111",
        "card_token": "111111111111112",
        "date": 1475920002,
        "partner_slug": partner_slug,
    }

    response = client.post(
        "/payment_service/payment_card/unenrol_and_redact",
        json=card_info | {"redact_only": redact_only},
        headers={
            "Authorization": auth_key,
            "X-Azure-Ref": "test-azure-ref",
            "X-Priority": str(priority),
        },
    )
    assert response.status_code == 200
    mock_task.apply_async.assert_called_once_with(
        args=[card_info | {"action_code": ActionCode.DELETE}],
        kwargs={"x_azure_ref": "test-azure-ref", "redact_only": redact_only},
        exchange="metis-celery-tasks",
        routing_key=expected_route,
        priority=priority,
    )


@pytest.mark.parametrize(
    "redact_only",
    (
        pytest.param(True, id="redact only"),
        pytest.param(False, id="unenroll and redact"),
    ),
)
@pytest.mark.parametrize(
    ("response_status", "response_payload"),
    (
        pytest.param(
            201,
            {
                "transaction": {
                    "succeeded": True,
                }
            },
            id="success response 1",
        ),
        pytest.param(
            201,
            {
                "transaction": {
                    "succeeded": False,
                    "payment_method": {"storage_state": "redacted"},
                }
            },
            id="success response 2",
        ),
        pytest.param(404, "Not Found", id="card not found"),
    ),
)
@pytest.mark.parametrize(
    "partner_slug",
    (
        "visa",
        "amex",
        "mastercard",
    ),
)
@responses.activate
def test_remove_and_redact_task_ok(
    mocker: MockerFixture, partner_slug: str, redact_only: bool, response_status: int, response_payload: dict
) -> None:
    from metis.settings import settings

    mock_remove_card = mocker.patch("metis.tasks.services.remove_card")
    mock_put_account_status = mocker.patch("metis.tasks.services.put_account_status")
    payment_token = str(uuid4())

    responses.add(
        responses.PUT,
        f"{settings.SPREEDLY_BASE_URL}/payment_methods/{payment_token}/redact.json",
        status=response_status,
        body=json.dumps(response_payload),
        content_type="application/json",
    )

    card_info = {
        "id": 1,
        "payment_token": payment_token,
        "card_token": "111111111111112",
        "date": 1475920002,
        "partner_slug": partner_slug,
        "action_code": ActionCode.DELETE,
    }

    remove_and_redact(card_info, redact_only, "test-azure-ref")

    mock_put_account_status.assert_not_called()

    if redact_only:
        mock_remove_card.assert_not_called()
    else:
        mock_remove_card.assert_called_once_with(card_info, retry_type=RetryTypes.REMOVE_AND_REDACT)


@pytest.mark.parametrize(
    "redact_only",
    (
        pytest.param(True, id="redact only"),
        pytest.param(False, id="unenroll and redact"),
    ),
)
@pytest.mark.parametrize(
    "response",
    (
        pytest.param(MagicMock(spec=Response, status_code=500, json=lambda: "System Error"), id="500 System Error"),
        pytest.param(ConnectionError, id="Connection Error"),
    ),
)
@pytest.mark.parametrize(
    "partner_slug",
    (
        "visa",
        "amex",
        "mastercard",
    ),
)
def test_remove_and_redact_task_errors(
    mocker: MockerFixture, partner_slug: str, response: Response | Exception, redact_only: bool
) -> None:
    mock_remove_card = mocker.patch("metis.tasks.services.remove_card")
    mock_send_request = mocker.patch("metis.tasks.services.send_request")
    mock_put_account_status = mocker.patch("metis.tasks.services.put_account_status")
    card_id = 1
    action_code = ActionCode.DELETE

    if isinstance(response, Response):
        mock_send_request.return_value = response
        put_status = 6
    else:
        mock_send_request.side_effect = response
        put_status = 5

    card_info = {
        "id": card_id,
        "payment_token": "111111111111112",
        "card_token": "111111111111112",
        "date": 1475920002,
        "partner_slug": partner_slug,
        "action_code": action_code,
    }

    remove_and_redact(card_info, redact_only, "test-azure-ref")

    if redact_only:
        mock_remove_card.assert_not_called()
    else:
        mock_remove_card.assert_called_once_with(card_info, retry_type=RetryTypes.REMOVE_AND_REDACT)

    mock_put_account_status.assert_called_once_with(
        put_status,
        card_id,
        response_action=action_code,
        response_state="Retry",
        retry_type=RetryTypes.REDACT.value,
    )
