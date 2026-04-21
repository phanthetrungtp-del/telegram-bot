import os
import requests
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

app = Flask(__name__)

telegram_app = ApplicationBuilder().token(TOKEN).build()

loop = asyncio.get_event_loop()

# ================= API =================

def safe_float(x):
    try:
        return float(x)
    except:
        return None


def get_price():
    try:
        url = "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT"
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        data = r.json()
        return safe_float(data["data"][0]["last"])
    except:
        return None


def get_funding():
    try:
        url = "https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP"
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        data = r.json()
        return safe_float(data["data"][0]["fundingRate"]) * 100
    except:
        return None


def get_fear():
    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=5).json()
        d = r["data"][0]
        return d["value"], d["value_classification"]
    except:
        return None, None


# ================= TELEGRAM =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot đang chạy 🚀")


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_price()
    if p:
        await update.message.reply_text(f"💰 BTC = ${p:,.0f}")
    else:
        await update.message.reply_text("API lỗi")


async def funding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    f = get_funding()
    if f:
        await update.message.reply_text(f"📈 Funding: {f:.4f}%")
    else:
        await update.message.reply_text("API lỗi")


async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = get_price()
    f = get_funding()
    fear, state = get_fear()

    msg = (
        "📊 Market Overview\n\n"
        f"BTC: {f'${p:,.0f}' if p else 'N/A'}\n"
        f"Funding: {f'{f:.4f}%' if f else 'N/A'}\n"
        f"Fear: {fear} ({state})\n\n"
        "Data by CoinGecko"
    )

    await update.message.reply_text(msg)


# ================= AUTO JOB =================

async def auto_send(context: ContextTypes.DEFAULT_TYPE):
    chat_id = os.getenv("CHAT_ID")

    p = get_price()

    if p:
        await context.bot.send_message(chat_id=chat_id, text=f"⏰ BTC: ${p:,.0f}")


# ================= HANDLER =================

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("price", price))
telegram_app.add_handler(CommandHandler("funding", funding))
telegram_app.add_handler(CommandHandler("market", market))


# ================= WEBHOOK =================

@app.route("/")
def home():
    return "Bot running"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    update = Update.de_json(data, telegram_app.bot)
    loop.create_task(telegram_app.process_update(update))
    return "ok"


async def main():
    await telegram_app.initialize()
    await telegram_app.start()

    # set webhook
    await telegram_app.bot.set_webhook(RENDER_URL + "/webhook")

    # auto job
    telegram_app.job_queue.run_repeating(auto_send, interval=3600, first=10)


if __name__ == "__main__":
    loop.run_until_complete(main())

    app.run(host="0.0.0.0", port=10000)