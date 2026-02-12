import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("📈 Kaan Quant Model")

###########################################
# SETTINGS
###########################################

with st.sidebar:
    st.header("Model Ayarları")
    rsi_buy = st.slider("RSI Al", 10, 50, 30)
    rsi_sell = st.slider("RSI Sat", 50, 90, 70)
    risk_ratio = st.slider("Risk/Ödül", 1.0, 4.0, 2.0)

###########################################
# DATA PREP (SAFE VERSION)
###########################################

def prepare_data(stock, period="1y"):

    try:
        df = yf.download(stock, period=period, auto_adjust=True, progress=False)
    except:
        return None

    if df is None or df.empty:
        return None

    df = df.copy()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    required_cols = ['Open','High','Low','Close','Volume']
    if not all(col in df.columns for col in required_cols):
        return None

    if len(df) < 250:  # SMA200 için minimum veri
        return None

    df['SMA50'] = df['Close'].rolling(50).mean()
    df['SMA200'] = df['Close'].rolling(200).mean()
    df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()

    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()

    df = df.dropna()

    if df.empty:
        return None

    return df

###########################################
# SIGNAL SAFE
###########################################

def generate_signal(df):

    if df is None or df.empty:
        return None, None

    latest = df.iloc[-1]
    score = 0

    if latest['SMA50'] > latest['SMA200']:
        score += 1

    if latest['RSI'] < rsi_buy:
        score += 1
    if latest['RSI'] > rsi_sell:
        score -= 1

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

###########################################
# RISK SAFE
###########################################

def calculate_risk(df):

    if df is None or df.empty:
        return None, None, None, None

    latest = df.iloc[-1]
    price = latest['Close']

    atr_indicator = ta.volatility.AverageTrueRange(
        df['High'], df['Low'], df['Close']
    )

    atr = atr_indicator.average_true_range().iloc[-1]

    stop = price - atr
    target = price + (price - stop) * risk_ratio

    rr = (target - price) / (price - stop)

    return round(price,2), round(stop,2), round(target,2), round(rr,2)

###########################################
# BACKTEST SAFE
###########################################

def backtest(df):

    if df is None or len(df) < 250:
        return None

    capital = 100000
    position = 0

    for i in range(200, len(df)):

        sub_df = df.iloc[:i+1]
        score, decision = generate_signal(sub_df)

        if decision is None:
            continue

        price = df['Close'].iloc[i]

        if decision == "BUY" and position == 0:
            position = capital / price
            capital = 0

        if decision == "SELL" and position > 0:
            capital = position * price
            position = 0

    if position > 0:
        capital = position * df['Close'].iloc[-1]

    return round(((capital-100000)/100000)*100,2)

###########################################
# SIMPLE STABLE BIST LIST
###########################################

def get_bist_list():
    return [
        "THYAO.IS","ASELS.IS","GARAN.IS","ISCTR.IS","AKBNK.IS",
        "KCHOL.IS","SAHOL.IS","BIMAS.IS","EREGL.IS","TUPRS.IS",
        "YKBNK.IS","SISE.IS","PETKM.IS","PGSUS.IS","SASA.IS"
    ]

###########################################
# TABS
###########################################

tab1, tab2, tab3 = st.tabs(["Analiz", "Backtest", "Screener"])

###########################################
# TAB 1
###########################################

with tab1:
    stock = st.text_input("Hisse Kodu (örn: THYAO.IS)")

    if stock:
        df = prepare_data(stock)

        if df is None:
            st.warning("Yeterli veri yok veya sembol hatalı.")
        else:
            score, decision = generate_signal(df)
            price, stop, target, rr = calculate_risk(df)

            col1, col2, col3 = st.columns(3)
            col1.metric("Karar", decision)
            col2.metric("Skor", score)
            col3.metric("Risk/Ödül", f"1:{rr}")

            st.write("Fiyat:", price)
            st.write("Stop:", stop)
            st.write("Hedef:", target)

###########################################
# TAB 2
###########################################

with tab2:
    stock_bt = st.text_input("Backtest Hisse", key="bt")

    if stock_bt:
        df = prepare_data(stock_bt, period="3y")
        result = backtest(df)

        if result is None:
            st.warning("Backtest için yeterli veri yok.")
        else:
            st.metric("Toplam Getiri %", result)

###########################################
# TAB 3
###########################################

with tab3:
    symbols = get_bist_list()

    buy_list = []
    sell_list = []

    for symbol in symbols:
        df = prepare_data(symbol, period="1y")
        if df is None:
            continue

        score, decision = generate_signal(df)

        if decision == "BUY":
            buy_list.append(symbol)

        if decision == "SELL":
            sell_list.append(symbol)

    col1, col2 = st.columns(2)

    col1.subheader("BUY")
    col1.write(buy_list)

    col2.subheader("SELL")
    col2.write(sell_list)
