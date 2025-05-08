import asyncio
import os
import urllib.parse
from pyrogram import Client
from data import config
from utils.core import logger, load_from_json, save_list_to_file, save_to_json, agents


def parse_proxy(proxy_str):
    """Parse a proxy string into a Pyrogram-compatible dictionary."""
    if not proxy_str:
        return None
    try:
        parsed = urllib.parse.urlparse(proxy_str)
        if not parsed.scheme or not parsed.hostname or not parsed.port:
            raise ValueError("Invalid proxy format")
        return {
            "scheme": parsed.scheme,
            "hostname": parsed.hostname,
            "port": parsed.port,
            "username": parsed.username or "",
            "password": parsed.password or ""
        }
    except Exception as ex:
        logger.error(f"Failed to parse proxy {proxy_str}: {ex}")
        return None


class Accounts:
    def __init__(self):
        self.workdir = config.WORKDIR
        self.api_id = config.API_ID
        self.api_hash = config.API_HASH

    @staticmethod
    def get_available_accounts(sessions: list):
        """Retrieve accounts from accounts.json that match session files."""
        accounts_from_json = load_from_json('sessions/accounts.json')
        if not accounts_from_json:
            logger.warning("No accounts found in sessions/accounts.json")
            return []

        available_accounts = []
        for session in sessions:
            for saved_account in accounts_from_json:
                if saved_account['session_name'] == session:
                    available_accounts.append(saved_account)
                    break

        return available_accounts

    def parse_sessions(self):
        """List all session files in the workdir."""
        sessions = [
            file.replace(".session", "")
            for file in os.listdir(self.workdir)
            if file.endswith(".session")
        ]
        logger.info(f"Found {len(sessions)} session(s)")
        return sessions

    async def check_valid_account(self, account: dict):
        """Check if an account is valid by connecting and fetching user info."""
        session_name = account.get('session_name', 'Unknown')
        user_agent = account.get('user_agent', None)
        proxy = account.get('proxy', None)
        logger.debug(f"Checking account: {session_name}, UA: {user_agent}, Proxy: {proxy}")

        proxy_dict = parse_proxy(proxy)
        if proxy and not proxy_dict:
            logger.error(f"Invalid proxy for {session_name}, skipping")
            return None

        client = None
        try:
            client = Client(
                name=session_name,
                api_id=self.api_id,
                api_hash=self.api_hash,
                workdir=self.workdir,
                proxy=proxy_dict
            )

            logger.debug(f"Attempting to connect for {session_name}")
            connected = await asyncio.wait_for(client.connect(), timeout=config.TIMEOUT)
            if connected:
                try:
                    me = await client.get_me()
                    logger.debug(f"Account {session_name} is valid (User: {me.username or me.phone_number})")
                    return account
                except Exception as ex:
                    logger.error(f"Failed to get user info for {session_name}: {ex}")
                    return None
            else:
                logger.warning(f"Connection failed for {session_name}")
                return None

        except asyncio.TimeoutError:
            logger.error(f"Timeout error for {session_name}: Connection timed out")
            return None
        except Exception as ex:
            logger.error(f"Error for {session_name}: {ex}")
            return None
        finally:
            if client is not None:
                try:
                    await client.disconnect()
                    logger.debug(f"Disconnected client for {session_name}")
                except Exception as ex:
                    logger.warning(f"Error during disconnect for {session_name}: {ex}")

    async def check_valid_accounts(self, accounts: list):
        """Check validity of multiple accounts concurrently."""
        logger.debug("Checking accounts for validity...")
        tasks = [self.check_valid_account(account) for account in accounts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_accounts = []
        invalid_accounts = []
        for account, result in zip(accounts, results):
            if isinstance(result, Exception):
                logger.error(f"Exception for {account.get('session_name', 'Unknown')}: {result}")
                invalid_accounts.append(account)
            elif result:
                valid_accounts.append(result)
            else:
                invalid_accounts.append(account)

        logger.success(f"Valid accounts: {len(valid_accounts)}; Invalid: {len(invalid_accounts)}")
        return valid_accounts, invalid_accounts

    async def get_accounts(self):
        """Retrieve valid accounts from session files."""
        sessions = self.parse_sessions()
        available_accounts = self.get_available_accounts(sessions)

        if not available_accounts:
            logger.warning("No available accounts found")
            return []

        logger.success(f"Found {len(available_accounts)} available account(s)")
        valid_accounts, invalid_accounts = await self.check_valid_accounts(available_accounts)

        if invalid_accounts:
            save_list_to_file(f"{self.workdir}/invalid_accounts.txt", invalid_accounts)
            logger.info(f"Saved {len(invalid_accounts)} invalid account(s) to {self.workdir}/invalid_accounts.txt")

        if not valid_accounts:
            logger.warning("No valid accounts found. Consider creating new sessions.")
        return valid_accounts

    async def create_sessions(self):
        """Create new Telegram sessions interactively."""
        while True:
            session_name = input('\nInput the name of the session (press Enter to exit): ').strip()
            if not session_name:
                return

            proxy = input("Input the proxy (login:password@ip:port, press Enter for no proxy): ").strip()
            proxy_dict = parse_proxy(proxy) if proxy else None
            if proxy and not proxy_dict:
                logger.error("Invalid proxy format, try again")
                continue

            user_agent = agents.generate_random_user_agent()
            phone_number = input("Input the phone number (e.g., +1234567890): ").strip()
            phone_number = '+' + phone_number.lstrip('+') if phone_number else ''

            if not phone_number or not phone_number.startswith('+'):
                logger.error("Invalid phone number format")
                continue

            try:
                client = Client(
                    name=session_name,
                    api_id=self.api_id,
                    api_hash=self.api_hash,
                    workdir=self.workdir,
                    phone_number=phone_number,
                    proxy=proxy_dict,
                    lang_code='en'
                )

                async with client:
                    me = await client.get_me()
                    account_data = {
                        "session_name": session_name,
                        "user_agent": user_agent,
                        "proxy": proxy
                    }
                    save_to_json(f"{self.workdir}/accounts.json", dict_=account_data)
                    logger.success(f"Added account {me.username or me.phone_number} ({me.first_name})")

            except Exception as ex:
                logger.error(f"Failed to create session {session_name}: {ex}")
                continue
