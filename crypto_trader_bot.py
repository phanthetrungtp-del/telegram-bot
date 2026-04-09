import os
import json
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

USERS_FILE = "users.json"

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

    coin = COIN_MAP.get(symbol.lower())
    pair = PAIR_MAP.get(symbol.lower())

    if not coin:
        return None, None

    # 1 CoinGecko
    data = safe_request(
        f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd"
    )

    if data and coin in data:
        return data[coin]["usd"], "CoinGecko"

    # 2 Binance
    if pair:
        data = safe_request(
            f"https://api.binance.com/api/v3/ticker/price?symbol={pair}"
        )

        if data and "price" in data:
            return float(data["price"]), "Binance"

    # 3 Bybit
    if pair:
        data = safe_request(
            f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={pair}"
        )

        if data and data.get("result"):
            try:
                return float(data["result"]["list"][0]["lastPrice"]), "Bybit"
            except:
                pass

    # 4 OKX
    if pair:
        data = safe_request(
            f"https://www.okx.com/api/v5/market/ticker?instId={pair}"
        )

        if data and data.get("data"):
            return float(data["data"][0]["last"]), "OKX"

    return None, None


# ================= FUNDING =================

def get_funding():

    # 1 Bybit
    data = safe_request(
        "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT"
    )

    if data and data.get("result"):
        try:
            rate = data["result"]["list"][0]["fundingRate"]

            if rate:
                return float(rate) * 100, "Bybit"
        except:
            pass

    # 2 Binance
    data = safe_request(
        "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT"
    )

    if data and "lastFundingRate" in data:
        return float(data["lastFundingRate"]) * 100, "Binance"

    return None, None


# ================= MARKET =================

def get_fear():

    data = safe_request("https://api.alternative.me/fng/")

    if not data:
        return None, None

    d = data["data"][0]

    return d["value"], d["value_classification"]


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

    chat_id = update.message.chat_id
    add_user(chat_id)

    await update.message.reply_text(
        "🚀 Crypto Trader Bot\n\n"
        "Auto Market mỗi 1 giờ ⏰\n\n"
        "/price btc\n"
        "/funding\n"
        "/fear\n"
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


async def funding(update: Update, context: ContextTypes.DEFAULT_TYPE):

    rate, source = get_funding()

    if not rate:
        return await update.message.reply_text("Không lấy được funding")

    await update.message.reply_text(
        f"📈 BTC Funding: {rate:.4f}%\n"
        f"Source: {source}"
    )


async def fear(update: Update, context: ContextTypes.DEFAULT_TYPE):

    value, text = get_fear()

    if not value:
        return await update.message.reply_text("API lỗi")

    await update.message.reply_text(
        f"😨 Fear Index: {value}\n"
        f"State: {text}"
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
    funding, fsrc = get_funding()
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

    users = load_users()

    if not users:
        return

    btc, src = get_price("btc")
    funding, fsrc = get_funding()
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
app.add_handler(CommandHandler("dominance", dominance))
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