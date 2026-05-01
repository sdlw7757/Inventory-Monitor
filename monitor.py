import json
import time
import re
import os
import smtplib
from email.mime.text import MIMEText
import requests

# 冷却时间 30分钟
COOLDOWN = 1800
last_alarm = {}

def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

# 精准库存抓取
def extract_stock(html, keyword):
    try:
        pattern = re.compile(keyword + r'[\s\S]*?库存[^\d]*?(\d+)', re.I)
        match = pattern.search(html)
        if match:
            return int(match.group(1))
        pattern = re.compile(keyword + r'[\s\S]*?>(\d+)<', re.I)
        match = pattern.search(html)
        if match:
            return int(match.group(1))
    except:
        pass
    return 0

# 【139短信强制触发专用】
def send_sms_alert(item, stock):
    from_email = os.getenv("FROM_EMAIL")
    from_pwd = os.getenv("FROM_PWD")
    to_phone = os.getenv("TO_PHONE")
    if not all([from_email, from_pwd, to_phone]):
        return

    to_mail = f"{to_phone}@139.com"
    # 关键：超短标题+紧急内容，139必转短信
    subject = "紧急库存提醒"
    content = "到货有货，尽快下单"

    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_mail

    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(from_email, from_pwd)
        server.sendmail(from_email, to_mail, msg.as_string())
        server.quit()
        print("✅ 紧急邮件已发送，手机即将收到短信")
    except Exception as e:
        print(f"❌ 发送失败：{e}")

def check_item(item):
    url = item["url"]
    keyword = item["keyword"]
    threshold = item.get("threshold", 0)

    try:
        headers = {"User-Agent":"Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        stock = extract_stock(res.text, keyword)
        print(f"{keyword} | 库存：{stock}")

        if stock > threshold:
            key = f"{url}_{keyword}"
            now = int(time.time())
            if key in last_alarm and now - last_alarm[key] < COOLDOWN:
                return
            last_alarm[key] = now
            send_sms_alert(item, stock)
    except Exception as e:
        print(f"❌ {keyword} 异常：{e}")

def main():
    config = load_config()
    print("🚀 开始监控")
    for item in config:
        check_item(item)

if __name__ == "__main__":
    main()
