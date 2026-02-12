import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🚀 Kaan Quant Investment Dashboard")

############################
# MARKET REGIME
############################

def market_regime():
    df = yf.download("^XU100", period="2y", auto_adjust=True, progress=False)
    if df is None or df.empty or len(df) < 200:
        return "Nötr", 0.8

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    sma50 = df['Close'].rolling(50).mean()
    sma200 = df['Close'].rolling(200).mean()

    if sma50.iloc[-1] > sma200.iloc[-1]:
        return "Risk-On 🟢", 1
    else:
        return "Risk-Off 🔴", 0.6

regime, regime_multiplier = market_regime()

st.sidebar.metric("Piyasa Modu", regime)

############################
# DATA
############################

def prepare_data(stock, period="2y"):
    df = yf.download(stock, period=period, auto_adjust=True, progress=False)

    if df is None or df.empty or len(df) < 250:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[['Open','High','Low','Close','Volume']]

    df['SMA50'] = df['Close'].rolling(50).mean()
    df['SMA200'] = df['Close'].rolling(200).mean()
    df['RSI'] = ta.momentum.RSIIndicator(df['Close'].squeeze(), 14).rsi()

    macd = ta.trend.MACD(df['Close'].squeeze())
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()

    df = df.dropna()

    return df

############################
# SCORE ENGINE (0-100)
############################

def generate_signal(df):

    latest = df.iloc[-1]
    score = 0

    trend_score = 25 if latest['SMA50'] > latest['SMA200'] else 5
    momentum_score = 25 if 45 < latest['RSI'] < 70 else 10
    macd_score = 25 if latest['MACD'] > latest['MACD_signal'] else 10
    volume_score = 25 if latest['Volume'] > df['Volume'].rolling(20).mean().iloc[-1] else 10

    score = (trend_score + momentum_score + macd_score + volume_score) * regime_multiplier

    if score >= 70:
        decision = "AL"
    elif score >= 55:
        decision = "İZLE"
    else:
        decision = "UZAK DUR"

    return round(score,1), decision

############################
# BACKTEST (Trend based)
############################

def backtest(df):

    df['Position'] = np.where(df['SMA50'] > df['SMA200'], 1, 0)
    df['Return'] = df['Close'].pct_change()
    df['Strategy'] = df['Position'].shift(1) * df['Return']

    df['Cum_Strategy'] = (1 + df['Strategy']).cumprod()
    df['Cum_Market'] = (1 + df['Return']).cumprod()

    total_return = (df['Cum_Strategy'].iloc[-1] - 1) * 100
    max_dd = ((df['Cum_Strategy'] / df['Cum_Strategy'].cummax()) - 1).min() * 100

    return total_return, max_dd, df

############################
# BIST LIST
############################

def get_bist_list():
    return [
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

############################
# TABS
############################

tab1, tab2, tab3, tab4 = st.tabs(["📊 Analiz", "📈 Backtest", "🔎 Screener", "💼 Portföy"])

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
            score, decision = generate_signal(df)
            latest = df.iloc[-1]

            col1,col2,col3 = st.columns(3)
            col1.metric("Karar", decision)
            col2.metric("Skor", score)
            col3.metric("RSI", round(latest['RSI'],2))

            st.markdown("### Senaryo Yorumu")
            st.write("Trend devam ederse pozisyon korunabilir.")
            st.write("Düzeltmelerde destek bölgeleri takip edilmeli.")
            st.write("Trend kırılımında risk azaltılmalı.")

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
            total_return, max_dd, df_bt = backtest(df)

            col1,col2 = st.columns(2)
            col1.metric("Toplam Getiri %", round(total_return,2))
            col2.metric("Max Drawdown %", round(max_dd,2))

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_bt.index, y=df_bt['Cum_Strategy'], name="Strateji"))
            fig.add_trace(go.Scatter(x=df_bt.index, y=df_bt['Cum_Market'], name="Pasif"))
            fig.update_layout(template="plotly_dark",
                              title="Strateji vs Pasif Getiri")
            st.plotly_chart(fig, use_container_width=True)

############################
# SCREENER
############################

with tab3:

    results = []

    for symbol in get_bist_list():
        df = prepare_data(symbol, "1y")
        if df is None:
            continue

        score, decision = generate_signal(df)

        results.append({
            "Hisse": symbol,
            "Skor": score,
            "Karar": decision
        })

    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values(by="Skor", ascending=False)

    st.dataframe(results_df, use_container_width=True)

############################
# PORTFÖY
############################

with tab4:

    portfolio_input = st.text_area("Sembol,Adet,Alış Fiyatı")
    start_value = st.number_input("Başlangıç Portföy Değeri", value=100000)

    if portfolio_input:

        rows = portfolio_input.split("\n")
        data=[]
        total=0

        for row in rows:
            sym,qty,buy=row.split(",")
            df=prepare_data(sym.strip())
            if df is None:
                continue
            price=df['Close'].iloc[-1]
            value=float(qty)*price
            total+=value
            data.append([sym.strip(),qty,buy,price,value])

        df_port=pd.DataFrame(data,columns=["Hisse","Adet","Alış","Güncel","Toplam"])
        st.dataframe(df_port,use_container_width=True)

        fig=go.Figure(data=[go.Pie(labels=df_port["Hisse"],
                                   values=df_port["Toplam"],
                                   hole=0.4)])
        fig.update_layout(template="plotly_dark", title="Portföy Dağılımı")
        st.plotly_chart(fig,use_container_width=True)

        growth=(total/start_value-1)*100
        st.metric("Toplam Getiri %",round(growth,2))
