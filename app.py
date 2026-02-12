import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.markdown("""
<style>
.metric-card {
    padding:20px;
    border-radius:15px;
    background-color:#111;
    box-shadow:0px 4px 15px rgba(0,0,0,0.4);
}
</style>
""", unsafe_allow_html=True)

st.title("📊 Kaan Quant Investment Panel")

# -----------------------
# BIST100 SAMPLE LIST
# -----------------------
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


# -----------------------
# DATA
# -----------------------
@st.cache_data
def get_data(symbol):
    df = yf.download(symbol, period="2y", interval="1d", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[['Open','High','Low','Close','Volume']]
    df.dropna(inplace=True)
    return df

# -----------------------
# INDICATORS
# -----------------------
def add_indicators(df):
    df["SMA50"] = df["Close"].rolling(50).mean()
    df["SMA200"] = df["Close"].rolling(200).mean()
    df["RSI"] = compute_rsi(df["Close"],14)
    df["ATR"] = compute_atr(df,14)
    return df

def compute_rsi(series, period):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100/(1+rs))

def compute_atr(df, period):
    high_low = df['High'] - df['Low']
    high_close = abs(df['High'] - df['Close'].shift())
    low_close = abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return true_range.rolling(period).mean()

# -----------------------
# MARKET MODE
# -----------------------
def market_regime():
    df = get_data("^XU100")
    if df.empty:
        return "Nötr",0.8
    df = add_indicators(df)
    if df["SMA50"].iloc[-1] > df["SMA200"].iloc[-1]:
        return "Risk-On",1
    elif df["SMA50"].iloc[-1] < df["SMA200"].iloc[-1]:
        return "Risk-Off",0.6
    else:
        return "Nötr",0.8

# -----------------------
# SCORE
# -----------------------
def generate_signal(df, regime_multiplier):
    if len(df) < 200:
        return 0,"Veri Yetersiz"
    df = add_indicators(df)

    trend = 25 if df["SMA50"].iloc[-1] > df["SMA200"].iloc[-1] else 5
    momentum = 25 if 45 < df["RSI"].iloc[-1] < 70 else 10
    volume = 25 if df["Volume"].iloc[-1] > df["Volume"].rolling(20).mean().iloc[-1] else 10
    volatility = 25 if df["ATR"].iloc[-1] < df["Close"].iloc[-1]*0.05 else 10

    score = (trend+momentum+volume+volatility)*regime_multiplier

    if score>=70:
        decision="AL"
    elif score>=55:
        decision="İZLE"
    else:
        decision="UZAK DUR"

    return round(score,1),decision

# -----------------------
# MENU
# -----------------------
menu = st.sidebar.radio("Menü",
["Dashboard","Karar Motoru","Screener","Backtest","Portföyüm"])

regime,regime_multiplier = market_regime()

# -----------------------
# DASHBOARD
# -----------------------
if menu=="Dashboard":

    col1,col2,col3 = st.columns(3)
    col1.metric("Piyasa Modu", regime)
    col2.metric("Risk Çarpanı", regime_multiplier)

    scores=[]
    for s in BIST100:
        df=get_data(s)
        score,decision=generate_signal(df,regime_multiplier)
        scores.append((s,score,decision))

    df_scores=pd.DataFrame(scores,columns=["Hisse","Skor","Karar"])
    df_scores=df_scores.sort_values("Skor",ascending=False)

    st.subheader("🔥 En Güçlü 5")
    st.dataframe(df_scores.head(),use_container_width=True)

# -----------------------
# KARAR MOTORU
# -----------------------
elif menu=="Karar Motoru":

    symbol=st.selectbox("Hisse",BIST100)
    df=get_data(symbol)

    score,decision=generate_signal(df,regime_multiplier)

    col1,col2=st.columns(2)
    col1.metric("Skor",score)
    col2.metric("Karar",decision)

    st.markdown("### Olası Senaryolar")
    st.write("Trend devam ederse pozisyon korunabilir.")
    st.write("Düzeltmede destek bölgeleri izlenmeli.")
    st.write("Trend kırılırsa risk azaltılmalı.")

# -----------------------
# SCREENER
# -----------------------
elif menu=="Screener":

    results=[]
    for s in BIST100:
        df=get_data(s)
        score,decision=generate_signal(df,regime_multiplier)
        results.append((s,score,decision))

    df_all=pd.DataFrame(results,columns=["Hisse","Skor","Karar"])
    df_all=df_all.sort_values("Skor",ascending=False)

    st.dataframe(df_all,use_container_width=True)

# -----------------------
# BACKTEST
# -----------------------
elif menu=="Backtest":

    symbol=st.selectbox("Hisse",BIST100)
    df=get_data(symbol)
    df=add_indicators(df)

    df["Position"]=np.where(df["SMA50"]>df["SMA200"],1,0)
    df["Return"]=df["Close"].pct_change()
    df["Strategy"]=df["Position"].shift(1)*df["Return"]

    df["Cum_Strategy"]=(1+df["Strategy"]).cumprod()
    df["Cum_Market"]=(1+df["Return"]).cumprod()

    fig=go.Figure()
    fig.add_trace(go.Scatter(x=df.index,y=df["Cum_Strategy"],name="Strateji"))
    fig.add_trace(go.Scatter(x=df.index,y=df["Cum_Market"],name="Pasif Tut"))
    st.plotly_chart(fig,use_container_width=True)

# -----------------------
# PORTFÖY
# -----------------------
elif menu=="Portföyüm":

    portfolio_input=st.text_area("Sembol,Adet,Alış Fiyatı")
    start_value=st.number_input("Başlangıç Değeri",value=100000)

    if portfolio_input:

        rows=portfolio_input.split("\n")
        data=[]
        total=0
