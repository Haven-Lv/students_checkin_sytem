# 学生活动签到系统 (Student Check-in System)

这是一个基于 **FastAPI (Python)** 和 **MySQL** 开发的地理位置签到系统。管理员可以创建活动并生成二维码，学生通过邮箱验证登录后，扫描二维码并在指定地点范围内进行签到和签退。

系统集成了 **高德地图 API** 用于地理围栏判定，支持防作弊（距离校验），并具备完善的管理员后台。

## ✨ 主要功能

### 👨‍💻 管理员端

  * **安全登录**：基于 JWT 的身份验证。
  * **活动管理**：
      * 创建活动：设置名称、时间、签到半径，并在地图上点选位置。
      * 生成二维码：一键生成活动专属签到二维码。
      * 管理活动：修改活动名称、时间、地点、半径、状态、删除活动。
  * **数据统计**：查看每个活动的详细签到/签退日志（包含学号、姓名、时间）。

### 🙋‍♂️ 学生端

  * **邮箱验证登录**：使用邮箱发送验证码登录，首次登录需绑定学号和姓名。
  * **扫码签到**：扫描活动二维码进入签到页面。
  * **位置校验**：系统自动获取当前 GPS 位置，计算与活动地点的距离，只有在规定半径内才允许签到。
  * **签退功能**：活动结束或离开时进行签退。
  * **状态同步**：支持跨设备状态同步（检测是否已签到）。

## 🛠 技术栈

  * **后端框架**: FastAPI (Python)
  * **数据库**: MySQL
  * **前端**:原生 HTML5 + CSS3 + JavaScript (无复杂框架依赖)
  * **地图服务**: 高德地图 JS API (AMap)
  * **认证机制**: OAuth2 + JWT (JSON Web Tokens)
  * **邮件服务**: SMTP (用于发送验证码)

## 📂 项目结构

```text
haven-lv/students_checkin_sytem/
├── app/
│   ├── __init__.py
│   ├── main.py             # 程序入口，API 路由定义
│   ├── config.py           # 配置文件 (数据库, 邮件, JWT密钥)
│   ├── models.py           # Pydantic 数据模型
│   ├── db_utils.py         # 数据库 CRUD 操作封装
│   ├── security.py         # 密码哈希与 Token 验证
│   ├── coord_utils.py      # 坐标转换工具 (GCJ02 <-> WGS84)
│   ├── create_admin.py     # 创建管理员账号的脚本
│   └── static/             # 静态资源 (HTML 页面)
│       ├── admin_dashboard.html
│       ├── admin_login.html
│       ├── checkin.html
│       └── student_login.html
├── requirements.txt        # 项目依赖列表
└── .gitignore
```

## 🚀 安装与部署

### 1\. 环境准备

  * Python 3.8+
  * MySQL 5.7+ 或 8.0+

### 2\. 安装依赖

在项目根目录下运行：

```bash
pip install fastapi uvicorn mysql-connector-python pydantic pydantic-settings python-jose[cryptography] passlib[bcrypt] qrcode[pil] haversine
```

### 3\. 数据库配置

请在 MySQL 中创建一个数据库（例如 `student_system_db`），并执行以下 SQL 语句创建必要的数据表：

```sql
CREATE DATABASE IF NOT EXISTS student_system_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE student_system_db;

-- 管理员表
CREATE TABLE admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL
);

-- 学生/参与者表
CREATE TABLE participants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 活动表
CREATE TABLE activities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    unique_code VARCHAR(36) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    location_name VARCHAR(255),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    radius_meters INT DEFAULT 100,
    start_time DATETIME,
    end_time DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 签到日志表
CREATE TABLE check_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    activity_id INT,
    participant_id INT,
    device_session_token VARCHAR(255),
    check_in_time DATETIME,
    check_out_time DATETIME,
    check_in_lat DECIMAL(10, 8),
    check_in_lon DECIMAL(11, 8),
    check_out_lat DECIMAL(10, 8),
    check_out_lon DECIMAL(11, 8),
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
    FOREIGN KEY (participant_id) REFERENCES participants(id)
);

-- 验证码表
CREATE TABLE verification_codes (
    email VARCHAR(100) PRIMARY KEY,
    code VARCHAR(10),
    expires_at DATETIME
);
```

### 4\. 修改配置文件

打开 `app/config.py`，根据你的实际环境修改以下配置：

```python
class Settings(BaseSettings):
    # 数据库配置
    DB_USER: str = 'root'             # 你的数据库用户名
    DB_PASSWORD: str = 'yourpassword' # 你的数据库密码
    DB_HOST: str = 'localhost'
    DB_NAME: str = 'student_system_db'
    
    # JWT 安全配置 (生产环境请务必修改 Secret Key)
    JWT_SECRET_KEY: str = 'your-secret-key-change-me'
    
    # 邮件 SMTP 配置 (用于发送登录验证码)
    SMTP_SERVER: str = 'smtp.qq.com'
    SMTP_PORT: int = 465
    SMTP_USER: str = 'your-email@qq.com'
    SMTP_PASSWORD: str = 'your-email-auth-code'
```


### 5\. 创建管理员账号

运行提供的脚本创建第一个管理员账号：

```bash
python -m app.create_admin
```

按照提示输入用户名和密码。

### 6\. 启动服务

在项目根目录运行：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📖 使用指南

### 管理员流程

1.  访问 `http://localhost:8000/students_system/admin_login.html` (注意 URL 路径可能需要根据你的 Nginx 配置或 FastAPI 挂载路径调整，默认为 `/static/admin_login.html`，若使用了 Nginx rewrite 则按 rewrite 规则访问)。
2.  登录后进入控制台。
3.  **创建活动**：填写信息，在地图上点击选择中心点，设置允许签到的半径。
4.  **发布**：点击列表中的“二维码和链接”，下载二维码或复制链接发给学生。

### 学生流程

1.  扫描管理员提供的二维码，或访问活动链接。
2.  如果没有登录，会跳转到登录页。输入邮箱获取验证码。若是新用户，需填写入学学号和姓名。
3.  登录成功后返回签到页，点击“立即签到”。
4.  浏览器会请求地理位置权限，系统校验距离。若在范围内，签到成功。
5.  活动结束后，点击“签退”按钮。

## ⚠️ 注意事项

1.  **HTTPS 协议**：现代浏览器要求地理位置 API (`navigator.geolocation`) 必须在 **HTTPS** 环境下才能调用（localhost 除外）。部署到服务器时请务必配置 SSL 证书。
2.  **坐标系**：系统内部处理了国内常见的火星坐标系 (GCJ-02) 与 GPS 坐标系 (WGS-84) 的转换，确保距离计算准确。
3.  **需创建 `.env` 文件**：根据实际环境修改 `app/config.py` 中的配置，使用 `.env` 文件来存储敏感信息（如数据库密码、JWT 密钥等）。

## 🤝 贡献

欢迎提交 Issue 或 Pull Request 来改进此项目。
