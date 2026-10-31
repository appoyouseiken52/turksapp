import streamlit as st
import paho.mqtt.client as mqtt
import json
import time

# --- STREAMLIT SAYFA AYARLARI ---
st.set_page_config(page_title="TÜRKSAPP VIP", page_icon="💬", layout="centered")
st.title("💬 TÜRKSAPP Chat")

# Sabit MQTT Sunucusu ve Oda Adı (İkiniz de otomatik buraya bağlanırsınız)
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "turksapp/genel_oda_v1"

# --- HAFIZA VE İSTEMCİ KURULUMU ---
if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = []

if "kullanici_adi" not in st.session_state:
    st.session_state.kullanici_adi = f"Kullanıcı_{int(time.time()) % 1000}"

# --- MQTT GELEN MESAJ DİNLENMESİ ---
def on_message(client, userdata, message):
    try:
        data = json.loads(message.payload.decode())
        # Kendimizden gelmeyen mesajları ekle
        if data.get("sender") != st.session_state.kullanici_adi:
            st.session_state.mesajlar.append({"role": "assistant", "content": f"{data['sender']}: {data['text']}"})
    except Exception:
        pass

# MQTT Bağlantısını Başlat
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

client = get_mqtt_client()

# --- ARAYÜZ VE MESAJ AKIŞI ---
st.write(f"**Takma Adınız:** {st.session_state.kullanici_adi}")

# Eski mesajları ekrana yaz
for msg in st.session_state.mesajlar:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Mesaj Giriş Alanı (Enter destekli)
prompt = st.chat_input("Mesajınızı yazın ve Enter'a basın...")

if prompt:
    # 1. Kendi mesajını ekrana yaz
    st.session_state.mesajlar.append({"role": "user", "content": f"Sen: {prompt}"})
    
    # 2. Mesajı MQTT kanalına yayınla
    payload = json.dumps({"sender": st.session_state.kullanici_adi, "text": prompt})
    client.publish(MQTT_TOPIC, payload)
    
    # 3. Sayfayı yenile
    st.rerun()
