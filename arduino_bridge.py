import serial
import requests
import time
from datetime import datetime

SERIAL_PORT = 'COM3'
BAUD_RATE = 115200
AZURE_URL = 'https://msdocs-python-webapp-quickstart-123-g0gvekgafpe0hzgt.polandcentral-01.azurewebsites.net/'
POLL_INTERVAL = 2

def connect_serial():
    while True:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            print(f'Connected to Arduino on {SERIAL_PORT}')
            return ser
        except Exception as e:
            print(f'Serial connection failed: {e}. Retrying in 5s...')
            time.sleep(5)

def send_to_azure(endpoint, data):
    try:
        res = requests.post(f'{AZURE_URL}{endpoint}', json=data, timeout=5)
        return res.status_code == 200
    except Exception as e:
        print(f'Azure request failed: {e}')
        return False

def get_pending_command():
    try:
        res = requests.get(f'{AZURE_URL}/pending', timeout=5)
        data = res.json()
        return data.get('command')
    except Exception as e:
        print(f'Failed to get pending command: {e}')
        return None

def process_serial_line(line):
    print(f'Arduino: {line}')

    if line.startswith('TEMP:'):
        try:
            temp = float(line.split(':')[1])
            send_to_azure('/update', { 'temperature': temp })
        except ValueError:
            print('Invalid temperature value')

    elif line.startswith('LED:'):
        state = line.split(':')[1].strip()
        send_to_azure('/update', { 'led': state == 'ON' })

    elif line == 'FLOOD:DETECTED':
        event_time = datetime.now().strftime('%d %b %Y, %H:%M:%S')
        send_to_azure('/flood', { 'time': event_time })
        print(f'Flood detected at {event_time}')

    elif line == 'FLOOD:CLEARED':
        print('Flood cleared')

    elif line == 'MSG:SAVED':
        print('Message saved to EEPROM')

    elif line.startswith('ERROR:'):
        print(f'Arduino error: {line}')

def main():
    ser = connect_serial()
    print(f'Bridge running. Connecting to: {AZURE_URL}')

    last_poll = time.time()

    while True:
        try:
            if ser.in_waiting:
                raw = ser.readline()
                try:
                    line = raw.decode('utf-8').strip()
                    if line:
                        process_serial_line(line)
                except UnicodeDecodeError:
                    print('Could not decode serial line, skipping')

            if time.time() - last_poll >= POLL_INTERVAL:
                command = get_pending_command()
                if command:
                    print(f'Sending command to Arduino: {command}')
                    ser.write((command + '\n').encode('utf-8'))
                last_poll = time.time()

        except serial.SerialException as e:
            print(f'Serial connection lost: {e}. Reconnecting...')
            ser = connect_serial()

        except KeyboardInterrupt:
            print('Bridge stopped by user')
            ser.close()
            break

        time.sleep(0.05)

if __name__ == '__main__':
    main()