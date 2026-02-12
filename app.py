import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

st.set_page_config(layout="wide")
st.title("KAAN QUANT TERMINAL")

# -----------------------------
# PARAMETRE PANELİ
# -----------------------------
st.sidebar.header("Model Ayarları")

rsi_upper = st.sidebar.slider("RSI Üst Seviye", 50, 70, 55)
rsi_lower = st.sidebar.slider("RSI Alt Seviye", 30, 50, 45)
atr_multiplier = st.sidebar.slider("ATR Stop Çarpanı", 1.0, 3.0, 1.5)
rr_ratio = st.sidebar.slider("Risk/Ödül Oranı", 1.0, 4.0, 2.0)

tabs = st.tabs(["Hisse Analiz", "BIST Screener", "Backtest"])

# ============================================================
# FONKSİYONLAR
# ============================================================

def prepare_data(ticker):
    df = yf.download(ticker, period="5y", interval="1d")

    if df.empty:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.dropna()

    df['SMA50'] = df['Close'].rolling(50).mean()
    df['SMA200'] = df['Close'].rolling(200).mean()

    df['RSI'] = ta.momentum.RSIIndicator(df['Close'], 14).rsi()
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['MACD_hist'] = macd.macd_diff()

    atr = ta.volatility.AverageTrueRange(df['High'], df['Low'], df['Close'], 14)
    df['ATR'] = atr.average_true_range()

    return df


def calculate_score(df):
    if len(df) < 200:
        return 0

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
    if df['RSI'].iloc[-1] > rsi_upper:
        score += 1
    elif df['RSI'].iloc[-1] < rsi_lower:
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


def calculate_risk(df):
    price = df['Close'].iloc[-1]
    atr_val = df['ATR'].iloc[-1]

    stop = price - (atr_multiplier * atr_val)
    risk = price - stop
    target = price + (rr_ratio * risk)

    return price, stop, target


def run_backtest(df):
    df = df.copy()
    df['Signal'] = 0

    for i in range(200, len(df)):
        temp = df.iloc[:i]
        sc = calculate_score(temp)

        if sc >= 3:
            df.loc[df.index[i], 'Signal'] = 1
        elif sc <= -2:
            df.loc[df.index[i], 'Signal'] = 0

    df['Return'] = df['Close'].pct_change()
    df['Strategy'] = df['Return'] * df['Signal'].shift(1)

    equity = (df['Strategy'].fillna(0) + 1).cumprod()
    total_return = equity.iloc[-1] - 1

    rolling_max = equity.cummax()
    drawdown = (equity - rolling_max) / rolling_max
    max_dd = drawdown.min()

    win_trades = df[df['Strategy'] > 0].shape[0]
    total_trades = df[df['Signal'] == 1].shape[0]
    win_rate = (win_trades / total_trades) * 100 if total_trades > 0 else 0

    return total_return, max_dd, win_rate, equity


# ============================================================
# TAB 1 – HİSSE ANALİZ
# ============================================================

with tabs[0]:

    ticker = st.text_input("Hisse Kodu (örn: THYAO.IS)")

    if ticker:
        df = prepare_data(ticker)

        if df is None:
            st.error("Veri bulunamadı.")
        else:
            score = calculate_score(df)
            decision = decision_from_score(score)
            price, stop, target = calculate_risk(df)

            col1, col2, col3 = st.columns(3)
            col1.metric("Skor", score)
            col2.metric("Karar", decision)
            col3.metric("Fiyat", round(price, 2))

            st.write(f"Stop: {round(stop,2)}")
            st.write(f"Hedef: {round(target,2)}")

            # Grafik
            fig = make_subplots(rows=3, cols=1,
                                shared_xaxes=True,
                                vertical_spacing=0.03,
                                row_heights=[0.6, 0.2, 0.2])

            fig.add_trace(go.Candlestick(
                x=df.index,
                open=df['Open'],
                high=df['High'],
                low=df['Low'],
                close=df['Close'],
                name="Fiyat"
            ), row=1, col=1)

            fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], name="SMA50"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA200'], name="SMA200"), row=1, col=1)

            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI"), row=2, col=1)

            fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name="MACD"), row=3, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MACD_signal'], name="Signal"), row=3, col=1)

            st.plotly_chart(fig, use_container_width=True)


# ============================================================
# TAB 2 – BIST SCREENER
# ============================================================

with tabs[1]:

    st.subheader("BIST Tarama")

    bist_list = [
        "THYAO.IS","GARAN.IS","ASELS.IS","BIMAS.IS","KCHOL.IS",
        "SAHOL.IS","EREGL.IS","TUPRS.IS","SISE.IS","AKBNK.IS"
    ]

    results = []

    for stock in bist_list:
        df = prepare_data(stock)
        if df is not None:
            sc = calculate_score(df)
            dec = decision_from_score(sc)
            results.append([stock, sc, dec])

    screener_df = pd.DataFrame(results, columns=["Hisse", "Skor", "Karar"])
    screener_df = screener_df.sort_values(by="Skor", ascending=False)

    st.dataframe(screener_df, use_container_width=True)


# ============================================================
# TAB 3 – BACKTEST
# ============================================================

with tabs[2]:

    ticker_bt = st.text_input("Backtest için hisse kodu")

    if ticker_bt:
        df = prepare_data(ticker_bt)

        if df is not None:
            total_return, max_dd, win_rate, equity = run_backtest(df)

            st.metric("Toplam Getiri %", round(total_return * 100, 2))
            st.metric("Max Drawdown %", round(max_dd * 100, 2))
            st.metric("Win Rate %", round(win_rate, 2))

            fig_eq = go.Figure()
            fig_eq.add_trace(go.Scatter(x=df.index, y=equity, name="Equity Curve"))
            st.plotly_chart(fig_eq, use_container_width=True)
