from pydantic import BaseModel, Field, field_validator


class CreateReceiverSchema(BaseModel, extra="allow"):
    receiver_type: str
    hostname: str | None = None


class CardInfoSchema(BaseModel):
    id: int  # noqa: A003
    payment_token: str = Field(..., min_length=1)
    card_token: str = Field(..., min_length=1)
    date: int
    partner_slug: str = Field(..., min_length=1)
    retry_id: int | None = None
    activations: dict | None = None


class _VisaVOPSchema(BaseModel):
    id: int  # noqa: A003
    payment_token: str
    partner_slug: str
    offer_id: str | None = None

    @field_validator("offer_id", mode="before")
    @classmethod
    def validate_offer_id(cls, value: int | str | None) -> str | None:
        if value is None:
            return None

        return str(value)


class VisaVOPActivationSchema(_VisaVOPSchema):
    merchant_group: str | None = None
    merchant_slug: str | None = None


# TODO: make sure activation id is not optional
class VisaVOPDeactivationSchema(_VisaVOPSchema):
    activation_id: str


class VisaDeactivationResponseSchema(BaseModel):
    response_status: str
    agent_response_code: str
    agent_response_message: str


class VisaActivationResponseSchema(VisaDeactivationResponseSchema):
    activation_id: str | None


class FoundationRetainSchema(BaseModel):
    id: int  # noqa: A003
    payment_token: str = Field(..., min_length=1)


class FoundationAddSchema(FoundationRetainSchema):
    card_token: str = Field(..., min_length=1)
    status_map: dict | None = None


class FoundationDeleteSchema(FoundationRetainSchema):
    partner_slug: str = Field(..., min_length=1)
    status_map: dict | None = None


class FoundationResponseSchema(BaseModel):
    status_code: int
    resp_text: str
    reason: str
    bink_status: str
    agent_response_code: str
    agent_retry_status: str
