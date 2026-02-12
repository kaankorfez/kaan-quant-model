import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from ta.trend import SMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from datetime import datetime

st.set_page_config(layout="wide")
st.title("Kaan Quant Panel")

# ----------------------------
# BIST100 LIST (Yahoo format)
# ----------------------------
BIST100 = [
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


# ----------------------------
# DATA FETCH
# ----------------------------
@st.cache_data
def get_data(symbol):
    df = yf.download(symbol, period="2y", interval="1d", progress=False)
    df.dropna(inplace=True)
    return df

# ----------------------------
# MARKET RISK MODE
# ----------------------------
def market_regime():
    df = get_data("^XU100")
    if df.empty or len(df) < 200:
        return "Nötr", 0.8

    sma50 = SMAIndicator(df['Close'], 50).sma_indicator()
    sma200 = SMAIndicator(df['Close'], 200).sma_indicator()
    rsi = RSIIndicator(df['Close'], 14).rsi()

    trend = sma50.iloc[-1] > sma200.iloc[-1]
    momentum = rsi.iloc[-1] > 45

    if trend and momentum:
        return "Risk-On", 1.0
    elif not trend:
        return "Risk-Off", 0.6
    else:
        return "Nötr", 0.8

# ----------------------------
# SCORE ENGINE
# ----------------------------
def generate_signal(df, regime_multiplier):

    if df.empty or len(df) < 200:
        return 0, "Veri Yetersiz"

    sma50 = SMAIndicator(df['Close'], 50).sma_indicator()
    sma200 = SMAIndicator(df['Close'], 200).sma_indicator()
    rsi = RSIIndicator(df['Close'], 14).rsi()
    atr = AverageTrueRange(df['High'], df['Low'], df['Close'], 14).average_true_range()

    latest = df.iloc[-1]

    trend_score = 25 if sma50.iloc[-1] > sma200.iloc[-1] else 5
    momentum_score = 25 if 45 < rsi.iloc[-1] < 70 else 10
    volume_score = 25 if latest['Volume'] > df['Volume'].rolling(20).mean().iloc[-1] else 10
    volatility_score = 25 if atr.iloc[-1] < df['Close'].iloc[-1] * 0.05 else 10

    score = (trend_score + momentum_score + volume_score + volatility_score)
    score = score * regime_multiplier

    if score >= 70:
        decision = "AL"
    elif score >= 55:
        decision = "İZLE"
    else:
        decision = "UZAK DUR"

    return round(score,1), decision

# ----------------------------
# BACKTEST
# ----------------------------
def backtest(df):
    sma50 = SMAIndicator(df['Close'], 50).sma_indicator()
    sma200 = SMAIndicator(df['Close'], 200).sma_indicator()

    df['Position'] = np.where(sma50 > sma200, 1, 0)
    df['Return'] = df['Close'].pct_change()
    df['Strategy'] = df['Position'].shift(1) * df['Return']

    df['Cumulative_Strategy'] = (1 + df['Strategy']).cumprod()
    df['Cumulative_Market'] = (1 + df['Return']).cumprod()

    return df

# ----------------------------
# MENU
# ----------------------------
menu = st.sidebar.radio("Menü", ["Dashboard","Karar Motoru","Screener","Backtest","Portföyüm"])

regime, regime_multiplier = market_regime()

# ----------------------------
# DASHBOARD
# ----------------------------
if menu == "Dashboard":

    st.subheader(f"Piyasa Risk Modu: {regime}")

    scores = []
    for s in BIST100:
        df = get_data(s)
        score, decision = generate_signal(df, regime_multiplier)
        scores.append((s,score,decision))

    df_scores = pd.DataFrame(scores, columns=["Hisse","Skor","Karar"])
    df_scores = df_scores.sort_values("Skor", ascending=False)

    st.write("En Güçlü 5 Hisse")
    st.dataframe(df_scores.head())

# ----------------------------
# KARAR MOTORU
# ----------------------------
elif menu == "Karar Motoru":

    symbol = st.selectbox("Hisse Seç", BIST100)
    df = get_data(symbol)

    score, decision = generate_signal(df, regime_multiplier)

    st.subheader(f"Genel Skor: {score}")
    st.subheader(f"Karar: {decision}")

    st.write("Senaryo 1 – Trend Devam:")
    st.write("Trend korunursa pozisyon taşınabilir.")

    st.write("Senaryo 2 – Düzeltme:")
    st.write("Geri çekilme destek bölgesine gelirse ekleme düşünülebilir.")

    st.write("Senaryo 3 – Negatif:")
    st.write("Trend kırılırsa pozisyon azaltılmalı.")

# ----------------------------
# SCREENER
# ----------------------------
elif menu == "Screener":

    results = []
    for s in BIST100:
        df = get_data(s)
        score, decision = generate_signal(df, regime_multiplier)
        results.append((s,score,decision))

    df_all = pd.DataFrame(results, columns=["Hisse","Skor","Karar"])
    df_all = df_all.sort_values("Skor", ascending=False)

    st.dataframe(df_all)

# ----------------------------
# BACKTEST
# ----------------------------
elif menu == "Backtest":

    symbol = st.selectbox("Hisse Seç", BIST100)
    df = get_data(symbol)
    df_bt = backtest(df)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_bt.index, y=df_bt['Cumulative_Strategy'], name="Strateji"))
    fig.add_trace(go.Scatter(x=df_bt.index, y=df_bt['Cumulative_Market'], name="Pasif Tut"))

    st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# PORTFÖY
# ----------------------------
elif menu == "Portföyüm":

    st.subheader("Portföy Girişi")

    portfolio_data = st.text_area("Sembol,Adet,Alış Fiyatı (örnek: ASELS.IS,100,45)")

    start_value = st.number_input("Başlangıç Portföy Değeri", value=100000)

    if portfolio_data:
        rows = portfolio_data.split("\n")
        data = []

        total_value = 0

        for row in rows:
            sym, qty, buy = row.split(",")
            df = get_data(sym.strip())
            price = df['Close'].iloc[-1]
            value = float(qty)*price
            total_value += value
            data.append([sym.strip(), qty, buy, price, value])

        df_port = pd.DataFrame(data, columns=["Hisse","Adet","Alış","Güncel","Toplam Değer"])
        st.dataframe(df_port)

        fig = go.Figure(data=[go.Pie(labels=df_port["Hisse"], values=df_port["Toplam Değer"])])
        st.subheader("Portföy Dağılımı")
        st.plotly_chart(fig)

        growth = total_value / start_value
        growth_series = np.linspace(start_value, total_value, 100)

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(y=growth_series, name="Portföy Büyümesi"))
        st.subheader("Portföy Büyüme Grafiği")
        st.plotly_chart(fig2)

        st.write(f"Toplam Güncel Değer: {round(total_value,2)}")
        st.write(f"Toplam Büyüme Oranı: %{round((growth-1)*100,2)}")
