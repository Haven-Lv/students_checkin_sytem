from fastapi import FastAPI, Depends, HTTPException, status, APIRouter, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
from datetime import timedelta
import models
import io
import qrcode # 确保已安装 qrcode[pil]
from datetime import datetime

# 导入我们创建的模块
import models
import security
import db_utils
from db_utils import get_db_connection

app = FastAPI(
    title="学生活动签到系统",
    description="API for student check-in system. Remember Nginx rewrite /students_system/ to /"
)

# --- 路由拆分 ---
router_admin = APIRouter(prefix="/api/admin", tags=["Admin"])
router_participant = APIRouter(prefix="/api/participant", tags=["Participant"])

# ==================================================
# 1. 管理员路由
# ==================================================

@router_admin.post("/login", response_model=models.Token)
async def login_for_access_token(form_data: models.AdminLogin):
    """
    管理员登录，获取 JWT Token
    """
    with get_db_connection() as db:
        admin = db_utils.get_admin_by_username(db, form_data.username)
    
    if not admin or not security.verify_password(form_data.password, admin['hashed_password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = security.create_access_token(
        data={"sub": admin['username']}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router_admin.post("/activities", response_model=models.ActivityResponse)
async def create_activity(
    activity: models.ActivityCreate, 
    admin_user: str = Depends(security.get_current_admin)
):
    """
    创建新活动 (受保护)
    """
    with get_db_connection() as db:
        try:
            unique_code = db_utils.db_create_activity(db, activity)
            new_activity = db_utils.get_activity_by_code(db, unique_code)
            return new_activity
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create activity: {e}")

@router_admin.get("/activities")
async def get_activities_list(admin_user: str = Depends(security.get_current_admin)):
    """
    获取所有活动列表 (受保护)
    """
    with get_db_connection() as db:
        activities = db_utils.get_all_activities(db)
        return activities

# 剪切这个函数 (原来在 router_admin 下)
@router_admin.get("/activities/{activity_code}/qr")
async def get_activity_qr_code(
    activity_code: str,
    admin_user: str = Depends(security.get_current_admin)
):
    """
    为活动生成签到二维码 (受保护)
    """
    with get_db_connection() as db:
        activity = db_utils.get_activity_by_code(db, activity_code)
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

    # 注意：URL 必须是 Nginx 暴露给外界的 URL
    checkin_url = f"https://havenchannel.xyz/students_system/checkin.html?code={activity_code}"

    img = qrcode.make(checkin_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")

@router_admin.get("/activities/{activity_code}/logs")
async def get_activity_logs(
    activity_code: str,
    admin_user: str = Depends(security.get_current_admin)
):
    """
    查看指定活动的签到/签退日志 (受保护)
    """
    with get_db_connection() as db:
        activity = db_utils.get_activity_by_code(db, activity_code)
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
        
        logs = db_utils.get_check_logs_for_activity(db, activity['id'])
        return {"activity_name": activity['name'], "logs": logs}

@router_admin.delete("/activities/{activity_code}")
async def delete_activity(
    activity_code: str,
    admin_user: str = Depends(security.get_current_admin)
):
    """
    删除一个活动 (受保护)
    """
    with get_db_connection() as db:
        activity = db_utils.get_activity_by_code(db, activity_code)
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
        
        try:
            db_utils.db_delete_activity(db, activity['id'])
            return {"message": "活动及所有签到记录已删除"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"删除失败: {e}")

@router_admin.put("/activities/{activity_code}")
async def update_activity_time(
    activity_code: str,
    time_update: models.ActivityTimeUpdate, # 使用我们新加的 model
    admin_user: str = Depends(security.get_current_admin)
):
    """
    更新活动时间 (受保护)
    """
    with get_db_connection() as db:
        activity = db_utils.get_activity_by_code(db, activity_code)
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
        
        try:
            db_utils.db_update_activity_time(
                db, activity['id'], time_update.start_time, time_update.end_time
            )
            # 返回更新后的活动信息
            updated_activity = db_utils.get_activity_by_code(db, activity_code)
            return updated_activity
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"更新失败: {e}")

# ==================================================
# 2. 参与者路由
# ==================================================

@router_participant.get("/activity/{activity_code}")
async def get_activity_details(activity_code: str):
    """
    获取单个活动的公开信息 (用于签到页面显示)
    """
    with get_db_connection() as db:
        activity = db_utils.get_activity_by_code(db, activity_code)
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
    
    return {
        "name": activity['name'],
        "location_name": activity['location_name'],
        "start_time": activity['start_time'],
        "end_time": activity['end_time']
    }

@router_participant.get("/activity/{activity_code}/qr") # <-- 确认此路由在 participant 之下
async def get_activity_qr_code(
    activity_code: str # <-- 确认移除了 admin_user 依赖
):
    """
    为活动生成签到二维码 (公开)
    """
    with get_db_connection() as db:
        activity = db_utils.get_activity_by_code(db, activity_code)
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

    checkin_url = f"https://havenchannel.xyz/students_system/checkin.html?code={activity_code}"
    
    img = qrcode.make(checkin_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    
    return StreamingResponse(buf, media_type="image/png")

@router_participant.post("/checkin", response_model=models.CheckInResponse)
async def participant_checkin(request: models.CheckInRequest):
    """
    参与者签到
    """
    # ... (此函数及 /checkout 函数保持不变) ...
    now = datetime.now()
    with get_db_connection() as db:
        activity = db_utils.get_activity_by_code(db, request.activity_code)
        
        # 1. 校验活动是否存在
        if not activity:
            raise HTTPException(status_code=404, detail="活动不存在")

        # 2. 校验时间
        if not (activity['start_time'] <= now <= activity['end_time']):
            raise HTTPException(status_code=400, detail="不在活动时间范围内")

        # 3. 校验地点
        distance = db_utils.calculate_distance(
            activity['latitude'], activity['longitude'],
            request.latitude, request.longitude
        )
        if distance > activity['radius_meters']:
            raise HTTPException(status_code=400, detail=f"您不在签到范围内 (距离 {int(distance)} 米)")

        # 4. 获取或创建参与者
        participant = db_utils.get_participant(db, request.student_id)
        if not participant:
            participant = db_utils.create_participant(db, request.student_id, request.name)
            if not participant:
                 raise HTTPException(status_code=400, detail="学号已存在但姓名不匹配 (或创建用户失败)")
        elif participant['name'] != request.name:
            raise HTTPException(status_code=400, detail="学号与姓名不匹配")

        # 5. 检查是否已签到
        if db_utils.get_check_log(db, participant['id'], activity['id']):
            raise HTTPException(status_code=400, detail="您已签到，请勿重复操作")

        # 6. 创建签到记录
        try:
            device_token = db_utils.create_check_log(
                db, activity['id'], participant['id'], request.latitude, request.longitude
            )
            return {"message": "签到成功", "device_session_token": device_token}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"签到失败: {e}")

@router_participant.post("/checkout")
async def participant_checkout(request: models.CheckOutRequest):
    """
    参与者签退
    """
    # ... (此函数保持不变) ...
    now = datetime.now()
    with get_db_connection() as db:
        # 1. 验证 device_token 并获取签到记录
        log = db_utils.get_log_by_device_token(db, request.device_session_token)
        
        if not log:
            raise HTTPException(status_code=404, detail="无效的签到凭证，请使用签到设备重试")

        # 2. 检查是否已签退
        if log['check_out_time']:
            raise HTTPException(status_code=400, detail="您已签退，请勿重复操作")

        # 3. 校验时间 (使用联表查询出的活动时间)
        if not (log['start_time'] <= now <= log['end_time']):
            raise HTTPException(status_code=400, detail="不在活动时间范围内")

        # 4. 校验地点
        distance = db_utils.calculate_distance(
            log['latitude'], log['longitude'],
            request.latitude, request.longitude
        )
        if distance > log['radius_meters']:
            raise HTTPException(status_code=400, detail=f"您不在签退范围内 (距离 {int(distance)} 米)")

        # 5. 更新签退记录
        try:
            db_utils.update_check_log_checkout(db, log['id'], request.latitude, request.longitude)
            return {"message": "签退成功"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"签退失败: {e}")

# ==================================================
# 3. 注册路由和静态文件
# ==================================================
app.include_router(router_admin)
app.include_router(router_participant)

# 挂载静态文件 (前端页面)
# Nginx 会将 /students_system/ 转发到 /
# 所以 FastAPI 应该从 / 提供静态文件
app.mount("/", StaticFiles(directory="static", html=True), name="static")
