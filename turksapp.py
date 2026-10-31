import streamlit as st
import paho.mqtt.client as mqtt
from Crypto.Cipher import AES
import base64

# --- STREAMLIT SAYFA AYARLARI ---
st.set_page_config(page_title="TÜRKSAPP", page_icon="💬", layout="centered")
st.title("💬 TÜRKSAPP Chat")

# --- MESAJ HAFIZASI ---
if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = []

# --- ESKİ MESAJLARI GÖSTER ---
for msg in st.session_state.mesajlar:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- SOHBET GİRİŞ ALANI ---
prompt = st.chat_input("Mesajınızı yazın ve Enter'a basın...")

if prompt:
    st.session_state.mesajlar.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    st.rerun()
