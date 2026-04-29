import datetime
import uuid
from enum import Enum
from typing import Any, Optional, Self
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, computed_field

IST = ZoneInfo("Asia/Kolkata")

# All Possible Enums for Status of the scheduled call
class CallStatus(str, Enum):
    SCHEDULED = "scheduled"
    QUEUED = "queued"
    RESCHEDULED = "rescheduled"
    INITIATED = "initiated"
    RINGING = "ringing"
    IN_PROGRESS = "in-progress"
    CALL_DISCONNECTED = "call-disconnected"
    COMPLETED = "completed"
    BALANCE_LOW = "balance-low"
    BUSY = "busy"
    NO_ANSWER = "no-answer"
    CANCELED = "canceled"
    FAILED = "failed"
    STOPPED = "stopped"
    ERROR = "error"

# All Call events to skip when alerting - as assignment said to "sends a Slack alert whenever a Bolna call ends"
ALERT_SKIP_STATUSES = [
    CallStatus.SCHEDULED,
    CallStatus.QUEUED,
    CallStatus.RESCHEDULED,
    CallStatus.INITIATED,
    CallStatus.RINGING,
    CallStatus.IN_PROGRESS,
    CallStatus.CANCELED,
]

# Slack has option to send messages with a certain color scheme
STATUS_COLORS: dict[CallStatus, str] = {
    CallStatus.COMPLETED: "#2eb67d",
    CallStatus.CALL_DISCONNECTED: "#ecb22e",
    CallStatus.BUSY: "#ec2ed6",
    CallStatus.NO_ANSWER: "#919191",
    CallStatus.FAILED: "#e01e5a",
    CallStatus.ERROR: "#e01e5a",
    CallStatus.STOPPED: "#919191",
    CallStatus.BALANCE_LOW: "#e8912d",
}


class CallType(str, Enum):
    OUTBOUND = "outbound"
    INBOUND = "inbound"


class TelephonyProvider(str, Enum):
    TWILIO = "twilio"
    PLIVO = "plivo"

# Schema for Payload for Scheduling Calls
class CallRequestModel(BaseModel):
    agent_id: uuid.UUID
    recipient_phone_number: str
    from_phone_number: Optional[str] = None

    date: Optional[datetime.date] = None
    time: Optional[datetime.time] = None
    timezone: str = "Asia/Kolkata"

    user_data: Optional[dict[str, Any]] = None
    agent_data: Optional[dict[str, Any]] = None
    retry_config: Optional[dict[str, Any]] = None

    @computed_field
    @property
    def scheduled_at(self: Self) -> Optional[str]:
        if self.date is None and self.time is None:
            return None
        tz = ZoneInfo(self.timezone)
        d = self.date or datetime.datetime.now(tz).date()
        t = self.time or datetime.datetime.now(tz).time()
        return datetime.datetime.combine(d, t).replace(tzinfo=tz).isoformat(timespec="milliseconds")

# Schema for Response for Scheduling Calls
class CallResponseModel(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "message": "done",
                    "status": "queued",
                    "execution_id": "7ce95e83-0b1b-452d-b687-91bf5d921bb3",
                }
            ]
        }
    )

    message: str
    status: str
    execution_id: str

# Schema for Error Response for fetching call execution result
class ErrorResponse(BaseModel):
    error: int
    message: str


class CostBreakdown(BaseModel):
    model_config = ConfigDict(extra="allow")

    llm: Optional[float] = None
    network: Optional[float] = None
    platform: Optional[float] = None
    synthesizer: Optional[float] = None
    transcriber: Optional[float] = None


class TelephonyData(BaseModel):
    model_config = ConfigDict(extra="allow")

    duration: Optional[str] = None
    to_number: Optional[str] = None
    from_number: Optional[str] = None
    recording_url: Optional[str] = None
    hosted_telephony: Optional[bool] = None
    provider_call_id: Optional[str] = None
    call_type: Optional[CallType] = None
    provider: Optional[TelephonyProvider] = None
    hangup_by: Optional[str] = None
    hangup_reason: Optional[str] = None
    hangup_provider_code: Optional[int] = None
    ring_duration: Optional[int] = None
    post_dial_delay: Optional[int] = None
    to_number_carrier: Optional[str] = None


class TransferCallData(BaseModel):
    model_config = ConfigDict(extra="allow")

    provider_call_id: Optional[str] = None
    status: Optional[CallStatus] = None
    duration: Optional[str] = None
    cost: Optional[float] = None
    to_number: Optional[str] = None
    from_number: Optional[str] = None
    recording_url: Optional[str] = None
    hangup_by: Optional[str] = None
    hangup_reason: Optional[str] = None
    hangup_provider_code: Optional[int] = None


class BatchRunData(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: Optional[CallStatus] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None
    retried: Optional[int] = None

# Schema for Response while fetching call execution result
class CallExecutionResponse(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "id": "7ce95e83-0b1b-452d-b687-91bf5d921bb3",
                    "agent_id": "3ead2b76-6776-4bce-983f-b7e0b8bb4754",
                    "status": "completed",
                    "transcript": "Agent: Hi, am I speaking with Aman?\nUser: Yes, who's this?\n...",
                    "conversation_time": 42.0,
                    "total_cost": 0.0125,
                    "telephony_data": {
                        "duration": "42",
                        "to_number": "+919354885227",
                        "from_number": "+918035735856",
                        "provider": "plivo",
                        "call_type": "outbound",
                        "hangup_by": "User",
                        "hangup_reason": "Normal hangup",
                    },
                    "created_at": "2026-04-29T12:59:27.064546Z",
                    "updated_at": "2026-04-29T13:02:22.443313Z",
                }
            ]
        },
    )

    id: Optional[uuid.UUID] = None
    agent_id: Optional[uuid.UUID] = None
    batch_id: Optional[str] = None
    conversation_time: Optional[float] = None
    total_cost: Optional[float] = None
    status: Optional[CallStatus] = None
    error_message: Optional[str] = None
    answered_by_voice_mail: Optional[bool] = None
    transcript: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None
    cost_breakdown: Optional[CostBreakdown] = None
    telephony_data: Optional[TelephonyData] = None
    transfer_call_data: Optional[TransferCallData] = None
    batch_run_details: Optional[BatchRunData] = None
    extracted_data: Optional[dict[str, Any]] = None
    context_details: Optional[dict[str, Any]] = None
