from fastapi import FastAPI, Depends, HTTPException, status, APIRouter, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
from datetime import timedelta, datetime
import io
import qrcode # 确保已安装 qrcode[pil]
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
import random
import os
from fastapi import Request # 需要导入 Request 对象
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from openpyxl import Workbook
from urllib.parse import quote

# 导入本地模块
from . import coord_utils
from . import db_utils
from .db_utils import get_db_connection
from . import models
from . import security
from .config import settings
from .security import get_current_student
from .email_templates import EmailTemplates

app = FastAPI(
    title="学生活动签到系统",
    description="API for student check-in system. Remember Nginx rewrite /students_system/ to /"
)
# 初始化 Limiter
# key_func=get_remote_address 表示根据客户端 IP 进行限制
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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

# [修改 1] 根据要求修改 create_activity
@router_admin.post("/activities", response_model=models.ActivityResponse)
async def create_activity(
    activity: models.ActivityCreate, 
    current_admin: dict = Depends(security.get_current_admin)
):
    """
    创建新活动 (受保护)
    """
    with get_db_connection() as db:
        try:
            # 传入 admin_id
            unique_code = db_utils.db_create_activity(db, activity, current_admin['id'])
            new_activity = db_utils.get_activity_by_code(db, unique_code)
            return new_activity
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create activity: {e}")

# [修改 2] 根据要求修改 get_activities_list
@router_admin.get("/activities")
async def get_activities_list(current_admin: dict = Depends(security.get_current_admin)):
    """
    获取所有活动列表 (受保护)
    """
    with get_db_connection() as db:
        # 传入 admin_id，只获取该管理员的活动
        activities = db_utils.get_all_activities(db, current_admin['id'])
        return activities

@router_admin.get("/activities/{activity_code}/qr")
async def get_activity_qr_code_admin(
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

@router_admin.get("/activities/{activity_code}/export")
async def export_activity_excel(
    activity_code: str,
    admin_user: str = Depends(security.get_current_admin)
):
    """
    导出指定活动的签到表为 Excel
    """
    with get_db_connection() as db:
        activity = db_utils.get_activity_by_code(db, activity_code)
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
        
        # 获取签到记录
        logs = db_utils.get_check_logs_for_activity(db, activity['id'])

    # 创建 Excel 工作簿
    wb = Workbook()
    ws = wb.active
    ws.title = "签到记录"
    
    # 写入表头
    headers = ["学号", "姓名", "签到时间", "签退时间"]
    ws.append(headers)
    
    # 写入数据
    for log in logs:
        # 格式化时间，处理 None 的情况
        c_in = log['check_in_time'].strftime('%Y-%m-%d %H:%M:%S') if log['check_in_time'] else "未签到"
        c_out = log['check_out_time'].strftime('%Y-%m-%d %H:%M:%S') if log['check_out_time'] else "未签退"
        
        ws.append([
            log['student_id'],
            log['name'],
            c_in,
            c_out
        ])
    
    # 保存到内存流
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    
    # 生成文件名：【活动名称】_签到表.xlsx
    filename = f"【{activity['name']}】_签到表.xlsx"
    # URL 编码文件名以解决中文乱码问题
    encoded_filename = quote(filename)
    
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=utf-8''{encoded_filename}"
        }
    )

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
async def update_activity(
    activity_code: str,
    activity_update: models.ActivityUpdate, # 使用新的模型
    admin_user: str = Depends(security.get_current_admin)
):
    """
    更新活动信息 (时间、地点、范围)
    """
    with get_db_connection() as db:
        activity = db_utils.get_activity_by_code(db, activity_code)
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
        
        try:
            # 调用新的数据库更新函数
            db_utils.db_update_activity(
                db, activity['id'], activity_update
            )
            # 返回更新后的最新数据
            updated_activity = db_utils.get_activity_by_code(db, activity_code)
            return updated_activity
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"更新失败: {e}")

# ==================================================
# 2. 参与者路由 (新增鉴权与邮箱功能)
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
        "end_time": activity['end_time'],
        "latitude": activity['latitude'],      
        "longitude": activity['longitude'],    
        "radius_meters": activity['radius_meters'] 
    }

@router_participant.get("/activity/{activity_code}/qr") 
async def get_activity_qr_code(activity_code: str):
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

