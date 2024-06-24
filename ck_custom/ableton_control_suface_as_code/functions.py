import socket
import importlib
import sys
import socket

def listen_for_reload(port, module_name):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', port))

def tick(self):
    data, addr = sock.recvfrom(1024)
    if data == b'reload':
        try:
            importlib.reload(sys.modules[module_name])
            print(f'Module {module_name} reloaded.')
        except Exception as e:
            print(f'Error reloading module: {e}')


    self.schedule_message(1, self.tick)
