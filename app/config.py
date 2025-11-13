from pydantic_settings import BaseSettings
from pydantic import ConfigDict  # 导入 V2 配置类

class Settings(BaseSettings):
    # 数据库配置
    DB_USER: str = 'student_system_user'
    DB_PASSWORD: str = '201303103670@Dxsg'  # 替换为您的密码
    DB_HOST: str = 'localhost'
    DB_NAME: str = 'student_system_db'
    
    # JWT (用于管理员登录)
    JWT_SECRET_KEY: str = '4b7e2f9d3a8b1c5d6e7f9a2b3c4d5e6f'  # 替换为一个随机长字符串
    JWT_ALGORITHM: str = 'HS256'
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 天

    # 替换原有的 class Config: 为 model_config（Pydantic V2 推荐写法）
    model_config = ConfigDict(
        case_sensitive=True  # 保留你原来的大小写敏感配置
    )

settings = Settings()