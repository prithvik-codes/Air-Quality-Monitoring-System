import streamlit as st
import paho.mqtt.client as mqtt
import json
from collections import deque
import threading
import time
import pandas as pd

# ----------------- Streamlit Page Setup -----------------
st.set_page_config(page_title="🌫️ Air Quality Dashboard", layout="wide")
st.title("🌫️ Real-Time Air Quality Monitoring")

# ----------------- Global Variables -----------------
MQTT_BROKER = "p212d112.ala.dedicated.aws.emqxcloud.com"
MQTT_PORT = 1883
MQTT_TOPIC = "airmonitor/data"
MQTT_USER = "prithviraj_k"         # optional
MQTT_PASSWORD = "12345678" # optional

# Use deques to store last 50 readings
max_len = 50
mq135_raw_list = deque(maxlen=max_len)
aqi_list = deque(maxlen=max_len)
temp_list = deque(maxlen=max_len)
humidity_list = deque(maxlen=max_len)
timestamps = deque(maxlen=max_len)

# Thread-safe lock for updating data
data_lock = threading.Lock()

# ----------------- MQTT CALLBACKS -----------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to MQTT Broker")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"❌ Failed to connect, rc={rc}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        with data_lock:
            mq135_raw_list.append(data['MQ135_RAW'])
            aqi_list.append(data['AQI'])
            temp_list.append(data['Temp'])
            humidity_list.append(data['Humidity'])
            timestamps.append(time.strftime('%H:%M:%S'))
    except Exception as e:
        print("Error parsing message:", e)

# ----------------- MQTT CLIENT THREAD -----------------
def mqtt_thread():
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

threading.Thread(target=mqtt_thread, daemon=True).start()

# ----------------- Streamlit UI -----------------
placeholder = st.empty()

while True:
    with data_lock:
        if len(timestamps) > 0:
            df = pd.DataFrame({
                'Time': list(timestamps),
                'MQ135_RAW': list(mq135_raw_list),
                'AQI': list(aqi_list),
                'Temperature (°C)': list(temp_list),
                'Humidity (%)': list(humidity_list)
            })

            with placeholder.container():
                st.subheader("📊 Latest Sensor Values")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("MQ135 RAW", df['MQ135_RAW'].iloc[-1])
                col2.metric("AQI", f"{df['AQI'].iloc[-1]:.1f}")
                col3.metric("Temperature (°C)", f"{df['Temperature (°C)'].iloc[-1]:.1f}")
                col4.metric("Humidity (%)", f"{df['Humidity (%)'].iloc[-1]:.1f}")

                st.subheader("📈 Sensor Trends")
                st.line_chart(df.set_index('Time')[['MQ135_RAW', 'AQI']])
                st.line_chart(df.set_index('Time')[['Temperature (°C)', 'Humidity (%)']])

    time.sleep(2)  # Update every 2 seconds
