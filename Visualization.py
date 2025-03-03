import paho.mqtt.client as mqtt
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import threading
import time
import csv
import signal
import os
from datetime import datetime

# MQTT Broker details

# test broker
BROKER = "mqtt.eclipseprojects.io"  
PORT = 1883

# actual broker
# BROKER = "192.168.1.1"
# PORT = 1884

TOPIC_TEMPLATE = "Shiveworks/segment/{}/command"  # Define the topic pattern
NUM_TOPICS = 40  # Number of topics to subscribe to

# Data storage
data = {i: [] for i in range(NUM_TOPICS)}
time_data = []

# Create timestamped folder for outputs
output_folder = datetime.now().strftime("output_%Y%m%d_%H%M%S")
os.makedirs(output_folder, exist_ok=True)
plot_counter = 0
data_start = False

# MQTT callbacks using Paho v2 API
def on_connect(client, userdata, flags, reason_code, properties):
    print("Connected with result code", reason_code)
    for i in range(NUM_TOPICS):
        topic = TOPIC_TEMPLATE.format(i)
        client.subscribe(topic)
        print(f"Subscribed to {topic}")

def on_message(client, userdata, message):
    topic_index = int(message.topic.split("/")[-1])
    try:
        value = float(message.payload.decode())
        data[topic_index].append(value)
        if len(time_data) < len(data[topic_index]):
            time_data.append(len(time_data))
    except ValueError:
        print(f"Invalid data received on {message.topic}: {message.payload.decode()}")

# MQTT client setup
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "VisualizationPC")
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)

def mqtt_loop():
    client.loop_forever()

# Start MQTT loop in a separate thread
threading.Thread(target=mqtt_loop, daemon=True).start()

def export_to_csv():
    csv_path = os.path.join(output_folder, "sensor_data.csv")
    with open(csv_path, "w", newline="") as file:
        writer = csv.writer(file)
        headers = ["Time"] + [f"Segment {i}" for i in range(NUM_TOPICS)]
        writer.writerow(headers)
        for i in range(len(time_data)):
            row = [time_data[i]] + [data[j][i] if i < len(data[j]) else "" for j in range(NUM_TOPICS)]
            writer.writerow(row)
    print(f"Data exported to {csv_path}")

# Initialize 2D plot
fig2d, ax2d = plt.subplots(1)
def update_2d_plot():
    global plot_counter
    ax2d.clear()
    for key, values in data.items():
        if values:
            ax2d.plot(time_data[:len(values)], values, label=f"Segment {key}")
    ax2d.set_xlabel("Time")
    ax2d.set_ylabel("Segment Angle")
    ax2d.legend()
    plt.draw()

def export2DPlotLive():
    plot_filename = os.path.join(output_folder, f"plot_{plot_counter}.png")
    fig2d.savefig(plot_filename)
    plot_counter += 1

# Initialize 3D plot
fig3d, ax3d = plt.subplots(subplot_kw={"projection": "3d"})
def update_3d_plot():
    ax3d.clear()
    X, Y = np.meshgrid(range(NUM_TOPICS), time_data)
    Z = np.array([[data[i][j] if j < len(data[i]) else 0 for i in range(NUM_TOPICS)] for j in range(len(time_data))])
    if np.any(Z): # this protects us at program startup from it crashing
        ax3d.plot_surface(X, Y, Z, cmap=cm.viridis)
        data_start = True
    ax3d.set_xlabel("Segment")
    ax3d.set_ylabel("Time")
    ax3d.set_zlabel("Angular Displacement")
    plt.draw()

def live_update():
    while True:
        update_3d_plot()
        update_2d_plot()
        if data_start:
            export2DPlotLive()
        plt.pause(1)

def save_3d_plot():
    plot3d_filename = os.path.join(output_folder, "3d_plot.png")
    fig3d.savefig(plot3d_filename)
    print(f"3D plot saved as {plot3d_filename}")

# Handle program exit
def handle_exit(sig, frame):
    save_3d_plot()
    export_to_csv()
    exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

# Start live updates in a separate thread

live_update()
plt.show()
