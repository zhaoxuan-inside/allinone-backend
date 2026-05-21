from typing import List

from fastapi import APIRouter, Depends

from common.permissions import Roles, require_role
from system_service.schemas import (
    EmailRequest, EmailResponse, EmailTemplateRequest,
    NotificationRequest, NotificationResponse,
    SystemStatusResponse
)
from system_service.service import EmailService, NotificationService, SystemStatusService

router = APIRouter(prefix="/system", tags=["system"])


@router.post("/email/send", response_model=EmailResponse)
async def send_email(
    request: EmailRequest,
    _=Depends(require_role(Roles.ADMIN))
):
    """发送普通邮件（管理员）"""
    service = EmailService()
    return await service.send_email(request)


@router.post("/email/template", response_model=EmailResponse)
async def send_template_email(request: EmailTemplateRequest):
    """发送模板邮件（注册验证、密码重置、账户解锁）"""
    service = EmailService()
    
    if request.template_type == "verification":
        return await service.send_verification_email(request.to_email, request.code)
    elif request.template_type == "password_reset":
        return await service.send_password_reset_email(request.to_email, request.url)
    elif request.template_type == "account_unlock":
        return await service.send_account_unlock_email(request.to_email, request.code)
    
    return EmailResponse(success=False, message="Invalid template type", sent_count=0)


@router.post("/notification/send", response_model=NotificationResponse)
async def send_notification(request: NotificationRequest):
    """发送系统通知"""
    service = NotificationService()
    return await service.send_notification(request)


@router.get("/status", response_model=List[SystemStatusResponse])
async def get_system_status():
    """获取系统状态"""
    service = SystemStatusService()
    return await service.check_status()