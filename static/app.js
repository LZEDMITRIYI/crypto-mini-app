function switchTab(tabName, button) {
    const pages = document.querySelectorAll(".tab-page");
    const navItems = document.querySelectorAll(".nav-item");

    pages.forEach(page => {
        page.classList.remove("active");
    });

    navItems.forEach(item => {
        item.classList.remove("active");
    });

    const targetPage = document.getElementById(`page-${tabName}`);

    if (targetPage) {
        targetPage.classList.add("active");
    }

    button.classList.add("active");

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
}

const tg = window.Telegram?.WebApp;

if (tg) {
    tg.ready();
    tg.expand();
}

async function getPrice() {
    const coin = document.getElementById("coinInput").value || "BTC";

    const res = await fetch(`/api/price/${coin}`);
    const data = await res.json();

    document.getElementById("priceResult").innerText =
        data.price ? `${data.symbol} = $${data.price}` : "Не вдалося отримати курс";
}

async function convert() {
    const amount = document.getElementById("amountInput").value;
    const from = document.getElementById("fromInput").value;
    const to = document.getElementById("toInput").value;

    if (!amount || !from || !to) {
        document.getElementById("convertResult").innerText = "Заповни всі поля";
        return;
    }

    const res = await fetch(`/api/convert?amount=${amount}&from_coin=${from}&to_coin=${to}`);
    const data = await res.json();

    document.getElementById("convertResult").innerText =
        data.result
            ? `${data.amount} ${data.from_coin} = ${data.result.toFixed(6)} ${data.to_coin}`
            : "Не вдалося виконати конвертацію";
}

async function getTop() {
    const res = await fetch("/api/top");
    const data = await res.json();

    if (!data.coins) {
        document.getElementById("topResult").innerHTML = "Не вдалося отримати топ";
        return;
    }

    const html = data.coins.map(coin =>
        `<div class="coin-row"><b>${coin.symbol}</b> — $${coin.price}</div>`
    ).join("");

    document.getElementById("topResult").innerHTML = html;
}

let priceChart = null;

async function getChart() {
    const coin = document.getElementById("chartInput").value || "BTC";

    const res = await fetch(`/api/chart/${coin}`);
    const data = await res.json();

    if (!data.ok || !data.prices || data.prices.length === 0) {
        document.getElementById("chartResult").innerText =
            "Не вдалося отримати графік";
        return;
    }

    document.getElementById("chartResult").innerText =
        `Графік ${data.symbol} за останні 24 години`;

    const ctx = document.getElementById("priceChart");

    if (priceChart) {
        priceChart.destroy();
    }

    priceChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: `${data.symbol} / USD`,
                    data: data.prices,
                    borderWidth: 2,
                    tension: 0.35,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: {
                        color: "#ffffff"
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: "#aaaaaa"
                    },
                    grid: {
                        color: "#333333"
                    }
                },
                y: {
                    ticks: {
                        color: "#aaaaaa"
                    },
                    grid: {
                        color: "#333333"
                    }
                }
            }
        }
    });
}
async function getNews() {
    const res = await fetch("/api/news");
    const data = await res.json();

    if (!data.news) {
        document.getElementById("newsResult").innerHTML = "Не вдалося отримати новини";
        return;
    }

    const html = data.news.map(item =>
        `<p><a href="${item.link}" target="_blank">${item.title}</a></p>`
    ).join("");

    document.getElementById("newsResult").innerHTML = html;
}
function getTelegramChatId() {
    const user = window.Telegram?.WebApp?.initDataUnsafe?.user;

    if (!user || !user.id) {
        return null;
    }

    return user.id;
}

async function addPriceAlert() {
    const chatId = getTelegramChatId();
    const symbol = document.getElementById("alertSymbol").value;
    const targetPrice = document.getElementById("alertPrice").value;
    const direction = document.getElementById("alertDirection").value;

    if (!chatId) {
        document.getElementById("priceAlertResult").innerText =
            "Відкрий Mini App саме через Telegram";
        return;
    }

    if (!symbol || !targetPrice) {
        document.getElementById("priceAlertResult").innerText =
            "Заповни монету і ціну";
        return;
    }

    const res = await fetch("/api/alerts/price", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            chat_id: chatId,
            symbol: symbol,
            target_price: Number(targetPrice),
            direction: direction,
        }),
    });

    const data = await res.json();

    document.getElementById("priceAlertResult").innerText =
        data.ok
            ? "✅ Порогове сповіщення створено"
            : "⛔ Не вдалося створити сповіщення";
}

async function addPeriodicAlert() {
    const chatId = getTelegramChatId();
    const symbol = document.getElementById("periodicSymbol").value;
    const interval = document.getElementById("periodicInterval").value;

    if (!chatId) {
        document.getElementById("periodicAlertResult").innerText =
            "Відкрий Mini App саме через Telegram";
        return;
    }

    if (!symbol || !interval) {
        document.getElementById("periodicAlertResult").innerText =
            "Заповни монету і інтервал";
        return;
    }

    const res = await fetch("/api/alerts/periodic", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            chat_id: chatId,
            symbol: symbol,
            interval_minutes: Number(interval),
        }),
    });

    const data = await res.json();

    document.getElementById("periodicAlertResult").innerText =
        data.ok
            ? "✅ Періодичне сповіщення створено"
            : "⛔ Не вдалося створити сповіщення";
}
async function stopAllAlerts() {
    const chatId = getTelegramChatId();

    if (!chatId) {
        document.getElementById("stopAlertsResult").innerText =
            "Відкрий Mini App саме через Telegram";
        return;
    }

    const res = await fetch("/api/alerts/stop", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            chat_id: chatId,
        }),
    });

    const data = await res.json();

    if (data.ok) {
        document.getElementById("stopAlertsResult").innerText =
            `✅ Сповіщення зупинено. Видалено: ${
                data.removed_price_alerts + data.removed_periodic_alerts
            }`;
    } else {
        document.getElementById("stopAlertsResult").innerText =
            "⛔ Не вдалося зупинити сповіщення";
    }
}