# --- 新增：邮箱验证码接口 ---
@router_participant.post("/send-code")
@limiter.limit("1/minute")
async def send_email_code(request: Request, req: models.EmailRequest):
    """发送 6 位数字验证码到邮箱 (使用 HTML 模板)"""
    code = str(random.randint(100000, 999999))
    
    # 1. 保存到数据库
    with get_db_connection() as db:
        db_utils.save_verification_code(db, req.email, code)
    
    # 2. 发送邮件
    try:
        # --- 修改开始：使用 HTML 模板 ---
        # 生成 HTML 内容
        html_content = EmailTemplates.verification_code_email(code, valid_minutes=5)
        
        # 构造 MIMEText，注意第二个参数改为 'html'
        msg = MIMEText(html_content, 'html', 'utf-8')
        
        msg['From'] = formataddr(["校园签到系统", settings.SMTP_USER])
        msg['To'] = req.email
        msg['Subject'] = "【安全验证】您的登录验证码" # 稍微改一下标题显得更正式
        # --- 修改结束 ---

        server = smtplib.SMTP_SSL(settings.SMTP_SERVER, settings.SMTP_PORT)
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_USER, [req.email], msg.as_string())
        server.quit()
    except Exception as e:
        print(f"邮件发送失败: {e}")
        # 在生产环境中，建议记录详细日志
        raise HTTPException(status_code=500, detail="邮件发送失败，请检查邮箱地址或联系管理员")

    return {"message": "验证码已发送"}

# 新增：获取当前签到状态接口
@router_participant.get("/status")
async def get_current_status(current_user: dict = Depends(get_current_student)):
    student_id = current_user['sub']
    # 新增：从 Token 解析出的 current_user 中获取 admin_id
    admin_id = current_user.get('admin_id') 
    
    with get_db_connection() as db:
        # 修改：传入 admin_id
        participant = db_utils.get_participant(db, student_id, admin_id)
        
        if not participant:
            # 如果用户不存在，说明没签到
            return {"is_checked_in": False}
            
        # 查数据库看有没有未签退的记录
        active_log = db_utils.get_active_log_by_student(db, participant['id'])
        
        if active_log:
            return {
                "is_checked_in": True,
                "activity_name": active_log['activity_name'],
                "activity_code": active_log['unique_code'],
                "check_in_time": active_log['check_in_time']
            }
        else:
            return {"is_checked_in": False}

# [修改 3] 根据要求修改 login_with_email
@router_participant.post("/login", response_model=models.Token)
async def login_with_email(req: models.StudentLogin):
    """邮箱登录/注册一体化接口 (多租户版)"""
    with get_db_connection() as db:
        # 1. 校验验证码
        valid_code = db_utils.get_valid_code(db, req.email)
        
        if not valid_code or valid_code != req.code:
            raise HTTPException(status_code=400, detail="验证码错误或已过期")
            
        # 2. 【核心】确定上下文 (是哪个学校？)
        target_admin_id = None
        if req.activity_code: 
            activity = db_utils.get_activity_by_code(db, req.activity_code)
            if activity:
                target_admin_id = activity['admin_id']
        
        # 如果没有活动码，无法确定注册到哪个学校，必须报错
        if not target_admin_id:
             raise HTTPException(status_code=400, detail="请通过扫描活动二维码进行注册/登录")

        # 3. 在特定学校下查询用户
        student = db_utils.get_participant_by_email_and_admin(db, req.email, target_admin_id)
        
        # 4. 注册逻辑
        if not student:
            if not req.student_id or not req.name:
                # 返回特定状态码，告诉前端需要弹出注册框
                raise HTTPException(status_code=400, detail="NEED_REGISTER_INFO")
            
            # 检查该学校下学号是否被占用
            if db_utils.get_participant(db, req.student_id, target_admin_id):
                 raise HTTPException(status_code=400, detail="该学号在当前组织已被绑定")
            
            try:
                # 注册时传入 admin_id
                db_utils.register_student_with_email(db, req.student_id, req.name, req.email, target_admin_id)
                student = db_utils.get_participant_by_email_and_admin(db, req.email, target_admin_id)
            except Exception as e:
                raise HTTPException(status_code=500, detail="注册失败")

        # 5. 生成 Token (Payload 中放入学号 student_id 和 admin_id)
        access_token = security.create_access_token(
            data={
                "sub": student['student_id'], 
                "role": "student", 
                "admin_id": target_admin_id # <--- 放入 Token
            } 
        )
        return {"access_token": access_token, "token_type": "bearer"}

