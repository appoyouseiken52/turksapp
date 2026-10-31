import streamlit as st
import paho.mqtt.client as mqtt
import json
import time

# --- STREAMLIT SAYFA AYARLARI ---
st.set_page_config(page_title="TÜRKSAPP VIP", page_icon="💬", layout="centered")
st.title("💬 TÜRKSAPP - Canlı Sohbet Odası")

# Sabit MQTT Sunucusu ve Ortak Oda
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "turksapp/genel_oda_v2"

# --- HAFIZA BAŞLATMA ---
if "mesajlar" not in st.session_state:
    st.session_state.mesajlar = []

if "bagli" not in st.session_state:
    st.session_state.bagli = False

# --- KULLANICI GİRİŞ PANELİ (KENAR ÇUCU) ---
with st.sidebar:
    st.header("⚙️ Sohbet Ayarları")
    girilen_ad = st.text_input("Kullanıcı Adınızı Girin:", value="Kanka")
    
    if st.button("Odaya Bağlan / Güncelle"):
        if girilen_ad.strip():
            st.session_state.kullanici_adi = girilen_ad.strip()
            st.session_state.bagli = True
            st.success(f"Bağlantı sağlandı: {st.session_state.kullanici_adi}")
        else:
            st.warning("Lütfen geçerli bir kullanıcı adı yazın!")

# Eğer kullanıcı adı seçilmediyse önce onu iste
if not st.session_state.bagli:
    st.info("👈 Soldaki menüden kullanıcı adını girip **Odaya Bağlan** butonuna basarak sohbete başlayabilirsin!")
else:
    st.write(f"🟢 Aktif Kullanıcı: **{st.session_state.kullanici_adi**} | Oda: `Genel Sohbet`")

    # --- MQTT GELEN MESAJ DİNLEYİCİSİ ---
    def on_message(client, userdata, message):
        try:
            data = json.loads(message.payload.decode())
            # Mesaj havuzuna gelenleri ekle (kendi mesajlarımız hariç)
            if data.get("sender") != st.session_state.kullanici_adi:
                st.session_state.mesajlar.append({
                    "sender": data["sender"],
                    "text": data["text"]
                })
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

    # --- GEÇMİŞ MESAJLARI EKRANDA GÖSTER ---
    for msg in st.session_state.mesajlar:
        gonderen = msg["sender"]
        icerik = msg["text"]
        if gonderen == st.session_state.kullanici_adi:
            with st.chat_message("user"):
                st.write(f"**Sen:** {icerik}")
        else:
            with st.chat_message("assistant"):
                st.write(f"**{gonderen}:** {icerik}")

    # --- MESAJ GİRİŞ ALANI (ENTER DESTEKLİ) ---
    prompt = st.chat_input("Mesajını yaz ve Enter'a bas...")

    if prompt:
        # 1. Kendi mesajını ekrana ve hafızaya bas
        st.session_state.mesajlar.append({
            "sender": st.session_state.kullanici_adi,
            "text": prompt
        })
        
        # 2. MQTT ile karşı tarafa fırlat
        payload = json.dumps({
            "sender": st.session_state.kullanici_adi,
            "text": prompt
        })
        mqtt_client.publish(MQTT_TOPIC, payload)
        
        # 3. Ekranı yenile
        st.rerun()
