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

PAIR_MAP = {
    "btc": "BTCUSDT",
    "eth": "ETHUSDT",
    "sol": "SOLUSDT",
    "bnb": "BNBUSDT"
}

# ================= SAFE REQUEST =================

def safe_request(url):

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    for _ in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=10)

            if r.status_code == 200:
                return r.json()

            print("API ERROR:", r.status_code, url)

        except Exception as e:
            print("REQUEST ERROR:", e)

    return None


# ================= PRICE =================

def get_price_coingecko(symbol):

    symbol = COIN_MAP.get(symbol.lower(), symbol.lower())

    url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"

    data = safe_request(url)

    if not data:
        return None

    return data.get(symbol, {}).get("usd")


def get_price_binance(symbol):

    pair = PAIR_MAP.get(symbol.lower())

    if not pair:
        return None

    url = f"https://api.binance.com/api/v3/ticker/price?symbol={pair}"

    data = safe_request(url)

    if not data:
        return None

    try:
        return float(data["price"])
    except:
        return None


def get_price(symbol):

    price = get_price_coingecko(symbol)

    if price:
        return price, "CoinGecko"

    price = get_price_binance(symbol)

    if price:
        return price, "Binance"

    return None, None


# ================= MARKET =================

def get_fear():

    data = safe_request("https://api.alternative.me/fng/")

    if not data:
        return None, None

    d = data["data"][0]
    return d["value"], d["value_classification"]


def get_funding():

    data = safe_request(
        "https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1"
    )

    if not data:
        return None

    return float(data[0]["fundingRate"]) * 100


def get_dominance():

    data = safe_request(
        "https://api.coingecko.com/api/v3/global"
    )

    if not data:
        return None

    return data["data"]["market_cap_percentage"]["btc"]


# ================= TELEGRAM =================

app = ApplicationBuilder().token(TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🚀 Crypto Trader Bot\n\n"
        "/price btc\n"
        "/fear\n"
        "/funding\n"
        "/dominance\n"
        "/market"
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        return await update.message.reply_text("Dùng: /price btc")

    coin = context.args[0]

    p, source = get_price(coin)

    if not p:
        return await update.message.reply_text("Không lấy được giá")

    await update.message.reply_text(
        f"💰 {coin.upper()} = ${p:,.2f}\n"
        f"Source: {source}"
    )


async def fear(update: Update, context: ContextTypes.DEFAULT_TYPE):

    value, text = get_fear()

    if not value:
        return await update.message.reply_text("API lỗi")

    await update.message.reply_text(
        f"😨 Fear Index: {value}\n"
        f"State: {text}\n\n"
        f"Source: alternative.me"
    )


async def funding(update: Update, context: ContextTypes.DEFAULT_TYPE):

    rate = get_funding()

    if not rate:
        return await update.message.reply_text("API lỗi")

    await update.message.reply_text(
        f"📈 BTC Funding: {rate:.4f}%\n"
        f"Source: Binance"
    )


async def dominance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    dom = get_dominance()

    if not dom:
        return await update.message.reply_text("API lỗi")

    await update.message.reply_text(
        f"👑 BTC Dominance: {dom:.2f}%\n"
        f"Source: CoinGecko"
    )


async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):

    btc, src = get_price("btc")
    funding = get_funding()
    fear, state = get_fear()
    dom = get_dominance()

    btc = f"${btc:,.2f}" if btc else "N/A"
    funding = f"{funding:.4f}%" if funding else "N/A"
    fear_text = f"{fear} ({state})" if fear else "N/A"
    dom = f"{dom:.2f}%" if dom else "N/A"

    msg = (
        "📊 Market Overview\n\n"
        f"BTC: {btc}\n"
        f"Funding: {funding}\n"
        f"Fear: {fear_text}\n"
        f"Dominance: {dom}\n\n"
        "Data provided by CoinGecko"
    )

    await update.message.reply_text(msg)


# ================= AUTO SEND =================

async def auto_market(context: ContextTypes.DEFAULT_TYPE):

    btc, src = get_price("btc")
    funding = get_funding()
    fear, state = get_fear()
    dom = get_dominance()

    btc = f"${btc:,.2f}" if btc else "N/A"
    funding = f"{funding:.4f}%" if funding else "N/A"
    fear_text = f"{fear} ({state})" if fear else "N/A"
    dom = f"{dom:.2f}%" if dom else "N/A"

    msg = (
        "⏰ Hourly Crypto Update\n\n"
        f"BTC: {btc}\n"
        f"Funding: {funding}\n"
        f"Fear: {fear_text}\n"
        f"Dominance: {dom}\n\n"
        "Data provided by CoinGecko"
    )

    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=msg
    )


# ================= HANDLERS =================

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("price", price))
app.add_handler(CommandHandler("fear", fear))
app.add_handler(CommandHandler("funding", funding))
app.add_handler(CommandHandler("dominance", dominance))
app.add_handler(CommandHandler("market", market))


# ================= RUN =================

if __name__ == "__main__":

    job_queue = app.job_queue

    job_queue.run_repeating(
        auto_market,
        interval=3600,
        first=30
    )

    app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=RENDER_URL + "/webhook",
        url_path="webhook"
    )