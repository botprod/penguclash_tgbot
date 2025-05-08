import asyncio
from utils.pengu import Pengu
from utils.core import logger


async def start(thread: int, session_name: str, user_agent: str, proxy: [str, None]):
    """Start a thread for a Pengu account, handling login and waitlist checks."""
    pengu = Pengu(session_name=session_name, user_agent=user_agent, thread=thread, proxy=proxy)
    account = f"{session_name}.session"

    try:
        login_result = await pengu.login()
        if login_result is None:
            logger.error(f"Thread {thread} | {account} | Login failed: No result returned")
            return

        status, data = login_result
        if status:
            logger.success(f"Thread {thread} | {account} | Login successful")
            try:
                waitlist_status = await pengu.check_waitlist()
                if waitlist_status == "pending":
                    await pengu.claim_waitlist()
            except Exception as e:
                logger.error(f"Thread {thread} | {account} | Waitlist error: {e}")
                await asyncio.sleep(5)
        else:
            logger.error(f"Thread {thread} | {account} | Login failed: {data or 'Unknown error'}")

    except Exception as e:
        logger.error(f"Thread {thread} | {account} | Login error: {e}")
    finally:
        try:
            await pengu.logout()
            logger.debug(f"Thread {thread} | {account} | Logged out")
        except Exception as e:
            logger.warning(f"Thread {thread} | {account} | Logout error: {e}")
