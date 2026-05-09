#!/usr/bin/env python3
"""
Fake Ableton device simulator — sends HUD protocol bursts to UDP :5006.
Usage:
  python bin/hud_sim.py               # cycles through demo devices every 3 seconds
  python bin/hud_sim.py once          # sends one burst then exits
"""
import socket
import time
import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from source_modules.hud_protocol import (
    encode_device, encode_slot, encode_slot_payload, encode_commit, EMPTY_SLOT,
)

HOST = '127.0.0.1'
PORT = 5006

DEVICES = [
    {
        'name': 'EQ Eight',
        'dials': ['Low Freq', 'Low Gain', 'Mid Freq', 'Mid Gain', 'Hi Freq', 'Hi Gain', 'Dry/Wet', ''],
        'buttons': [],
    },
    {
        'name': 'Auto Filter',
        'dials': ['Frequency', 'Resonance', 'Drive', 'Dry/Wet', 'LFO Rate', 'LFO Amt', '', ''],
        'buttons': ['On/Off', '', '', '', '', '', '', ''],
    },
    {
        'name': 'Reverb',
        'dials': ['Room Size', 'Decay', 'Pre-Delay', 'Diffusion', 'Dry/Wet', '', '', ''],
        'buttons': ['On/Off', 'Freeze', '', '', '', '', '', ''],
    },
]


def send(sock, line: str):
    sock.sendto((line + '\n').encode('utf-8'), (HOST, PORT))
    print(f'  >> {line}')


def send_burst(sock, device: dict):
    name = device['name']
    print(f'\n--- Sending burst for: {name} ---')
    send(sock, encode_device(name))

    count = 0
    for i, param in enumerate(device.get('dials', [])):
        if param:
            value = round(random.uniform(0.0, 1.0), 3)
            send(sock, encode_slot('dial', i, param, value, 0.0, 1.0))
        else:
            send(sock, encode_slot_payload('dial', i, EMPTY_SLOT))
        count += 1

    for i, param in enumerate(device.get('buttons', [])):
        if param:
            value = random.choice([0.0, 1.0])
            send(sock, encode_slot('button', i, param, value, 0.0, 1.0))
        else:
            send(sock, encode_slot_payload('button', i, EMPTY_SLOT))
        count += 1

    send(sock, encode_commit(count))


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    once = len(sys.argv) > 1 and sys.argv[1] == 'once'

    if once:
        send_burst(sock, DEVICES[0])
        return

    print(f'HUD simulator running — sending bursts to {HOST}:{PORT} every 3s. Ctrl-C to stop.')
    idx = 0
    while True:
        send_burst(sock, DEVICES[idx % len(DEVICES)])
        idx += 1
        time.sleep(3)


if __name__ == '__main__':
    main()
