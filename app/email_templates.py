# app/email_templates.py

from datetime import datetime

class EmailTemplates:
    """
    邮件模板管理类
    集中管理系统中所有发送邮件的 HTML 样式和结构
    """

    @staticmethod
    def _get_base_style() -> str:
        """
        获取基础 CSS 样式
        """
        return """
        <style>
            body {
                margin: 0;
                padding: 0;
                background-color: #f4f7f6;
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                -webkit-font-smoothing: antialiased;
            }
            .email-container {
                max-width: 600px;
                margin: 20px auto;
                background-color: #ffffff;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
                border: 1px solid #e1e4e8;
            }
            .email-header {
                background-color: #007bff;
                background-image: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
                color: #ffffff;
                padding: 30px 20px;
                text-align: center;
            }
            .email-header h1 {
                margin: 0;
                font-size: 24px;
                font-weight: 600;
                letter-spacing: 1px;
            }
            .email-body {
                padding: 40px 30px;
                color: #333333;
                line-height: 1.8;
                font-size: 16px;
            }
            .verification-code {
                display: block;
                width: fit-content;
                margin: 30px auto;
                padding: 15px 40px;
                background-color: #f8f9fa;
                border: 2px dashed #007bff;
                border-radius: 6px;
                font-size: 32px;
                font-weight: bold;
                color: #007bff;
                letter-spacing: 8px;
                text-align: center;
            }
            .info-box {
                background-color: #eaf4ff;
                border-left: 4px solid #007bff;
                padding: 15px;
                margin: 20px 0;
                color: #004085;
                font-size: 14px;
            }
            .email-footer {
                background-color: #f8f9fa;
                padding: 20px;
                text-align: center;
                border-top: 1px solid #eeeeee;
                color: #888888;
                font-size: 12px;
            }
            .email-footer p {
                margin: 5px 0;
            }
            a {
                color: #007bff;
                text-decoration: none;
            }
            @media only screen and (max-width: 600px) {
                .email-container {
                    width: 100% !important;
                    margin: 0 !important;
                    border-radius: 0 !important;
                }
                .email-body {
                    padding: 20px !important;
                }
            }
        </style>
        """

    @staticmethod
    def verification_code_email(code: str, valid_minutes: int = 5) -> str:
        """
        生成验证码邮件 HTML 内容
        """
        current_year = datetime.now().year
        style = EmailTemplates._get_base_style()
        
        return f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>安全验证</title>
            {style}
        </head>
        <body>
            <div class="email-container">
                <div class="email-header">
                    <h1>校园活动签到系统</h1>
                </div>
                <div class="email-body">
                    <p>亲爱的同学：</p>
                    <p>您好！您正在登录或注册校园活动签到系统。为了保障您的账号安全，我们需要验证您的身份。</p>
                    
                    <p>请使用以下验证码完成验证：</p>
                    
                    <div class="verification-code">
                        {code}
                    </div>
                    
                    <div class="info-box">
                        <strong>注意：</strong>
                        此验证码将在 <strong>{valid_minutes} 分钟</strong>后失效。如果您没有请求此验证码，请忽略此邮件，您的账号安全不会受到影响。
                    </div>
                    
                    <p>为了安全起见，请勿将验证码转发给他人。</p>
                    <br>
                    <p>祝您生活愉快！</p>
                    <p style="text-align: right;">— 校园签到管理团队</p>
                </div>
                <div class="email-footer">
                    <p>此邮件由系统自动发送，请勿回复。</p>
                    <p>&copy; {current_year} Student Check-in System. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

    @staticmethod
    def welcome_email(name: str, school_name: str) -> str:
        current_year = datetime.now().year
        style = EmailTemplates._get_base_style()
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>{style}</head>
        <body>
            <div class="email-container">
                <div class="email-header">
                    <h1>欢迎加入</h1>
                </div>
                <div class="email-body">
                    <p>亲爱的 <strong>{name}</strong>：</p>
                    <p>欢迎加入 <strong>{school_name}</strong> 的活动签到系统！</p>
                    <p>您的账号已成功创建。现在您可以：</p>
                    <ul>
                        <li>扫描二维码参加校园活动</li>
                        <li>实时记录您的活动考勤</li>
                        <li>查看历史活动记录</li>
                    </ul>
                    <p>如果您在使用过程中遇到任何问题，请联系管理员。</p>
                </div>
                <div class="email-footer">
                    <p>&copy; {current_year} Student Check-in System.</p>
                </div>
            </div>
        </body>
        </html>
        """

    @staticmethod
    def _get_additional_styles() -> str:
        """
        获取额外的样式（用于活动通知和签到回执）
        """
        return """
        .success-icon {
            text-align: center;
            font-size: 48px;
            color: #28a745;
            margin-bottom: 20px;
        }
        .event-card {
            background-color: #f8f9fa;
            border-left: 4px solid #17a2b8;
            padding: 20px;
            margin: 20px 0;
            border-radius: 0 4px 4px 0;
        }
        .event-detail-item {
            display: flex;
            margin-bottom: 10px;
            align-items: baseline;
        }
        .event-label {
            font-weight: bold;
            color: #555;
            width: 80px;
            flex-shrink: 0;
        }
        .event-value {
            color: #333;
        }
        .btn {
            display: inline-block;
            background-color: #007bff;
            color: #ffffff !important;
            padding: 12px 25px;
            border-radius: 4px;
            text-decoration: none;
            font-weight: bold;
            margin-top: 20px;
            text-align: center;
        }
        .btn:hover {
            background-color: #0056b3;
        }
        .receipt-box {
            border: 2px solid #28a745;
            background-color: #f0fff4;
            padding: 30px;
            border-radius: 8px;
            text-align: center;
            margin: 20px 0;
        }
        .receipt-title {
            color: #28a745;
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .timestamp {
            color: #6c757d;
            font-size: 14px;
            margin-top: 15px;
            border-top: 1px dashed #c3e6cb;
            padding-top: 10px;
        }
        """

    @staticmethod
    def activity_start_notification(activity_name: str, start_time: str, location: str, activity_url: str) -> str:
        """
        生成活动开始提醒邮件
        """
        current_year = datetime.now().year
        # 合并基础样式和额外样式
        style = EmailTemplates._get_base_style().replace("</style>", f"{EmailTemplates._get_additional_styles()}</style>")
        
        return f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>活动提醒</title>
            {style}
        </head>
        <body>
            <div class="email-container">
                <div class="email-header" style="background-image: linear-gradient(135deg, #17a2b8 0%, #117a8b 100%);">
                    <h1>⏰ 活动即将开始</h1>
                </div>
                <div class="email-body">
                    <p>各位同学：</p>
                    <p>您关注的活动 <strong>{activity_name}</strong> 即将开始！请务必准时到达指定地点进行签到。</p>
                    
                    <div class="event-card">
                        <div class="event-detail-item">
                            <span class="event-label">活动名称:</span>
                            <span class="event-value">{activity_name}</span>
                        </div>
                        <div class="event-detail-item">
                            <span class="event-label">开始时间:</span>
                            <span class="event-value">{start_time}</span>
                        </div>
                        <div class="event-detail-item">
                            <span class="event-label">活动地点:</span>
                            <span class="event-value">{location}</span>
                        </div>
                    </div>
                    
                    <p>请点击下方按钮查看活动详情或进行签到：</p>
                    
                    <div style="text-align: center;">
                        <a href="{activity_url}" class="btn">查看活动详情</a>
                    </div>
                    
                    <div class="info-box" style="margin-top: 30px;">
                        <strong>温馨提示：</strong>
                        系统将通过 GPS 定位验证您的签到位置，请确保手机已开启定位服务，并授权浏览器获取位置信息。
                    </div>
                </div>
                <div class="email-footer">
                    <p>如需请假或有其他疑问，请联系活动组织者。</p>
                    <p>&copy; {current_year} Student Check-in System.</p>
                </div>
            </div>
        </body>
        </html>
        """

    @staticmethod
    def checkin_success_notification(student_name: str, activity_name: str, checkin_time: str, location_name: str) -> str:
        """
        生成签到成功回执邮件
        """
        current_year = datetime.now().year
        # 合并样式
        style = EmailTemplates._get_base_style().replace("</style>", f"{EmailTemplates._get_additional_styles()}</style>")
        
        return f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>签到回执</title>
            {style}
        </head>
        <body>
            <div class="email-container">
                <div class="email-header" style="background-image: linear-gradient(135deg, #28a745 0%, #218838 100%);">
                    <h1>✅ 签到成功回执</h1>
                </div>
                <div class="email-body">
                    <p>亲爱的 <strong>{student_name}</strong>：</p>
                    <p>系统已确认您的签到信息。此邮件可作为您的考勤凭证，请妥善保存。</p>
                    
                    <div class="receipt-box">
                        <div class="success-icon">🎉</div>
                        <div class="receipt-title">签到成功</div>
                        <p>您已成功加入活动</p>
                        <h3 style="color: #333; margin: 10px 0;">{activity_name}</h3>
                        
                        <div class="timestamp">
                            记录时间：{checkin_time}
                        </div>
                    </div>

                    <div class="event-card" style="border-left-color: #28a745;">
                        <div class="event-detail-item">
                            <span class="event-label">签到地点:</span>
                            <span class="event-value">{location_name}</span>
                        </div>
                        <div class="event-detail-item">
                            <span class="event-label">状态:</span>
                            <span class="event-value" style="color: #28a745; font-weight: bold;">正常 (已验证)</span>
                        </div>
                    </div>
                    
                    <p style="font-size: 14px; color: #666;">
                        * 如果活动包含签退环节，请不要忘记在活动结束时进行签退操作。
                    </p>
                </div>
                <div class="email-footer">
                    <p>此凭证由系统自动生成，具有唯一效力。</p>
                    <p>&copy; {current_year} Student Check-in System.</p>
                </div>
            </div>
        </body>
        </html>
        """