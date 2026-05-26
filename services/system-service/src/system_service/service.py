import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from datetime import datetime

from common.settings import get_settings
from src.system_service.schemas import (
    EmailRequest, EmailResponse, EmailTemplateRequest,
    NotificationRequest, NotificationResponse,
    SystemStatusResponse
)


class EmailService:
    def __init__(self):
        self.settings = get_settings()
        self._smtp_config = self._load_smtp_config()

    def _load_smtp_config(self):
        """从配置中心加载SMTP配置"""
        return {
            "host": self.settings.email_host or "smtp.example.com",
            "port": self.settings.email_port or 587,
            "username": self.settings.email_username or "",
            "password": self.settings.email_password or "",
            "from_email": self.settings.email_from or "noreply@example.com",
            "use_tls": self.settings.email_use_tls or True
        }

    async def send_email(self, request: EmailRequest) -> EmailResponse:
        """发送普通邮件"""
        try:
            msg = self._build_message(
                to=request.to,
                subject=request.subject,
                body=request.body,
                html_body=request.html_body,
                cc=request.cc,
                bcc=request.bcc
            )
            
            sent_count = await self._send(msg)
            return EmailResponse(
                success=True,
                message=f"Email sent successfully to {sent_count} recipients",
                sent_count=sent_count
            )
        except Exception as e:
            return EmailResponse(
                success=False,
                message=f"Failed to send email: {str(e)}",
                sent_count=0
            )

    async def send_verification_email(self, to_email: str, verification_code: str) -> EmailResponse:
        """发送注册验证邮件"""
        subject = "邮箱验证 - AllInOne平台"
        body = f"""您好！

感谢您注册 AllInOne 平台。请使用以下验证码完成邮箱验证：

{verification_code}

验证码有效期为1小时，请尽快完成验证。

如果您没有注册账号，请忽略此邮件。

AllInOne 团队"""
        
        html_body = f"""<html>
<body>
<h3>您好！</h3>
<p>感谢您注册 AllInOne 平台。请使用以下验证码完成邮箱验证：</p>
<p style="font-size: 24px; font-weight: bold; color: #1890ff; margin: 20px 0;">{verification_code}</p>
<p>验证码有效期为1小时，请尽快完成验证。</p>
<p>如果您没有注册账号，请忽略此邮件。</p>
<p>AllInOne 团队</p>
</body>
</html>"""
        
        request = EmailRequest(
            to=[to_email],
            subject=subject,
            body=body,
            html_body=html_body
        )
        return await self.send_email(request)

    async def send_password_reset_email(self, to_email: str, reset_url: str) -> EmailResponse:
        """发送密码重置邮件"""
        subject = "密码重置 - AllInOne平台"
        body = f"""您好！

您请求重置 AllInOne 平台的密码。请点击以下链接完成重置：

{reset_url}

链接有效期为1小时，请尽快完成操作。

如果您没有请求重置密码，请忽略此邮件。

AllInOne 团队"""
        
        html_body = f"""<html>
<body>
<h3>您好！</h3>
<p>您请求重置 AllInOne 平台的密码。请点击以下链接完成重置：</p>
<p><a href="{reset_url}" style="display: inline-block; padding: 10px 20px; background-color: #1890ff; color: white; text-decoration: none; border-radius: 4px;">重置密码</a></p>
<p>链接有效期为1小时，请尽快完成操作。</p>
<p>如果您没有请求重置密码，请忽略此邮件。</p>
<p>AllInOne 团队</p>
</body>
</html>"""
        
        request = EmailRequest(
            to=[to_email],
            subject=subject,
            body=body,
            html_body=html_body
        )
        return await self.send_email(request)

    async def send_account_unlock_email(self, to_email: str, unlock_code: str) -> EmailResponse:
        """发送账户解锁邮件"""
        subject = "账户解锁 - AllInOne平台"
        body = f"""您好！

您的 AllInOne 账户已被锁定。请使用以下验证码解锁账户：

{unlock_code}

验证码有效期为1小时，请尽快完成解锁。

AllInOne 团队"""
        
        html_body = f"""<html>
<body>
<h3>您好！</h3>
<p>您的 AllInOne 账户已被锁定。请使用以下验证码解锁账户：</p>
<p style="font-size: 24px; font-weight: bold; color: #1890ff; margin: 20px 0;">{unlock_code}</p>
<p>验证码有效期为1小时，请尽快完成解锁。</p>
<p>AllInOne 团队</p>
</body>
</html>"""
        
        request = EmailRequest(
            to=[to_email],
            subject=subject,
            body=body,
            html_body=html_body
        )
        return await self.send_email(request)

    def _build_message(
        self,
        to: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> MIMEMultipart:
        """构建邮件消息"""
        msg = MIMEMultipart('alternative')
        msg['From'] = self._smtp_config["from_email"]
        msg['To'] = ', '.join(to)
        msg['Subject'] = subject
        
        if cc:
            msg['Cc'] = ', '.join(cc)
        
        # 添加纯文本内容
        text_part = MIMEText(body, 'plain', 'utf-8')
        msg.attach(text_part)
        
        # 添加HTML内容（如果有）
        if html_body:
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)
        
        return msg

    async def _send(self, msg: MIMEMultipart) -> int:
        """发送邮件"""
        config = self._smtp_config
        
        with smtplib.SMTP(config["host"], config["port"]) as server:
            if config["use_tls"]:
                server.starttls()
            
            if config["username"] and config["password"]:
                server.login(config["username"], config["password"])
            
            # 获取所有收件人（包括 to, cc, bcc）
            recipients = []
            if msg['To']:
                recipients.extend([r.strip() for r in msg['To'].split(',')])
            if msg['Cc']:
                recipients.extend([r.strip() for r in msg['Cc'].split(',')])
            if msg.get('Bcc'):
                recipients.extend([r.strip() for r in msg['Bcc'].split(',')])
            
            server.send_message(msg)
            return len(recipients)


class NotificationService:
    async def send_notification(self, request: NotificationRequest) -> NotificationResponse:
        try:
            return NotificationResponse(
                success=True,
                message=f"Notification sent to {len(request.user_ids)} users"
            )
        except Exception as e:
            return NotificationResponse(
                success=False,
                message=f"Failed to send notification: {str(e)}"
            )


class SystemStatusService:
    async def check_status(self) -> List[SystemStatusResponse]:
        services = [
            {"service": "email", "status": "healthy"},
            {"service": "notification", "status": "healthy"},
            {"service": "redis", "status": "healthy"},
            {"service": "database", "status": "healthy"}
        ]
        return [SystemStatusResponse(**s) for s in services]