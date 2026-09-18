<div align="center">

<img width="100%" alt="header" src="https://capsule-render.vercel.app/api?type=waving&height=210&text=Axionet%20Bot&fontAlign=50&fontAlignY=36&fontSize=56&desc=Ads%20%7C%20Tasks%20%7C%20Check-in%20%7C%20Mystery%20Box%20%7C%20Farming%20%7C%20Referral&descAlign=50&descAlignY=58"/>

<img alt="typing" src="https://readme-typing-svg.demolab.com?font=Inter&size=18&duration=3000&pause=650&center=true&vCenter=true&width=900&lines=Auto+Ads+%7C+4+Networks+Until+Daily+Limit;Auto+GigaPub+Link+Tasks+%7C+Claim+Gold;Auto+Advertiser+Tasks+%7C+Click+%26+Claim;Auto+Daily+Check-in+%7C+Earn+Gems;Auto+Mystery+Box+%7C+Ad+Verified+Claim;Auto+Farming+%7C+Boost+%2F+Start+%2F+Claim;Auto+Referral+Claim+%7C+TON+Wallet+Payout"/>

<p>
  <img alt="python" src="https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white"/>
  <img alt="platform" src="https://img.shields.io/badge/Platform-Axionet%20Miniapp-111111"/>
  <img alt="multi-account" src="https://img.shields.io/badge/Multi--Account-Supported-111111"/>
  <img alt="proxy" src="https://img.shields.io/badge/Proxy-Supported-111111"/>
  <img alt="author" src="https://img.shields.io/badge/by-Yuurisandesu-111111"/>
</p>

<p>
  <b>Axionet Bot</b> is a full automation bot for the Axionet Telegram Miniapp.<br/>
  It handles the complete cycle: watching ads across four networks until each hits its daily limit, claiming GigaPub link task rewards, claiming all eligible advertiser task rewards, the daily check-in, the mystery box via ad session, farming by applying available boosts, starting a session, and claiming when complete, collecting referral bonuses, saving the TON payout wallet, and reporting withdrawal eligibility, all running automatically across multiple accounts with proxy support and a live countdown between cycles.<br/>
  Built and distributed by <b>Yuurisandesu</b>.
</p>

</div>

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Features](#features)
- [File Structure](#file-structure)
- [Disclaimer](#disclaimer)

---

## Requirements

- Python `3.12+`
- Git

---

## Installation

**Clone the repository:**

```bash
git clone https://github.com/Yuurisan-N1/Axionet-Miniapp.git
cd Axionet-Miniapp
```

**Install dependencies:**

```bash
pip install aiohttp yuurisan
```

---

## Configuration

### 1. Accounts (data.txt)

Fill `data.txt` with one entry per line. Each line can be just `initData`, or `initData` followed by a TON wallet address separated by `|`:

```
user=%7B%22id%22...&hash=abc123
user=%7B%22id%22...&hash=def456|UQAbc...yourwalletaddress
```

If a wallet address is included, the bot saves it as the payout wallet for that account on every cycle. Lines without a wallet address skip the wallet save step.

> `initData` can be obtained from the browser DevTools when opening Axionet on Telegram Web.

### 2. Proxy (proxy.txt)

Fill `proxy.txt` with proxies, one per line (optional, leave empty to run without proxy):

```
host:port
host:port:user:pass
http://user:pass@host:port
```

Proxies are assigned to accounts by index in round-robin order.

### 3. Bot Settings (config.json)

`sleep_seconds` controls how many seconds the bot waits between cycles. If `config.json` is missing, the bot falls back to a default of `900` seconds.

---

## Running the Bot

```bash
python bot.py
```

Press `Ctrl+C` at any time to stop the bot cleanly.

---

## Features

### Auto Ads
The bot watches ads across four networks: AdsGram, MonetaG, GigaPub, and USL Ads. For each network, it reads the daily limit and watched count from the server settings, calculates remaining slots, and claims each one. Each slot registers an ad session, waits the required duration, then submits a watch completion request. Cooldown responses are respected automatically. Unverified results are tolerated up to 3 times before the network is skipped. Each verified slot logs the network name, count, and Gems earned.

### GigaPub Link Tasks
The bot claims up to three GigaPub sponsored link rewards. For each unclaimed link, it sends a start request, waits 4 seconds, then claims the reward. Each claimed link logs the task number and Gold earned.

### Auto Advertiser Tasks
The bot fetches all advertiser tasks and claims each eligible one. Tasks requiring manual verification are skipped. For each valid task, it sends a click request followed by a claim request. The total number of rewards claimed is logged.

### Daily Check-in
The bot submits the daily check-in claim and logs the Gems reward. If already claimed today, it is skipped.

### Mystery Box
The bot registers an ad session for the mystery box context, waits the required duration, then submits a claim request. The Gems reward is logged on success. If already claimed or not configured, it is skipped.

### Auto Farming
The bot reads the current farming state. If the session is complete, it claims the Gold reward and logs the amount. If the session is still running, the remaining time is logged in `HH:MM:SS` format. If no session is active, the bot applies any available farming boost steps up to the maximum, then starts a new session and logs the multiplier.

### Referral Claim
The bot submits a referral bonus claim. If a bonus is available, the amount is logged. If nothing is pending, it is noted and skipped.

### TON Wallet Payout
If a wallet address is provided in `data.txt` for the account, the bot sends a PATCH request to save it as the TON payout address. A confirmation is logged on success.

### Withdrawal Status
At the end of each account cycle, the bot checks the minimum Gold balance, minimum ads watched, and minimum invites required for withdrawal against the account's current state, and logs whether withdrawal is ready or still locked with the required amount.

### Multi Account
All accounts in `data.txt` are processed sequentially within every cycle. Gold balance is logged at the start of each account. The cycle number is logged at the start and end of each round.

### Proxy Support
Proxies are loaded from `proxy.txt` and assigned to accounts by position in round-robin order. Proxy credentials are masked in log output. Running without proxies is fully supported.

### Auto Countdown
After all accounts complete a cycle, the bot displays a live `HH:MM:SS` countdown until the next cycle starts.

---

## File Structure

```text
Axionet-Miniapp/
├── bot.py          # Main bot, full cycle automation
├── config.json     # Sleep duration between cycles
├── data.txt        # Account initData and optional wallet, one per line
├── proxy.txt       # Proxy list, one per line (optional)
├── LICENSE         # License file
└── utils/
    └── banner.py   # Banner using yuurisan module
```

---

## Disclaimer

This tool is built for educational and technical exploration purposes. Use it wisely and at your own responsibility.

---

<div align="center">
<img width="100%" alt="footer" src="https://capsule-render.vercel.app/api?type=waving&height=120&section=footer"/>
</div>