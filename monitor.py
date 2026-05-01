import json
import time
import smtplib
import re
import os
from email.mime.text import MIMEText
from email.header import Header
import requests

# 冷却时间：30分钟
COOLDOWN = 1800
last_alarm = {}

def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

# 精准库存抓取（和本地一致）
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

# 【139强制短信专用格式】
def send_sms_alert(item, stock):
    from_email = os.getenv("FROM_EMAIL")
    from_pwd = os.getenv("FROM_PWD")
    to_phone = os.getenv("TO_PHONE")

    if not from_email or not from_pwd or not to_phone:
        print("❌ 邮箱/手机号密钥缺失")
        return

    to_email = f"{to_phone}@139.com"
    title = "库存告警"
    content = f"商品:{item['keyword']}\n库存:{stock}\n及时下单！"

    msg = MIMEText(content, "plain", "utf-8")
    msg["From"] = Header("库存监控", "utf-8") + f" <{from_email}>"
    msg["To"] = to_email
    msg["Subject"] = Header(title, "utf-8")

    try:
        with smtplib.SMTP_SSL("smtp.qq.com", 465) as server:
            server.login(from_email, from_pwd)
            server.sendmail(from_email, [to_email], msg.as_string())
        print(f"✅ 短信推送成功，即将下发至手机")
    except Exception as e:
        print(f"❌ 发送异常：{str(e)}")

def check_item(item):
    url = item.get("url")
    keyword = item.get("keyword")
    threshold = item.get("threshold", 0)

    if not url or not keyword:
        return

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, timeout=15, headers=headers)
        html = r.text
        stock = extract_stock(html, keyword)

        print(f"商品：{keyword} | 库存：{stock} | 阈值：{threshold}")

        if stock > threshold:
            now = int(time.time())
            key = f"{url}_{keyword}"
            if key in last_alarm and now - last_alarm[key] < COOLDOWN:
                print("⚠️ 冷却中，跳过提醒")
                return
            last_alarm[key] = now
            send_sms_alert(item, stock)

    except Exception as e:
        print(f"❌ 访问失败：{str(e)}")

def main():
    config = load_config()
    if not config:
        print("ℹ️ 无监控配置")
        return
    print("🚀 开始监控库存...")
    for item in config:
        check_item(item)

if __name__ == "__main__":
    main()
