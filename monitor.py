import json
import time
import smtplib
import re
import os
from email.mime.text import MIMEText
import requests

# 冷却时间：30分钟内不重复提醒
COOLDOWN = 1800
last_alarm = {}

# 读取监控配置
def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

# 【精准库存提取】和网页逻辑完全一致
def extract_stock(html, keyword):
    try:
        # 规则1：优先匹配 库存:9 / 库存：9
        pattern = re.compile(keyword + r'[\s\S]*?库存[^\d]*?(\d+)', re.I)
        match = pattern.search(html)
        if match:
            return int(match.group(1))

        # 规则2：匹配网页标签内的数字 <div>9</div>
        pattern = re.compile(keyword + r'[\s\S]*?>(\d+)<', re.I)
        match = pattern.search(html)
        if match:
            return int(match.group(1))
    except:
        pass
    return 0

# 发送短信（移动139邮箱短信）
def send_sms_alert(item, stock):
    from_email = os.getenv("FROM_EMAIL")
    from_pwd = os.getenv("FROM_PWD")
    to_phone = os.getenv("TO_PHONE")

    if not from_email or not from_pwd or not to_phone:
        print("❌ 未配置邮箱或手机号")
        return

    to_email = f"{to_phone}@139.com"
    title = f"【库存告警】{item['keyword']} 有货！库存：{stock}"
    content = f"商品：{item['keyword']}\n库存：{stock}\n地址：{item['url']}"

    try:
        msg = MIMEText(content, "plain", "utf-8")
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = title

        with smtplib.SMTP_SSL("smtp.qq.com", 465) as server:
            server.login(from_email, from_pwd)
            server.sendmail(from_email, [to_email], msg.as_string())

        print(f"✅ 短信已发送至：{to_phone}")
    except Exception as e:
        print(f"❌ 短信发送失败：{str(e)}")

# 检查单个商品
def check_item(item):
    url = item.get("url")
    keyword = item.get("keyword")
    threshold = item.get("threshold", 0)

    if not url or not keyword:
        return

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        r = requests.get(url, headers=headers, timeout=15)
        html = r.text
        stock = extract_stock(html, keyword)

        print(f"商品：{keyword} | 库存：{stock} | 阈值：{threshold}")

        # 超过阈值则告警
        if stock > threshold:
            now = int(time.time())
            key = f"{url}_{keyword}"

            # 冷却判断
            if key in last_alarm and now - last_alarm[key] < COOLDOWN:
                print("⚠️ 冷却中，不重复提醒")
                return

            last_alarm[key] = now
            send_sms_alert(item, stock)

    except Exception as e:
        print(f"❌ {keyword} 访问失败：{str(e)}")

# 主程序
def main():
    config = load_config()
    if not config:
        print("ℹ️ 暂无监控项")
        return

    print("🚀 开始监控库存...")
    for item in config:
        check_item(item)

if __name__ == "__main__":
    main()