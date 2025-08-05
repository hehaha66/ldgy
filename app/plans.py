# 文件: app/plans.py

import datetime
import secrets
from typing import Optional
from . import models

UNLIMITED = -1

PLANS_CONFIG = {
    "freemium": {"min_interval": 3.0, "max_codes": 20, "max_connections": 1, "api_access_level": "none"},
    "pro": {"min_interval": 1.0, "max_codes": 50, "max_connections": 3, "api_access_level": "basic"},
    "master": {"min_interval": 0.2, "max_codes": 500, "max_connections": 10, "api_access_level": "advanced"},
    "admin": {"min_interval": 0.2, "max_codes": UNLIMITED, "max_connections": UNLIMITED, "api_access_level": "admin"}
}
PLANS_PRICING = {
    "pro": {"monthly": 30, "yearly": 365},
    "master": {"monthly": 30, "yearly": 365}
}


def grant_subscription(user: models.User, plan_name: str, duration_days: Optional[int] = None):
    """
    【简化版】只负责更新用户的套餐计划和过期时间。
    """
    if plan_name not in PLANS_CONFIG:
        raise ValueError(f"Invalid plan name: {plan_name}")

    user.plan = plan_name

    if duration_days is None:
        user.expires_at = None
    else:
        base_date = user.expires_at if user.expires_at and user.expires_at > datetime.datetime.utcnow() else datetime.datetime.utcnow()
        user.expires_at = base_date + datetime.timedelta(days=duration_days)

    return user


def reset_api_token(user: models.User) -> models.User:
    """
    【新增】专门为用户生成一个新的、与其当前套餐匹配的 API Token。
    """
    plan_prefix = "adm" if user.is_superuser else user.plan[:4]
    user.api_token = f"ldst_{plan_prefix}_{secrets.token_urlsafe(24)}"
    return user


def apply_plan_limits(user: models.User) -> models.User:
    """
    检查并应用用户的套餐限制。
    如果套餐过期，只更新 plan 字段，不再触碰 token。
    """
    if user.is_superuser and user.plan != "admin":
        user.plan = "admin"  # 确保超管的 plan 字段正确

    if user.expires_at and user.expires_at < datetime.datetime.utcnow() and not user.is_superuser:
        # 套餐过期，降级到免费版
        user.plan = "freemium"

    return user
