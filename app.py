import asyncio
import os
import time

import feedparser
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://127.0.0.1:8000")
PRICE_ALERTS = []
PERIODIC_ALERTS = []

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

TOP_COINS = [
    ("bitcoin", "BTC"),
    ("ethereum", "ETH"),
    ("tether", "USDT"),
    ("ripple", "XRP"),
    ("binancecoin", "BNB"),
    ("solana", "SOL"),
    ("usd-coin", "USDC"),
    ("dogecoin", "DOGE"),
    ("cardano", "ADA"),
    ("tron", "TRX"),
]


def get_price(from_coin, to_coin="USD"):
    url = (
        "https://min-api.cryptocompare.com/data/price"
        f"?fsym={from_coin.upper()}&tsyms={to_coin.upper()}"
    )

    try:
        response = requests.get(url, timeout=10)
        print("CryptoCompare price:", response.status_code, response.text[:300])
    except requests.RequestException as e:
        print("CryptoCompare request error:", e)
        return None

    if response.status_code != 200:
        return None

    return response.json().get(to_coin.upper())


def get_top_coins():
    result = []

    for coin_id, symbol in TOP_COINS:
        price = get_price(symbol, "USD")

        if price is not None:
            result.append({
                "id": coin_id,
                "symbol": symbol,
                "price": price,
            })

    return result if result else None


def get_crypto_news():
    feed_url = "https://cointelegraph.com/rss"

    try:
        feed = feedparser.parse(feed_url)
    except Exception:
        return []

    return [
        {
            "title": entry.title,
            "link": entry.link,
        }
        for entry in feed.entries[:5]
    ]


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/api/price/{symbol}")
async def api_price(symbol: str):
    price = get_price(symbol, "USD")

    return {
        "symbol": symbol.upper(),
        "price": price,
    }


@app.get("/api/convert")
async def api_convert(
    amount: float = Query(...),
    from_coin: str = Query(...),
    to_coin: str = Query(...),
):
    price = get_price(from_coin, to_coin)

    if price is None:
        return {
            "ok": False,
            "result": None,
        }

    return {
        "ok": True,
        "amount": amount,
        "from_coin": from_coin.upper(),
        "to_coin": to_coin.upper(),
        "rate": price,
        "result": amount * price,
    }


@app.get("/api/top")
async def api_top():
    return {
        "coins": get_top_coins(),
    }

@app.get("/api/news")
async def api_news():
    return {
        "news": get_crypto_news(),
    }

@app.get("/api/alerts")
async def api_get_alerts():
    return {
        "price_alerts": PRICE_ALERTS,
        "periodic_alerts": PERIODIC_ALERTS,
    }


@app.post("/api/alerts/price")
async def api_add_price_alert(payload: dict):
    try:
        alert = {
            "id": int(time.time() * 1000),
            "chat_id": payload.get("chat_id"),
            "symbol": str(payload.get("symbol", "")).upper(),
            "target_price": float(payload.get("target_price")),
            "direction": payload.get("direction"),
            "created_at": int(time.time()),
            "triggered": False,
        }
    except Exception:
        return {
            "ok": False,
            "error": "Invalid alert data",
        }

    if not alert["chat_id"] or not alert["symbol"] or alert["direction"] not in ["above", "below"]:
        return {
            "ok": False,
            "error": "Invalid alert data",
        }

    PRICE_ALERTS.append(alert)

    return {
        "ok": True,
        "alert": alert,
    }


@app.post("/api/alerts/periodic")
async def api_add_periodic_alert(payload: dict):
    try:
        alert = {
            "id": int(time.time() * 1000),
            "chat_id": payload.get("chat_id"),
            "symbol": str(payload.get("symbol", "")).upper(),
            "interval_minutes": int(payload.get("interval_minutes")),
            "last_sent_at": 0,
            "created_at": int(time.time()),
            "active": True,
        }
    except Exception:
        return {
            "ok": False,
            "error": "Invalid periodic alert data",
        }

    if not alert["chat_id"] or not alert["symbol"] or alert["interval_minutes"] <= 0:
        return {
            "ok": False,
            "error": "Invalid periodic alert data",
        }

    PERIODIC_ALERTS.append(alert)

    return {
        "ok": True,
        "alert": alert,
    }

