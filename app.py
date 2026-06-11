from flask import Flask
from flask import render_template
from flask import jsonify
from flask import request

import os
import smtplib

from email.mime.text import MIMEText
from datetime import datetime


app = Flask(__name__)

current_temp = None
led_state = False

flood_events = []
flood_id_counter = 0

pending_command = None


EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_TO = os.environ.get('EMAIL_TO')


def send_flood_email(event_time):

    try:

        print('\nEMAIL DEBUG')
        print(f'FROM → {EMAIL_ADDRESS}')
        print(f'TO → {EMAIL_TO}')
        print(
            f'PASSWORD SET → '
            f'{EMAIL_PASSWORD is not None}'
        )

        if (
            not EMAIL_ADDRESS
            or not EMAIL_PASSWORD
            or not EMAIL_TO
        ):
            print(
                'Email variables missing'
            )
            return

        msg = MIMEText(
            f'Eveniment inundatie detectat la: {event_time}'
        )

        msg['Subject'] = 'Alerta Inundatie!'
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = EMAIL_TO

        print('Connecting to Gmail...')

        with smtplib.SMTP_SSL(
            'smtp.gmail.com',
            465
        ) as smtp:

            smtp.login(
                EMAIL_ADDRESS,
                EMAIL_PASSWORD
            )

            smtp.send_message(msg)

        print('Email sent')

    except Exception as e:

        print(
            f'Email error → {e}'
        )


@app.route('/')
def index():

    return render_template(
        'index.html'
    )


@app.route('/status')
def status():

    return jsonify({
        'temperature': current_temp,
        'led': led_state,
        'floods': flood_events
    })


@app.route('/led/<state>')
def led(state):

    global led_state
    global pending_command

    if state == 'on':

        led_state = True
        pending_command = 'A'

    elif state == 'off':

        led_state = False
        pending_command = 'S'

    return jsonify({
        'led': led_state
    })


@app.route('/message', methods=['POST'])
def message():

    global pending_command

    data = request.get_json()

    msg = data.get(
        'text',
        ''
    ).strip()

    if not msg:

        return jsonify({
            'status': 'error'
        }), 400

    pending_command = (
        f'MSG:{msg}'
    )

    return jsonify({
        'status': 'sent'
    })


@app.route('/update', methods=['POST'])
def update():

    global current_temp
    global led_state

    data = request.get_json()

    print(
        f'UPDATE → {data}'
    )

    if 'temperature' in data:

        current_temp = round(
            float(
                data['temperature']
            ),
            1
        )

    if 'led' in data:

        led_state = bool(
            data['led']
        )

    return jsonify({
        'status': 'ok'
    })


@app.route('/flood', methods=['POST'])
def flood():

    global flood_id_counter

    print('\nFLOOD ENDPOINT HIT')

    data = request.get_json()

    print(
        f'DATA → {data}'
    )

    event_time = data.get(
        'time',
        datetime.now().strftime(
            '%d %b %Y, %H:%M:%S'
        )
    )

    flood_id_counter += 1

    event = {
        'id': flood_id_counter,
        'time': event_time
    }

    if len(flood_events) >= 10:
        flood_events.pop(0)

    flood_events.append(event)

    print(
        f'Flood events → {flood_events}'
    )

    send_flood_email(
        event_time
    )

    return jsonify({
        'status': 'ok'
    })


@app.route('/floods/delete/<int:event_id>',
           methods=['DELETE'])
def delete_flood(event_id):

    global flood_events

    flood_events = [

        e

        for e in flood_events

        if e['id'] != event_id
    ]

    return jsonify({
        'status': 'deleted'
    })


@app.route('/pending')
def pending():

    global pending_command

    cmd = pending_command

    pending_command = None

    return jsonify({
        'command': cmd
    })


@app.route('/clear',
           methods=['POST'])
def clear():

    global pending_command

    pending_command = None

    return jsonify({
        'status': 'cleared'
    })


if __name__ == '__main__':

    app.run(
        host='0.0.0.0',
        port=8000,
        debug=True
    )