import os
import sys
import json
import time
import uuid
import signal
import asyncio
import aiohttp

from utils.banner import show_banner

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"

MY_PROJECT = "Axionet Miniapp"
BASE_URL = "https://axionet.duckdns.org"
REF_CODE = "5d599ef3b20b"

AD_NETWORKS = (
    ("adsgram", "AdsGram", "adsWatchedToday"),
    ("monetag", "MonetaG", "monetagAdsWatchedToday"),
    ("gigapub", "GigaPub", "gigapubAdsWatchedToday"),
    ("uslads", "USL Ads", "usladsAdsWatchedToday"),
)
GIGAPUB_LINK_TASKS = (1, 2, 3)
LINK_VERIFY_SECONDS = 4

CALL_ATTEMPTS = 3
CALL_RETRY_SECONDS = 4
ROUND_PAUSE_SECONDS = 1
AD_COOLDOWN_SECONDS = 9
AD_UNVERIFIED_LIMIT = 3
AD_SESSION_SECONDS = 4
BACKGROUND_MILLISECONDS = 16000
BUSY_STATUS = (429, 500, 502, 503, 504)

BANNED_CODES = (
    91, 93, 124, 35, 33, 64, 36, 37, 94, 38, 42, 40, 41,
    45, 44, 58, 59, 39, 34, 96, 126, 43, 61, 60, 62, 63, 47, 92,
)
BANNED_CHARS = tuple(chr(code) for code in BANNED_CODES)

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36"
)


def log_green(msg):
    print(f"{GREEN}{BOLD}{msg}{RESET}")


def log_yellow(msg):
    print(f"{YELLOW}{BOLD}{msg}{RESET}")


def log_red(msg):
    print(f"{RED}{BOLD}{msg}{RESET}")


def signal_handler(sig, frame):
    print()
    log_red("Script stopped by user")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def clean_text(value, fallback):
    text = str(value)
    for symbol in BANNED_CHARS:
        text = text.replace(symbol, " ")
    text = " ".join(text.split())
    return text if text else str(fallback)


def unit_word(value, singular, plural):
    try:
        return singular if int(float(value)) == 1 else plural
    except Exception:
        return plural


