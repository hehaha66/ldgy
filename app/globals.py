# 文件: app/globals.py

from dotenv import load_dotenv
load_dotenv() # 确保在所有其他导入之前加载 .env

import logging
import os
from fastapi_mail import FastMail, ConnectionConfig
from .common.response_model import APIException # 引入统一异常

# --- 日志配置 ---
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 邮件服务配置 ---
# 这个配置块现在能更健壮地处理来自 .env 的字符串值
try:
    mail_conf = ConnectionConfig(
        MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
        MAIL_FROM=os.getenv("MAIL_FROM"),
        MAIL_PORT=int(os.getenv("MAIL_PORT", 587)), # .env 中的值将被正确转为整数
        MAIL_SERVER=os.getenv("MAIL_SERVER"),
        MAIL_STARTTLS=(os.getenv("MAIL_STARTTLS", "false").lower() == 'true'), # 将 "False" -> False
        MAIL_SSL_TLS=(os.getenv("MAIL_SSL_TLS", "true").lower() == 'true'),   # 将 "True" -> True
        USE_CREDENTIALS=(os.getenv("USE_CREDENTIALS", "true").lower() == 'true'),
        VALIDATE_CERTS=(os.getenv("VALIDATE_CERTS", "true").lower() == 'true')
    )
    fm = FastMail(mail_conf)
except (ValueError, TypeError) as e:
    logger.error(f"邮件服务配置失败: {e}. 请检查你的 .env 文件，特别是 MAIL_PORT。")
    fm = None # 如果配置失败，将 fm 设为 None


import threading

# 用于缓存每个查询组合的最后一次成功获取的数据
# 键是市场代码字符串(如 '1.000001,0.00700')，值是获取到的数据列表
LAST_KNOWN_GOOD_DATA = {}
LAST_GOOD_DATA_LOCK = threading.Lock()

# 用于跟踪每个用户的活动SSE连接数
# 键是用户ID字符串(如 'USER_123')，值是该用户的当前连接数
ACTIVE_CONNECTIONS = {}
CONNECTION_LOCK = threading.Lock()