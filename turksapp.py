import streamlit as st
import paho.mqtt.client as mqtt
import json
import base64
from streamlit_autorefresh import st_autorefresh

# --- STREAMLIT SAYFA AYARLARI ---
st.set_page_config(page_title="TÜRKSAPP VIP", page_icon="💬", layout="centered")
st.title("💬 TÜRKSAPP - Gerçek Zamanlı Sohbet")

# 3 saniyede bir ekranı otomatik yenile (Telefon ve PC arası senkronizasyon için şart)
st_autorefresh(interval=3000, key="datarefresh")

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "turksapp/genel_oda_v5"

# --- HAFIZA ---
if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = []

if "kullanici_adi" not in st.session_state:
    st.session_state.kullanici_adi = ""

# --- SOL MENÜ: KULLANICI ADI ---
with st.sidebar:
    st.header("⚙️ Profil")
    giris = st.text_input("Kullanıcı Adı:", value=st.session_state.kullanici_adi)
    if st.button("Kaydet ve Bağlan"):
        if giris.strip():
            st.session_state.kullanici_adi = giris.strip()
            st.success("Bağlandı!")

if not st.session_state.kullanici_adi:
    st.warning("👈 Önce soldan kullanıcı adını girip kaydet.")
    st.stop()

# --- MQTT BAĞLANTISI ---
def on_message(client, userdata, message):
    try:
        data = json.loads(message.payload.decode())
        if data not in st.session_state.mesajlar:
            st.session_state.mesajlar.append(data)
    except Exception:
        pass

@st.cache_resource
def get_mqtt_client():
    client = mqtt.Client()
    client.on_message = on_message
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.subscribe(MQTT_TOPIC)
        client.loop_start()
    except Exception:
        pass
    return client

mqtt_client = get_mqtt_client()

# --- MEDYA GÖNDERME (FOTO / SES) ---
with st.expander("📷 Fotoğraf veya 🎙️ Ses Gönder"):
    dosya = st.file_uploader("Dosya Seç", type=["png", "jpg", "jpeg", "mp3", "wav"])
    if dosya is not None and st.button("Yayınla"):
        encoded = base64.b64encode(dosya.read()).decode("utf-8")
        paket = {
            "sender": st.session_state.kullanici_adi,
            "type": "media",
            "mime": dosya.type,
            "data": encoded
        }
        st.session_state.mesajlar.append(paket)
        mqtt_client.publish(MQTT_TOPIC, json.dumps(paket))
        st.success("Gönderildi!")
        st.rerun()

# --- MESAJLARI LİSTELE ---
st.write(f"🟢 Aktif: **{st.session_state.kullanici_adi}**")

for msg in st.session_state.mesajlar:
    gonderen = msg.get("sender", "Biri")
    is_me = (gonderen == st.session_state.kullanici_adi)
    role = "user" if is_me else "assistant"
    
    with st.chat_message(role):
        st.write(f"**{gonderen}:**")
        if msg.get("type") == "text":
            st.write(msg.get("text"))
        elif msg.get("type") == "media":
            raw = base64.b64decode(msg["data"])
            mime = msg.get("mime", "")
            if "image" in mime:
                st.image(raw)
            elif "audio" in mime:
                st.audio(raw, format=mime)

# --- MESAJ GİRİŞİ ---
prompt = st.chat_input("Mesaj yaz ve Enter'a bas...")

if prompt:
    paket = {
        "sender": st.session_state.kullanici_adi,
        "type": "text",
        "text": prompt
    }
    st.session_state.mesajlar.append(paket)
    mqtt_client.publish(MQTT_TOPIC, json.dumps(paket))
    st.rerun()