# [修改 4] 根据要求修改 checkin_authorized
@router_participant.post("/checkin-auth", response_model=models.CheckInResponse)
async def checkin_authorized(
    request: models.CheckInRequestAuthorized, 
    current_user: dict = Depends(get_current_student) 
):
    """已登录用户的签到接口"""
    student_id = current_user['sub']
    # 新增：获取 admin_id
    admin_id = current_user.get('admin_id') 

    try:
        with get_db_connection() as db:
            # 修改：传入 admin_id 查找学生
            participant = db_utils.get_participant(db, student_id, admin_id)
            if not participant:
                raise HTTPException(status_code=401, detail="用户不存在")

            now = datetime.now()
            activity = db_utils.get_activity_by_code(db, request.activity_code)
            
            if not activity:
                return JSONResponse(status_code=200, content={"detail": "活动不存在"})
            
            # 新增校验：防止 A 学校的学生扫 B 学校的码签到
            if activity['admin_id'] != admin_id:
                 return JSONResponse(status_code=200, content={"detail": "您无权签到该活动 (组织不匹配)"})

            if not (activity['start_time'] <= now <= activity['end_time']):
                return JSONResponse(status_code=200, content={"detail": "不在活动时间范围内"})

            # --- 坐标转换与距离计算 (保持不变) ---
            try:
                act_lon_float = float(activity['longitude'])
                act_lat_float = float(activity['latitude'])
                act_wgs_lon, act_wgs_lat = coord_utils.gcj2wgs(act_lon_float, act_lat_float)
                
                req_lon_float = float(request.longitude)
                req_lat_float = float(request.latitude)
                req_wgs_lon, req_wgs_lat = coord_utils.gcj2wgs(req_lon_float, req_lat_float)
                
                distance = db_utils.calculate_distance(
                    act_wgs_lat, act_wgs_lon,
                    req_wgs_lat, req_wgs_lon
                )
            except Exception as e:
                print(f"Check-in calc error: {e}")
                raise HTTPException(status_code=500, detail=f"定位计算失败: {str(e)}")
                
            if distance > activity['radius_meters']:
                return JSONResponse(status_code=200, content={"detail": f"您不在签到范围内 (距离 {int(distance)} 米)"})

            # --- 检查重复签到 ---
            if db_utils.get_check_log(db, participant['id'], activity['id']):
                raise HTTPException(status_code=400, detail="您已签到，请勿重复操作")

            # --- 写入记录 ---
            device_token = db_utils.create_check_log(
                db, activity['id'], participant['id'], request.latitude, request.longitude
            )
            return {"message": "签到成功", "device_session_token": device_token}
            
    except HTTPException:
        raise
    except Exception as e:
        # 这里会捕获 TypeError (参数缺失) 并转为 500，就是你看到的报错
        print(f"Error in checkin: {e}") 
        raise HTTPException(status_code=500, detail=f"签到未知错误: {str(e)}")


@router_participant.post("/checkout-auth")
async def checkout_authorized(
    request: models.CheckInRequestAuthorized, 
    current_user: dict = Depends(get_current_student)
):
    """实名签退"""
    student_id = current_user['sub']
    # 新增：获取 admin_id
    admin_id = current_user.get('admin_id')
    
    with get_db_connection() as db:
        # 修改：传入 admin_id
        participant = db_utils.get_participant(db, student_id, admin_id)
        if not participant:
            raise HTTPException(status_code=401, detail="用户不存在")
            
        # 2. 找记录 (查该用户当前活动的未签退记录)
        active_log = db_utils.get_active_log_by_student(db, participant['id'])
        
        if not active_log:
             raise HTTPException(status_code=400, detail="未找到有效的签到记录，或已签退")
             
        # 3. 校验活动是否匹配
        if active_log['unique_code'] != request.activity_code:
             raise HTTPException(status_code=400, detail="您当前的签到记录与此活动不符")

        # 4. 校验时间
        now = datetime.now()
        if not (active_log['start_time'] <= now <= active_log['end_time']):
             raise HTTPException(status_code=400, detail="不在活动时间范围内")

        # 5. 校验地点
        try:
            act_wgs_lat, act_wgs_lon = coord_utils.gcj2wgs(float(active_log['longitude']), float(active_log['latitude']))
            req_wgs_lat, req_wgs_lon = coord_utils.gcj2wgs(float(request.longitude), float(request.latitude))
            distance = db_utils.calculate_distance(act_wgs_lat, act_wgs_lon, req_wgs_lat, req_wgs_lon)
        except Exception:
            distance = 0
            
        if distance > active_log['radius_meters']:
             return JSONResponse(status_code=200, content={"detail": f"您不在签退范围内 (距离 {int(distance)} 米)"})

        # 6. 执行签退
        db_utils.update_check_log_checkout(db, active_log['id'], request.latitude, request.longitude)
        
        return {"message": "签退成功"}

# ==================================================
# 3. 注册路由和静态文件
# ==================================================
app.include_router(router_admin)
app.include_router(router_participant)

# 挂载静态文件
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True), name="static")