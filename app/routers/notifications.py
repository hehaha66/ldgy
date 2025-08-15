# 文件路径: app/routers/notifications.py
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi_mail import MessageSchema
from pydantic import BaseModel, EmailStr

from .. import models
from ..database import get_db
from ..common.dependencies import get_current_active_user
from ..common.response_model import ResponseModel
from ..globals import fm, logger
from ..routers.auth import send_email_task  # 复用 auth.py 的后台任务

router = APIRouter(
    tags=["Notifications"],
    dependencies=[Depends(get_current_active_user)]
)


class TestEmailRequest(BaseModel):
    target_email: EmailStr


@router.post("/notifications/send-test-email", response_model=ResponseModel)
async def send_test_notification_email(
        req: TestEmailRequest,
        background_tasks: BackgroundTasks,
        current_user: models.User = Depends(get_current_active_user),
):
    """发送一封测试警报邮件到指定邮箱。"""
    subject = "【雷达股眼】这是一封测试警报邮件"
    body = f"<p>您好, {current_user.nickname or current_user.email}！</p><p>如果您收到这封邮件，说明您的警报邮箱通知已配置成功。</p>"

    message = MessageSchema(
        subject=subject,
        recipients=[req.target_email],
        body=body,
        subtype="html"
    )
    background_tasks.add_task(send_email_task, message)

    logger.info(f"用户 {current_user.email} 发送了一封测试邮件到 {req.target_email}")
    return ResponseModel(msg="测试邮件已发送，请注意查收。")