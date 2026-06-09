import logging

from .pythonosc.udp_client import SimpleUDPClient
from .pythonosc.osc_message_builder import ArgValue


class NullOSCClient:
    def send_message(self, address: str, value: ArgValue) -> None:
        pass


class OSCClient:

    def __init__(self, host='127.0.0.1', port=5005):
        self.client = SimpleUDPClient(host, port)
        self.logger = logging.getLogger("osc-client")

        self.logger.info(f"OSCClient created with host {host} and port {port}")

    def send_message(self, address: str, value: ArgValue) -> None:
        try:
            self.client.send_message(address, value)
        except Exception as e:
            self.logger.error(f"Error sending OSC message {address} {value} {e}")


class OSCMultiClient:

    def __init__(self, clients: list[OSCClient]):
        self.clients = clients

    def send_message(self, address: str, value: ArgValue) -> None:
        for client in self.clients:
            client.send_message(address, value)
