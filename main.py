import aiohttp
import asyncio
import time
import os
import sys
import re
from datetime import datetime, timedelta

TEAMEAR_URLS = [ 
    "https://teamear.tixcraft.com/ticket/area/25_crowdticc/19969", 
    "https://teamear.tixcraft.com/ticket/area/25_crowdticc/19970", 
]

DISCORD_WEBHOOK_URL_MAIN = "https://discord.com/api/webhooks/1376944537142034512/llRKwpmLteNX-uID94ns2m2cppeeIyx_la2jU5225WoBCTT3GHMOU8YBzJNhefxHUg5A"

last_sent_tickets = {
    'TEAMEAR': {}
}

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,ja;q=0.6",
    "Cache-Control": "max-age=0",
    "Priority": "u=0, i",
    "Referer": "https://teamear.tixcraft.com/activity/detail/25_crowdticc",
    "Sec-CH-UA": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
}

def normalize_ticket_text(text: str) -> str:
    return re.sub(r'\s+', '', text.strip())

def parse_ticket_status(t: str):
    t = normalize_ticket_text(t)
    if "已售完" in t:
        return "soldout"
    elif "剩餘" in t:
        return "available"
    else:
        return "unknown"

def extract_event_title(html):
    pattern = r'<select id="gameId".*?>(.*?)</select>'
    select_match = re.search(pattern, html, re.DOTALL)

    if not select_match:
        return "未知場次"

    select_content = select_match.group(1)

    option_pattern = r'<option value=".*?" selected>(.*?)</option>'
    option_match = re.search(option_pattern, select_content, re.DOTALL)

    if option_match:
        text = option_match.group(1)
        return text.replace("&lt;", "<").replace("&gt;", ">").strip()

    return "未知場次"

def build_embed(platform, event_title, url, available_tickets):
    now = datetime.now() + timedelta(hours=8)
    return {
        "description": f"🔥**清票啦（{platform}）**",
        "color": 0xFFA500,
        "fields": [
            {"name": "🎤 場次名稱：", "value": event_title, "inline": False},
            {"name": "🔗 網站：", "value": f"[點我前往購票]({url})", "inline": False},
            {"name": "🎟️ 可購買的票區", "value": "\n".join(available_tickets) if available_tickets else "無可購買票區", "inline": False},
            {"name": "", "value": f"⏰更新時間：{now.strftime('%Y-%m-%d %H:%M:%S')}", "inline": False}
        ],
    }

async def send_single_message(session, url, payload):
    try:
        async with session.post(url, json=payload) as response:
            if response.status == 204:
                print(f"✅ 成功發送到: {url}")
            else:
                error_text = await response.text()
                print(f"❌ 發送失敗 ({url}) 狀態碼: {response.status}，訊息: {error_text}")
    except aiohttp.ClientError as e:
        print(f"❌ 發送錯誤 ({url}): {e}")

async def send_discord_message(session, embed, urls=None):
    payload = {
        "username": "🚨【清票搶購】票務小幫手🚨",
        "embeds": [embed]
    }
    if urls is None:
        urls = [DISCORD_WEBHOOK_URL_MAIN]

    tasks = [send_single_message(session, url, payload) for url in urls]
    await asyncio.gather(*tasks)

async def check_teamear_single(session, url):
    url_key = url.split("/")[-1]

    first_check = True

    while True:
        try:
            async with session.get(url, headers=headers, timeout=10) as response:
                html = await response.text()

            event_title = extract_event_title(html)

            pattern = r'<li>.*?<font.*?>(.*?)</font>'
            matches = re.findall(pattern, html, re.DOTALL)

            changed = False
            tickets_for_notify = []

            if url_key not in last_sent_tickets['TEAMEAR']:
                last_sent_tickets['TEAMEAR'][url_key] = {}

            if first_check:
                print(f"[首次初始化] {event_title}")

            for t in matches:
                if "身障" in t:
                    continue

                ticket_name = normalize_ticket_text(t)
                status = parse_ticket_status(t)

                last_status = last_sent_tickets['TEAMEAR'][url_key].get(ticket_name)

                if first_check:
                    print(f"  {t.strip()}")
                else:
                    if last_status != status:
                        changed = True
                        tickets_for_notify.append(t)
                        print(f"🔔 [{url_key}] {event_title} | {ticket_name} 狀態變化: {last_status} ➔ {status}")

                last_sent_tickets['TEAMEAR'][url_key][ticket_name] = status

            if changed and not first_check:
                embed = build_embed("Teamear", event_title, url, tickets_for_notify)
                await send_discord_message(session, embed)

            first_check = False

        except Exception as e:
            print(f"⚠️ [{url_key}] 發生錯誤: {e}")

        await asyncio.sleep(1)

async def main():
    try:
        async with aiohttp.ClientSession() as session:
            tasks = [check_teamear_single(session, url) for url in TEAMEAR_URLS]
            await asyncio.gather(*tasks)
    except Exception as e:
        print(f"⚠️ 主程式錯誤: {e}")

if __name__ == "__main__":
    asyncio.run(main())
