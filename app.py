import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🚀 Kaan Quant Trading Dashboard")

###################################################
# DATA PREP (ADVANCED QUANT VERSION)
###################################################

def prepare_data(symbol, period="1y"):

    if not symbol:
        return None

    symbol = str(symbol).strip()

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, auto_adjust=True)
    except:
        return None

    if df is None or len(df) < 252:
        return None

    df = df.copy()

    df["SMA50"] = df["Close"].rolling(50).mean()
    df["SMA200"] = df["Close"].rolling(200).mean()

    df["RSI"] = ta.momentum.RSIIndicator(df["Close"]).rsi()

    macd = ta.trend.MACD(df["Close"])
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()

    df["ATR"] = ta.volatility.AverageTrueRange(
        df["High"], df["Low"], df["Close"]
    ).average_true_range()

    df["Volume_MA"] = df["Volume"].rolling(20).mean()

    df["Volatility"] = df["Close"].pct_change().rolling(20).std() * np.sqrt(252)

    df["52W_High"] = df["Close"].rolling(252).max()

    df["Donchian_Low"] = df["Low"].rolling(20).min()

    df.dropna(inplace=True)

    return df


###################################################
# MARKET TREND (BIST100 CONFIRMATION)
###################################################

def get_market_trend():

    df = yf.download("^XU100", period="1y", progress=False)

    df["SMA50"] = df["Close"].rolling(50).mean()
    df["SMA200"] = df["Close"].rolling(200).mean()

    if df["SMA50"].iloc[-1] > df["SMA200"].iloc[-1]:
        return "UP"
    else:
        return "DOWN"


###################################################
# 10 POINT QUANT SCORING ENGINE
###################################################

def generate_quant_score(df, market_trend):

    latest = df.iloc[-1]
    score = 0
    explanation = []

    if latest["SMA50"] > latest["SMA200"]:
        score += 2
        explanation.append("Trend yukarı (SMA50 > SMA200)")

    if latest["Close"] > df["Close"].iloc[-20]:
        score += 2
        explanation.append("20 günlük momentum pozitif")

    if 40 < latest["RSI"] < 70:
        score += 1
        explanation.append("RSI sağlıklı bölgede")

    if latest["MACD"] > latest["MACD_signal"]:
        score += 1
        explanation.append("MACD pozitif")

    if latest["Volume"] > latest["Volume_MA"]:
        score += 1
        explanation.append("Hacim ortalamanın üstünde")

    if latest["Volatility"] < 0.50:
        score += 1
        explanation.append("Volatilite kontrol altında")

    if latest["Close"] > 0.85 * latest["52W_High"]:
        score += 1
        explanation.append("52W high'a yakın")

    if market_trend == "UP":
        score += 1
        explanation.append("Piyasa yönü destekliyor")

    if score >= 8:
        decision = "STRONG BUY"
    elif score >= 6:
        decision = "BUY"
    elif score >= 4:
        decision = "HOLD"
    elif score >= 2:
        decision = "SELL"
    else:
        decision = "STRONG SELL"

    return score, decision, explanation


###################################################
# ATR RISK MODEL
###################################################

def risk_model(df):

    latest = df.iloc[-1]
    atr = latest["ATR"]
    entry = latest["Close"]

    stop_loss = entry - (2 * atr)
    highest_close = df["Close"].rolling(20).max().iloc[-1]
    trailing_stop = highest_close - (2 * atr)
    support_level = min(
        df["Low"].rolling(20).min().iloc[-1],
        latest["Donchian_Low"]
    )

    risk_pct = ((entry - stop_loss) / entry) * 100

    if risk_pct < 3:
        risk_score = "LOW RISK"
    elif risk_pct < 6:
        risk_score = "MEDIUM RISK"
    else:
        risk_score = "HIGH RISK"

    return stop_loss, trailing_stop, support_level, risk_score


###################################################
# BIST LIST
###################################################

bist_list = [
"AEFES.IS","AGHOL.IS","AKBNK.IS","AKSA.IS","AKSEN.IS","ALARK.IS","ALTNY.IS","ANSGR.IS","ARCLK.IS","ASELS.IS",
"ASTOR.IS","BALSU.IS","BIMAS.IS","BRSAN.IS","BRYAT.IS","BSOKE.IS","BTCIM.IS","CANTE.IS","CCOLA.IS","CIMSA.IS",
"CWENE.IS","DAPGM.IS","DOAS.IS","DOHOL.IS","DSTKF.IS","ECILC.IS","EFOR.IS","EGEEN.IS","EKGYO.IS","ENERY.IS",
"ENJSA.IS","ENKAI.IS","EREGL.IS","EUPWR.IS","FENER.IS","FROTO.IS","GARAN.IS","GENIL.IS","GESAN.IS","GLRMK.IS",
"GRSEL.IS","GRTHO.IS","GSRAY.IS","GUBRF.IS","HALKB.IS","HEKTS.IS","ISCTR.IS","ISMEN.IS","IZENR.IS","KCAER.IS",
"KCHOL.IS","KLRHO.IS","KONTR.IS","KRDMD.IS","KTLEV.IS","KUYAS.IS","MAGEN.IS","MAVI.IS","MGROS.IS","MIATK.IS",
"MPARK.IS","OBAMS.IS","ODAS.IS","OTKAR.IS","OYAKC.IS","PASEU.IS","PATEK.IS","PETKM.IS","PGSUS.IS","QUAGR.IS",
"RALYH.IS","REEDR.IS","SAHOL.IS","SASA.IS","SISE.IS","SKBNK.IS","SOKM.IS","TABGD.IS","TAVHL.IS","TCELL.IS",
"THYAO.IS","TKFEN.IS","TOASO.IS","TRALT.IS","TRENJ.IS","TRMET.IS","TSKB.IS","TSPOR.IS","TTKOM.IS","TTRAK.IS",
"TUKAS.IS","TUPRS.IS","TUREX.IS","TURSG.IS","ULKER.IS","VAKBN.IS","VESTL.IS","YEOTK.IS","YKBNK.IS","ZOREN.IS"
]


