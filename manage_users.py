# 文件: manage_users.py
# 这是一个用于管理用户的命令行工具脚本。
# 请将此文件放置在项目的根目录 (backend/) 下，然后直接在PyCharm中运行。

import os
import sys
import getpass
import datetime
from sqlalchemy.orm import Session

# -- 关键步骤: 将项目根目录添加到Python路径中 --
# 这使得脚本可以像FastAPI应用一样找到 app 模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# -- 从您的项目中导入必要的模块 --
from app.database import SessionLocal
from app.models import User
from app.crud import user as crud_user
from app.plans import PLANS_CONFIG, grant_subscription
from app.common.dependencies import get_password_hash


def upgrade_user_plan(db: Session):
    """交互式地升级一个现有用户的套餐。"""
    print("\n--- 升级用户套餐 ---")
    email = input("请输入要升级的用户的邮箱: ").strip()

    user = crud_user.get_user_by_email(db, email=email)
    if not user:
        print(f"错误: 找不到邮箱为 '{email}' 的用户。")
        return

    print(f"\n找到用户: {user.username} (邮箱: {user.email})")
    print(f"当前套餐: {user.plan}")
    if user.expires_at:
        print(f"当前过期时间: {user.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("当前过期时间: 永不过期")

    print("\n可用套餐列表:")
    for plan_name in PLANS_CONFIG.keys():
        print(f"- {plan_name}")

    new_plan = input("请输入新的套餐名称: ").strip().lower()
    if new_plan not in PLANS_CONFIG:
        print(f"错误: 无效的套餐名称 '{new_plan}'。")
        return

    duration_str = input("请输入订阅天数 (直接回车表示永不过期): ").strip()
    duration_days = None
    if duration_str:
        try:
            duration_days = int(duration_str)
            if duration_days <= 0:
                print("错误: 天数必须是正整数。")
                return
        except ValueError:
            print("错误: 请输入一个有效的数字天数。")
            return

    try:
        # 使用您项目中已有的函数来处理订阅逻辑
        grant_subscription(user, plan_name=new_plan, duration_days=duration_days)
        db.commit()
        db.refresh(user)
        print("\n🎉 用户套餐升级成功!")
        print(f"新套餐: {user.plan}")
        if user.expires_at:
            print(f"新过期时间: {user.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("新过期时间: 永不过期")
    except Exception as e:
        db.rollback()
        print(f"升级失败: {e}")


def create_admin_user(db: Session):
    """交互式地创建一个新的管理员用户。"""
    print("\n--- 创建新的管理员用户 ---")
    email = input("请输入新管理员的邮箱: ").strip()

    if crud_user.get_user_by_email(db, email=email):
        print(f"错误: 邮箱 '{email}' 已被注册。")
        return

    username = input("请输入新管理员的用户名: ").strip()
    # 使用 getpass 模块安全地输入密码，不会在屏幕上显示
    password = getpass.getpass("请输入新管理员的密码: ")
    password_confirm = getpass.getpass("请再次输入密码以确认: ")

    if password != password_confirm:
        print("错误: 两次输入的密码不匹配。")
        return

    if not password:
        print("错误: 密码不能为空。")
        return

    try:
        # 直接创建 User 模型实例，并设置管理员权限
        hashed_password = get_password_hash(password)
        new_admin = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=True,  # <-- 关键: 设置为管理员
            plan='admin',       # <-- 关键: 匹配管理员套餐
            expires_at=None     # 管理员永不过期
        )
        db.add(new_admin)
        db.commit()
        print(f"\n🎉 管理员用户 '{username}' 创建成功!")
    except Exception as e:
        db.rollback()
        print(f"创建失败: {e}")


def main():
    """主函数，提供操作菜单。"""
    # 创建数据库会话
    db = SessionLocal()
    try:
        while True:
            print("\n=========================")
            print("  用户管理后台工具")
            print("=========================")
            print("1. 升级用户套餐")
            print("2. 创建新的管理员用户")
            print("3. 退出")
            choice = input("请输入您的选择 (1/2/3): ").strip()

            if choice == '1':
                upgrade_user_plan(db)
            elif choice == '2':
                create_admin_user(db)
            elif choice == '3':
                print("已退出。")
                break
            else:
                print("无效的输入，请输入 1, 2, 或 3。")
    finally:
        # 确保数据库会话在任何情况下都会被关闭
        db.close()
        print("\n数据库连接已关闭。")


if __name__ == "__main__":
    main()