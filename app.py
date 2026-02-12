import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🚀 Kaan Quant Trading Dashboard")

############################
# SIDEBAR
############################

with st.sidebar:
    st.header("Model Parametreleri")
    rsi_buy = st.slider("RSI Al Eşiği", 10, 50, 30)
    rsi_sell = st.slider("RSI Sat Eşiği", 50, 90, 70)

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

    df = df.dropna()

    return df

############################
# SIGNAL
############################

def generate_signal(df):
    latest = df.iloc[-1]
    score = 0

    trend = "Downtrend"
    if latest['SMA50'] > latest['SMA200']:
        score += 1
        trend = "Uptrend"

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

    return score, decision, trend

############################
# BACKTEST
############################

def backtest(df):

    capital = 100000
    position = 0
    equity = []
    drawdown = []
    trades = []

    for i in range(200, len(df)):

        sub = df.iloc[:i+1]
        score, decision, _ = generate_signal(sub)
        price = df['Close'].iloc[i]

        if decision == "BUY" and position == 0:
            position = capital / price
            entry = price
            capital = 0

        elif decision == "SELL" and position > 0:
            capital = position * price
            trades.append((price-entry)/entry)
            position = 0

        current_equity = capital if position == 0 else position * price
        equity.append(current_equity)

    equity_series = pd.Series(equity)
    peak = equity_series.cummax()
    dd = (equity_series / peak - 1) * 100

    total_return = (equity_series.iloc[-1] - 100000) / 100000 * 100
    win_rate = (np.array(trades) > 0).mean()*100 if trades else 0

    return total_return, win_rate, equity_series, dd

############################
# BIST LIST
############################

def get_bist_list():
    return ["THYAO.IS","ASELS.IS","GARAN.IS","BIMAS.IS","EREGL.IS",
            "TUPRS.IS","SAHOL.IS","KCHOL.IS","AKBNK.IS","ISCTR.IS"]

############################
# TABS
############################

tab1, tab2, tab3 = st.tabs(["📊 Analiz", "📈 Backtest", "🔎 Screener"])

############################
# ANALIZ
############################

with tab1:
    stock = st.text_input("Hisse Kodu")

    if stock:
        df = prepare_data(stock)

        if df is None:
            st.warning("Yeterli veri yok.")
        else:
            score, decision, trend = generate_signal(df)
            latest = df.iloc[-1]

            st.subheader("Model Kararı")
            col1,col2,col3 = st.columns(3)
            col1.metric("Karar", decision)
            col2.metric("Trend", trend)
            col3.metric("RSI", round(latest['RSI'],2))

            st.write("Bu grafik fiyat ile birlikte 50 ve 200 günlük ortalamaları gösterir. Trend yönünü anlamak için kullanılır.")

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name="Fiyat"))
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], name="SMA50"))
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA200'], name="SMA200"))
            fig.update_layout(template="plotly_dark",
                              title="Fiyat ve Trend Ortalamaları")
            st.plotly_chart(fig, use_container_width=True)

############################
# BACKTEST
############################

with tab2:
    stock_bt = st.text_input("Backtest Hisse", key="bt")

    if stock_bt:
        df = prepare_data(stock_bt, "3y")

        if df is not None:
            total_return, win_rate, equity, dd = backtest(df)

            st.subheader("Strateji Performansı")
            col1,col2 = st.columns(2)
            col1.metric("Toplam Getiri %", round(total_return,2))
            col2.metric("Win Rate %", round(win_rate,2))

            st.write("Equity Curve: Stratejinin zaman içindeki portföy değerini gösterir.")

            fig = go.Figure()
            fig.add_trace(go.Scatter(y=equity, name="Equity"))
            fig.update_layout(template="plotly_dark",
                              title="Equity Curve")
            st.plotly_chart(fig, use_container_width=True)

            st.write("Drawdown: En yüksek noktadan yaşanan düşüş yüzdesi.")

            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(y=dd, name="Drawdown"))
            fig2.update_layout(template="plotly_dark",
                               title="Drawdown (%)")
            st.plotly_chart(fig2, use_container_width=True)

############################
# SCREENER
############################

with tab3:
    st.subheader("BIST Trend & Momentum Tarama")

    results = []

    for symbol in get_bist_list():
        df = prepare_data(symbol, "1y")
        if df is None:
            continue

        score, decision, trend = generate_signal(df)
        rsi = round(df['RSI'].iloc[-1],2)

        results.append({
            "Hisse": symbol,
            "Skor": score,
            "Karar": decision,
            "Trend": trend,
            "RSI": rsi
        })

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values(by="Skor", ascending=False)

    st.write("Tüm hisseler skorlarına göre sıralanır. En yüksek skor en güçlü teknik yapıyı gösterir.")
    st.dataframe(results_df, use_container_width=True)