###################################################
# TABS
###################################################

tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Analiz","📈 Backtest","🔎 Screener","💼 Portföy"]
)


###################################################
# ANALIZ TAB
###################################################

with tab1:

    stock = st.selectbox("Hisse Seç", bist_list)

    df = prepare_data(stock, "1y")

    if df is None:
        st.warning("Veri alınamadı.")
    else:

        market_trend = get_market_trend()

        score, decision, explanation = generate_quant_score(df, market_trend)

        stop_loss, trailing_stop, support_level, risk_score = risk_model(df)

        col1,col2,col3,col4 = st.columns(4)

        col1.metric("Quant Skor", score)
        col2.metric("Karar", decision)
        col3.metric("Risk", risk_score)
        col4.metric("Piyasa", market_trend)

        st.markdown("### Karar Açıklaması")
        for e in explanation:
            st.write("•", e)

        st.markdown("### Risk Seviyeleri")
        st.write(f"Stop Loss: {round(stop_loss,2)}")
        st.write(f"Trailing Stop: {round(trailing_stop,2)}")
        st.write(f"Destek: {round(support_level,2)}")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["Close"], name="Fiyat"))
        fig.add_trace(go.Scatter(x=df.index, y=df["SMA50"], name="SMA50"))
        fig.add_trace(go.Scatter(x=df.index, y=df["SMA200"], name="SMA200"))
        fig.update_layout(template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)


###################################################
# BACKTEST (10 POINT MODEL BASED)
###################################################

with tab2:

    stock_bt = st.selectbox("Backtest Hisse", bist_list)

    df = prepare_data(stock_bt, "2y")

    if df is None:
        st.warning("Backtest için veri yok.")
    else:

        market_trend = get_market_trend()

        initial_capital = 100000
        capital = initial_capital
        position = 0
        equity = []

        for i in range(252, len(df)):

            sub = df.iloc[:i+1]
            score, decision, _ = generate_quant_score(sub, market_trend)

            price = df["Close"].iloc[i]

            if decision in ["STRONG BUY","BUY"] and position == 0:
                position = capital / price
                capital = 0

            elif decision in ["SELL","STRONG SELL"] and position > 0:
                capital = position * price
                position = 0

            current_value = capital if position==0 else position*price
            equity.append(current_value)

        equity_series = pd.Series(equity)

        total_return = (equity_series.iloc[-1]-initial_capital)/initial_capital*100
        max_dd = ((equity_series/equity_series.cummax())-1).min()*100
        sharpe = (equity_series.pct_change().mean()/equity_series.pct_change().std())*np.sqrt(252)

        col1,col2,col3 = st.columns(3)
        col1.metric("Toplam Getiri %", round(total_return,2))
        col2.metric("Max Drawdown %", round(max_dd,2))
        col3.metric("Sharpe Ratio", round(sharpe,2))

        fig = go.Figure()
        fig.add_trace(go.Scatter(y=equity_series,name="Equity"))
        fig.update_layout(template="plotly_dark")
        st.plotly_chart(fig,use_container_width=True)


###################################################
# SCREENER (NEW MODEL)
###################################################

with tab3:

    results = []

    market_trend = get_market_trend()

    for stock in bist_list:

        df = prepare_data(stock, "1y")
        if df is None:
            continue

        score, decision, _ = generate_quant_score(df, market_trend)

        results.append([stock, score, decision])

    if results:
        screener_df = pd.DataFrame(
            results,
            columns=["Hisse","Quant Skor","Karar"]
        ).sort_values(by="Quant Skor",ascending=False)

        st.dataframe(screener_df,use_container_width=True)


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
            df = yf.download(row["Hisse"],period="5d",progress=False)
            price = float(df["Close"].iloc[-1])
            total_value += price*row["Adet"]
            total_cost += row["Maliyet"]*row["Adet"]
        except:
            continue

    pnl_pct = ((total_value-total_cost)/total_cost*100) if total_cost>0 else 0

    col1,col2,col3 = st.columns(3)
    col1.metric("Portföy Değeri",round(total_value,2))
    col2.metric("Toplam Maliyet",round(total_cost,2))
    col3.metric("Kar/Zarar %",round(pnl_pct,2))
