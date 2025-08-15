# 文件: manage_users.py (最终功能完整版)

import os
import sys
import getpass
import datetime
from sqlalchemy.orm import Session

# -- 关键步骤: 将项目根目录添加到Python路径中 --
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# -- 从您的项目中导入所有必要的模块 --
from app.database import SessionLocal
from app.models import User
from app.crud import user as crud_user
from app.plans import PLANS_CONFIG, grant_subscription, reset_api_token
from app.common.dependencies import get_password_hash


def upgrade_user_plan(db: Session):
    """交互式地升级一个现有用户的套餐。"""
    print("\n--- 升级用户套餐 ---")
    email = input("请输入要升级的用户的邮箱: ").strip()

    user = crud_user.get_user_by_email(db, email=email)
    if not user:
        print(f"错误: 找不到邮箱为 '{email}' 的用户。")
        return

    if user.is_superuser:
        print(f"提示: 用户 '{email}' 已经是管理员，无需升级套餐。")
        return

    print(f"\n找到用户: {user.username} (邮箱: {user.email})")
    print(f"当前套餐: {user.plan}")
    if user.expires_at:
        print(f"当前过期时间: {user.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("当前过期时间: 永不过期")

    print("\n可用套餐列表:")
    for plan_name in PLANS_CONFIG.keys():
        if plan_name != 'admin':
            print(f"- {plan_name}")

    new_plan = input("请输入新的套餐名称: ").strip().lower()
    if new_plan not in PLANS_CONFIG or new_plan == 'admin':
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
        grant_subscription(user, plan_name=new_plan, duration_days=duration_days)
        reset_api_token(user)
        db.commit()
        db.refresh(user)

        print("\n🎉 用户套餐升级成功!")
        print(f"新套餐: {user.plan}")
        if user.expires_at:
            print(f"新过期时间: {user.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("新过期时间: 永不过期")
        print(f"新的 API Token: {user.api_token}")

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
    #
    # username = input("请输入新管理员的用户名: ").strip()
    password = getpass.getpass("请输入新管理员的密码: ")
    password_confirm = getpass.getpass("请再次输入密码以确认: ")

    if password != password_confirm:
        print("错误: 两次输入的密码不匹配。")
        return
    if not password:
        print("错误: 密码不能为空。")
        return

    try:
        hashed_password = get_password_hash(password)
        new_admin = User(
            email=email,
            username=email,
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=True,
            plan='admin',
            expires_at=None
        )
        reset_api_token(new_admin)
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)

        print(f"\n🎉 管理员用户 '{email}' 创建成功!")
        print(f"生成的 API Token: {new_admin.api_token}")

    except Exception as e:
        db.rollback()
        print(f"创建失败: {e}")


# 【【核心新增功能】】
def toggle_admin_status(db: Session):
    """交互式地将一个现有用户提升为管理员，或将管理员降级。"""
    print("\n--- 设为/取消管理员 ---")
    email = input("请输入要操作的用户的邮箱: ").strip()

    user = crud_user.get_user_by_email(db, email=email)
    if not user:
        print(f"错误: 找不到邮箱为 '{email}' 的用户。")
        return

    # 切换 is_superuser 的状态
    new_status = not user.is_superuser
    action_text = "提升为" if new_status else "降级为"

    confirm = input(f"您确定要将用户 '{user.email}' {action_text}管理员吗？(y/n): ").strip().lower()
    if confirm != 'y':
        print("操作已取消。")
        return

    try:
        user.is_superuser = new_status
        if new_status:
            # 提升为管理员
            user.plan = 'admin'
            user.expires_at = None
            print(f"用户 '{user.email}' 已成功提升为管理员。")
        else:
            # 降级为普通用户
            user.plan = 'freemium'  # 降级后重置为免费版
            user.expires_at = None
            print(f"用户 '{user.email}' 已成功降级为普通用户 (freemium套餐)。")

        # 无论升降级，都重置Token以反映新的身份
        reset_api_token(user)
        db.commit()
        db.refresh(user)
        print(f"该用户的新 API Token: {user.api_token}")

    except Exception as e:
        db.rollback()
        print(f"操作失败: {e}")


def main():
    """主函数，提供操作菜单。"""
    db = SessionLocal()
    try:
        while True:
            print("\n=========================")
            print("  用户管理后台工具")
            print("=========================")
            print("1. 升级用户套餐")
            print("2. 创建新的管理员用户")
            print("3. 设为/取消管理员")  # <-- 新增菜单项
            print("4. 退出")  # <-- 退出选项后移
            choice = input("请输入您的选择 (1/2/3/4): ").strip()

            if choice == '1':
                upgrade_user_plan(db)
            elif choice == '2':
                create_admin_user(db)
            elif choice == '3':  # <-- 新增选项的逻辑
                toggle_admin_status(db)
            elif choice == '4':
                print("已退出。")
                break
            else:
                print("无效的输入，请输入 1, 2, 3, 或 4。")
    finally:
        db.close()
        print("\n数据库连接已关闭。")


if __name__ == "__main__":
    main()