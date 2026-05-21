from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class EmailRequest(BaseModel):
    to: List[EmailStr]
    subject: str = Field(..., min_length=1, max_length=200)
    body: str
    html_body: Optional[str] = None
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None


class EmailTemplateRequest(BaseModel):
    to_email: EmailStr
    template_type: str = Field(..., pattern="^(verification|password_reset|account_unlock)$")
    code: Optional[str] = None
    url: Optional[str] = None


class EmailResponse(BaseModel):
    success: bool
    message: str
    sent_count: int


class SMSRequest(BaseModel):
    phone_numbers: List[str]
    message: str = Field(..., max_length=500)


class SMSResponse(BaseModel):
    success: bool
    message: str
    sent_count: int


class NotificationRequest(BaseModel):
    user_ids: List[str]
    title: str
    content: str
    type: str = Field(..., pattern="^(info|warning|error|success)$")


class NotificationResponse(BaseModel):
    success: bool
    message: str


class SystemStatusResponse(BaseModel):
    service: str
    status: str
    details: Optional[dict] = None