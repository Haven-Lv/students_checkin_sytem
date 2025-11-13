import getpass
from security import get_password_hash
from db_utils import get_db_connection, db_create_admin

def main():
    print("--- 创建超级管理员 ---")
    username = input("请输入管理员用户名: ")
    password = getpass.getpass("请输入管理员密码: ")
    password_confirm = getpass.getpass("请再次确认密码: ")
    
    if password != password_confirm:
        print("错误：两次输入的密码不一致。")
        return

    if not username or not password:
        print("错误：用户名和密码不能为空。")
        return

    hashed_password = get_password_hash(password)
    
    try:
        with get_db_connection() as db:
            db_create_admin(db, username, hashed_password)
        print(f"管理员 '{username}' 创建成功！")
    except Exception as e:
        print(f"创建失败: {e}")
        print("请检查数据库连接和配置。")

if __name__ == "__main__":
    main()