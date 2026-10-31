import streamlit as st
import paho.mqtt.client as mqtt
import json
import base64

# --- STREAMLIT SAYFA AYARLARI ---
st.set_page_config(page_title="TÜRKSAPP VIP", page_icon="💬", layout="centered")
st.title("💬 TÜRKSAPP - Canlı Sohbet ve Medya")

# Sabit MQTT Sunucusu ve Oda
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "turksapp/genel_oda_v4"

# --- HAFIZA BAŞLATMA ---
if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = []

if "kullanici_adi" not in st.session_state:
    st.session_state.kullanici_adi = ""

# --- SOL MENÜ: KULLANICI ADI AYARI ---
with st.sidebar:
    st.header("⚙️ Profil Ayarları")
    adi_input = st.text_input("Kullanıcı Adınızı Girin:", value=st.session_state.kullanici_adi)
    if st.button("Kaydet ve Bağlan"):
        if adi_input.strip():
            st.session_state.kullanici_adi = adi_input.strip()
            st.success("Kullanıcı adı kaydedildi!")

if not st.session_state.kullanici_adi:
    st.warning("👈 Soldaki menüden kullanıcı adını yazıp 'Kaydet ve Bağlan' butonuna bas.")
    st.stop()

# --- MQTT DİNLEYİCİSİ ---
def on_message(client, userdata, message):
    try:
        data = json.loads(message.payload.decode())
        if data.get("sender") != st.session_state.kullanici_adi:
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

# --- ÜST BAR: BAĞLANTI VE YENİLEME ---
col1, col2 = st.columns([3, 1])
with col1:
    st.write(f"🟢 Aktif Kullanıcı: **{st.session_state.kullanici_adi}**")
with col2:
    if st.button("🔄 Akışı Yenile"):
        st.rerun()

# --- FOTOĞRAF VE SES GÖNDERME ---
with st.expander("📷 Resim veya 🎙️ Ses Dosyası Gönder"):
    yuklenen_dosya = st.file_uploader("Dosya Seç", type=["png", "jpg", "jpeg", "mp3", "wav"])
    if yuklenen_dosya is not None:
        if st.button("Medyayı Yayınla"):
            dosya_bayt = yuklenen_dosya.read()
            encoded_data = base64.b64encode(dosya_bayt).decode("utf-8")
            
            medya_paketi = {
                "sender": st.session_state.kullanici_adi,
                "type": "media",
                "mime": yuklenen_dosya.type,
                "data": encoded_data
            }
            st.session_state.mesajlar.append(medya_paketi)
            mqtt_client.publish(MQTT_TOPIC, json.dumps(medya_paketi))
            st.success("Medya gönderildi!")
            st.rerun()

# --- GEÇMİŞ MESAJLARI VE MEDYALARI GÖSTER ---
for msg in st.session_state.mesajlar:
    gonderen = msg.get("sender", "Biri")
    is_me = (gonderen == st.session_state.kullanici_adi)
    role = "user" if is_me else "assistant"
    
    with st.chat_message(role):
        st.write(f"**{gonderen}:**")
        if msg.get("type") == "text":
            st.write(msg.get("text"))
        elif msg.get("type") == "media":
            raw_data = base64.b64decode(msg["data"])
            mime = msg.get("mime", "")
            if "image" in mime:
                st.image(raw_data)
            elif "audio" in mime:
                st.audio(raw_data, format=mime)

# --- METİN MESAJI GİRİŞİ (ENTER DESTEKLİ) ---
prompt = st.chat_input("Mesajınızı yazın ve Enter'a basın...")

if prompt:
    mesaj_paketi = {
        "sender": st.session_state.kullanici_adi,
        "type": "text",
        "text": prompt
    }
    st.session_state.mesajlar.append(mesaj_paketi)
    mqtt_client.publish(MQTT_TOPIC, json.dumps(mesaj_paketi))
    st.rerun()
