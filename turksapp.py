import streamlit as st
import paho.coinmqtt as mqtt  # veya paho.mqtt.client as mqtt (eski kodundaki neyse)
import paho.mqtt.client as mqtt
from Crypto.Cipher import AES
import base64

# --- STREAMLIT SAYFA AYARLARI ---
st.set_page_config(page_title="TÜRKSAPP", page_icon="💬", layout="centered")
st.title("💬 TÜRKSAPP Chat")

# --- MESAJ HAFIZASI (ENTER TUŞUNDA SİLİNMEMESİ İÇİN) ---
if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = []

# --- ESKİ MESAJLARI EKRANDA GÖSTER ---
for msg in st.session_state.mesajlar:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- SOHBET GİRİŞ ALANI (ENTER DESTEKLİ) ---
prompt = st.chat_input("Mesajınızı yazın ve Enter'a basın...")

if prompt:
    # 1. Kullanıcının yazdığı mesajı hafızaya ve ekrana ekle
    st.session_state.mesajlar.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    # 2. Sayfayı yenileyerek akışı sabitle
    st.rerun()
