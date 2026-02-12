import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🚀 Kaan Quant Trading Dashboard")

###################################################
# DATA PREP (STABLE VERSION)
###################################################

def prepare_data(symbol, period="1y"):

    if not symbol:
        return None

    # Liste gelirse ilk elemanı al
    if isinstance(symbol, (list, tuple, set)):
        if len(symbol) == 0:
            return None
        symbol = list(symbol)[0]

    symbol = str(symbol).strip()

    if symbol == "":
        return None

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, auto_adjust=True)
    except Exception:
        return None

    if df is None or df.empty:
        return None

    if "Close" not in df.columns:
        return None

    df = df.copy()
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df.dropna(subset=["Close"], inplace=True)

    # SMA200 için minimum bar
    if len(df) < 200:
        return None

    close = df["Close"]

    df["SMA50"] = close.rolling(50).mean()
    df["SMA200"] = close.rolling(200).mean()
    df["RSI"] = ta.momentum.RSIIndicator(close).rsi()

    macd = ta.trend.MACD(close)
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()

    df.dropna(inplace=True)

    if len(df) < 50:
        return None

    return df



###################################################
# MARKET PANEL
###################################################

def get_market_data():

    tickers = {
        "BIST100": "^XU100",
        "USDTRY": "USDTRY=X",
        "EURTRY": "EURTRY=X",
        "Altın": "GC=F",
        "Brent": "BZ=F",
        "BTC": "BTC-USD"
    }

    results = {}

    for name, ticker in tickers.items():
        try:
            df = yf.download(ticker, period="5d", progress=False, threads=False)

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            if len(df) < 2:
                continue

            last = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2])
            change = ((last - prev) / prev) * 100

            results[name] = (round(last,2), round(change,2))
        except:
            continue

    return results


###################################################
# SIGNAL ENGINE
###################################################

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


###################################################
# SIDEBAR
###################################################

with st.sidebar:

    st.header("Model Profili")

    model_profile = st.selectbox(
        "Profil Seç",
        ["Conservative","Balanced","Aggressive"]
    )

    if model_profile == "Conservative":
        rsi_buy, rsi_sell = 35, 65
    elif model_profile == "Balanced":
        rsi_buy, rsi_sell = 30, 70
    else:
        rsi_buy, rsi_sell = 25, 75

    period = st.selectbox("Zaman Aralığı", ["6mo","1y","2y","3y"], index=1)


###################################################
# BIST LIST (ÖRNEK - TAM LİSTENİ BURAYA KOY)
###################################################

bist_list = [
    "THYAO.IS","ASELS.IS","KCHOL.IS","BIMAS.IS",
    "EREGL.IS","GARAN.IS","AKBNK.IS","TUPRS.IS"
]


###################################################
# TABS
###################################################

tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Analiz","📈 Backtest","🔎 Screener","💼 Portföy"]
)


###################################################
# ANALIZ
###################################################

with tab1:

    stock = st.selectbox("Hisse Seç", bist_list)

    df = prepare_data(stock, period)

    if df is None:
        st.warning("Veri alınamadı veya yetersiz.")
    else:

        score, decision, trend = generate_signal(df, rsi_buy, rsi_sell)
        latest = df.iloc[-1]

        col1,col2,col3 = st.columns(3)
        col1.metric("Karar", decision)
        col2.metric("Trend", trend)
        col3.metric("RSI", round(float(latest["RSI"]),2))

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["Close"], name="Fiyat"))
        fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"], name="SMA50"))
        fig.add_trace(go.Scatter(x=df.index, y=df["SMA200"], name="SMA200"))
        fig.update_layout(template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)


###################################################
# BACKTEST
###################################################

with tab2:

    stock_bt = st.selectbox("Backtest Hisse", bist_list, key="bt")

    df = prepare_data(stock_bt, period)

    if df is None:
        st.warning("Backtest için yeterli veri yok.")
    else:

        initial_capital = 100000
        capital = initial_capital
        position = 0
        equity = []

        for i in range(200, len(df)):

            sub = df.iloc[:i+1]
            _, decision, _ = generate_signal(sub, rsi_buy, rsi_sell)

            price = df["Close"].iloc[i]

            if decision == "BUY" and position == 0:
                position = capital / price
                capital = 0

            elif decision == "SELL" and position > 0:
                capital = position * price
                position = 0

            current_value = capital if position==0 else position*price
            equity.append(current_value)

        if len(equity) > 0:

            equity_series = pd.Series(equity)

            total_return = (equity_series.iloc[-1]-initial_capital)/initial_capital*100
            max_drawdown = ((equity_series/equity_series.cummax())-1).min()*100

            col1,col2 = st.columns(2)
            col1.metric("Toplam Getiri %", round(total_return,2))
            col2.metric("Max Drawdown %", round(max_drawdown,2))

            fig = go.Figure()
            fig.add_trace(go.Scatter(y=equity_series,name="Equity"))
            fig.update_layout(template="plotly_dark")
            st.plotly_chart(fig,use_container_width=True)


###################################################
# SCREENER (SINIR YOK)
###################################################

with tab3:

    results = []

    for stock in bist_list:

        df = prepare_data(stock, period)
        if df is None:
            continue

        score, decision, trend = generate_signal(df, rsi_buy, rsi_sell)

        results.append([
            stock,
            score,
            decision,
            trend,
            round(df["RSI"].iloc[-1],2)
        ])

    if results:
        screener_df = pd.DataFrame(
            results,
            columns=["Hisse","Score","Karar","Trend","RSI"]
        ).sort_values(by="Score",ascending=False)

        st.dataframe(screener_df,use_container_width=True)
    else:
        st.info("Veri bulunamadı.")


###################################################
# PORTFÖY
###################################################

with tab4:

    portfolio = st.data_editor(
        pd.DataFrame({
            "Hisse":["THYAO.IS"],
            "Adet":[100],
            "Maliyet":[100.0]
        }),
        num_rows="dynamic"
    )

    total_value = 0
    total_cost = 0

    for _, row in portfolio.iterrows():

        try:
            symbol = str(row["Hisse"]).strip()
            df = yf.download(symbol,period="5d",progress=False,threads=False)

            if isinstance(df.columns,pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            price = float(df["Close"].iloc[-1])
            adet = float(row["Adet"])
            maliyet = float(row["Maliyet"])

            total_value += price*adet
            total_cost += maliyet*adet

        except:
            continue

    pnl_pct = ((total_value-total_cost)/total_cost*100) if total_cost>0 else 0

    col1,col2,col3 = st.columns(3)
    col1.metric("Portföy Değeri",round(total_value,2))
    col2.metric("Toplam Maliyet",round(total_cost,2))
    col3.metric("Kar/Zarar %",round(pnl_pct,2))

