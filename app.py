import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.title("📈 Kaan Quant Trading Model")

#############################################
# MODEL SETTINGS PANEL
#############################################

with st.sidebar:
    st.header("⚙️ Model Ayarları")

    rsi_buy = st.slider("RSI Al Alt Sınır", 10, 50, 30)
    rsi_sell = st.slider("RSI Sat Üst Sınır", 50, 90, 70)
    risk_ratio = st.slider("Risk / Ödül Oranı", 1.0, 4.0, 2.0)

#############################################
# DATA PREPARATION
#############################################

def prepare_data(stock, period="1y"):
    df = yf.download(stock, period=period, auto_adjust=True)

    if df.empty:
        return None

    df = df.copy()

    # Eğer multiindex gelirse düzelt
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[['Open','High','Low','Close','Volume']]

    df['SMA50'] = df['Close'].rolling(50).mean()
    df['SMA200'] = df['Close'].rolling(200).mean()

    df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()

    return df.dropna()

#############################################
# SIGNAL ENGINE
#############################################

def generate_signal(df):
    latest = df.iloc[-1]
    score = 0

    # Trend
    if latest['SMA50'] > latest['SMA200']:
        score += 1

    # RSI
    if latest['RSI'] < rsi_buy:
        score += 1
    if latest['RSI'] > rsi_sell:
        score -= 1

    # MACD
    if latest['MACD'] > latest['MACD_signal']:
        score += 1
    else:
        score -= 1

    if score >= 2:
        decision = "BUY"
    elif score <= -1:
        decision = "SELL"
    else:
        decision = "WATCH"

    return score, decision

#############################################
# RISK MANAGEMENT
#############################################

def calculate_risk(df):
    latest = df.iloc[-1]
    price = latest['Close']

    atr = ta.volatility.AverageTrueRange(
        df['High'], df['Low'], df['Close']
    ).average_true_range().iloc[-1]

    stop = price - atr
    target = price + (price - stop) * risk_ratio

    rr = (target - price) / (price - stop)

    return round(price,2), round(stop,2), round(target,2), round(rr,2)

#############################################
# BACKTEST
#############################################

def backtest(df):
    capital = 100000
    position = 0
    entry_price = 0

    for i in range(200, len(df)):

        sma50 = df['SMA50'].iloc[i]
        sma200 = df['SMA200'].iloc[i]
        rsi = df['RSI'].iloc[i]
        macd = df['MACD'].iloc[i]
        macd_sig = df['MACD_signal'].iloc[i]
        price = df['Close'].iloc[i]

        score = 0

        if sma50 > sma200:
            score += 1
        if rsi < rsi_buy:
            score += 1
        if rsi > rsi_sell:
            score -= 1
        if macd > macd_sig:
            score += 1
        else:
            score -= 1

        # BUY
        if score >= 2 and position == 0:
            position = capital / price
            entry_price = price
            capital = 0

        # SELL
        if score <= -1 and position > 0:
            capital = position * price
            position = 0

    if position > 0:
        capital = position * df['Close'].iloc[-1]

    total_return = ((capital - 100000) / 100000) * 100
    return round(total_return,2)

#############################################
# TABS
#############################################

tab1, tab2, tab3 = st.tabs(["📊 Analiz", "📈 Backtest", "🔎 BIST Screener"])

#############################################
# TAB 1 ANALYSIS
#############################################

with tab1:
    stock = st.text_input("Hisse Kodu Gir (örn: THYAO.IS)")

    if stock:
        df = prepare_data(stock)

        if df is None:
            st.error("Veri alınamadı.")
        else:
            score, decision = generate_signal(df)
            price, stop, target, rr = calculate_risk(df)

            col1, col2, col3 = st.columns(3)

            col1.metric("Karar", decision)
            col2.metric("Skor", score)
            col3.metric("Risk/Ödül", f"1:{rr}")

            st.write(f"Güncel Fiyat: {price}")
            st.write(f"Stop Loss: {stop}")
            st.write(f"Hedef: {target}")

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='Close'))
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], name='SMA50'))
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA200'], name='SMA200'))
            st.plotly_chart(fig, use_container_width=True)

#############################################
# TAB 2 BACKTEST
#############################################

with tab2:
    stock_bt = st.text_input("Backtest Hisse Kodu (örn: THYAO.IS)", key="bt")

    if stock_bt:
        df = prepare_data(stock_bt, period="3y")
        if df is not None:
            result = backtest(df)
            st.metric("Backtest Toplam Getiri (%)", result)

#############################################
# TAB 3 BIST SCREENER (DYNAMIC)
#############################################

with tab3:

    st.write("BIST Momentum Tarama")

    # Dinamik BIST 100 liste
    bist100 = pd.read_html(
        "https://tr.wikipedia.org/wiki/BIST_100"
    )[2]

    symbols = bist100['Kod'].tolist()
    symbols = [s + ".IS" for s in symbols]

    results = []

    for symbol in symbols:
        df = prepare_data(symbol, period="6mo")
        if df is None:
            continue

        score, decision = generate_signal(df)

        if decision == "BUY":
            results.append(symbol)

    st.write("BUY Sinyali Verenler:")
    st.write(results)
