import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🚀 Kaan Quant Dashboard")

############################
# SIDEBAR
############################

with st.sidebar:
    st.header("Model Ayarları")

    rsi_buy = st.slider("RSI Al", 10, 50, 30)
    rsi_sell = st.slider("RSI Sat", 50, 90, 70)
    risk_ratio = st.slider("Risk/Ödül", 1.0, 4.0, 2.0)

############################
# DATA
############################

def prepare_data(stock, period="2y"):
    df = yf.download(stock, period=period, auto_adjust=True, progress=False)

    if df is None or df.empty or len(df) < 250:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df['SMA50'] = df['Close'].rolling(50).mean()
    df['SMA200'] = df['Close'].rolling(200).mean()
    df['RSI'] = ta.momentum.RSIIndicator(df['Close'], 14).rsi()

    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()

    df['ATR'] = ta.volatility.AverageTrueRange(
        df['High'], df['Low'], df['Close']
    ).average_true_range()

    df = df.dropna()

    return df if not df.empty else None

############################
# SIGNAL
############################

def generate_signal(df):
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

############################
# ADVANCED BACKTEST
############################

def backtest(df):

    capital = 100000
    position = 0
    equity_curve = []
    trades = []

    for i in range(200, len(df)):

        sub = df.iloc[:i+1]
        score, decision = generate_signal(sub)
        price = df['Close'].iloc[i]

        if decision == "BUY" and position == 0:
            position = capital / price
            entry_price = price
            capital = 0

        elif decision == "SELL" and position > 0:
            capital = position * price
            trades.append((price-entry_price)/entry_price)
            position = 0

        current_equity = capital if position == 0 else position * price
        equity_curve.append(current_equity)

    equity_series = pd.Series(equity_curve)

    total_return = (equity_series.iloc[-1] - 100000) / 100000 * 100
    drawdown = (equity_series / equity_series.cummax() - 1).min() * 100
    win_rate = (np.array(trades) > 0).mean() * 100 if trades else 0
    sharpe = equity_series.pct_change().mean() / equity_series.pct_change().std() * np.sqrt(252)

    return {
        "return": round(total_return,2),
        "max_dd": round(drawdown,2),
        "win_rate": round(win_rate,2),
        "trades": len(trades),
        "sharpe": round(sharpe,2),
        "equity": equity_series
    }

############################
# SCREENER (IMPROVED)
############################

def get_bist_list():
    return ["THYAO.IS","ASELS.IS","GARAN.IS","BIMAS.IS","EREGL.IS",
            "TUPRS.IS","SAHOL.IS","KCHOL.IS","AKBNK.IS","ISCTR.IS"]

############################
# TABS
############################

tab1, tab2, tab3 = st.tabs(["📊 Analiz", "📈 Backtest", "🔎 Screener"])

############################
# ANALYSIS TAB
############################

with tab1:
    stock = st.text_input("Hisse Kodu (örn: THYAO.IS)")

    if stock:
        df = prepare_data(stock)

        if df is None:
            st.warning("Yeterli veri yok.")
        else:
            score, decision = generate_signal(df)
            latest = df.iloc[-1]

            col1, col2, col3 = st.columns(3)
            col1.metric("Karar", decision)
            col2.metric("Skor", score)
            col3.metric("RSI", round(latest['RSI'],2))

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name="Close"))
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], name="SMA50"))
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA200'], name="SMA200"))
            fig.update_layout(template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

############################
# BACKTEST TAB
############################

with tab2:
    stock_bt = st.text_input("Backtest Hisse", key="bt")

    if stock_bt:
        df = prepare_data(stock_bt, "3y")

        if df is not None:
            results = backtest(df)

            col1,col2,col3,col4,col5 = st.columns(5)
            col1.metric("Toplam Getiri %", results["return"])
            col2.metric("Max Drawdown %", results["max_dd"])
            col3.metric("Win Rate %", results["win_rate"])
            col4.metric("İşlem Sayısı", results["trades"])
            col5.metric("Sharpe", results["sharpe"])

            fig = go.Figure()
            fig.add_trace(go.Scatter(y=results["equity"], name="Equity Curve"))
            fig.update_layout(template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

############################
# SCREENER TAB
############################

with tab3:
    st.write("Trend + Momentum Filtresi")

    symbols = get_bist_list()
    strong = []

    for symbol in symbols:
        df = prepare_data(symbol, "1y")
        if df is None:
            continue

        score, decision = generate_signal(df)
        latest = df.iloc[-1]

        if decision == "BUY" and latest['Volume'] > df['Volume'].mean():
            strong.append((symbol, score))

    strong = sorted(strong, key=lambda x: x[1], reverse=True)

    for s in strong:
        st.write(f"{s[0]} | Skor: {s[1]}")
