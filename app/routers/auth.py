from fastapi import APIRouter, Depends, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import random
import datetime

from .. import schemas, crud, models, plans
from ..database import get_db
from ..common.dependencies import create_access_token, create_refresh_token, get_current_active_user
from ..common.response_model import ResponseModel, APIException
from ..globals import fm, logger
from fastapi_mail import MessageSchema
from aiosmtplib.errors import SMTPResponseException


router = APIRouter()

async def send_email_task(message: MessageSchema):
    try:
        await fm.send_message(message)
        logger.info(f"邮件已成功投递到 SMTP 服务器: 主题='{message.subject}', 收件人={message.recipients}")
    except SMTPResponseException as e:
        logger.warning(f"邮件发送后关闭连接时出现SMTP响应异常 (通常无害): {e}")
    except Exception as e:
        logger.error(f"发送邮件时发生严重错误: {e}", exc_info=True)

@router.post("/send-registration-code", response_model=ResponseModel)
async def send_code(req: schemas.SendCodeRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, email=req.email):
        raise APIException(code=status.HTTP_400_BAD_REQUEST, msg="该邮箱已注册")
    code = f"{random.randint(0, 999999):06d}"
    expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    crud.create_or_update_verification_code(db, req.email, code, expires)
    db.commit()
    message = MessageSchema(
        subject="【雷达股眼】您的注册验证码",
        recipients=[req.email],
        body=f"<p>您的注册验证码是: <strong>{code}</strong></p><p>该验证码10分钟内有效。</p>",
        subtype="html"
    )
    background_tasks.add_task(send_email_task, message)
    logger.info(f"验证码邮件任务已添加至后台队列，发送至: {req.email}")
    return ResponseModel(msg="验证码已发送至您的邮箱，请注意查收。")

@router.post("/register", response_model=ResponseModel[schemas.UserInfo])
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    code_obj = crud.get_verification_code(db, email=user_data.email)
    if not code_obj or code_obj.code != user_data.verification_code or code_obj.expires_at < datetime.datetime.utcnow():
        raise APIException(code=status.HTTP_400_BAD_REQUEST, msg="验证码错误或已过期")
    if crud.get_user_by_username(db, username=user_data.email):
        raise APIException(code=status.HTTP_400_BAD_REQUEST, msg="该邮箱已被注册")
    new_user = crud.create_user(db, user_data)
    crud.delete_verification_code(db, user_data.email)
    db.commit()
    db.refresh(new_user)
    return ResponseModel(data=new_user)

@router.post("/token", response_model=ResponseModel[schemas.Token])
def login_for_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = crud.authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user: raise APIException(code=status.HTTP_401_UNAUTHORIZED, msg="邮箱或密码错误")
    if not user.is_active: raise APIException(code=status.HTTP_400_BAD_REQUEST, msg="账户已被禁用")
    user = plans.apply_plan_limits(user)
    crud.update_user(db, user=user)
    token_data = {"user_id": user.id}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)
    return ResponseModel(data=schemas.Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer", user_info=user))

@router.get("/me", response_model=ResponseModel[schemas.UserInfo])
def read_me(current_user: models.User = Depends(get_current_active_user)):
    return ResponseModel(data=current_user)

@router.post("/me/reset-api-token", response_model=ResponseModel[schemas.UserInfo])
def reset_api_token_route(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    updated_user = plans.reset_api_token(current_user)
    crud.update_user(db, user=updated_user)
    logger.info(f"用户 {current_user.email} 成功重置了 API Token。")
    return ResponseModel(data=updated_user, msg="API Token 重置成功！")