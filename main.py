import aiohttp
import asyncio
import re
import html
from datetime import datetime, timedelta

TEAMEAR_URLS = [ 
    "https://teamear.tixcraft.com/ticket/area/25_crowdticc/19969", 
    "https://teamear.tixcraft.com/ticket/area/25_crowdticc/19970", 
]

DISCORD_WEBHOOK_URL_MAIN = "https://discord.com/api/webhooks/1371436288330436618/_WsfwLwakJLC1vW7g01iZcDzPTiSnxhR4ijRv0gtsxv4Yo27J49Dx8zubkZqb_m-GW00"

last_sent_tickets = {'TEAMEAR': {}}

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
    return text.strip()

def parse_ticket_status(t: str):
    if "已售完" in t:
        return "soldout"
    elif "剩餘" in t:
        return "available"
    else:
        return "unknown"

def extract_event_title(html_text):
    pattern = r'<select id="gameId".*?>(.*?)</select>'
    select_match = re.search(pattern, html_text, re.DOTALL)
    if not select_match:
        return "未知場次"
    select_content = select_match.group(1)
    option_pattern = r'<option value=".*?" selected>(.*?)</option>'
    option_match = re.search(option_pattern, select_content, re.DOTALL)
    if option_match:
        return html.unescape(option_match.group(1)).strip()
    return "未知場次"

def build_embed(platform, event_title, url, available_tickets):
    now = datetime.now() + timedelta(hours=8)
    return {
        "description": f"🔥**清票啦（{platform}）**",
        "color": 0xFFA500,
        "fields": [
            {"name": "🎤 場次名稱：", "value": event_title, "inline": False},
            {"name": "🔗 網站：", "value": f"[點我前往購票]({url})", "inline": False},
            {"name": "🎟️ 可購買的票區", "value": "\n".join(available_tickets), "inline": False},
            {"name": "", "value": f"⏰更新時間：{now.strftime('%Y-%m-%d %H:%M:%S')}", "inline": False}
        ],
    }

async def send_discord_message(session, embed):
    payload = {
        "username": "🚨【清票搶購】票務小幫手🚨",
        "embeds": [embed]
    }
    async with session.post(DISCORD_WEBHOOK_URL_MAIN, json=payload) as resp:
        if resp.status != 204:
            print(f"❌ Discord通知失敗: {await resp.text()}")

async def check_teamear_single(session, url):
    url_key = url.split("/")[-1]
    first_check = True

    while True:
        try:
            async with session.get(url, headers=headers, timeout=10) as resp:
                html_text = await resp.text()

            event_title = extract_event_title(html_text)

            # 剩餘票區（class="select_form_b"）
            pattern_available = r'<li class="select_form_b">.*?<a.*?>(.*?)</a>'
            matches_available = re.findall(pattern_available, html_text, re.DOTALL)

            # 已售完票區（不含 class="select_form_b"）
            pattern_soldout = r'<li(?! class="select_form_b").*?<font.*?>(.*?)</font>'
            matches_soldout = re.findall(pattern_soldout, html_text, re.DOTALL)

            all_tickets = []
            tickets_for_notify = []

            for t in matches_available:
                if "身障" in t:
                    continue
                cleaned = html.unescape(re.sub(r'<.*?>', '', t).strip())
                all_tickets.append(cleaned)
                tickets_for_notify.append(cleaned)

            for t in matches_soldout:
                if "身障" in t:
                    continue
                cleaned = html.unescape(t.strip())
                all_tickets.append(cleaned)

            if url_key not in last_sent_tickets['TEAMEAR']:
                last_sent_tickets['TEAMEAR'][url_key] = {}

            changed = False

            if first_check:
                print(f"[首次初始化] {event_title}")
                for ticket in all_tickets:
                    print(f"  {ticket}")

                for ticket in all_tickets:
                    ticket_name = normalize_ticket_text(ticket)
                    status = parse_ticket_status(ticket)
                    last_sent_tickets['TEAMEAR'][url_key][ticket_name] = status

            else:
                for ticket in tickets_for_notify:
                    ticket_name = normalize_ticket_text(ticket)
                    status = parse_ticket_status(ticket)
                    last_status = last_sent_tickets['TEAMEAR'][url_key].get(ticket_name)
                    if last_status != status:
                        changed = True
                        print(f"🔔 {event_title} | {ticket_name} 狀態變化: {last_status} ➔ {status}")
                    last_sent_tickets['TEAMEAR'][url_key][ticket_name] = status

                if changed and tickets_for_notify:
                    embed = build_embed("Teamear", event_title, url, tickets_for_notify)
                    await send_discord_message(session, embed)

            first_check = False

        except Exception as e:
            print(f"⚠️ [{url_key}] 錯誤: {e}")

        await asyncio.sleep(1)

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [check_teamear_single(session, url) for url in TEAMEAR_URLS]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
