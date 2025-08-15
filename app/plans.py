# 文件: app/plans.py (最终版本，已加入功能限制)

import datetime
import secrets
from typing import Optional
from . import models

UNLIMITED = -1

PLANS_CONFIG = {
    # 免费版: 普通用户的基础限制
    "freemium": {
        "min_interval": 3.0,
        "max_codes": 20,
        "max_connections": 1,
        "api_access_level": "none",
        "max_custom_indicators": 1,
        "max_stock_groups": 1,
        "max_alerts": 1,
        "max_workspaces": 1
    },
    # 专业版: 解除功能性限制
    "pro": {
        "min_interval": 1.0,
        "max_codes": 50,
        "max_connections": 3,
        "api_access_level": "basic",
        # --- 【新增】功能性限制 ---
        "max_custom_indicators": UNLIMITED,
        "max_stock_groups": UNLIMITED,
        "max_alerts": UNLIMITED,
        "max_workspaces": UNLIMITED

    },
    # 大师版: 解除功能性限制，并提供更高API配额
    "master": {
        "min_interval": 0.2,
        "max_codes": 500,
        "max_connections": 10,
        "api_access_level": "advanced",
        # --- 【新增】功能性限制 ---
        "max_custom_indicators": UNLIMITED,
        "max_stock_groups": UNLIMITED,
        "max_alerts": UNLIMITED,
        "max_workspaces": UNLIMITED
    },
    # 管理员: 完全无限制
    "admin": {
        "min_interval": 0.2,
        "max_codes": UNLIMITED,
        "max_connections": UNLIMITED,
        "api_access_level": "admin",
        # --- 【新增】功能性限制 ---
        "max_custom_indicators": UNLIMITED,
        "max_stock_groups": UNLIMITED,
        "max_alerts": UNLIMITED,
        "max_workspaces": UNLIMITED
    }
}

# 价格配置保持不变
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
    专门为用户生成一个新的、与其当前套餐匹配的 API Token。
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
        user.plan = "admin"

    if user.expires_at and user.expires_at < datetime.datetime.utcnow() and not user.is_superuser:
        # 套餐过期，降级到免费版
        user.plan = "freemium"

    return user
