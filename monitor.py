import json
import time
import re
import os
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
        if pattern.search(html):
            return int(pattern.search(html).group(1))
    except:
        pass
    return 0

# 微信推送 Server酱
def wechat_push(title, content):
    key = os.getenv("SCT_KEY")
    if not key:
        print("❌ 未配置微信推送密钥")
        return
    url = f"https://sctapi.ftqq.com/{key}.send"
    data = {
        "title": title,
        "desp": content
    }
    try:
        res = requests.post(url, data=data, timeout=10)
        print("✅ 微信推送发送成功")
    except Exception as e:
        print(f"❌ 微信推送失败：{str(e)}")

def check_item(item):
    url = item.get("url")
    keyword = item.get("keyword")
    threshold = item.get("threshold", 0)

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=15)
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

            # 推送微信消息
            title = "【库存告警】有货提醒"
            content = f"商品：{keyword}\n当前库存：{stock}\n可前往下单"
            wechat_push(title, content)

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
