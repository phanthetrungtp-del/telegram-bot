import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
CHAT_ID = os.getenv("CHAT_ID")


# ================= SAFE REQUEST =================

def safe_get(url):
    try:
        r = requests.get(url, timeout=5)
        print("STATUS:", r.status_code, url)

        if r.status_code == 200:
            return r.json()

        return None
    except Exception as e:
        print("REQUEST ERROR:", e)
        return None


# ================= API =================

def get_price():
    try:
        url = "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT"
        data = safe_get(url)

        if data and "data" in data:
            return float(data["data"][0]["last"])
    except:
        pass
    return None


def get_funding():
    try:
        url = "https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP"
        data = safe_get(url)

        if data and "data" in data:
            return float(data["data"][0]["fundingRate"]) * 100
    except:
        pass
    return None


def get_fear():
    try:
        url = "https://api.alternative.me/fng/"
        data = safe_get(url)

        if data:
            return data["data"][0]["value"], data["data"][0]["value_classification"]
    except:
        pass
    return None, None


def get_dominance():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        data = safe_get(url)

        if data:
            return data["data"]["market_cap_percentage"]["btc"]
    except:
        pass
    return None


def get_long_short():
    # OKX
    try:
        url = "https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio?ccy=BTC"
        data = safe_get(url)

        if data and "data" in data and len(data["data"]) > 0:
            return float(data["data"][0]["ratio"]), None
    except:
        pass

    # Binance fallback
    try:
        url = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=5m&limit=1"
        data = safe_get(url)

        if isinstance(data, list) and len(data) > 0:
            return float(data[0]["longAccount"]), float(data[0]["shortAccount"])
    except:
        pass

    return None, None


# ================= TELEGRAM =================

app = ApplicationBuilder().token(TOKEN).build()


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    p = get_price()
    await update.message.reply_text(
        f"💰 BTC = ${p:,.0f}" if p else "Không lấy được giá"
    )


async def funding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    f = get_funding()
    await update.message.reply_text(
        f"📈 Funding: {f:.4f}%" if f else "Không lấy được funding"
    )


async def fear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    v, s = get_fear()
    await update.message.reply_text(
        f"😨 Fear: {v} ({s})" if v else "Không lấy được fear"
    )


async def dominance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    d = get_dominance()
    await update.message.reply_text(
        f"👑 Dominance: {d:.2f}%" if d else "Không lấy được dominance"
    )


async def longshort(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    long, short = get_long_short()

    if long is None:
        return await update.message.reply_text("Không lấy được Long/Short")

    if short:
        await update.message.reply_text(f"⚔️ Long: {long:.2f} | Short: {short:.2f}")
    else:
        await update.message.reply_text(f"⚔️ Ratio: {long:.2f}")


async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    p = get_price()
    f = get_funding()
    fear, state = get_fear()
    d = get_dominance()
    long, short = get_long_short()

    msg = "📊 Market Overview\n\n"
    msg += f"BTC: ${p:,.0f}\n" if p else "BTC: N/A\n"
    msg += f"Funding: {f:.4f}%\n" if f else "Funding: N/A\n"
    msg += f"Fear: {fear} ({state})\n" if fear else "Fear: N/A\n"
    msg += f"Dominance: {d:.2f}%\n" if d else "Dominance: N/A\n"

    if long:
        msg += f"Long/Short: {long:.2f}\n" if not short else f"Long: {long:.2f} | Short: {short:.2f}\n"

    msg += "\nData by CoinGecko"

    await update.message.reply_text(msg)


# ================= AUTO JOB =================

async def auto_market(context: ContextTypes.DEFAULT_TYPE):
    try:
        p = get_price()
        f = get_funding()
        fear, state = get_fear()
        d = get_dominance()
        long, short = get_long_short()

        msg = "⏰ Auto Update\n\n"
        msg += f"BTC: ${p:,.0f}\n" if p else "BTC: N/A\n"
        msg += f"Funding: {f:.4f}%\n" if f else "Funding: N/A\n"
        msg += f"Fear: {fear} ({state})\n" if fear else "Fear: N/A\n"
        msg += f"Dominance: {d:.2f}%\n" if d else "Dominance: N/A\n"

        if long:
            msg += f"Long/Short: {long:.2f}\n" if not short else f"Long: {long:.2f} | Short: {short:.2f}\n"

        await context.bot.send_message(chat_id=CHAT_ID, text=msg)

    except Exception as e:
        print("AUTO ERROR:", e)


# ================= HANDLER =================

app.add_handler(CommandHandler("price", price))
app.add_handler(CommandHandler("funding", funding))
app.add_handler(CommandHandler("fear", fear))
app.add_handler(CommandHandler("dominance", dominance))
app.add_handler(CommandHandler("longshort", longshort))
app.add_handler(CommandHandler("market", market))


# ================= RUN =================

if __name__ == "__main__":
    print("Bot running...")

    job_queue = app.job_queue

    if job_queue:
        job_queue.run_repeating(auto_market, interval=3600, first=30)
    else:
        print("JobQueue lỗi ❌ (thiếu job-queue package)")

    app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=RENDER_URL + "/webhook",
        url_path="webhook"
    )