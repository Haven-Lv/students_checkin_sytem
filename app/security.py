from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from .config import settings
from . import db_utils  # <--- 必须导入 db_utils

# 1. 密码哈希
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# 2. JWT 生成
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

# 3. OAuth2 依赖 (Admin)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/login")

async def get_current_admin(token: str = Depends(oauth2_scheme)):
    """
    管理员鉴权：返回完整的 admin 字典对象 (包含 id)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # 查库获取 admin_id
    with db_utils.get_db_connection() as db:
        admin = db_utils.get_admin_by_username(db, username)
        if not admin:
            raise credentials_exception
        return admin 

# 4. OAuth2 依赖 (Student)
oauth2_student_scheme = OAuth2PasswordBearer(tokenUrl="/api/participant/login")

async def get_current_student(token: str = Depends(oauth2_student_scheme)):
    """
    学生鉴权：解析 Token 并返回 student_id 和 admin_id
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录已过期，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        student_id: str = payload.get("sub")
        role: str = payload.get("role")
        
        # --- 关键修改：必须从 payload 中提取 admin_id ---
        admin_id: int = payload.get("admin_id") 
        
        if student_id is None or role != "student":
            raise credentials_exception
        
        # 返回包含 admin_id 的字典
        return {"sub": student_id, "role": role, "admin_id": admin_id}
    except JWTError:
        raise credentials_exception