import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import numpy as np

st.title("Kaan Quant Dashboard")

ticker = st.text_input("Hisse Kodu (örn: THYAO.IS)")

# ----------------------------
# SCORE HESAPLAMA
# ----------------------------
def calculate_score(df):

    if len(df) < 200:
        return 0

    df = df.copy()

    df['SMA50'] = df['Close'].rolling(50).mean()
    df['SMA200'] = df['Close'].rolling(200).mean()

    rsi = ta.momentum.RSIIndicator(df['Close'], window=14)
    df['RSI'] = rsi.rsi()

    macd = ta.trend.MACD(df['Close'])
    df['MACD_hist'] = macd.macd_diff()

    score = 0

    # Trend
    if df['Close'].iloc[-1] > df['SMA200'].iloc[-1]:
        score += 2
    else:
        score -= 2

    if df['SMA50'].iloc[-1] > df['SMA200'].iloc[-1]:
        score += 1
    else:
        score -= 1

    # Momentum
    if df['RSI'].iloc[-1] > 55:
        score += 1
    elif df['RSI'].iloc[-1] < 45:
        score -= 1

    if df['MACD_hist'].iloc[-1] > 0:
        score += 1
    else:
        score -= 1

    # Volume
    if df['Volume'].iloc[-3:].mean() > df['Volume'].rolling(20).mean().iloc[-1]:
        score += 1
    else:
        score -= 1

    return score


# ----------------------------
# KARAR MOTORU
# ----------------------------
def decision_from_score(score):
    if score >= 5:
        return "STRONG BUY"
    elif score >= 3:
        return "BUY"
    elif score >= 1:
        return "WATCH"
    elif score <= -3:
        return "STRONG SELL"
    elif score <= -2:
        return "SELL"
    else:
        return "NEUTRAL"


# ----------------------------
# RİSK HESABI
# ----------------------------
def calculate_risk(df):

    df = df.copy()

    atr = ta.volatility.AverageTrueRange(
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        window=14
    )

    df['ATR'] = atr.average_true_range()

    price = df['Close'].iloc[-1]
    atr_val = df['ATR'].iloc[-1]

    stop = price - (1.5 * atr_val)
    risk = price - stop
    target = price + (2 * risk)

    return price, stop, target


# ----------------------------
# ANA ÇALIŞMA BLOĞU
# ----------------------------
if ticker:

    try:
        df = yf.download(ticker, period="5y", interval="1d")

        if df.empty:
            st.error("Veri bulunamadı.")
            st.stop()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.dropna()

        score = calculate_score(df)
        decision = decision_from_score(score)
        price, stop, target = calculate_risk(df)

        st.subheader(f"Skor: {score}")
        st.subheader(f"Karar: {decision}")

        st.write(f"Güncel Fiyat: {round(price,2)}")
        st.write(f"Stop Loss: {round(stop,2)}")
        st.write(f"Hedef: {round(target,2)}")
        st.write("Risk/Ödül: 1:2")

        # ----------------------------
        # BASİT BACKTEST
        # ----------------------------
        df['Signal'] = 0

        for i in range(200, len(df)):
            temp = df.iloc[:i]
            sc = calculate_score(temp)

            if sc >= 3:
                df.loc[df.index[i], 'Signal'] = 1
            elif sc <= -2:
                df.loc[df.index[i], 'Signal'] = -1

        df['Return'] = df['Close'].pct_change()
        df['Strategy'] = df['Return'] * df['Signal'].shift(1)

        total_return = (df['Strategy'].fillna(0) + 1).prod() - 1

        st.subheader(f"Backtest Toplam Getiri: %{round(total_return*100,2)}")

    except Exception as e:
        st.error("Bir hata oluştu.")
        st.write(e)
