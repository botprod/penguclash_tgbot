# Pengu Clash Bot

Bot for [@pengu_clash_bot](https://t.me/pengu_clash_bot?start=invite-avo5rj)

[Telegram](https://t.me/botpr0d "BOTPROD")<br>
[www.botprod.ru](https://www.botprod.ru "site")

## Functionality

| Functional                               | Supported |
|------------------------------------------|:---------:|
| Multithreading                           |     ✅     |
| Binding a proxy to a session             |     ✅     |
| Random sleep time between accounts; hits |     ✅     |
| Support pyrogram .session                |     ✅     |
| Get login links for all accounts         |     ✅     |

## Settings data/config.py

| Setting               | Description                                                                     |
|-----------------------|---------------------------------------------------------------------------------|
| **API_ID / API_HASH** | Platform data from which to launch a Telegram session                           |
| **DELAYS**            | Delay between connections to accounts (the more accounts, the longer the delay) |
| **LOG_LEVEL**         | Logging level                                                                   |
| **REF_LINK**          | Your referal link                                                               |
| **WORKDIR**           | directory with session                                                          |
| **TIMEOUT**           | timeout in seconds for checking accounts on valid                               |

## Requirements

- Python 3.9 (you can install it [here](https://www.python.org/downloads/release/python-390/))
- Telegram API_ID and API_HASH (you can get them [here](https://my.telegram.org/auth))

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the bot:
   ```bash
   python main.py
   ```
