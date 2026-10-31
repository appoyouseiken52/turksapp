import streamlit as st
import paho.mqtt.client as mqtt
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
import json
import io
import time
import sounddevice as sd
from scipy.io.wavfile import write
from plyer import notification
from moviepy import VideoFileClip
import tempfile
import os

# ----------------------------------------------------
# 1. AYARLAR & GÜVENLİK (AES-256 ŞİFRELEME & MQTT)
# ----------------------------------------------------
SECRET_KEY = b"TURKSAPP_GIZLI_KEY_32_BYTE_12345"  # Arkadaşınla AYNI olmalı!
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883

def encrypt_data(plain_text: str) -> str:
    """Veriyi AES-256-CBC ile şifreler."""
    cipher = AES.new(SECRET_KEY, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(plain_text.encode('utf-8'), AES.block_size))
    iv = base64.b64encode(cipher.iv).decode('utf-8')
    ct = base64.b64encode(ct_bytes).decode('utf-8')
    return json.dumps({'iv': iv, 'ciphertext': ct})

def decrypt_data(json_str: str) -> str:
    """Şifreli veriyi çözer."""
    try:
        b64 = json.loads(json_str)
        iv = base64.b64decode(b64['iv'])
        ct = base64.b64decode(b64['ciphertext'])
        cipher = AES.new(SECRET_KEY, AES.MODE_CBC, iv)
        pt = unpad(cipher.decrypt(ct), AES.block_size)
        return pt.decode('utf-8')
    except Exception as e:
        return f"[Şifre Çözülemedi - Hatalı Anahtar]"

def send_local_notification(title, message):
    """Sistem Bildirimi Gönderir"""
    try:
        notification.notify(title=title, message=message, app_name="TÜRKSAPP", timeout=4)
    except:
        pass

def compress_video_bytes(input_bytes):
    """WhatsApp tarzı videoyu küçültür ve sunucuyu/RAM'i korur"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_in:
            tmp_in.write(input_bytes)
            tmp_in_path = tmp_in.name
            
        output_path = tmp_in_path.replace(".mp4", "_compressed.mp4")
        
        clip = VideoFileClip(tmp_in_path)
        resized_clip = clip.resize(height=480) # 480p optimize
        resized_clip.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac", 
            bitrate="800k", 
            logger=None
        )
        
        clip.close()
        resized_clip.close()
        
        with open(output_path, "rb") as f:
            compressed_bytes = f.read()
            
        os.remove(tmp_in_path)
        os.remove(output_path)
        return compressed_bytes
    except:
        return input_bytes # Hata olursa orijinalini döndür

# ----------------------------------------------------
# 2. STREAMLIT & MQTT BAĞLANTIYI KURMA
# ----------------------------------------------------
st.set_page_config(page_title="TÜRKSAPP VIP", page_icon="⚡", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("⚡ TÜRKSAPP")
    user_name = st.text_input("Kullanıcı Adı", value="Maymun_Reyis")
    chat_type = st.radio("Sohbet Tipi", ["Grup (Genel)", "Özel Oda"])
    
    if chat_type == "Özel Oda":
        target_room = st.text_input("Oda Kodu", value="konyavebaku")
    else:
        target_room = "GENEL_AKIS"
    
    current_topic = f"turksapp/{target_room}"
    st.success(f"Aktif Kanal: {target_room}")

def on_message(client, userdata, msg):
    try:
        encrypted_payload = msg.payload.decode('utf-8')
        raw_json = decrypt_data(encrypted_payload)
        data = json.loads(raw_json)
        st.session_state.messages.append(data)
        
        if data.get("sender") != user_name:
            send_local_notification(
                title=f"TÜRKSAPP: {data.get('sender')}",
                message=f"Yeni {data.get('type')} mesajı geldi!"
            )
    except:
        pass

@st.cache_resource
def get_mqtt_client():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    return client

client = get_mqtt_client()
client.subscribe(current_topic)

# ----------------------------------------------------
# 3. ARAYÜZ VE MESAJ GÖSTERİMİ
# ----------------------------------------------------
st.header(f"🔒 Uçtan Uca Şifreli Kanal: {target_room}")

for msg in st.session_state.messages:
    if msg.get("room") == target_room:
        is_me = msg.get("sender") == user_name
        avatar = "🐵" if is_me else "👤"
        
        with st.chat_message(msg.get("sender"), avatar=avatar):
            st.caption(f"**{msg.get('sender')}**")
            
            if msg["type"] == "text":
                st.write(msg["content"])
            elif msg["type"] == "video":
                st.video(base64.b64decode(msg["content"]))
                if msg.get("caption"):
                    st.write(msg.get("caption"))
            elif msg["type"] == "audio":
                st.audio(base64.b64decode(msg["content"]), format="audio/wav")

# ----------------------------------------------------
# 4. GİRDİ VE GÖNDERME PANELLERİ
# ----------------------------------------------------
st.divider()
text_input = st.text_input("Mesajınızı yazın...", key="chat_input")
uploaded_file = st.file_uploader("Medya Ekleyin (Video/Ses/Foto)", type=["mp4", "mp3", "wav", "png", "jpg"])

col_send, col_rec = st.columns([1, 1])

def publish_payload(msg_dict):
    raw_str = json.dumps(msg_dict)
    encrypted_str = encrypt_data(raw_str)
    client.publish(current_topic, encrypted_str)

# Metin Gönder
if col_send.button("💬 Mesaj Gönder") and text_input:
    publish_payload({
        "room": target_room, "sender": user_name,
        "type": "text", "content": text_input
    })
    st.rerun()

# Medya Gönder (Otomatik Sıkıştırma Dahil)
if uploaded_file is not None and st.button("📁 Medyayı Şifreleyip Gönder"):
    file_bytes = uploaded_file.read()
    f_type = "video" if "video" in uploaded_file.type else "audio"
    
    if f_type == "video":
        st.info("Video WhatsApp tarzı sıkıştırılıyor...")
        file_bytes = compress_video_bytes(file_bytes)
        
    b64_content = base64.b64encode(file_bytes).decode('utf-8')
    
    publish_payload({
        "room": target_room, "sender": user_name,
        "type": f_type, "content": b64_content, "caption": text_input
    })
    st.success("Medya Gönderildi!")
    st.rerun()

# Ses Kaydı Gönder (3 Saniye)
if col_rec.button("🎙️ Sesli Mesaj (3s)"):
    st.warning("Kayıt yapılıyor...")
    fs = 44100
    recording = sd.rec(int(3 * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    
    wav_io = io.BytesIO()
    write(wav_io, fs, recording)
    audio_b64 = base64.b64encode(wav_io.getvalue()).decode('utf-8')
    
    publish_payload({
        "room": target_room, "sender": user_name,
        "type": "audio", "content": audio_b64
    })
    st.success("Ses İletildi!")
    st.rerun()