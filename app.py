from flask import Flask, render_template_string, request, jsonify
import paho.mqtt.client as mqtt
import json

app = Flask(__name__)

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883

# Odalara göre mesajları tutan sözlük: { room_id: [ {sender, text}, ... ] }
rooms_messages = {}
subscribed_rooms = set()

# MQTT İstemcisi
client = mqtt.Client()

def on_message(client, userdata, msg):
    try:
        # Topic formatı: turksapp/room/<room_id>
        parts = msg.topic.split('/')
        if len(parts) >= 3:
            room_id = parts[2]
            data = json.loads(msg.payload.decode())
            if room_id not in rooms_messages:
                rooms_messages[room_id] = []
            if data not in rooms_messages[room_id]:
                rooms_messages[room_id].append(data)
    except:
        pass

client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TÜRKSAPP - Özel Oda</title>
    <style>
        body { font-family: Arial, sans-serif; background: #121212; color: #fff; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: auto; background: #1e1e1e; padding: 20px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
        #chat-box { height: 350px; overflow-y: scroll; border: 1px solid #333; padding: 10px; margin-bottom: 15px; background: #181818; border-radius: 5px; display: none; }
        .message { margin-bottom: 10px; padding: 8px; border-radius: 5px; background: #2c2c2c; }
        .message b { color: #4CAF50; }
        .input-group { display: flex; gap: 10px; margin-bottom: 10px; }
        input, button { padding: 10px; font-size: 16px; border-radius: 5px; border: none; }
        input[type="text"] { flex: 1; background: #333; color: #fff; }
        button { background: #4CAF50; color: white; cursor: pointer; }
        button:hover { background: #45a049; }
        #setup-screen { display: block; }
        #chat-screen { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h2>💬 TÜRKSAPP Özel Oda</h2>
        
        <!-- GİRİŞ EKRANI -->
        <div id="setup-screen">
            <p>Sohbete katılmak için adını ve ortak <b>Oda ID</b>'ni gir:</p>
            <div class="input-group">
                <input type="text" id="username" placeholder="Kullanıcı Adın...">
            </div>
            <div class="input-group">
                <input type="text" id="room_id" placeholder="Oda ID (Örn: benimoda123)...">
            </div>
            <button onclick="joinRoom()" style="width:100%;">Odaya Gir</button>
        </div>

        <!-- SOHBET EKRANI -->
        <div id="chat-screen">
            <div style="margin-bottom: 10px; font-size: 14px; color: #aaa;">
                Oda: <b id="current_room_label" style="color:#4CAF50;"></b> | Kullanıcı: <b id="current_user_label" style="color:#fff;"></b>
            </div>
            <div id="chat-box"></div>
            <div class="input-group">
                <input type="text" id="message" placeholder="Mesajını yaz ve Enter'a bas..." onkeypress="checkEnter(event)">
                <button onclick="sendMessage()">Gönder</button>
            </div>
        </div>
    </div>

    <script>
        let currentUser = "";
        let currentRoom = "";

        function joinRoom() {
            currentUser = document.getElementById('username').value.trim();
            currentRoom = document.getElementById('room_id').value.trim();

            if(!currentUser || !currentRoom) {
                alert("Lütfen hem kullanıcı adını hem de Oda ID'yi boş bırakma!");
                return;
            }

            fetch('/join_room', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ room_id: currentRoom })
            }).then(() => {
                document.getElementById('setup-screen').style.display = 'none';
                document.getElementById('chat-screen').style.display = 'block';
                document.getElementById('chat-box').style.display = 'block';
                document.getElementById('current_room_label').innerText = currentRoom;
                document.getElementById('current_user_label').innerText = currentUser;
                setInterval(fetchMessages, 1500); // 1.5 saniyede bir canlı senkronizasyon
            });
        }

        function fetchMessages() {
            if(!currentRoom) return;
            fetch(`/get_messages?room_id=${currentRoom}`)
                .then(response => response.json())
                .then(data => {
                    let chatBox = document.getElementById('chat-box');
                    let scrollable = chatBox.scrollTop === (chatBox.scrollHeight - chatBox.clientHeight);
                    chatBox.innerHTML = '';
                    data.forEach(msg => {
                        let div = document.createElement('div');
                        div.className = 'message';
                        div.innerHTML = `<b>${msg.sender}:</b> ${msg.text}`;
                        chatBox.appendChild(div);
                    });
                    if (scrollable || chatBox.innerHTML === "") {
                        chatBox.scrollTop = chatBox.scrollHeight;
                    }
                });
        }

        function sendMessage() {
            let msg = document.getElementById('message').value.trim();
            if(!msg) return;

            fetch('/send_message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ room_id: currentRoom, sender: currentUser, text: msg })
            }).then(() => {
                document.getElementById('message').value = '';
                fetchMessages();
            });
        }

        function checkEnter(e) {
            if (e.key === 'Enter') { sendMessage(); }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/join_room', methods=['POST'])
def join_room():
    data = request.json
    room_id = data.get('room_id')
    if room_id and room_id not in subscribed_rooms:
        client.subscribe(f"turksapp/room/{room_id}")
        subscribed_rooms.add(room_id)
    return jsonify({"status": "success"})

@app.route('/get_messages')
def get_messages():
    room_id = request.args.get('room_id')
    return jsonify(rooms_messages.get(room_id, []))

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    room_id = data.get('room_id')
    sender = data.get('sender')
    text = data.get('text')
    if room_id and sender and text:
        msg_packet = {"sender": sender, "text": text}
        if room_id not in rooms_messages:
            rooms_messages[room_id] = []
        rooms_messages[room_id].append(msg_packet)
        client.publish(f"turksapp/room/{room_id}", json.dumps(msg_packet))
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
