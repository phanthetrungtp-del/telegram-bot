import os
import requests
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

COIN_MAP = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "bnb": "binancecoin"
}

chat_id_global = None

# ================= SAFE REQUEST =================

def safe_request(url):

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    for _ in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                return r.json()
        except:
            pass

    return None


# ================= API =================

def get_price(symbol):
    symbol = COIN_MAP.get(symbol.lower(), symbol.lower())

    url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"
    data = safe_request(url)

    if not data:
        return None

    return data.get(symbol, {}).get("usd")


def get_fear():
    data = safe_request("https://api.alternative.me/fng/")

    if not data:
        return None, None

    try:
        value = data["data"][0]["value"]
        state = data["data"][0]["value_classification"]
        return value, state
    except:
        return None, None


def get_funding():
    data = safe_request(
        "https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1"
    )

    if not data:
        return None

    try:
        return float(data[0]["fundingRate"]) * 100
    except:
        return None


def get_oi():
    data = safe_request(
        "https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT"
    )

    if not data:
        return None

    try:
        return float(data["openInterest"])
    except:
        return None


def get_dominance():
    data = safe_request(
        "https://api.coingecko.com/api/v3/global"
    )

    if not data:
        return None

    try:
        return data["data"]["market_cap_percentage"]["btc"]
    except:
        return None


def get_long_short():
    data = safe_request(
        "https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=5m&limit=1"
    )

    if not data:
        return None, None

    try:
        return float(data[0]["longAccount"]), float(data[0]["shortAccount"])
    except:
        return None, None


def get_top():

    data = safe_request(
        "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&per_page=10"
    )

    if not data:
        return "Lỗi lấy dữ liệu"

    text = "🏆 Top 10 Crypto\n\n"

    for i, coin in enumerate(data, 1):
        text += f"{i}. {coin['symbol'].upper()} — ${coin['current_price']:,}\n"

    return text


# ================= TELEGRAM =================

telegram_app = ApplicationBuilder().token(TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global chat_id_global

    chat_id_global = update.effective_chat.id

    await update.message.reply_text(
        "🚀 Crypto Trader Bot\n\n"
        "/price btc\n"
        "/fear\n"
        "/funding\n"
        "/oi\n"
        "/dominance\n"
        "/longshort\n"
        "/top\n"
        "/market\n\n"
        "Bot sẽ auto gửi mỗi 1 tiếng"
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        return await update.message.reply_text("Dùng: /price btc")

    coin = context.args[0]
    p = get_price(coin)

    if p:
        await update.message.reply_text(f"💰 {coin.upper()} = ${p:,}")
    else:
        await update.message.reply_text("Không lấy được dữ liệu")


async def fear(update: Update, context: ContextTypes.DEFAULT_TYPE):

    value, state = get_fear()

    if not value:
        return await update.message.reply_text("Không lấy được Fear Index")

    await update.message.reply_text(
        f"😨 Fear & Greed\n\nIndex: {value}\nState: {state}"
    )


async def funding(update: Update, context: ContextTypes.DEFAULT_TYPE):

    rate = get_funding()

    if rate is None:
        return await update.message.reply_text("Không lấy được funding")

    await update.message.reply_text(
        f"📈 BTC Funding Rate\n\n{rate:.4f}%"
    )


async def oi(update: Update, context: ContextTypes.DEFAULT_TYPE):

    oi_value = get_oi()

    if oi_value is None:
        return await update.message.reply_text("Không lấy được OI")

    await update.message.reply_text(
        f"📊 BTC Open Interest\n\n{oi_value:,.0f}"
    )


async def dominance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    dom = get_dominance()

    if dom is None:
        return await update.message.reply_text("Không lấy được dominance")

    await update.message.reply_text(
        f"👑 BTC Dominance\n\n{dom:.2f}%"
    )


async def longshort(update: Update, context: ContextTypes.DEFAULT_TYPE):

    long, short = get_long_short()

    if long is None:
        return await update.message.reply_text("Không lấy được Long/Short")

    await update.message.reply_text(
        f"⚔️ Long / Short\n\nLong: {long}\nShort: {short}"
    )


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_top())


async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):

    price_value = get_price("btc")
    funding_value = get_funding()
    fear_value, state = get_fear()
    dom = get_dominance()

    msg = "📊 Crypto Market\n\n"

    if price_value:
        msg += f"BTC Price: ${price_value:,}\n"

    if funding_value:
        msg += f"Funding: {funding_value:.4f}%\n"

    if fear_value:
        msg += f"Fear: {fear_value} ({state})\n"

    if dom:
        msg += f"Dominance: {dom:.2f}%"

    await update.message.reply_text(msg)


# ================= AUTO SEND =================

async def auto_market(context: ContextTypes.DEFAULT_TYPE):

    global chat_id_global

    if not chat_id_global:
        return

    price_value = get_price("btc")

    if not price_value:
        return

    await context.bot.send_message(
        chat_id=chat_id_global,
        text=f"⏰ Hourly BTC Update\n\nBTC Price: ${price_value:,}"
    )


# ================= HANDLERS =================

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("price", price))
telegram_app.add_handler(CommandHandler("fear", fear))
telegram_app.add_handler(CommandHandler("funding", funding))
telegram_app.add_handler(CommandHandler("oi", oi))
telegram_app.add_handler(CommandHandler("dominance", dominance))
telegram_app.add_handler(CommandHandler("longshort", longshort))
telegram_app.add_handler(CommandHandler("top", top))
telegram_app.add_handler(CommandHandler("market", market))


# ================= RUN =================

if __name__ == "__main__":

    telegram_app.job_queue.run_repeating(
        auto_market,
        interval=3600,
        first=60
    )

    telegram_app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=RENDER_URL + "/webhook",
        url_path="webhook"
    )