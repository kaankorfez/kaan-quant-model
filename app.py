import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🚀 Kaan Quant Trading Dashboard")

############################################
# DATA SAFE PREP
############################################

def prepare_data(stock, period="2y"):

    df = yf.download(stock, period=period, auto_adjust=True, progress=False)

    if df is None or df.empty or len(df) < 220:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if "Close" not in df.columns:
        return None

    df = df.copy()

    df["SMA50"] = df["Close"].rolling(50).mean()
    df["SMA200"] = df["Close"].rolling(200).mean()

    rsi = ta.momentum.RSIIndicator(close=df["Close"], window=14)
    df["RSI"] = rsi.rsi()

    macd = ta.trend.MACD(close=df["Close"])
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()

    df.dropna(inplace=True)

    return df

############################################
# MARKET PANEL
############################################

def get_market_data():

    tickers = {
        "BIST100": "^XU100",
        "USDTRY": "USDTRY=X",
        "EURTRY": "EURTRY=X",
        "Altın (Ons)": "GC=F",
        "Gümüş (Ons)": "SI=F",
        "Brent": "BZ=F",
        "BTC": "BTC-USD"
    }

    results = {}

    for name, ticker in tickers.items():
        try:
            df = yf.download(ticker, period="5d", progress=False)

            if df is None or df.empty or len(df) < 2:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            last = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2])

            change = ((last - prev) / prev) * 100

            results[name] = {
                "price": round(last, 2),
                "change": round(change, 2)
            }

        except:
            continue

    return results

############################################
# SIGNAL ENGINE
############################################

def generate_signal(df, rsi_buy, rsi_sell):

    latest = df.iloc[-1]
    score = 0
    trend = "Downtrend"

    if latest["SMA50"] > latest["SMA200"]:
        score += 1
        trend = "Uptrend"

    if latest["RSI"] < rsi_buy:
        score += 1

    if latest["RSI"] > rsi_sell:
        score -= 1

    if latest["MACD"] > latest["MACD_signal"]:
        score += 1
    else:
        score -= 1

    if score >= 2:
        decision = "BUY"
    elif score <= -1:
        decision = "SELL"
    else:
        decision = "WATCH"

    return score, decision, trend

############################################
# SIDEBAR
############################################

with st.sidebar:

    st.header("📊 Piyasa Özeti")

    market = get_market_data()

    for k, v in market.items():

        price = f"{v['price']:,}"
        change = f"{v['change']} %"

        delta_color = "inverse" if k in ["USDTRY", "EURTRY"] else "normal"

        st.metric(label=k, value=price, delta=change, delta_color=delta_color)

    st.divider()
    st.header("Model Parametreleri")

    rsi_buy = st.slider("RSI Al Eşiği", 10, 50, 30)
    rsi_sell = st.slider("RSI Sat Eşiği", 50, 90, 70)

    period = st.selectbox("Zaman Aralığı", ["6mo", "1y", "2y", "3y"], index=1)

    risk_mode = st.checkbox("Piyasa Risk Modu Aktif")

############################################
# TABS
############################################

tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Analiz", "📈 Backtest", "🔎 Screener", "💼 Portföy"]
)

############################################
# ANALIZ
############################################

with tab1:

    stock = st.text_input("Hisse Kodu")

    if stock:

        df = prepare_data(stock, period)

        if df is None:
            st.warning("Yeterli veri yok.")
        else:

            score, decision, trend = generate_signal(df, rsi_buy, rsi_sell)

            if risk_mode:
                xu100 = prepare_data("^XU100", "1y")
                if xu100 is not None:
                    _, m_decision, _ = generate_signal(xu100, rsi_buy, rsi_sell)
                    if m_decision == "SELL":
                        decision = "RISK OFF"

            latest = df.iloc[-1]

            col1, col2, col3 = st.columns(3)
            col1.metric("Karar", decision)
            col2.metric("Trend", trend)
            col3.metric("RSI", round(float(latest["RSI"]), 2))

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df.index, y=df["Close"], name="Fiyat"))
            fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"], name="SMA50"))
            fig.add_trace(go.Scatter(x=df.index, y=df["SMA200"], name="SMA200"))
            fig.update_layout(template="plotly_dark", title="Fiyat ve Trend Ortalamaları")
            st.plotly_chart(fig, use_container_width=True)

############################################
# BACKTEST
############################################

with tab2:

    stock_bt = st.text_input("Backtest Hisse", key="bt")

    if stock_bt:

        df = prepare_data(stock_bt, period)

        if df is not None:

            capital = 100000
            position = 0
            equity = []

            for i in range(200, len(df)):

                sub = df.iloc[:i+1]
                score, decision, _ = generate_signal(sub, rsi_buy, rsi_sell)
                price = df["Close"].iloc[i]

                if decision == "BUY" and position == 0:
                    position = capital / price
                    capital = 0

                elif decision == "SELL" and position > 0:
                    capital = position * price
                    position = 0

                current = capital if position == 0 else position * price
                equity.append(current)

            if equity:
                equity_series = pd.Series(equity)
                total_return = (equity_series.iloc[-1] - 100000) / 100000 * 100

                st.metric("Toplam Getiri %", round(total_return, 2))

                fig = go.Figure()
                fig.add_trace(go.Scatter(y=equity_series, name="Equity"))
                fig.update_layout(template="plotly_dark", title="Equity Curve")
                st.plotly_chart(fig, use_container_width=True)

############################################
# PORTFÖY
############################################

with tab4:

    st.subheader("Portföy Takibi")

    initial_value = st.number_input("Başlangıç Portföy Değeri", value=100000)

    portfolio = st.data_editor(
        pd.DataFrame({
            "Hisse": ["THYAO.IS"],
            "Adet": [100],
            "Maliyet": [100]
        }),
        num_rows="dynamic"
    )

    total_value = 0
    labels = []
    values = []

    for _, row in portfolio.iterrows():
        try:
            df = yf.download(row["Hisse"], period="5d", progress=False)

            if df is None or df.empty:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            price = float(df["Close"].iloc[-1])
            val = price * float(row["Adet"])

            total_value += val
            labels.append(row["Hisse"])
            values.append(val)

        except:
            continue

    st.metric("Güncel Portföy Değeri", round(total_value, 2))

    if values:
        fig = go.Figure(data=[go.Pie(labels=labels, values=values)])
        fig.update_layout(template="plotly_dark", title="Portföy Dağılımı")
        st.plotly_chart(fig, use_container_width=True)

    growth = pd.Series(np.linspace(initial_value, total_value, 100))

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(y=growth, name="Portföy Büyüme"))
    fig2.update_layout(template="plotly_dark", title="Portföy Büyüme Grafiği")
    st.plotly_chart(fig2, use_container_width=True)
