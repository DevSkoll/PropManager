from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PaymentStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


@dataclass
class PaymentResult:
    success: bool
    transaction_id: Optional[str] = None
    status: PaymentStatus = PaymentStatus.PENDING
    error_message: Optional[str] = None
    raw_response: Optional[dict] = None


@dataclass
class RefundResult:
    success: bool
    refund_id: Optional[str] = None
    error_message: Optional[str] = None


class PaymentGateway(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def create_payment(self, amount, currency, metadata) -> PaymentResult:
        ...

    @abstractmethod
    def verify_payment(self, transaction_id) -> PaymentStatus:
        ...

    @abstractmethod
    def refund_payment(self, transaction_id, amount=None) -> RefundResult:
        ...

    @abstractmethod
    def get_client_config(self) -> dict:
        ...
