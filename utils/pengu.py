import json
import random
import urllib.parse
import os
from utils.core import logger
from pyrogram import Client
from pyrogram.raw.functions.messages import RequestWebView
import asyncio
from aiohttp_socks import ProxyConnector
import aiohttp
from data import config


def parse_proxy(proxy_str):
    """Parse a proxy string into a Pyrogram-compatible dictionary."""
    if not proxy_str:
        logger.debug("No proxy string provided, returning None")
        return None
    try:
        parsed = urllib.parse.urlparse(proxy_str)
        if not parsed.scheme or not parsed.hostname or not parsed.port:
            raise ValueError("Invalid proxy format")
        proxy_dict = {
            "scheme": parsed.scheme,
            "hostname": parsed.hostname,
            "port": parsed.port,
            "username": parsed.username or "",
            "password": parsed.password or ""
        }
        logger.debug(f"Parsed proxy: {proxy_dict}")
        return proxy_dict
    except Exception as ex:
        logger.error(f"Failed to parse proxy {proxy_str}: {ex}")
        return None


class Pengu:
    def __init__(self, thread: int, session_name: str, user_agent: str, proxy: [str, None]):
        self.headers = None
        self.useragent = user_agent
        self.account = session_name + '.session'
        self.thread = thread
        self.tg_init_data = None
        self.proxy = proxy if proxy else None
        logger.debug(
            f"Thread {self.thread} | {self.account} | Initializing Pengu with user_agent: {user_agent}, proxy: {proxy}")
        connector = ProxyConnector.from_url(self.proxy) if proxy else aiohttp.TCPConnector(verify_ssl=False)
        self.client = Client(
            name=session_name,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            workdir=config.WORKDIR,
            proxy=parse_proxy(proxy),
            lang_code='en'
        )
        self.session = aiohttp.ClientSession(trust_env=True, connector=connector)
        logger.debug(f"Thread {self.thread} | {self.account} | HTTP session initialized")

    async def logout(self):
        logger.debug(f"Thread {self.thread} | {self.account} | Attempting to close HTTP session")
        try:
            await self.session.close()
            logger.info(f"Thread {self.thread} | {self.account} | HTTP session closed successfully")
        except Exception as e:
            logger.warning(f"Thread {self.thread} | {self.account} | Error closing HTTP session: {e}")

    async def login(self):
        logger.debug(f"Thread {self.thread} | {self.account} | Starting login process")
        await asyncio.sleep(random.uniform(*config.DELAYS['ACCOUNT']))
        logger.debug(
            f"Thread {self.thread} | {self.account} | Slept for {random.uniform(*config.DELAYS['ACCOUNT']):.2f} seconds")

        query = await self.get_tg_web_data()
        if query is None:
            logger.error(f"Thread {self.thread} | {self.account} | Failed to get tg_web_data")
            return False, "Failed to get Telegram web data"
        logger.debug(f"Thread {self.thread} | {self.account} | Retrieved tg_web_data: {query}")

        self.tg_init_data = query
        self.headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://api.pudgy-clash.elympics.ai',
            'priority': 'u=1, i',
            'referer': 'https://api.pudgy-clash.elympics.ai/',
            'sec-ch-ua': '"Microsoft Edge";v="136", "Microsoft Edge WebView2";v="136", "Not.A/Brand";v="99", "Chromium";v="136"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': self.useragent,
        }
        logger.debug(f"Thread {self.thread} | {self.account} | Initialized headers: {self.headers}")

        # Parse the init data to get required fields
        init_data = urllib.parse.parse_qs(query)
        logger.debug(f"Thread {self.thread} | {self.account} | Parsed init data: {init_data}")
        user_data = json.loads(init_data['user'][0])
        logger.debug(f"Thread {self.thread} | {self.account} | User data: {user_data}")

        # Prepare the login request data
        login_data = {
            "typedData": json.dumps({
                "id": "6e4cf20b-7599-40ce-8db1-ffe00d6e71cc",
                "name": "Pengu Clash"
            }),
            "initDataRaw": query,
            "invitationCode": config.REF_LINK,
            "gameId": "6e4cf20b-7599-40ce-8db1-ffe00d6e71cc"
        }
        logger.debug(f"Thread {self.thread} | {self.account} | Login request data: {login_data}")

        try:
            async with aiohttp.ClientSession() as session:
                logger.debug(
                    f"Thread {self.thread} | {self.account} | Sending login request to https://api.elympics.cc/v2/auth/user/telegram-auth-v2")
                async with session.post(
                        'https://api.elympics.cc/v2/auth/user/telegram-auth-v2',
                        headers=self.headers,
                        json=login_data,
                        ssl=False
                ) as response:
                    logger.debug(f"Thread {self.thread} | {self.account} | Login response status: {response.status}")
                    response_text = await response.text()
                    logger.debug(f"Thread {self.thread} | {self.account} | Login response body: {response_text}")
                    if response.status == 200:
                        response_json = await response.json()
                        logger.debug(f"Thread {self.thread} | {self.account} | Login response JSON: {response_json}")
                        if "jwtToken" in response_json:
                            self.jwt_token = response_json["jwtToken"]
                            self.user_id = response_json["userId"]
                            self.nickname = response_json["nickname"]
                            self.avatar_url = response_json["avatarUrl"]
                            self.headers["authorization"] = f"Bearer {self.jwt_token}"
                            logger.info(
                                f"Thread {self.thread} | {self.account} | JWT token received, user_id: {self.user_id}, nickname: {self.nickname}")
                            logger.debug(
                                f"Thread {self.thread} | {self.account} | Updated headers with authorization: {self.headers}")

                            waitlist_status = await self.check_waitlist()
                            logger.info(f"Thread {self.thread} | {self.account} | Waitlist status: {waitlist_status}")
                            if waitlist_status == "not-joined":
                                logger.debug(
                                    f"Thread {self.thread} | {self.account} | Waitlist not joined, proceeding to join")
                                await self.join_waitlist()
                                await asyncio.sleep(3)
                                await self.process_tasks()

                            if waitlist_status == "pending":
                                logger.debug(
                                    f"Thread {self.thread} | {self.account} | Waitlist pending, proceeding to claim")
                                await self.claim_waitlist()
                                await asyncio.sleep(3)
                                await self.process_tasks()

                            logger.success(f"Thread {self.thread} | {self.account} | Login successful")
                            return True, {"user_id": self.user_id, "nickname": self.nickname}
                        else:
                            logger.error(f"Thread {self.thread} | {self.account} | JWT token not found in response")
                            return False, "No JWT token in response"
                    else:
                        logger.error(
                            f"Thread {self.thread} | {self.account} | Login HTTP error {response.status}: {response_text}")
                        return False, f"HTTP {response.status}: {response_text}"
        except Exception as e:
            logger.error(f"Thread {self.thread} | {self.account} | Login error: {e}")
            return False, str(e)

    async def check_waitlist(self):
        logger.debug(f"Thread {self.thread} | {self.account} | Checking waitlist status")
        try:
            async with aiohttp.ClientSession() as session:
                logger.debug(
                    f"Thread {self.thread} | {self.account} | Sending GET request to https://api.pudgy-clash.elympics.ai/api/waitlist with headers: {self.headers}")
                async with session.get(
                        'https://api.pudgy-clash.elympics.ai/api/waitlist',
                        headers=self.headers,
                        ssl=False
                ) as response:
                    logger.debug(
                        f"Thread {self.thread} | {self.account} | Waitlist check response status: {response.status}")
                    response_text = await response.text()
                    logger.debug(
                        f"Thread {self.thread} | {self.account} | Waitlist check response body: {response_text}")
                    if response.status == 200:
                        response_json = await response.json()
                        logger.debug(
                            f"Thread {self.thread} | {self.account} | Waitlist check response JSON: {response_json}")
                        status = response_json.get("status", "unknown")
                        logger.info(f"Thread {self.thread} | {self.account} | Waitlist status: {status}")
                        return status
                    logger.error(
                        f"Thread {self.thread} | {self.account} | Waitlist check HTTP error {response.status}: {response_text}")
                    return "unknown"
        except Exception as e:
            logger.error(f"Thread {self.thread} | {self.account} | Waitlist check error: {e}")
            return "unknown"

    async def join_waitlist(self):
        join_data = {
            "elympicsAvatarUrl": self.avatar_url,
            "elympicsNickname": self.nickname,
            "telegramNickname": self.nickname,
            "telegramUserId": self.user_id,
            "invitationCode": config.REF_LINK
        }
        logger.debug(f"Thread {self.thread} | {self.account} | Joining waitlist with data: {join_data}")

        try:
            async with aiohttp.ClientSession() as session:
                logger.debug(
                    f"Thread {self.thread} | {self.account} | Sending POST request to https://api.pudgy-clash.elympics.ai/api/waitlist/join with headers: {self.headers}")
                async with session.post(
                        'https://api.pudgy-clash.elympics.ai/api/waitlist/join',
                        headers=self.headers,
                        json=join_data,
                        ssl=False
                ) as response:
                    logger.debug(
                        f"Thread {self.thread} | {self.account} | Join waitlist response status: {response.status}")
                    response_text = await response.text()
                    logger.debug(
                        f"Thread {self.thread} | {self.account} | Join waitlist response body: {response_text}")
                    if response.status == 200:
                        logger.success(f"Thread {self.thread} | {self.account} | Successfully joined waitlist")
                    else:
                        logger.error(
                            f"Thread {self.thread} | {self.account} | Failed to join waitlist: HTTP {response.status}: {response_text}")
        except Exception as e:
            logger.error(f"Thread {self.thread} | {self.account} | Join waitlist error: {e}")

    async def claim_waitlist(self):
        logger.debug(f"Thread {self.thread} | {self.account} | Claiming waitlist")
        try:
            async with aiohttp.ClientSession() as session:
                logger.debug(
                    f"Thread {self.thread} | {self.account} | Sending POST request to https://api.pudgy-clash.elympics.ai/api/waitlist/claim with headers: {self.headers}")
                async with session.post(
                        'https://api.pudgy-clash.elympics.ai/api/waitlist/claim',
                        headers=self.headers,
                        json={},
                        ssl=False
                ) as response:
                    logger.debug(
                        f"Thread {self.thread} | {self.account} | Claim waitlist response status: {response.status}")
                    response_text = await response.text()
                    logger.debug(
                        f"Thread {self.thread} | {self.account} | Claim waitlist response body: {response_text}")
                    if response.status == 200:
                        logger.success(f"Thread {self.thread} | {self.account} | Successfully claimed waitlist")
                    else:
                        logger.error(
                            f"Thread {self.thread} | {self.account} | Failed to claim waitlist: HTTP {response.status}: {response_text}")
        except Exception as e:
            logger.error(f"Thread {self.thread} | {self.account} | Claim waitlist error: {e}")

    async def complete_twitter(self, retries=3, delay=5):
        logger.debug(
            f"Thread {self.thread} | {self.account} | Attempting to complete Twitter task with {retries} retries, delay {delay}s")
        for attempt in range(retries):
            logger.info(f"Thread {self.thread} | {self.account} | Twitter task attempt {attempt + 1}/{retries}")
            try:
                async with aiohttp.ClientSession() as session:
                    logger.debug(
                        f"Thread {self.thread} | {self.account} | Sending POST request to https://api.pudgy-clash.elympics.ai/api/waitlist/complete/twitter with headers: {self.headers}")
                    async with session.post(
                            'https://api.pudgy-clash.elympics.ai/api/waitlist/complete/twitter',
                            headers=self.headers,
                            json={},
                            ssl=False
                    ) as response:
                        logger.debug(
                            f"Thread {self.thread} | {self.account} | Twitter task response status: {response.status}")
                        response_text = await response.text()
                        logger.debug(
                            f"Thread {self.thread} | {self.account} | Twitter task response body: {response_text}")
                        if response.status == 200:
                            logger.success(
                                f"Thread {self.thread} | {self.account} | Successfully completed Twitter task")
                            return True
                        else:
                            logger.error(
                                f"Thread {self.thread} | {self.account} | Failed to complete Twitter task: HTTP {response.status}: {response_text}")
                            if response.status == 400 and attempt < retries - 1:
                                logger.info(
                                    f"Thread {self.thread} | {self.account} | Retrying Twitter task in {delay} seconds...")
                                await asyncio.sleep(delay)
                            else:
                                return False
            except Exception as e:
                logger.error(f"Thread {self.thread} | {self.account} | Complete Twitter task error: {e}")
                if attempt < retries - 1:
                    logger.info(f"Thread {self.thread} | {self.account} | Retrying Twitter task in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    return False
        logger.error(f"Thread {self.thread} | {self.account} | Twitter task failed after {retries} attempts")
        return False

    async def complete_telegram(self, retries=3, delay=5):
        logger.debug(
            f"Thread {self.thread} | {self.account} | Attempting to complete Telegram task with {retries} retries, delay {delay}s")
        for attempt in range(retries):
            logger.info(f"Thread {self.thread} | {self.account} | Telegram task attempt {attempt + 1}/{retries}")
            try:
                async with aiohttp.ClientSession() as session:
                    logger.debug(
                        f"Thread {self.thread} | {self.account} | Sending POST request to https://api.pudgy-clash.elympics.ai/api/waitlist/complete/telegram with headers: {self.headers}")
                    async with session.post(
                            'https://api.pudgy-clash.elympics.ai/api/waitlist/complete/telegram',
                            headers=self.headers,
                            json={},
                            ssl=False
                    ) as response:
                        logger.debug(
                            f"Thread {self.thread} | {self.account} | Telegram task response status: {response.status}")
                        response_text = await response.text()
                        logger.debug(
                            f"Thread {self.thread} | {self.account} | Telegram task response body: {response_text}")
                        if response.status == 200:
                            logger.success(
                                f"Thread {self.thread} | {self.account} | Successfully completed Telegram task")
                            return True
                        else:
                            logger.error(
                                f"Thread {self.thread} | {self.account} | Failed to complete Telegram task: HTTP {response.status}: {response_text}")
                            if response.status == 400 and attempt < retries - 1:
                                logger.info(
                                    f"Thread {self.thread} | {self.account} | Retrying Telegram task in {delay} seconds...")
                                await asyncio.sleep(delay)
                            else:
                                return False
            except Exception as e:
                logger.error(f"Thread {self.thread} | {self.account} | Complete Telegram task error: {e}")
                if attempt < retries - 1:
                    logger.info(f"Thread {self.thread} | {self.account} | Retrying Telegram task in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    return False
        logger.error(f"Thread {self.thread} | {self.account} | Telegram task failed after {retries} attempts")
        return False

    async def process_tasks(self):
        logger.debug(f"Thread {self.thread} | {self.account} | Processing tasks")
        # Fetch waitlist data to check task status
        waitlist_data = await self.get_waitlist_data()
        if not waitlist_data:
            logger.error(f"Thread {self.thread} | {self.account} | Failed to fetch waitlist data for task processing")
            return

        # Check tasks in waitlist data
        tasks = waitlist_data.get("tasks", [])
        logger.debug(f"Thread {self.thread} | {self.account} | Waitlist tasks: {tasks}")
        for task in tasks:
            task_type = task.get("type")
            progress = task.get("progress", {})
            is_completed = "completed" in progress
            logger.info(
                f"Thread {self.thread} | {self.account} | Task {task_type} status: {'completed' if is_completed else 'todo'}")

            if not is_completed:
                if task_type == "followTwitter":
                    logger.info(
                        f"Thread {self.thread} | {self.account} | Twitter task is in 'todo' state, attempting to complete...")
                    await self.complete_twitter()
                elif task_type == "followAnnouncementsChannel":
                    logger.info(
                        f"Thread {self.thread} | {self.account} | Telegram task is in 'todo' state, attempting to complete...")
                    await self.complete_telegram()

        # Fetch waitlist data again to save updated status
        logger.debug(f"Thread {self.thread} | {self.account} | Fetching waitlist data again after task processing")
        await self.get_waitlist_data()

    async def get_waitlist_data(self):
        logger.debug(f"Thread {self.thread} | {self.account} | Retrieving waitlist data")
        try:
            async with aiohttp.ClientSession() as session:
                logger.debug(
                    f"Thread {self.thread} | {self.account} | Sending GET request to https://api.pudgy-clash.elympics.ai/api/waitlist with headers: {self.headers}")
                async with session.get(
                        'https://api.pudgy-clash.elympics.ai/api/waitlist',
                        headers=self.headers,
                        ssl=False
                ) as response:
                    logger.debug(
                        f"Thread {self.thread} | {self.account} | Waitlist data response status: {response.status}")
                    response_text = await response.text()
                    logger.debug(
                        f"Thread {self.thread} | {self.account} | Waitlist data response body: {response_text}")
                    if response.status == 200:
                        response_json = await response.json()
                        invite_code = response_json.get("inviteCode", "unknown")
                        logger.success(
                            f"Thread {self.thread} | {self.account} | Successfully retrieved waitlist data with invite code: {invite_code}")
                        logger.debug(f"Thread {self.thread} | {self.account} | Waitlist data JSON: {response_json}")

                        # Prepare account data to save
                        account_data = {
                            "account": self.account,
                            "user_id": self.user_id,
                            "nickname": self.nickname,
                            "invite_code": invite_code,
                            "waitlist_status": response_json.get("status", "unknown"),
                            "reward": response_json.get("reward", "unknown")
                        }
                        logger.debug(f"Thread {self.thread} | {self.account} | Account data to save: {account_data}")

                        # Save to file
                        output_dir = "output"
                        os.makedirs(output_dir, exist_ok=True)
                        output_file = os.path.join(output_dir, "accounts_data.json")
                        logger.debug(f"Thread {self.thread} | {self.account} | Saving account data to {output_file}")

                        # Thread-safe file writing
                        try:
                            # Read existing data
                            existing_data = []
                            if os.path.exists(output_file):
                                with open(output_file, 'r', encoding='utf-8') as f:
                                    try:
                                        existing_data = json.load(f)
                                        if not isinstance(existing_data, list):
                                            existing_data = [existing_data]
                                        logger.debug(
                                            f"Thread {self.thread} | {self.account} | Loaded existing data: {existing_data}")
                                    except json.JSONDecodeError:
                                        logger.warning(
                                            f"Thread {self.thread} | {self.account} | Existing JSON file is corrupted, starting with empty data")
                                        existing_data = []

                            # Append new data
                            existing_data.append(account_data)
                            logger.debug(
                                f"Thread {self.thread} | {self.account} | Appended new data, total entries: {len(existing_data)}")

                            # Write back to file
                            with open(output_file, 'w', encoding='utf-8') as f:
                                json.dump(existing_data, f, indent=4, ensure_ascii=False)
                            logger.success(
                                f"Thread {self.thread} | {self.account} | Saved account data to {output_file}")
                        except Exception as e:
                            logger.error(f"Thread {self.thread} | {self.account} | Failed to save account data: {e}")

                        return response_json
                    else:
                        logger.error(
                            f"Thread {self.thread} | {self.account} | Failed to retrieve waitlist data: HTTP {response.status}: {response_text}")
                        return None
        except Exception as e:
            logger.error(f"Thread {self.thread} | {self.account} | Get waitlist data error: {e}")
            return None

    async def get_tg_web_data(self):
        logger.debug(f"Thread {self.thread} | {self.account} | Retrieving Telegram web data")
        try:
            logger.debug(
                f"Thread {self.thread} | {self.account} | Connecting to Telegram with timeout {config.TIMEOUT}s")
            connected = await asyncio.wait_for(self.client.connect(), timeout=config.TIMEOUT)
            if not connected:
                logger.error(f"Thread {self.thread} | {self.account} | Failed to connect to Telegram")
                return None

            try:
                logger.debug(
                    f"Thread {self.thread} | {self.account} | Sending /start command with invite-{config.REF_LINK}")
                await self.client.send_message("pengu_clash_bot", f'/start invite-{config.REF_LINK}')
                peer = await self.client.resolve_peer('pengu_clash_bot')
                logger.debug(f"Thread {self.thread} | {self.account} | Resolved peer for pengu_clash_bot: {peer}")
                await asyncio.sleep(3)
                logger.debug(f"Thread {self.thread} | {self.account} | Slept for 3 seconds before requesting web view")
                web_view = await self.client.invoke(RequestWebView(
                    peer=peer,
                    bot=peer,
                    platform='android',
                    from_bot_menu=False,
                    start_param=f"invite-{config.REF_LINK}",
                    url='https://api.pudgy-clash.elympics.ai'
                ))
                auth_url = web_view.url
                logger.debug(f"Thread {self.thread} | {self.account} | Web view auth URL: {auth_url}")
                query = urllib.parse.unquote(auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0])
                logger.debug(f"Thread {self.thread} | {self.account} | Got tg_web_data: {query}")
                return query
            finally:
                logger.debug(f"Thread {self.thread} | {self.account} | Disconnecting from Telegram")
                await self.client.disconnect()
                logger.info(f"Thread {self.thread} | {self.account} | Disconnected from Telegram")
        except asyncio.TimeoutError:
            logger.error(f"Thread {self.thread} | {self.account} | Timeout connecting to Telegram")
            return None
        except Exception as e:
            logger.error(f"Thread {self.thread} | {self.account} | Error in get_tg_web_data: {e}")
            return None
