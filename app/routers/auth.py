# 文件: app/routers/auth.py (最终修正版 - 中文注释)

from fastapi import APIRouter, Depends, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import random
import datetime

from .. import schemas, crud, models, plans
from ..database import get_db
# 确保导入了正确的依赖
from ..common.dependencies import create_access_token, create_refresh_token, get_current_active_user, \
    get_user_from_header_or_query
from ..common.response_model import ResponseModel, APIException
from ..globals import fm, logger
from fastapi_mail import MessageSchema
from aiosmtplib.errors import SMTPResponseException

router = APIRouter()


def get_full_user_response_data(user: models.User) -> dict:
    """
    一个辅助函数，用于创建包含完整权限的、用于API响应的字典。
    这是一个最佳实践，可以避免代码重复。
    """
    # 1. 从 PLANS_CONFIG 中获取该用户当前套餐对应的所有权限
    user_plan_config = plans.PLANS_CONFIG.get(user.plan, plans.PLANS_CONFIG["freemium"])

    # 2. 创建一个包含所有基础信息和附加权限的字典
    response_data = {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "nickname": getattr(user, 'nickname', None),  # 安全地获取nickname，防止数据库模型中没有该字段时报错
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "plan": user.plan,
        "expires_at": user.expires_at,
        "api_token": user.api_token,
        # ** 使用字典解包语法，将权限字典中的所有键值对合并进来 **
        **user_plan_config
    }
    return response_data


async def send_email_task(message: MessageSchema):
    """后台发送邮件的任务"""
    try:
        await fm.send_message(message)
        logger.info(f"邮件已成功投递到 SMTP 服务器: 主题='{message.subject}', 收件人={message.recipients}")
    except SMTPResponseException as e:
        logger.warning(f"邮件发送后关闭连接时出现SMTP响应异常 (通常无害): {e}")
    except Exception as e:
        logger.error(f"发送邮件时发生严重错误: {e}", exc_info=True)


@router.post("/send-registration-code", response_model=ResponseModel)
async def send_code(req: schemas.SendCodeRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """发送注册验证码"""
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
    """用户注册 (返回基础信息即可，无需修改)"""
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
    """用户登录获取Token"""
    user = crud.authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user: raise APIException(code=status.HTTP_401_UNAUTHORIZED, msg="邮箱或密码错误")
    if not user.is_active: raise APIException(code=status.HTTP_400_BAD_REQUEST, msg="账户已被禁用")

    # 确保 apply_plan_limits 被调用，以获得最新plan（处理管理员和过期降级）
    user = plans.apply_plan_limits(user)
    crud.update_user(db, user=user)  # 更新数据库中的plan（如果已降级）

    token_data = {"user_id": user.id}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    # 【重要修改】使用辅助函数创建包含完整权限的 user_info 对象
    full_user_info = get_full_user_response_data(user)

    return ResponseModel(data=schemas.Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_info=full_user_info
    ))


@router.get("/me", response_model=ResponseModel[schemas.UserOut])
def read_me(current_user: models.User = Depends(get_user_from_header_or_query)):
    """获取当前登录用户的完整信息（包括权限）"""
    # 【重要修改】使用辅助函数创建完整的响应数据，并用 UserOut 模型进行验证和序列化
    full_user_info = get_full_user_response_data(current_user)
    return ResponseModel(data=full_user_info)


@router.post("/me/reset-api-token", response_model=ResponseModel[schemas.UserOut])
def reset_api_token_route(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    """重置用户的API Token"""
    updated_user = plans.reset_api_token(current_user)
    crud.update_user(db, user=updated_user)
    logger.info(f"用户 {current_user.email} 成功重置了 API Token。")

    # 【重要修改】确保返回的也是包含完整权限的用户信息
    full_user_info = get_full_user_response_data(updated_user)
    return ResponseModel(data=full_user_info, msg="API Token 重置成功！")
