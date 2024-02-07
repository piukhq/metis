from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from httpx import Response


class AbstractAgentBase(ABC):
    @abstractmethod
    def response_handler(
        self,
        response: "Response",
        action_name: str,
        status_mapping: dict,
    ) -> dict:
        ...

    @abstractmethod
    def remove_card_body(self, card_info: dict) -> str:
        ...
