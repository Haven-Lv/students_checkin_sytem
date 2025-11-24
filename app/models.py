from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# --- 管理员认证模型 ---
class AdminLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# --- 活动模型 ---
class ActivityCreate(BaseModel):
    name: str
    location_name: str
    latitude: float
    longitude: float
    radius_meters: int
    start_time: datetime
    end_time: datetime

class ActivityResponse(ActivityCreate):
    id: int
    unique_code: str
    created_at: datetime

# --- 新增：学生认证相关 ---
class EmailRequest(BaseModel):
    email: str

class StudentLogin(BaseModel):
    email: str
    code: str
    activity_code: Optional[str] = None
    student_id: Optional[str] = None
    name: Optional[str] = None

# --- 修改：签到请求 (移除 student_id 和 name，因为通过 Token 自动获取) ---
class CheckInRequestAuthorized(BaseModel):
    activity_code: str
    latitude: float
    longitude: float


# --- 参与者模型 ---
class ParticipantLogin(BaseModel):
    student_id: str
    name: str

class CheckInRequest(ParticipantLogin):
    activity_code: str
    latitude: float
    longitude: float

class CheckOutRequest(BaseModel):
    device_session_token: str
    latitude: float
    longitude: float

class CheckInResponse(BaseModel):
    message: str
    device_session_token: str
    
class ActivityUpdate(BaseModel):
    start_time: datetime
    end_time: datetime
    radius_meters: int
    location_name: str
    latitude: float
    longitude: float