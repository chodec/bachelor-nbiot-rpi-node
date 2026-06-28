import os
import socket
import serial
import time
import json
from dotenv import load_dotenv

TCP_IP = "0.0.0.0"
TCP_PORT = 6000
VPS_IP = os.getenv("VPS_IP")
VPS_PORT = int(os.getenv("VPS_PORT"))
NB_IOT_APN = os.getenv("NB_IOT_APN")

print("--- SYSTEM START: INITIALIZING TCP SERVER & SERIAL PORT ---")

ser = serial.Serial('/dev/ttyAMA0', 115200, timeout=5)

def send_at(command, delay=2.0):
    ser.write((command + '\r\n').encode())
    time.sleep(delay)
    response = ""
    while ser.inWaiting():
        response += ser.read(ser.inWaiting()).decode('utf-8', errors='ignore')
    print(f"Command: {command}\nResponse:\n{response.strip()}")
    print("-" * 40)
    return response

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((TCP_IP, TCP_PORT))
server_socket.listen(5)

print(f"Gateway listening on TCP port {TCP_PORT}...")
print("Waiting for ESP32 packets...")

try:
    while True:
        client_socket, addr = server_socket.accept()
        data = client_socket.recv(1024)
        
        if data:
            local_message = data.decode('utf-8').strip()
            print(f"\n[ESP32] Received message: {local_message}")
            
            payload_text = "TEST-123-ABC"
            try:
                parsed_json = json.loads(local_message)
                if "code" in parsed_json:
                    payload_text = parsed_json["code"]
            except:
                pass
            
            text_to_send = payload_text.strip() + "\r\n"
            length = len(text_to_send)
            
            print(f"--- STARTING TRANSMISSION FOR PAYLOAD: {payload_text.strip()} ---")
            
            ser.write(b'\r\n')
            time.sleep(0.5)

            send_at('ATE1', delay=0.5)
            send_at('AT', delay=0.5)
            send_at(f'AT+CGDCONT=1,"IP","{NB_IOT_APN}"', delay=1.0)
            send_at('AT+CNACT=0,1', delay=3.0)

            open_res = send_at(f'AT+CAOPEN=0,0,"UDP","{VPS_IP}",{VPS_PORT}', delay=3.0)

            print("Activating data sending...")
            ser.write(f'AT+CASEND=0,{length}\r\n'.encode())
            time.sleep(1.0)

            if ser.inWaiting():
                print(ser.read(ser.inWaiting()).decode('utf-8', errors='ignore').strip())

            print("Sending payload...")
            full_packet = text_to_send.encode('utf-8') + b'\x1a'
            ser.write(full_packet)
            time.sleep(4.0)

            if ser.inWaiting():
                print(ser.read(ser.inWaiting()).decode('utf-8', errors='ignore').strip())
                print("-" * 40)

            send_at('AT+CACLOSE=0', delay=1.0)
            print("--- TRANSMISSION END ---")
            
        client_socket.close()

except KeyboardInterrupt:
    print("\nGateway stopped.")
    server_socket.close()
    ser.close()