def format_duration(seconds):
    total = int(seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    rest = total % 60
    return f"{hours:02d}:{minutes:02d}:{rest:02d}"


def load_config():
    defaults = {"settings": {"sleep_seconds": 900}}
    if not os.path.exists("config.json"):
        return defaults
    try:
        with open("config.json") as handle:
            return json.load(handle)
    except Exception:
        return defaults


def load_lines(filename, required):
    if not os.path.exists(filename):
        if required:
            log_red(f"File {clean_text(filename, 'data.txt')} was not found")
            sys.exit(1)
        return []
    lines = [line.strip() for line in open(filename).readlines() if line.strip()]
    if required and not lines:
        log_red("File data.txt is empty")
        sys.exit(1)
    return lines


def parse_line(line):
    parts = line.split("|", 1)
    init_data = parts[0].strip()
    wallet = parts[1].strip() if len(parts) > 1 else ""
    return init_data, wallet


def normalize_proxy(proxy_line):
    if not proxy_line:
        return None
    value = proxy_line.strip()
    if "://" in value:
        return value
    parts = value.split(":")
    if len(parts) == 4:
        host, port, user, password = parts
        return f"http://{user}:{password}@{host}:{port}"
    if len(parts) == 3:
        host, port, user = parts
        return f"http://{user}@{host}:{port}"
    return f"http://{value}"


def mask_proxy(proxy_url):
    try:
        value = proxy_url.split("://")[-1]
        after_at = value.split("@")[-1]
        host_part = after_at.split(":")[0]
        port_part = after_at.split(":")[1] if ":" in after_at else ""
        octets = host_part.split(".")
        if len(octets) == 4:
            masked_host = f"{octets[0]}*****{octets[3]}"
        elif len(host_part) > 4:
            masked_host = f"{host_part[:2]}*****{host_part[-2:]}"
        else:
            masked_host = "***"
        suffix = f":{port_part}" if port_part else ""
        return f"http://user:pass@{masked_host}{suffix}"
    except Exception:
        return "http://user:pass@***:***"


def build_headers(init_data, device_id):
    fingerprint = {
        "userAgent": USER_AGENT,
        "platform": "Linux armv8l",
        "language": "en-US",
        "screenResolution": "412x915",
        "timezone": "Asia/Jakarta",
        "tgPlatform": "android",
        "tgVersion": "9.6",
    }
    return {
        "accept": "application/json",
        "content-type": "application/json",
        "origin": BASE_URL,
        "referer": BASE_URL + "/",
        "user-agent": USER_AGENT,
        "x-telegram-data": init_data,
        "x-device-id": device_id,
        "x-device-fingerprint": json.dumps(fingerprint, separators=(",", ":")),
        "x-tg-platform": "android",
    }


def error_message(payload):
    if isinstance(payload, dict):
        message = payload.get("message") or payload.get("error")
        if message:
            return str(message)
    return ""


def payload_flag(payload, key):
    return isinstance(payload, dict) and bool(payload.get(key))


def busy_error(status, payload):
    if status in BUSY_STATUS:
        return True
    message = error_message(payload).lower()
    return "busy" in message or "timeout" in message


async def api_call(session, method, path, headers, body=None, proxy=None):
    url = f"{BASE_URL}{path}"
    last_status = 0
    last_payload = None
    attempts = CALL_ATTEMPTS if method == "POST" else 2
    for attempt in range(1, attempts + 1):
        try:
            request = session.request(
                method,
                url,
                headers=headers,
                json=body,
                proxy=proxy,
                timeout=aiohttp.ClientTimeout(total=30),
            )
            async with request as response:
                last_status = response.status
                text = await response.text()
                try:
                    last_payload = json.loads(text)
                except Exception:
                    last_payload = None
                if response.status < 400 or not busy_error(response.status, last_payload):
                    return last_status, last_payload
        except Exception:
            last_status = 0
            last_payload = None
        if attempt < attempts:
            await asyncio.sleep(CALL_RETRY_SECONDS * attempt)
    return last_status, last_payload


async def authenticate(session, headers, init_data, proxy):
    body = {"initData": init_data}
    if REF_CODE:
        body["startParam"] = REF_CODE
    status, payload = await api_call(session, "POST", "/api/auth/telegram", headers, body, proxy)
    if status == 200 and isinstance(payload, dict):
        return payload
    return None


async def fetch_json(session, headers, path, proxy):
    status, payload = await api_call(session, "GET", path, headers, None, proxy)
    if status == 200 and isinstance(payload, dict):
        return payload
    return {}


async def watch_network(session, headers, settings, user, proxy, ad_type, label, counter):
    if settings.get(f"{ad_type}Enabled") is False:
        return 0, 0, 0
    limit = int(settings.get(f"{ad_type}AdLimit") or 0)
    if limit <= 0 and ad_type == "adsgram":
        limit = int(settings.get("dailyAdLimit") or 0)
    if limit <= 0:
        return 0, 0, 0
    reward_per_ad = int(settings.get(f"{ad_type}RewardPerAd") or 0)
    watched = int(user.get(counter) or 0)
    remaining = max(limit - watched, 0)
    credited = 0
    unverified = 0
    for _ in range(remaining):
        session_id = str(uuid.uuid4())
        register_status, _ = await api_call(
            session,
            "POST",
            "/api/ads/register-session",
            headers,
            {"sessionId": session_id, "adType": ad_type, "context": "ads_watch"},
            proxy,
        )
        if register_status != 200:
            break
        started = time.time()
        await asyncio.sleep(AD_SESSION_SECONDS)
        body = {
            "adType": ad_type,
            "sessionId": session_id,
            "backgroundDuration": int((time.time() - started) * 1000),
            "backgroundEntered": True,
            "sessionStart": int(started * 1000),
        }
        status, payload = await api_call(session, "POST", "/api/ads/watch", headers, body, proxy)
        if isinstance(payload, dict) and payload.get("errorType") == "cooldown":
            await asyncio.sleep(int(payload.get("secsLeft") or AD_COOLDOWN_SECONDS) + 1)
            continue
        if status != 200 or not payload_flag(payload, "success"):
            break
        fresh = await fetch_json(session, headers, "/api/auth/user", proxy)
        fresh_watched = int(fresh.get(counter) or 0)
        delta = fresh_watched - watched
        if delta <= 0:
            unverified += 1
            if unverified >= AD_UNVERIFIED_LIMIT:
                break
        else:
            reward = int(payload.get("rewardGems") or reward_per_ad)
            credited += reward * delta
            watched = fresh_watched
            log_green(f"{clean_text(label, 'Network')} ad {clean_text(watched, 0)} of {clean_text(limit, 0)} was verified and earned {clean_text(reward * delta, 0)} Gems")
        await asyncio.sleep(AD_COOLDOWN_SECONDS)
    return watched, credited, limit


async def claim_gigapub_links(session, headers, user, proxy):
    claimed = 0
    for task_id in GIGAPUB_LINK_TASKS:
        flag = f"gigapubShortLink{task_id}Claimed"
        if user.get(flag):
            continue
        start_status, start_payload = await api_call(
            session,
            "POST",
            "/api/tasks/gigapub-short-link/start",
            headers,
            {"taskId": task_id},
            proxy,
        )
        if start_status != 200 or not start_payload:
            continue
        await asyncio.sleep(LINK_VERIFY_SECONDS)
        claim_status, payload = await api_call(
            session,
            "POST",
            "/api/tasks/gigapub-short-link/claim",
            headers,
            {"taskId": task_id},
            proxy,
        )
        if claim_status != 200 or not payload_flag(payload, "success"):
            continue
        fresh = await fetch_json(session, headers, "/api/auth/user", proxy)
        if not fresh.get(flag):
            continue
        user = fresh
        reward = int(payload.get("reward") or 0)
        claimed += 1
        log_green(f"GigaPub link {clean_text(task_id, 0)} of {clean_text(len(GIGAPUB_LINK_TASKS), 0)} was verified and earned {clean_text(reward, 0)} Gold")
    return claimed, user


async def claim_tasks(session, headers, proxy):
    data = await fetch_json(session, headers, "/api/tasks/home/unified", proxy)
    tasks = data.get("tasks") or []
    claimed = 0
    for task in tasks:
        if task.get("verificationRequired"):
            continue
        task_id = task.get("id")
        if not task_id:
            continue
        click_status, _ = await api_call(
            session, "POST", f"/api/advertiser-tasks/{task_id}/click", headers, None, proxy
        )
        if click_status != 200:
            continue
        claim_status, payload = await api_call(
            session, "POST", f"/api/advertiser-tasks/{task_id}/claim", headers, None, proxy
        )
        if claim_status == 200 and payload_flag(payload, "success"):
            claimed += 1
    return claimed


async def claim_checkin(session, headers, proxy):
    status, payload = await api_call(
        session,
        "POST",
        "/api/missions/daily-checkin/claim",
        headers,
        {"doubleReward": False, "proof": None},
        proxy,
    )
    if status == 200 and payload_flag(payload, "success"):
        return "claimed", int(payload.get("reward") or 0)
    message = error_message(payload).lower()
    if "already" in message:
        return "already", 0
    return "failed", 0


async def claim_mystery_box(session, headers, proxy):
    session_id = str(uuid.uuid4())
    register_status, _ = await api_call(
        session,
        "POST",
        "/api/ads/register-session",
        headers,
        {"sessionId": session_id, "adType": "adsgram", "context": "mystery_box"},
        proxy,
    )
    if register_status != 200:
        return "failed", 0
    started = time.time()
    await asyncio.sleep(AD_SESSION_SECONDS)
    body = {
        "sessionId": session_id,
        "backgroundEntered": True,
        "backgroundDuration": int((time.time() - started) * 1000),
    }
    status, payload = await api_call(session, "POST", "/api/mystery-box", headers, body, proxy)
    if status == 200 and payload_flag(payload, "success"):
        return "claimed", int(payload.get("reward") or 0)
    message = error_message(payload).lower()
    if "already" in message or "not configured" in message:
        return "already", 0
    return "failed", 0


async def run_farming(session, headers, proxy):
    state = await fetch_json(session, headers, "/api/farming/state", proxy)
    if state.get("isComplete"):
        status, payload = await api_call(session, "POST", "/api/farming/claim", headers, {}, proxy)
        if status == 200 and payload_flag(payload, "success"):
            return "claimed", int(float(payload.get("amount") or 0))
        return "failed", 0
    if state.get("isActive"):
        return "running", int(state.get("remainingSeconds") or 0)
    boost_step = int(state.get("boostStep") or 0)
    max_boost = int(state.get("maxBoost") or 0)
    if boost_step < max_boost:
        await api_call(session, "POST", "/api/farming/boost", headers, {}, proxy)
    status, payload = await api_call(session, "POST", "/api/farming/start", headers, {}, proxy)
    if status == 200 and payload_flag(payload, "success"):
        return "started", int(payload.get("multiplier") or 1)
    return "failed", 0


async def claim_referrals(session, headers, proxy):
    status, payload = await api_call(session, "POST", "/api/referrals/claim", headers, None, proxy)
    if status == 200 and payload_flag(payload, "success"):
        amount = float(payload.get("amount") or 0)
        if amount > 0:
            return "claimed", amount
        return "empty", 0
    return "failed", 0


async def report_withdrawal(session, headers, user, settings, proxy):
    watched = int(user.get("adsWatchedToday") or 0)
    required_ads = int(settings.get("minimumAdsForWithdrawal") or 0)
    invites = int(user.get("friendsInvited") or 0)
    required_invites = int(settings.get("minimumInvitesForWithdrawal") or 0)
    minimum = int(settings.get("minimumCashoutGold") or 0)
    gold = float(user.get("balance") or 0)
    if gold < minimum:
        return "locked", minimum
    if watched < required_ads or invites < required_invites:
        return "locked", minimum
    return "ready", minimum


async def process_account(line, proxy, index):
    init_data, wallet = parse_line(line)
    if not init_data:
        log_red(f"Line {clean_text(index, 1)} does not hold a valid initData value")
        return

    device_id = uuid.uuid4().hex
    headers = build_headers(init_data, device_id)
    connector = aiohttp.TCPConnector(ssl=False)
    jar = aiohttp.CookieJar(unsafe=True)

    async with aiohttp.ClientSession(connector=connector, cookie_jar=jar) as session:
        profile = await authenticate(session, headers, init_data, proxy)
        if not profile:
            log_red(f"Sign in failed for account number {clean_text(index, 1)}")
            return

        name = profile.get("firstName") or profile.get("username") or "Unknown"
        log_green(f"Account {clean_text(name, 'Unknown')} signed in successfully")

        settings = await fetch_json(session, headers, "/api/app-settings", proxy)
        user = await fetch_json(session, headers, "/api/auth/user", proxy)
        if not user:
            user = profile
        log_yellow(f"Total balance is {clean_text(user.get('balance'), 0)} Gold")

        for ad_type, label, counter in AD_NETWORKS:
            watched, credited, limit = await watch_network(
                session, headers, settings, user, proxy, ad_type, label, counter
            )
            if credited > 0 or limit <= 0:
                continue
            if watched >= limit:
                log_green(f"{clean_text(label, 'Network')} ad quota was already filled for this account")
            else:
                log_yellow(f"{clean_text(label, 'Network')} rewards could not be verified on this run")

        links, user = await claim_gigapub_links(session, headers, user, proxy)
        if links <= 0:
            log_green("Every sponsored GigaPub link was already claimed")

        claimed = await claim_tasks(session, headers, proxy)
        if claimed > 0:
            log_green(f"{clean_text(claimed, 0)} {unit_word(claimed, 'advertiser reward was', 'advertiser rewards were')} claimed")
        else:
            log_green("Every eligible advertiser reward was already claimed")

        state, reward = await claim_checkin(session, headers, proxy)
        if state == "claimed":
            log_green(f"Daily check in reward of {clean_text(reward, 0)} Gems was claimed")
        elif state == "already":
            log_green("Daily check in was already claimed for this account")
        else:
            log_yellow("Daily check in could not be claimed on this run")

        state, reward = await claim_mystery_box(session, headers, proxy)
        if state == "claimed":
            log_green(f"Mystery box reward of {clean_text(reward, 0)} Gems was claimed")
        elif state == "already":
            log_green("Mystery box was already claimed for this account")
        else:
            log_yellow("Mystery box could not be claimed on this run")

        state, value = await run_farming(session, headers, proxy)
        if state == "claimed":
            log_green(f"Mining reward of {clean_text(value, 0)} Gold was claimed")
        elif state == "running":
            log_yellow(f"Mining is still running with {format_duration(value)} left")
        elif state == "started":
            log_green(f"Mining started with a {clean_text(value, 1)} times multiplier")
        else:
            log_yellow("Mining could not be started on this run")

        state, amount = await claim_referrals(session, headers, proxy)
        if state == "claimed":
            log_green(f"Referral bonus of {clean_text(amount, 0)} was claimed")
        elif state == "empty":
            log_green("No referral bonus is ready to collect yet")
        else:
            log_yellow("Referral bonus could not be claimed on this run")

        if wallet:
            save_status, _ = await api_call(
                session,
                "PATCH",
                "/api/wallet/payout",
                headers,
                {"currency": "TON", "address": wallet},
                proxy,
            )
            if save_status == 200:
                log_green("Payout wallet was saved for this account")

        state, minimum = await report_withdrawal(session, headers, user, settings, proxy)
        if state == "ready":
            log_green(f"Withdrawal of {clean_text(minimum, 0)} Gold can be requested now")
        else:
            log_yellow(f"Withdrawal is still locked until {clean_text(minimum, 0)} Gold")


async def main_async(accounts, proxies, sleep_secs):
    cycle = 1
    while True:
        log_yellow(f"Starting automation cycle number {clean_text(cycle, 0)}")

        for index, line in enumerate(accounts):
            if index > 0:
                print()

            proxy_line = proxies[index % len(proxies)] if proxies else None
            proxy_url = normalize_proxy(proxy_line) if proxy_line else None
            if proxy_url:
                log_yellow(f"Using proxy {mask_proxy(proxy_url)}")

            await process_account(line, proxy_url, index + 1)
            await asyncio.sleep(ROUND_PAUSE_SECONDS)

        log_yellow(f"Automation cycle number {clean_text(cycle, 0)} is complete")
        cycle += 1
        countdown(sleep_secs)
        show_banner(MY_PROJECT)


def countdown(seconds):
    for remaining in range(int(seconds), 0, -1):
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        rest = remaining % 60
        print(f"\r{YELLOW}{BOLD}Next cycle starts in {hours:02d}:{minutes:02d}:{rest:02d}{RESET}", end="", flush=True)
        time.sleep(1)
    print()


def main():
    show_banner(MY_PROJECT)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    config = load_config()
    sleep_secs = config.get("settings", {}).get("sleep_seconds", 900)
    accounts = load_lines("data.txt", True)
    proxies = load_lines("proxy.txt", False)
    asyncio.run(main_async(accounts, proxies, sleep_secs))


if __name__ == "__main__":
    main()
