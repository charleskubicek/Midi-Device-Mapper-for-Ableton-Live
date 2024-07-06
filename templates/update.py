import argparse
import socket
from time import sleep


def send_udp_message(message, ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Send the message
        sock.sendto(message, (ip, port))
        print(f"Sent message to {ip}:{port}")
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
    parser.add_argument('command', type=str, choices=['reload', 'debug', 'dump'], help='Command to be executed')

    args = parser.parse_args()

    ip = '0.0.0.0'  # Replace with your target IP address if needed
    port = $udp_port  # Replace with your desired UDP port number

    if args.command == 'reload':
        message = b'reload'
        send_udp_message(message, ip, port)
    elif args.command == 'debug':
        message = b'debug'
        send_udp_message(message, ip, port)
    elif args.command == 'dump':
        message = b'dump'
        send_udp_message(message, ip, port)
    else:
        print("Invalid command. Use 'reload' or 'debug' to send the respective message.")

if __name__ == '__main__':
    main()