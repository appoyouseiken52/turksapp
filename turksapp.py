import streamlit as st
import paho.mqtt.client as mqtt
import json
import base64
import time
from streamlit_autorefresh import st_autorefresh

# --- STREAMLIT SAYFA AYARLARI ---
st.set_page_config(page_title="TÜRKSAPP VIP", page_icon="💬", layout="centered")
st.title("💬 TÜRKSAPP - Canlı Sohbet & Medya")

# Canlı bağlantı için 3 saniyede bir ekranı otomatik yenile (Karşı tarafın mesajlarını anında görmek için)
st_autorefresh(interval=3000, key="chat_refresh")

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "turksapp/genel_oda_v3"

# --- HAFIZA BAŞLATMA ---
if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = []

if "kullanici_adi" not in st.session_state:
    st.session_state.kullanici_adi = ""

# --- SOL MENÜ: KULLANICI ADI AYARI ---
with st.sidebar:
    st.header("⚙️ Profil Ayarları")
    k_adi = st.text_input("Kullanıcı Adınız:", value=st.session_state.kullanici_adi)
    if st.button("Kaydet ve Bağlan"):
        st.session_state.kullanici_adi = k_adi.strip()
        st.success("Kullanıcı adı kaydedildi!")

if not st.session_state.kullanici_adi:
    st.warning("👈 Soldaki menüden bir kullanıcı adı girip 'Kaydet ve Bağlan' butonuna basın.")
    st.stop()

# --- MQTT GELEN MESAJ DİNLENMESİ ---
def on_message(client, userdata, message):
    try:
        data = json.loads(message.payload.decode())
        if data.get("sender") != st.session_state.kullanici_adi:
            # Tekrarlayan mesaj kontrolü
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

# --- MEDYA GÖNDERME ALANI (FOTOĞRAF VE SES) ---
with st.expander("📷 / 🎙️ Fotoğraf veya Ses Gönder"):
    yuklenen_dosya = st.file_uploader("Dosya Seç (Resim veya Ses)", type=["png", "jpg", "jpeg", "mp3", "wav", "ogg"])
    if st.button("Medya Gönder") and yuklenen_dosya is not None:
        dosya_turu = yuklenen_dosya.type
        dosya_iceriği = base64.b64encode(yuklenen_dosya.read()).decode("utf-8")
        
        yeni_medya = {
            "sender": st.session_state.kullanici_adi,
            "type": "media",
            "mime": dosya_turu,
            "data": dosya_iceriği
        }
        
        st.session_state.mesajlar.append(yeni_medya)
        mqtt_client.publish(MQTT_TOPIC, json.dumps(yeni_medya))
        st.success("Medya başarıyla gönderildi!")

# --- ESKİ MESAJLARI VE MEDYALARI GÖSTER ---
st.write(f"🟢 Bağlı Kullanıcı: **{st.session_state.kullanici_adi}**")

for msg in st.session_state.mesajlar:
    gonderen = msg.get("sender", "Bilinmeyen")
    is_me = (gonderen == st.session_state.kullanici_adi)
    role = "user" if is_me else "assistant"
    
    with st.chat_message(role):
        st.write(f"**{gonderen}:**")
        
        # Eğer mesaj metin ise
        if msg.get("type") == "text":
            st.write(msg.get("text"))
            
        # Eğer mesaj medya (resim/ses) ise
        elif msg.get("type") == "media":
            raw_data = base64.b64decode(msg["data"])
            mime = msg.get("mime", "")
            
            if "image" in mime:
                st.image(raw_data)
            elif "audio" in mime:
                st.audio(raw_data, format=mime)

# --- METİN MESAJ GİRİŞİ (ENTER DESTEKLİ) ---
prompt = st.chat_input("Mesaj yazın ve Enter'a basın...")

if prompt:
    yeni_mesaj = {
        "sender": st.session_state.kullanici_adi,
        "type": "text",
        "text": prompt
    }
    
    st.session_state.mesajlar.append(yeni_mesaj)
    mqtt_client.publish(MQTT_TOPIC, json.dumps(yeni_mesaj))
    st.rerun()
