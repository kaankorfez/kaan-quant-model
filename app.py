import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🚀 Kaan Quant Trading Dashboard")

###################################################
# DATA PREP
###################################################

def prepare_data(symbol, period="1y"):

    df = yf.download(symbol, period=period, auto_adjust=True, progress=False)

    if df is None or df.empty or len(df) < 220:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if "Close" not in df.columns:
        return None

    df = df.copy()

    df["SMA50"] = df["Close"].rolling(50).mean()
    df["SMA200"] = df["Close"].rolling(200).mean()

    df["RSI"] = ta.momentum.RSIIndicator(df["Close"]).rsi()

    macd = ta.trend.MACD(df["Close"])
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()

    df = df.dropna()

    return df


###################################################
# MARKET PANEL
###################################################

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

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

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

    st.header("📊 Piyasa Özeti")

    market = get_market_data()

    for k, v in market.items():
        st.metric(k, f"{v[0]:,}", f"{v[1]} %")

    st.divider()

    st.header("Model Parametreleri")

    rsi_buy = st.slider("RSI Al Eşiği", 10, 50, 30)
    rsi_sell = st.slider("RSI Sat Eşiği", 50, 90, 70)
    period = st.selectbox("Zaman Aralığı", ["6mo","1y","2y","3y"], index=1)
    risk_mode = st.checkbox("Piyasa Risk Modu Aktif")


###################################################
# HISSE LISTESI (Searchable Dropdown)
###################################################

bist_list = [
    "THYAO.IS","GARAN.IS","ASELS.IS","KCHOL.IS","SISE.IS",
    "AKBNK.IS","BIMAS.IS","EREGL.IS","TUPRS.IS","ISCTR.IS"
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

    stock = st.selectbox("Hisse Seç (arama destekli)", bist_list)

    df = prepare_data(stock, period)

    if df is not None:

        score, decision, trend = generate_signal(df, rsi_buy, rsi_sell)

        if risk_mode:
            xu100 = prepare_data("^XU100","1y")
            if xu100 is not None:
                _, m_decision, _ = generate_signal(xu100, rsi_buy, rsi_sell)
                if m_decision == "SELL":
                    decision = "RISK OFF"

        latest = df.iloc[-1]

        col1,col2,col3 = st.columns(3)
        col1.metric("Karar", decision)
        col2.metric("Trend", trend)
        col3.metric("RSI", round(float(latest["RSI"]),2))

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["Close"], name="Fiyat"))
        fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"], name="SMA50"))
        fig.add_trace(go.Scatter(x=df.index, y=df["SMA200"], name="SMA200"))
        fig.update_layout(template="plotly_dark", title=f"{stock} Fiyat & Ortalamalar")
        st.plotly_chart(fig, use_container_width=True)


###################################################
# BACKTEST
###################################################

with tab2:

    stock_bt = st.selectbox("Backtest Hisse", bist_list, key="bt")

    df = prepare_data(stock_bt, period)

    if df is not None:

        capital = 100000
        position = 0
        equity = []
        equity_index = []

        for i in range(200,len(df)):

            sub = df.iloc[:i+1]
            _, decision, _ = generate_signal(sub, rsi_buy, rsi_sell)
            price = df["Close"].iloc[i]

            if decision == "BUY" and position == 0:
                position = capital / price
                capital = 0

            elif decision == "SELL" and position > 0:
                capital = position * price
                position = 0

            current = capital if position==0 else position*price
            equity.append(current)
            equity_index.append(df.index[i])

        equity_series = pd.Series(equity,index=equity_index)

        total_return = (equity_series.iloc[-1] - 100000)/100000*100
        st.metric("Toplam Getiri %", round(total_return,2))

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=equity_series.index,y=equity_series,name="Equity Curve"))
        fig.update_layout(template="plotly_dark", title="Backtest Equity Curve")
        st.plotly_chart(fig, use_container_width=True)


###################################################
# SCREENER
###################################################

with tab3:

    st.subheader("Model Screener")

    results = []

    for stock in bist_list:

        df = prepare_data(stock, period)

        if df is None:
            continue

        score, decision, trend = generate_signal(df, rsi_buy, rsi_sell)

        if decision == "BUY":
            results.append([stock, trend, round(df["RSI"].iloc[-1],2)])

    if results:
        screener_df = pd.DataFrame(results, columns=["Hisse","Trend","RSI"])
        st.dataframe(screener_df)
    else:
        st.info("Şu an BUY sinyali yok.")


###################################################
# PORTFÖY
###################################################

with tab4:

    initial_value = st.number_input("Başlangıç Portföy Değeri", value=100000)

    portfolio = st.data_editor(
        pd.DataFrame({
            "Hisse":["THYAO.IS"],
            "Adet":[100]
        }),
        num_rows="dynamic"
    )

    total_value = 0
    labels = []
    values = []

    for _, row in portfolio.iterrows():

        try:
            df = yf.download(row["Hisse"], period="5d", progress=False)

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            price = float(df["Close"].iloc[-1])
            val = price * float(row["Adet"])

            total_value += val
            labels.append(row["Hisse"])
            values.append(val)

        except:
            continue

    st.metric("Güncel Portföy Değeri", round(total_value,2))

    if values:

        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.4)])
        fig.update_layout(template="plotly_dark", title="Portföy Dağılımı")
        st.plotly_chart(fig, use_container_width=True)

        growth = np.linspace(initial_value, total_value, 120)
        growth_series = pd.Series(growth)

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(y=growth_series,name="Portföy Büyüme"))
        fig2.update_layout(template="plotly_dark", title="Portföy Büyüme Simülasyonu")
        st.plotly_chart(fig2, use_container_width=True)
