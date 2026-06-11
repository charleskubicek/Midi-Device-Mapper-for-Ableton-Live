import argparse
import socket
import sys
from pathlib import Path
from time import sleep

ableton_dir = Path("$ableton_dir")

def send_udp_message(message, ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Send the message
        print(f"Sending message to {ip}:{port}")
        sock.sendto(message, (ip, port))
        sleep(1)
        # Wait for a response
        try:
            data, server = sock.recvfrom(4096)
            print(f"Received response from {server}: {data}")
        except socket.timeout:
            print("No response received within the timeout period.")
    finally:
        # Close the socket
        sock.close()

def main():
    parser = argparse.ArgumentParser(description="Send a UDP message based on command parameter.")
    parser.add_argument('command', type=str, choices=['reload', 'debug', 'dump', 'dump2', 'dumpnames', 'lom', 'doctor', 'showinfo', 'cs_dir', 'options'], help='Command to be executed')

    args = parser.parse_args()

    ip = '127.0.0.1'  # Replace with your target IP address if needed
    port = $udp_port  # Replace with your desired UDP port number

    if args.command == 'cs_dir':
        print((ableton_dir / 'Contents/App-Resources/MIDI Remote Scripts').resolve())
    elif args.command == 'options':
        print((Path.home() / '/Library/Preferences/Ableton').resolve())
    elif args.command == 'reload':
        message = b'reload'
        send_udp_message(message, ip, port)
    elif args.command == 'debug':
        message = b'debug'
        send_udp_message(message, ip, port)
    elif args.command == 'dumpnames':
        message = b'dumpnames'
        send_udp_message(message, ip, port)
    elif args.command == 'lom':
        message = b'lom'
        send_udp_message(message, ip, port)
    elif args.command == 'dump':
        message = b'dump'
        send_udp_message(message, ip, port)
    elif args.command == 'dump2': # splits encoders and buttons
        message = b'dump2'
        send_udp_message(message, ip, port)
    elif args.command == 'doctor': # hardware-mode diagnostic; run once to arm, again to report
        message = b'doctor'
        send_udp_message(message, ip, port)
    elif args.command == 'showinfo': # toggle HUD edge-annotated button feedback
        message = b'showinfo'
        send_udp_message(message, ip, port)
    else:
        print("Invalid command. Use 'reload' or 'debug' to send the respective message.")
        sys.exit(1)

    sys.exit(0)

if __name__ == '__main__':
    main()