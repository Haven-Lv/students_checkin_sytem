import mysql.connector
from mysql.connector.cursor import MySQLCursorDict
from contextlib import contextmanager
from config import settings
from models import ActivityCreate, ParticipantLogin
from datetime import datetime
import uuid
import haversine as hs
from haversine import Unit

# 数据库连接配置
DB_CONFIG = {
    'user': settings.DB_USER,
    'password': settings.DB_PASSWORD,
    'host': settings.DB_HOST,
    'database': settings.DB_NAME
}

@contextmanager
def get_db_connection():
    """提供一个带事务和自动关闭的数据库连接"""
    try:
        db = mysql.connector.connect(**DB_CONFIG)
        yield db
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        raise
    finally:
        if db.is_connected():
            db.close()

# --- 地理位置计算 ---
def calculate_distance(lat1, lon1, lat2, lon2) -> float:
    """计算两个经纬度之间的距离（米）"""
    loc1 = (lat1, lon1)
    loc2 = (lat2, lon2)
    return hs.haversine(loc1, loc2, unit=Unit.METERS)

# --- 管理员相关 ---
def get_admin_by_username(db, username: str):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
    admin = cursor.fetchone()
    cursor.close()
    return admin

def db_create_admin(db, username: str, hashed_pass: str):
    cursor = db.cursor()
    try:
        cursor.execute("INSERT INTO admins (username, hashed_password) VALUES (%s, %s)", (username, hashed_pass))
        db.commit()
    except mysql.connector.Error as err:
        db.rollback()
        raise err
    finally:
        cursor.close()

# --- 活动相关 ---
def db_create_activity(db, activity: ActivityCreate):
    unique_code = str(uuid.uuid4())
    cursor = db.cursor()
    query = """
    INSERT INTO activities (name, location_name, latitude, longitude, radius_meters, start_time, end_time, unique_code)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        cursor.execute(query, (
            activity.name, activity.location_name, activity.latitude, activity.longitude,
            activity.radius_meters, activity.start_time, activity.end_time, unique_code
        ))
        db.commit()
        return unique_code
    except mysql.connector.Error as err:
        db.rollback()
        raise err
    finally:
        cursor.close()

def get_activity_by_code(db, code: str):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM activities WHERE unique_code = %s", (code,))
    activity = cursor.fetchone()
    cursor.close()
    return activity

def get_all_activities(db):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name, unique_code, start_time, end_time FROM activities ORDER BY created_at DESC")
    activities = cursor.fetchall()
    cursor.close()
    return activities

def get_check_logs_for_activity(db, activity_id: int):
    cursor = db.cursor(dictionary=True)
    query = """
    SELECT p.student_id, p.name, cl.check_in_time, cl.check_out_time
    FROM check_logs cl
    JOIN participants p ON cl.participant_id = p.id
    WHERE cl.activity_id = %s
    ORDER BY cl.check_in_time
    """
    cursor.execute(query, (activity_id,))
    logs = cursor.fetchall()
    cursor.close()
    return logs

# --- 参与者/签到相关 ---
def get_participant(db, student_id: str):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM participants WHERE student_id = %s", (student_id,))
    participant = cursor.fetchone()
    cursor.close()
    return participant

def create_participant(db, student_id: str, name: str):
    cursor = db.cursor()
    try:
        cursor.execute("INSERT INTO participants (student_id, name) VALUES (%s, %s)", (student_id, name))
        db.commit()
        new_id = cursor.lastrowid
        cursor.close()
        return {"id": new_id, "student_id": student_id, "name": name}
    except mysql.connector.Error as err:
        db.rollback()
        cursor.close()
        # 可能是学号重复，返回 None 让主逻辑处理
        return None

def get_check_log(db, p_id: int, a_id: int):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM check_logs WHERE participant_id = %s AND activity_id = %s", (p_id, a_id))
    log = cursor.fetchone()
    cursor.close()
    return log

def create_check_log(db, a_id: int, p_id: int, lat: float, lon: float) -> str:
    device_token = str(uuid.uuid4())
    cursor = db.cursor()
    query = """
    INSERT INTO check_logs (activity_id, participant_id, check_in_time, device_session_token, check_in_lat, check_in_lon)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    try:
        cursor.execute(query, (a_id, p_id, datetime.now(), device_token, lat, lon))
        db.commit()
        cursor.close()
        return device_token
    except mysql.connector.Error as err:
        db.rollback()
        cursor.close()
        raise err

def get_log_by_device_token(db, token: str):
    cursor = db.cursor(dictionary=True)
    # 联表查询活动信息
    cursor.execute("""
        SELECT cl.*, a.start_time, a.end_time, a.latitude, a.longitude, a.radius_meters 
        FROM check_logs cl
        JOIN activities a ON cl.activity_id = a.id
        WHERE cl.device_session_token = %s
    """, (token,))
    log = cursor.fetchone()
    cursor.close()
    return log

def update_check_log_checkout(db, log_id: int, lat: float, lon: float):
    cursor = db.cursor()
    query = """
    UPDATE check_logs 
    SET check_out_time = %s, check_out_lat = %s, check_out_lon = %s
    WHERE id = %s
    """
    try:
        cursor.execute(query, (datetime.now(), lat, lon, log_id))
        db.commit()
        cursor.close()
        return True
    except mysql.connector.Error as err:
        db.rollback()
        cursor.close()
        raise err
    
def db_delete_activity(db, activity_id: int):
    """删除活动，会先删除关联的签到记录 (事务)"""
    cursor = db.cursor()
    try:
        # 1. 删除签到日志 (外键约束)
        cursor.execute("DELETE FROM check_logs WHERE activity_id = %s", (activity_id,))
        # 2. 删除活动
        cursor.execute("DELETE FROM activities WHERE id = %s", (activity_id,))
        db.commit()
    except mysql.connector.Error as err:
        db.rollback()
        cursor.close()
        raise err
    finally:
        cursor.close()

def db_update_activity_time(db, activity_id: int, start_time: datetime, end_time: datetime):
    """更新活动的开始和结束时间"""
    cursor = db.cursor()
    query = "UPDATE activities SET start_time = %s, end_time = %s WHERE id = %s"
    try:
        cursor.execute(query, (start_time, end_time, activity_id))
        db.commit()
        cursor.close()
        return True
    except mysql.connector.Error as err:
        db.rollback()
        cursor.close()
        raise err