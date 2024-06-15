import socket

# The message you want to send
message = b'reload'

# The target IP address and port
ip = '0.0.0.0'
port = $udp_port

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

try:
    # Send the message
    sock.sendto(message, (ip, port))
    print(f"Sent message to {ip}:{port}")
finally:
    # Close the socket
    sock.close()
