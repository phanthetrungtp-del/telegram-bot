import os
import requests
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

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

            if r.status_code == 429:
                time.sleep(5)

        except Exception as e:
            print("ERROR:", e)

        time.sleep(2)

    return None


# ================= PRICE (OKX) =================

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


# ================= FUNDING (OKX) =================

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
        return data["data"][0]["value"], data["data"][0]["value_classification"]

    return None, None


# ================= DOMINANCE (CACHE + RETRY) =================

last_dom = None
last_time = 0

def get_dominance():
    global last_dom, last_time

    # cache 5 phút
    if time.time() - last_time < 300:
        return last_dom

    url = "https://api.coingecko.com/api/v3/global"

    data = safe_request(url)

    if data:
        last_dom = data["data"]["market_cap_percentage"]["btc"]
        last_time = time.time()
        return last_dom

    return last_dom


# ================= LONG SHORT (OKX) =================

def get_long_short():

    url = "https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio?ccy=BTC&period=5m"

    data = safe_request(url)

    if data and "data" in data and len(data["data"]) > 0:

        ratio = float(data["data"][0]["longShortRatio"])

        long = ratio
        short = round(1 / ratio, 2)

        return long, short

    return None, None


# ================= SIGNAL =================

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
        "📊 BTC Signal\n\n"
        f"Price: ${price:,.0f}\n"
        f"Funding: {funding:.4f}%\n"
        f"Fear: {fear} ({state})\n"
        f"Long: {long}\n"
        f"Short: {short}\n\n"
        f"Signal: {signal}"
    )


# ================= TELEGRAM =================

app = ApplicationBuilder().token(TOKEN).build()


# ================= COMMAND =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/price btc\n/funding\n/fear\n/dominance\n/longshort\n/signal\n/market"
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coin = context.args[0] if context.args else "btc"
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
        await update.message.reply_text(f"😨 Fear & Greed\n\n{value} ({state})")
    else:
        await update.message.reply_text("Không lấy được fear")


async def dominance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dom = get_dominance()

    if dom:
        await update.message.reply_text(
            f"👑 BTC Dominance\n\n{dom:.2f}%\n\nSource: CoinGecko"
        )
    else:
        await update.message.reply_text(
            "⚠️ Dominance tạm thời unavailable (CoinGecko rate limit)"
        )


async def longshort(update: Update, context: ContextTypes.DEFAULT_TYPE):
    long, short = get_long_short()

    if long:
        await update.message.reply_text(
            f"⚔️ Long / Short\n\nLong: {long}\nShort: {short}"
        )
    else:
        await update.message.reply_text("⚠️ Không lấy được Long/Short")


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(btc_signal())


async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):

    price = get_price()
    funding = get_funding()
    fear, state = get_fear()
    dom = get_dominance()
    long, short = get_long_short()

    msg = "📊 Market Overview\n\n"

    msg += f"BTC: ${price:,.0f}\n" if price else "BTC: N/A\n"
    msg += f"Funding: {funding:.4f}%\n" if funding else "Funding: N/A\n"
    msg += f"Fear: {fear} ({state})\n" if fear else "Fear: N/A\n"
    msg += f"Dominance: {dom:.2f}%\n" if dom else "Dominance: N/A\n"
    msg += f"Long: {long}\n" if long else "Long: N/A\n"
    msg += f"Short: {short}\n" if short else "Short: N/A\n"

    msg += "\nSource: CoinGecko (Dominance)"

    await update.message.reply_text(msg)


# ================= AUTO =================

async def auto_market(context: ContextTypes.DEFAULT_TYPE):

    price = get_price()
    funding = get_funding()
    fear, state = get_fear()
    dom = get_dominance()

    msg = "📊 Auto Market Update\n\n"

    msg += f"BTC: ${price:,.0f}\n" if price else "BTC: N/A\n"
    msg += f"Funding: {funding:.4f}%\n" if funding else "Funding: N/A\n"
    msg += f"Fear: {fear} ({state})\n" if fear else "Fear: N/A\n"
    msg += f"Dominance: {dom:.2f}%\n" if dom else "Dominance: N/A\n"

    await context.bot.send_message(chat_id=CHAT_ID, text=msg)


# ================= HANDLER =================

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("price", price))
app.add_handler(CommandHandler("funding", funding))
app.add_handler(CommandHandler("fear", fear))
app.add_handler(CommandHandler("dominance", dominance))
app.add_handler(CommandHandler("longshort", longshort))
app.add_handler(CommandHandler("signal", signal))
app.add_handler(CommandHandler("market", market))


# ================= JOB =================

job_queue = app.job_queue

if job_queue:
    job_queue.run_repeating(auto_market, interval=3600, first=20)


# ================= RUN =================

if __name__ == "__main__":
    app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=RENDER_URL + "/webhook",
        url_path="webhook"
    )