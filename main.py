from utils.core.telegram import Accounts
from utils.starter import start
import asyncio
import os


async def main():
    print('PENGU CLASH')
    print("Soft's author: https://t.me/botpr0d\n")
    action = int(input("Select action:\n1. Start soft\n2. Create sessions\n\n> "))

    if not os.path.exists('sessions'): os.mkdir('sessions')
    if not os.path.exists('sessions/accounts.json'):
        with open("sessions/accounts.json", 'w') as f:
            f.write("[]")

    if action == 2:
        await Accounts().create_sessions()

    if action == 1:
        accounts = await Accounts().get_accounts()
        tasks = []
        for thread, account in enumerate(accounts):
            session_name, user_agent, proxy = account.values()
            tasks.append(asyncio.create_task(
                start(session_name=session_name, user_agent=user_agent, thread=thread, proxy=proxy)))

        await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
