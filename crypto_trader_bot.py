import os
import json
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

USERS_FILE = "users.json"

PAIR_MAP = {
    "btc": "BTC-USDT",
    "eth": "ETH-USDT",
    "sol": "SOL-USDT",
    "bnb": "BNB-USDT"
}

# ================= USERS =================

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def add_user(chat_id):
    users = load_users()
    if chat_id not in users:
        users.append(chat_id)
        save_users(users)

# ================= SAFE REQUEST =================

def safe_request(url):

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)

        print("URL:", url)
        print("STATUS:", r.status_code)

        if r.status_code == 200:
            return r.json()

        return None

    except Exception as e:
        print("ERROR:", e)
        return None


# ================= PRICE =================

def get_price(symbol):

    pair = PAIR_MAP.get(symbol.lower())

    if not pair:
        return None

    url = f"https://www.okx.com/api/v5/market/ticker?instId={pair}"

    data = safe_request(url)

    if not data:
        return None

    try:
        return float(data["data"][0]["last"])
    except:
        return None


# ================= FUNDING =================

def get_funding():

    url = "https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP"

    data = safe_request(url)

    if not data:
        return None

    try:
        rate = data["data"][0]["fundingRate"]
        return float(rate) * 100
    except:
        return None


# ================= FEAR =================

def get_fear():

    data = safe_request("https://api.alternative.me/fng/")

    if not data:
        return None, None

    d = data["data"][0]

    return d["value"], d["value_classification"]


# ================= TELEGRAM =================

app = ApplicationBuilder().token(TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.message.chat_id
    add_user(chat_id)

    await update.message.reply_text(
        "🚀 Crypto Trader Bot\n\n"
        "Auto update mỗi 1 giờ ⏰\n\n"
        "/price btc\n"
        "/funding\n"
        "/fear\n"
        "/market"
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        return await update.message.reply_text("Dùng: /price btc")

    coin = context.args[0]

    p = get_price(coin)

    if not p:
        return await update.message.reply_text("Không lấy được giá")

    await update.message.reply_text(
        f"💰 {coin.upper()} = ${p:,.2f}\n"
        f"Source: OKX"
    )


async def funding(update: Update, context: ContextTypes.DEFAULT_TYPE):

    rate = get_funding()

    if not rate:
        return await update.message.reply_text("Funding API lỗi")

    await update.message.reply_text(
        f"📈 BTC Funding: {rate:.4f}%\n"
        f"Source: OKX"
    )


async def fear(update: Update, context: ContextTypes.DEFAULT_TYPE):

    value, text = get_fear()

    if not value:
        return await update.message.reply_text("Fear API lỗi")

    await update.message.reply_text(
        f"😨 Fear Index: {value}\n"
        f"State: {text}\n"
        f"Source: alternative.me"
    )


async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):

    btc = get_price("btc")
    funding = get_funding()
    fear, state = get_fear()

    btc = f"${btc:,.2f}" if btc else "N/A"
    funding = f"{funding:.4f}%" if funding else "N/A"
    fear_text = f"{fear} ({state})" if fear else "N/A"

    msg = (
        "📊 Market Overview\n\n"
        f"BTC: {btc}\n"
        f"Funding: {funding}\n"
        f"Fear: {fear_text}\n\n"
        "Data provided by OKX"
    )

    await update.message.reply_text(msg)


# ================= AUTO SEND =================

async def auto_market(context: ContextTypes.DEFAULT_TYPE):

    users = load_users()

    if not users:
        return

    btc = get_price("btc")
    funding = get_funding()
    fear, state = get_fear()

    btc = f"${btc:,.2f}" if btc else "N/A"
    funding = f"{funding:.4f}%" if funding else "N/A"
    fear_text = f"{fear} ({state})" if fear else "N/A"

    msg = (
        "⏰ Hourly Crypto Update\n\n"
        f"BTC: {btc}\n"
        f"Funding: {funding}\n"
        f"Fear: {fear_text}\n\n"
        "Data provided by OKX"
    )

    for user in users:
        try:
            await context.bot.send_message(chat_id=user, text=msg)
        except:
            pass


# ================= HANDLERS =================

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("price", price))
app.add_handler(CommandHandler("funding", funding))
app.add_handler(CommandHandler("fear", fear))
app.add_handler(CommandHandler("market", market))


# ================= RUN =================

if __name__ == "__main__":

    job_queue = app.job_queue

    job_queue.run_repeating(
        auto_market,
        interval=3600,
        first=60
    )

    app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=RENDER_URL + "/webhook",
        url_path="webhook"
    )