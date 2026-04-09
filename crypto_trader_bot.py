import os
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

COIN_MAP = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "bnb": "binancecoin"
}

# ================= PRICE =================

def get_price(symbol):
    symbol = COIN_MAP.get(symbol.lower(), symbol.lower())

    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"
        r = requests.get(url, timeout=5).json()
        return r.get(symbol, {}).get("usd")
    except:
        return None


# ================= FEAR GREED =================

def get_fear():
    try:
        url = "https://api.alternative.me/fng/"
        r = requests.get(url).json()
        data = r["data"][0]
        return data["value"], data["value_classification"]
    except:
        return None, None


# ================= FUNDING =================

def get_funding():
    try:
        url = "https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1"
        r = requests.get(url).json()
        return float(r[0]["fundingRate"]) * 100
    except:
        return None


# ================= OPEN INTEREST =================

def get_oi():
    try:
        url = "https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT"
        r = requests.get(url).json()
        return float(r["openInterest"])
    except:
        return None


# ================= BTC DOMINANCE =================

def get_dominance():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        r = requests.get(url).json()
        return r["data"]["market_cap_percentage"]["btc"]
    except:
        return None


# ================= LONG SHORT =================

def get_long_short():
    try:
        url = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=5m&limit=1"
        r = requests.get(url).json()
        return float(r[0]["longAccount"]), float(r[0]["shortAccount"])
    except:
        return None, None


# ================= TOP COINS =================

def get_top():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=10&page=1"
        r = requests.get(url).json()

        text = "🏆 Top 10 Crypto\n\n"

        for i, coin in enumerate(r, 1):
            name = coin["symbol"].upper()
            price = coin["current_price"]
            text += f"{i}. {name} — ${price:,}\n"

        return text
    except:
        return None


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
    oi = get_oi()
    await update.message.reply_text(f"📊 BTC Open Interest\n\n{oi:,.0f}")


async def dominance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dom = get_dominance()
    await update.message.reply_text(f"👑 BTC Dominance\n\n{dom:.2f}%")


async def longshort(update: Update, context: ContextTypes.DEFAULT_TYPE):
    long, short = get_long_short()
    await update.message.reply_text(
        f"⚔️ Long / Short Ratio\n\nLong: {long}\nShort: {short}"
    )


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_top()
    await update.message.reply_text(data)


async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price = get_price("btc")
    funding = get_funding()
    fear, state = get_fear()
    dom = get_dominance()

    msg = (
        "📊 Crypto Market Overview\n\n"
        f"BTC Price: ${price:,}\n"
        f"Funding: {funding:.4f}%\n"
        f"Fear Index: {fear} ({state})\n"
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


# ================= FLASK WEBHOOK =================

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Crypto Trader Bot Running"


@flask_app.route("/webhook", methods=["POST"])
async def webhook():
    data = request.get_json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return "ok"


if __name__ == "__main__":
    telegram_app.initialize()
    telegram_app.bot.set_webhook(
        url=os.getenv("RENDER_EXTERNAL_URL") + "/webhook"
    )

    flask_app.run(host="0.0.0.0", port=10000)