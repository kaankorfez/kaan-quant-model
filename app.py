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

    if df is None or df.empty:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if "Close" not in df.columns:
        return None

    df = df.copy()

    close = df["Close"]

    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    close = pd.Series(close.values.flatten(), index=df.index)
    df["Close"] = close

    # Minimum bar kontrolü (SMA200 için)
    if len(df) < 200:
        return None

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

    st.header("📊 Piyasa Özeti")

    market = get_market_data()

    for k, v in market.items():
        st.metric(k, f"{v[0]:,}", f"{v[1]} %")

    st.divider()
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
    risk_mode = st.checkbox("Piyasa Risk Modu Aktif")


###################################################
# HISSE LISTESI
###################################################

bist_list = [ ... ]  # (Buraya senin uzun listen aynen gelecek, kısaltmadım)


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
        fig.update_layout(template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)


###################################################
# BACKTEST
###################################################

with tab2:

    stock_bt = st.selectbox("Backtest Hisse", bist_list, key="bt")

    df = prepare_data(stock_bt, period)

    if df is None:
        st.warning("Veri alınamadı.")
    else:

        initial_capital = 100000
        capital = initial_capital
        position = 0
        equity = []
        equity_index = []
        trades = []

        for i in range(1, len(df)):

            sub = df.iloc[:i+1]
            _, decision, _ = generate_signal(sub, rsi_buy, rsi_sell)
            price = df["Close"].iloc[i]
            date = df.index[i]

            if decision == "BUY" and position == 0:
                position = capital / price
                capital = 0
                trades.append((date,"BUY",price))

            elif decision == "SELL" and position > 0:
                capital = position * price
                position = 0
                trades.append((date,"SELL",price))

            current_value = capital if position==0 else position*price
            equity.append(current_value)
            equity_index.append(date)

        if len(equity) > 0:

            equity_series = pd.Series(equity,index=equity_index)

            total_return = (equity_series.iloc[-1]-initial_capital)/initial_capital*100

            rolling_max = equity_series.cummax()
            drawdown = (equity_series-rolling_max)/rolling_max
            max_drawdown = drawdown.min()*100

            col1,col2 = st.columns(2)
            col1.metric("Toplam Getiri %", round(total_return,2))
            col2.metric("Max Drawdown %", round(max_drawdown,2))

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=equity_series.index,y=equity_series,name="Equity"))
            fig.update_layout(template="plotly_dark")
            st.plotly_chart(fig,use_container_width=True)

            if trades:
                trade_df = pd.DataFrame(trades,columns=["Tarih","İşlem","Fiyat"])
                st.dataframe(trade_df)


###################################################
# SCREENER
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
        )
        screener_df = screener_df.sort_values(by="Score",ascending=False)
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
    labels = []
    values = []

    for _, row in portfolio.iterrows():

        try:
            df = yf.download(row["Hisse"],period="5d",progress=False)

            if isinstance(df.columns,pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            price = float(df["Close"].iloc[-1])
            adet = float(row["Adet"])
            maliyet = float(row["Maliyet"])

            current_val = price*adet
            cost_val = maliyet*adet

            total_value += current_val
            total_cost += cost_val

            labels.append(row["Hisse"])
            values.append(current_val)

        except:
            continue

    pnl = total_value-total_cost
    pnl_pct = (pnl/total_cost*100) if total_cost>0 else 0

    col1,col2,col3 = st.columns(3)
    col1.metric("Portföy Değeri",round(total_value,2))
    col2.metric("Toplam Maliyet",round(total_cost,2))
    col3.metric("Toplam Kar/Zarar %",round(pnl_pct,2))

    if values:
        fig = go.Figure(data=[go.Pie(labels=labels,values=values,hole=0.4)])
        fig.update_layout(template="plotly_dark")
        st.plotly_chart(fig,use_container_width=True)
