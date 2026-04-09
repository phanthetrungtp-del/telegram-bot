import os
import requests
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

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
        r = requests.get(url, timeout=5).json()
        return r.get(symbol, {}).get("usd")
    except:
        return None


def get_fear():
    try:
        url = "https://api.alternative.me/fng/"
        r = requests.get(url).json()
        data = r["data"][0]
        return data["value"], data["value_classification"]
    except:
        return None, None


def get_funding():
    try:
        url = "https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1"
        r = requests.get(url).json()
        return float(r[0]["fundingRate"]) * 100
    except:
        return None


def get_oi():
    try:
        url = "https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT"
        r = requests.get(url).json()
        return float(r["openInterest"])
    except:
        return None


def get_dominance():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        r = requests.get(url).json()
        return r["data"]["market_cap_percentage"]["btc"]
    except:
        return None


def get_long_short():
    try:
        url = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=5m&limit=1"
        r = requests.get(url).json()
        return float(r[0]["longAccount"]), float(r[0]["shortAccount"])
    except:
        return None, None


def get_top():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&per_page=10"
        r = requests.get(url).json()

        text = "🏆 Top 10 Crypto\n\n"
        for i, coin in enumerate(r, 1):
            text += f"{i}. {coin['symbol'].upper()} — ${coin['current_price']:,}\n"

        return text
    except:
        return "Lỗi lấy dữ liệu"


# ================= TELEGRAM =================

telegram_app = ApplicationBuilder().token(TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 Crypto Trader Bot\n\n"
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

    if p:
        await update.message.reply_text(f"💰 {coin.upper()} = ${p:,}")
    else:
        await update.message.reply_text("Không tìm thấy coin")


async def fear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value, text = get_fear()
    await update.message.reply_text(
        f"😨 Fear & Greed\n\nIndex: {value}\nState: {text}"
    )


async def funding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rate = get_funding()
    await update.message.reply_text(f"📈 BTC Funding Rate\n\n{rate:.4f}%")


async def oi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    oi_value = get_oi()
    await update.message.reply_text(f"📊 BTC Open Interest\n\n{oi_value:,.0f}")


async def dominance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dom = get_dominance()
    await update.message.reply_text(f"👑 BTC Dominance\n\n{dom:.2f}%")


async def longshort(update: Update, context: ContextTypes.DEFAULT_TYPE):
    long, short = get_long_short()
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

    msg = (
        "📊 Crypto Market Overview\n\n"
        f"BTC Price: ${price_value:,}\n"
        f"Funding: {funding_value:.4f}%\n"
        f"Fear Index: {fear_value} ({state})\n"
        f"BTC Dominance: {dom:.2f}%"
    )

    await update.message.reply_text(msg)


telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("price", price))
telegram_app.add_handler(CommandHandler("fear", fear))
telegram_app.add_handler(CommandHandler("funding", funding))
telegram_app.add_handler(CommandHandler("oi", oi))
telegram_app.add_handler(CommandHandler("dominance", dominance))
telegram_app.add_handler(CommandHandler("longshort", longshort))
telegram_app.add_handler(CommandHandler("top", top))
telegram_app.add_handler(CommandHandler("market", market))


# ================= FLASK =================

flask_app = Flask(__name__)
loop = asyncio.get_event_loop()


@flask_app.route("/")
def home():
    return "Crypto Trader Bot Running"


@flask_app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    update = Update.de_json(data, telegram_app.bot)

    loop.create_task(telegram_app.process_update(update))

    return "ok"


async def telegram_main():
    await telegram_app.initialize()
    await telegram_app.start()

    if RENDER_URL:
        await telegram_app.bot.set_webhook(
            url=RENDER_URL + "/webhook"
        )
        print("Webhook set:", RENDER_URL + "/webhook")


if __name__ == "__main__":
    loop.create_task(telegram_main())

    flask_app.run(host="0.0.0.0", port=10000)