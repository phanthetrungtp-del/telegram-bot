import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
CHAT_ID = os.getenv("CHAT_ID")

COIN_MAP = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "bnb": "binancecoin"
}

# ================= API =================

def get_price(symbol):
    symbol = COIN_MAP.get(symbol.lower(), symbol.lower())

    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"
        r = requests.get(url, timeout=5)

        if r.status_code != 200:
            print("Price error:", r.text)
            return None

        data = r.json()
        return data.get(symbol, {}).get("usd")

    except Exception as e:
        print("Price exception:", e)
        return None


def get_fear():
    try:
        url = "https://api.alternative.me/fng/"
        r = requests.get(url, timeout=5)

        if r.status_code != 200:
            return None, None

        data = r.json()["data"][0]

        return data["value"], data["value_classification"]

    except Exception as e:
        print("Fear exception:", e)
        return None, None


def get_funding():
    try:
        url = "https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1"
        r = requests.get(url, timeout=5)

        if r.status_code != 200:
            return None

        data = r.json()

        if not data:
            return None

        return float(data[0]["fundingRate"]) * 100

    except Exception as e:
        print("Funding exception:", e)
        return None


def get_oi():
    try:
        url = "https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT"
        r = requests.get(url, timeout=5)

        if r.status_code != 200:
            return None

        data = r.json()
        return float(data["openInterest"])

    except Exception as e:
        print("OI exception:", e)
        return None


def get_dominance():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        r = requests.get(url, timeout=5)

        if r.status_code != 200:
            return None

        data = r.json()
        return data["data"]["market_cap_percentage"]["btc"]

    except Exception as e:
        print("Dominance exception:", e)
        return None


def get_long_short():
    try:
        url = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=5m&limit=1"
        r = requests.get(url, timeout=5)

        if r.status_code != 200:
            return None, None

        data = r.json()

        if not data:
            return None, None

        return float(data[0]["longAccount"]), float(data[0]["shortAccount"])

    except Exception as e:
        print("LongShort exception:", e)
        return None, None


def get_top():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&per_page=10"
        r = requests.get(url, timeout=5)

        if r.status_code != 200:
            return "Không lấy được top crypto"

        data = r.json()

        text = "🏆 Top 10 Crypto\n\n"

        for i, coin in enumerate(data, 1):
            text += f"{i}. {coin['symbol'].upper()} — ${coin['current_price']:,}\n"

        return text

    except:
        return "Lỗi lấy dữ liệu"


# ================= TELEGRAM =================

telegram_app = ApplicationBuilder().token(TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global CHAT_ID

    CHAT_ID = update.effective_chat.id

    await update.message.reply_text(
        "🚀 Crypto Trader Bot\n\n"
        "Auto gửi mỗi 1 giờ đã bật\n\n"
        "/price btc\n"
        "/fear\n"
        "/funding\n"
        "/oi\n"
        "/dominance\n"
        "/longshort\n"
        "/top\n"
        "/market"
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Dùng: /price btc")

    coin = context.args[0]
    p = get_price(coin)

    if p is None:
        return await update.message.reply_text("Không lấy được giá")

    await update.message.reply_text(f"💰 {coin.upper()} = ${p:,}")


async def fear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value, text = get_fear()

    if value is None:
        return await update.message.reply_text("Không lấy được Fear Index")

    await update.message.reply_text(
        f"😨 Fear & Greed\n\nIndex: {value}\nState: {text}"
    )


async def funding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rate = get_funding()

    if rate is None:
        return await update.message.reply_text("Không lấy được funding rate")

    await update.message.reply_text(
        f"📈 BTC Funding Rate\n\n{rate:.4f}%"
    )


async def oi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    oi_value = get_oi()

    if oi_value is None:
        return await update.message.reply_text("Không lấy được Open Interest")

    await update.message.reply_text(
        f"📊 BTC Open Interest\n\n{oi_value:,.0f}"
    )


async def dominance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dom = get_dominance()

    if dom is None:
        return await update.message.reply_text("Không lấy được BTC Dominance")

    await update.message.reply_text(
        f"👑 BTC Dominance\n\n{dom:.2f}%"
    )


async def longshort(update: Update, context: ContextTypes.DEFAULT_TYPE):
    long, short = get_long_short()

    if long is None:
        return await update.message.reply_text("Không lấy được Long/Short")

    await update.message.reply_text(
        f"⚔️ Long / Short Ratio\n\nLong: {long}\nShort: {short}"
    )


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_top())


async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):

    price_value = get_price("btc")
    funding_value = get_funding()
    fear_value, state = get_fear()
    dom = get_dominance()

    price_text = f"${price_value:,}" if price_value else "N/A"
    funding_text = f"{funding_value:.4f}%" if funding_value else "N/A"
    fear_text = f"{fear_value} ({state})" if fear_value else "N/A"
    dom_text = f"{dom:.2f}%" if dom else "N/A"

    msg = (
        "📊 Crypto Market Overview\n\n"
        f"BTC Price: {price_text}\n"
        f"Funding: {funding_text}\n"
        f"Fear Index: {fear_text}\n"
        f"BTC Dominance: {dom_text}"
    )

    await update.message.reply_text(msg)


# ================= AUTO HOURLY =================

async def auto_market(context: ContextTypes.DEFAULT_TYPE):

    if not CHAT_ID:
        return

    price_value = get_price("btc")
    funding_value = get_funding()
    fear_value, state = get_fear()
    dom = get_dominance()

    price_text = f"${price_value:,}" if price_value else "N/A"
    funding_text = f"{funding_value:.4f}%" if funding_value else "N/A"
    fear_text = f"{fear_value} ({state})" if fear_value else "N/A"
    dom_text = f"{dom:.2f}%" if dom else "N/A"

    msg = (
        "⏰ Hourly Crypto Update\n\n"
        f"BTC Price: {price_text}\n"
        f"Funding: {funding_text}\n"
        f"Fear Index: {fear_text}\n"
        f"BTC Dominance: {dom_text}"
    )

    await context.bot.send_message(chat_id=CHAT_ID, text=msg)


async def error_handler(update, context):
    print("Error:", context.error)


telegram_app.add_error_handler(error_handler)

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