@app.post("/api/alerts/stop")
async def api_stop_alerts(payload: dict):
    chat_id = payload.get("chat_id")

    if not chat_id:
        return {
            "ok": False,
            "error": "Chat ID is required",
        }

    before_price_count = len(PRICE_ALERTS)
    before_periodic_count = len(PERIODIC_ALERTS)

    PRICE_ALERTS[:] = [
        alert for alert in PRICE_ALERTS
        if str(alert.get("chat_id")) != str(chat_id)
    ]

    PERIODIC_ALERTS[:] = [
        alert for alert in PERIODIC_ALERTS
        if str(alert.get("chat_id")) != str(chat_id)
    ]

    removed_price_count = before_price_count - len(PRICE_ALERTS)
    removed_periodic_count = before_periodic_count - len(PERIODIC_ALERTS)

    return {
        "ok": True,
        "removed_price_alerts": removed_price_count,
        "removed_periodic_alerts": removed_periodic_count,
    }


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(
                "🚀 Відкрити Mini App",
                web_app=WebAppInfo(url=WEBAPP_URL),
            )
        ]
    ]

    await update.message.reply_text(
        "👋 Привіт! Я LZECryptoBot.\n\n"
        "Натисни кнопку нижче, щоб відкрити Mini App:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
@app.get("/api/chart/{symbol}")
async def api_chart(symbol: str):
    url = (
        "https://min-api.cryptocompare.com/data/v2/histohour"
        f"?fsym={symbol.upper()}&tsym=USD&limit=23"
    )

    try:
        response = requests.get(url, timeout=10)
    except requests.RequestException:
        return {
            "ok": False,
            "symbol": symbol.upper(),
            "labels": [],
            "prices": [],
        }

    if response.status_code != 200:
        return {
            "ok": False,
            "symbol": symbol.upper(),
            "labels": [],
            "prices": [],
        }

    data = response.json().get("Data", {}).get("Data", [])

    if not data:
        return {
            "ok": False,
            "symbol": symbol.upper(),
            "labels": [],
            "prices": [],
        }

    prices = [point["close"] for point in data]
    labels = [f"{i}:00" for i in range(len(prices))]

    return {
        "ok": True,
        "symbol": symbol.upper(),
        "labels": labels,
        "prices": prices,
    }

telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))

async def alerts_worker():
    while True:
        now = int(time.time())

        # порогові сповіщення
        for alert in PRICE_ALERTS:
            if alert.get("triggered"):
                continue

            symbol = alert["symbol"]
            price = get_price(symbol, "USD")

            if price is None:
                continue

            direction = alert["direction"]
            target_price = alert["target_price"]

            should_trigger = (
                direction == "above" and price >= target_price
            ) or (
                direction == "below" and price <= target_price
            )

            if should_trigger:
                alert["triggered"] = True

                direction_text = "вище" if direction == "above" else "нижче"

                await telegram_app.bot.send_message(
                    chat_id=alert["chat_id"],
                    text=(
                        f"🔔 Сповіщення по {symbol}\n\n"
                        f"Поточна ціна: ${price:.4f}\n"
                        f"Поріг: {direction_text} ${target_price:.4f}"
                    ),
                )

        # періодичні сповіщення 
        for alert in PERIODIC_ALERTS:
            if not alert.get("active"):
                continue

            interval_seconds = alert["interval_minutes"] * 60

            if now - alert["last_sent_at"] < interval_seconds:
                continue

            symbol = alert["symbol"]
            price = get_price(symbol, "USD")

            if price is None:
                continue

            alert["last_sent_at"] = now

            await telegram_app.bot.send_message(
                chat_id=alert["chat_id"],
                text=(
                    f"📊 Оновлення ціни {symbol}\n\n"
                    f"Поточна ціна: ${price:.4f}\n"
                    f"Інтервал: кожні {alert['interval_minutes']} хв."
                ),
            )

        await asyncio.sleep(30)

@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

@app.on_event("startup")
async def startup():
    await telegram_app.initialize()
    await telegram_app.start()

    if WEBAPP_URL.startswith("https://"):
        webhook_url = f"{WEBAPP_URL}/telegram-webhook"
        await telegram_app.bot.set_webhook(webhook_url)
        print(f"Webhook set to: {webhook_url}")
    else:
        print("Local mode: webhook not set")

    asyncio.create_task(alerts_worker())


@app.on_event("shutdown")
async def shutdown():
    await telegram_app.stop()
    await telegram_app.shutdown()
