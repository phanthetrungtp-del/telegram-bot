import os
import requests
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================= ENV =================

TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
CHAT_ID = os.getenv("CHAT_ID")

# ================= REQUEST =================

def safe_request(url):

    for _ in range(3):
        try:
            r = requests.get(url, timeout=10)

            print("STATUS:", r.status_code, url)

            if r.status_code == 200:
                return r.json()

        except Exception as e:
            print("ERROR:", e)

        time.sleep(2)

    return None


# ================= PRICE OKX =================

def get_price(symbol="btc"):

    pair_map = {
        "btc": "BTC-USDT",
        "eth": "ETH-USDT",
        "sol": "SOL-USDT",
        "bnb": "BNB-USDT"
    }

    pair = pair_map.get(symbol.lower(), "BTC-USDT")

    url = f"https://www.okx.com/api/v5/market/ticker?instId={pair}"

    data = safe_request(url)

    if data and "data" in data:
        return float(data["data"][0]["last"])

    return None


# ================= FUNDING OKX =================

def get_funding():

    url = "https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP"

    data = safe_request(url)

    if data and "data" in data and len(data["data"]) > 0:
        return float(data["data"][0]["fundingRate"]) * 100

    return None


# ================= FEAR =================

def get_fear():

    url = "https://api.alternative.me/fng/"

    data = safe_request(url)

    if data:
        value = data["data"][0]["value"]
        state = data["data"][0]["value_classification"]

        return value, state

    return None, None


# ================= DOMINANCE COINGECKO =================

def get_dominance():

    url = "https://api.coingecko.com/api/v3/global"

    data = safe_request(url)

    if data:
        return data["data"]["market_cap_percentage"]["btc"]

    return None


# ================= LONG SHORT OKX =================

def get_long_short():

    url = "https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio?ccy=BTC&period=5m"

    data = safe_request(url)

    if data and "data" in data and len(data["data"]) > 0:

        long_ratio = float(data["data"][0]["longShortRatio"])

        long = long_ratio
        short = round(1 / long_ratio, 2)

        return long, short

    return None, None


# ================= BTC SIGNAL =================

def btc_signal():

    price = get_price()
    funding = get_funding()
    fear, state = get_fear()
    long, short = get_long_short()

    if None in (price, funding, fear, long, short):
        return "⚠️ Không đủ dữ liệu để tạo signal"

    signal = "Neutral"

    if funding > 0.01 and long > 1.3 and int(fear) < 40:
        signal = "SHORT ⚠️"

    elif funding < -0.01 and long < 0.8 and int(fear) > 60:
        signal = "LONG 🚀"

    return (
        "📊 BTC Market Signal\n\n"
        f"Price: ${price:,.0f}\n"
        f"Funding: {funding:.4f}%\n"
        f"Fear: {fear} ({state})\n"
        f"Long: {long}\n"
        f"Short: {short}\n\n"
        f"Signal: {signal}"
    )


# ================= TELEGRAM =================

telegram_app = ApplicationBuilder().token(TOKEN).build()

# ================= COMMAND =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🚀 Crypto Trader Bot\n\n"
        "/price btc\n"
        "/funding\n"
        "/fear\n"
        "/dominance\n"
        "/longshort\n"
        "/signal\n"
        "/market"
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):

    coin = "btc"

    if context.args:
        coin = context.args[0]

    p = get_price(coin)

    if p:
        await update.message.reply_text(f"💰 {coin.upper()} = ${p:,.0f}")
    else:
        await update.message.reply_text("Không lấy được giá")


async def funding(update: Update, context: ContextTypes.DEFAULT_TYPE):

    rate = get_funding()

    if rate:
        await update.message.reply_text(f"📈 BTC Funding\n\n{rate:.4f}%")
    else:
        await update.message.reply_text("Không lấy được funding")


async def fear(update: Update, context: ContextTypes.DEFAULT_TYPE):

    value, state = get_fear()

    if value:
        await update.message.reply_text(
            f"😨 Fear & Greed\n\n{value} ({state})"
        )
    else:
        await update.message.reply_text("Không lấy được fear")


async def dominance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    dom = get_dominance()

    if dom:
        await update.message.reply_text(
            f"👑 BTC Dominance\n\n{dom:.2f}%\n\nSource: CoinGecko"
        )
    else:
        await update.message.reply_text("Không lấy được dominance")


async def longshort(update: Update, context: ContextTypes.DEFAULT_TYPE):

    long, short = get_long_short()

    if long:
        await update.message.reply_text(
            f"⚔️ Long / Short\n\nLong: {long}\nShort: {short}"
        )
    else:
        await update.message.reply_text("Không lấy được Long/Short")


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(btc_signal())


async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):

    price = get_price()
    funding = get_funding()
    fear, state = get_fear()
    dom = get_dominance()
    long, short = get_long_short()

    msg = (
        "📊 Crypto Market Overview\n\n"
        f"BTC: ${price:,.0f}\n"
        f"Funding: {funding:.4f}%\n"
        f"Fear: {fear} ({state})\n"
        f"Dominance: {dom:.2f}%\n"
        f"Long: {long}\n"
        f"Short: {short}\n\n"
        "Source: CoinGecko (Dominance)"
    )

    await update.message.reply_text(msg)


# ================= AUTO =================

async def auto_market(context: ContextTypes.DEFAULT_TYPE):

    price = get_price()
    funding = get_funding()
    fear, state = get_fear()
    dom = get_dominance()
    long, short = get_long_short()

    msg = (
        "📊 Crypto Market Update (1H)\n\n"
        f"BTC: ${price:,.0f}\n"
        f"Funding: {funding:.4f}%\n"
        f"Fear: {fear} ({state})\n"
        f"Dominance: {dom:.2f}%\n"
        f"Long: {long}\n"
        f"Short: {short}\n\n"
        "Source: CoinGecko"
    )

    await context.bot.send_message(chat_id=CHAT_ID, text=msg)


async def auto_signal(context: ContextTypes.DEFAULT_TYPE):

    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=btc_signal()
    )


# ================= HANDLER =================

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("price", price))
telegram_app.add_handler(CommandHandler("funding", funding))
telegram_app.add_handler(CommandHandler("fear", fear))
telegram_app.add_handler(CommandHandler("dominance", dominance))
telegram_app.add_handler(CommandHandler("longshort", longshort))
telegram_app.add_handler(CommandHandler("signal", signal))
telegram_app.add_handler(CommandHandler("market", market))


# ================= JOB =================

job_queue = telegram_app.job_queue

job_queue.run_repeating(auto_market, interval=3600, first=20)
job_queue.run_repeating(auto_signal, interval=3600, first=40)


# ================= RUN =================

if __name__ == "__main__":

    telegram_app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=RENDER_URL + "/webhook",
        url_path="webhook"
    )