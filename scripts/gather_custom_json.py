#!/usr/bin/env python3
"""
Gather custom device mappings by moving parameters in Ableton.

Usage:
    poetry run python scripts/gather_custom_json.py [--output data/custom_device_mappings.json]

Workflow:
    1. Focus a device in Ableton
    2. Move encoders in the order you want them (position 1 first, position 2 second, ...)
    3. Move quantized parameters (buttons) — they go into the buttons array
    4. Change devices in Ableton to start recording a new device
    5. Ctrl+C to exit (file is saved after every change)

Output is written directly to --output (default: data/custom_device_mappings.json).
Existing entries for already-known devices are preserved and merged.
"""

import argparse
import json
import socket
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class DeviceInfo:
    class_name: str
    name: str
    param_count: int

    def key(self) -> str:
        return f"{self.class_name}:{self.name}"


@dataclass
class DeviceParam:
    index: int
    name: str
    min_value: float
    max_value: float
    is_quantized: bool = False


class UDPClient:
    def __init__(self, host: str, server_port: int, client_port: int, timeout: float) -> None:
        self._server_addr = (host, server_port)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(("", client_port))
        self._sock.settimeout(timeout)

    def close(self) -> None:
        self._sock.close()

    def send_and_receive(self, command: str) -> Optional[str]:
        message = (command + "\n").encode("utf-8")
        self._sock.sendto(message, self._server_addr)
        try:
            data, _ = self._sock.recvfrom(65535)
        except socket.timeout:
            return None
        return data.decode("utf-8").strip()

    def send_and_expect(self, command: str, expected_prefix: str) -> Optional[str]:
        response = self.send_and_receive(command)
        if response is None:
            return None
        if not response.startswith(expected_prefix + "|") and response != expected_prefix:
            return None
        if response == expected_prefix:
            return ""
        return response[len(expected_prefix) + 1:]


@dataclass
class DeviceEntry:
    class_name: str
    device_name: str
    fixed: bool = False
    encoders: list = field(default_factory=list)  # [{"name": str, "display"?: str}]
    buttons: list = field(default_factory=list)   # [{"name": str, "min"?: int, "max"?: int}]

    def encoder_names(self) -> set:
        return {e["name"] for e in self.encoders if "name" in e}

    def button_names(self) -> set:
        return {b["name"] for b in self.buttons if "name" in b}


class CustomJsonGatherer:
    def __init__(self, client: UDPClient, output_path: Path, chunk_size: int) -> None:
        self._client = client
        self._output_path = output_path
        self._chunk_size = chunk_size

        self._device: Optional[DeviceInfo] = None
        self._params: list[DeviceParam] = []
        self._last_values: dict[int, float] = {}

        self._devices: dict[str, DeviceEntry] = self._load_existing()

    def _load_existing(self) -> dict[str, DeviceEntry]:
        if not self._output_path.exists():
            return {}
        try:
            raw = json.loads(self._output_path.read_text())
        except (json.JSONDecodeError, OSError):
            print(f"Warning: could not read {self._output_path}, starting fresh.")
            return {}

        result = {}
        for d in raw.get("devices", []):
            entry = DeviceEntry(
                class_name=d["className"],
                device_name=d.get("deviceName", d["className"]),
                fixed=d.get("fixed", False),
                encoders=d.get("encoders", []),
                buttons=d.get("buttons", []),
            )
            result[entry.class_name] = entry
        print(f"Loaded {len(result)} existing device(s) from {self._output_path}")
        return result

    def run(self, poll_interval: float) -> None:
        print(f"Listening for parameter moves. Output: {self._output_path}")
        print("Move encoders in order — non-quantized → encoders array, quantized → buttons array.")
        print("Ctrl+C to exit.\n")

        while True:
            changed_params = self._poll_once()
            for param in changed_params:
                self._handle_changed_param(param)
            time.sleep(poll_interval)

    def _poll_once(self) -> list[DeviceParam]:
        device = self._get_device()
        if device is None:
            return []

        if self._device is None or device.key() != self._device.key():
            self._on_device_changed(device)

        if not self._params:
            return []

        values = self._get_param_values(len(self._params))
        if values is None:
            return []

        changed: list[DeviceParam] = []
        for param, value in zip(self._params, values):
            last = self._last_values.get(param.index)
            if last is not None and abs(value - last) > 0.001:
                changed.append(param)
            self._last_values[param.index] = value

        return changed

    def _on_device_changed(self, device: DeviceInfo) -> None:
        self._device = device
        self._params = self._get_params(device.param_count)
        self._last_values = {}
        values = self._get_param_values(len(self._params))
        if values:
            for param, value in zip(self._params, values):
                self._last_values[param.index] = value

        existing = self._devices.get(device.class_name)
        enc_count = len(existing.encoders) if existing else 0
        btn_count = len(existing.buttons) if existing else 0
        status = f" (existing: {enc_count} encoders, {btn_count} buttons)" if existing else " (new)"
        print(f"\n--- {device.class_name} ({device.name}){status} ---")
        print(f"    Move encoders → encoders[], quantized params → buttons[]")

    def _handle_changed_param(self, param: DeviceParam) -> None:
        device = self._device
        assert device is not None

        entry = self._devices.setdefault(device.class_name, DeviceEntry(
            class_name=device.class_name,
            device_name=device.name,
        ))

        if param.is_quantized:
            if param.name in entry.button_names():
                return
            btn: dict = {"name": param.name}
            if int(param.max_value) > 1:
                btn["min"] = int(param.min_value)
                btn["max"] = int(param.max_value)
            entry.buttons.append(btn)
            print(f"  button[{len(entry.buttons) - 1}] → {param.name!r}")
        else:
            if param.name in entry.encoder_names():
                return
            entry.encoders.append({"name": param.name})
            print(f"  encoder[{len(entry.encoders) - 1}] → {param.name!r}")

        self._save()

    def _save(self) -> None:
        devices_list = []
        for entry in sorted(self._devices.values(), key=lambda e: e.class_name):
            d: dict = {
                "className": entry.class_name,
                "deviceName": entry.device_name,
                "fixed": entry.fixed,
                "encoders": entry.encoders,
            }
            if entry.buttons:
                d["buttons"] = entry.buttons
            devices_list.append(d)

        result = {"devices": devices_list}
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        self._output_path.write_text(json.dumps(result, indent=2) + "\n")
        print(f"  Saved → {self._output_path}")

    def _get_device(self) -> Optional[DeviceInfo]:
        payload = self._client.send_and_expect("GET_DEVICE", "DEVICE")
        if payload is None:
            return None
        parts = payload.split("|")
        if len(parts) < 3 or not parts[0]:
            return None
        try:
            param_count = int(parts[2])
        except ValueError:
            return None
        return DeviceInfo(class_name=parts[0], name=parts[1], param_count=param_count)

    def _get_params(self, param_count: int) -> list[DeviceParam]:
        params: list[DeviceParam] = []
        for start in range(0, param_count, self._chunk_size):
            count = min(self._chunk_size, param_count - start)
            payload = self._client.send_and_expect(f"GET_PARAMS|{start}|{count}", "PARAMS")
            if not payload:
                continue
            for entry in payload.split(";"):
                fields = entry.split(",")
                if len(fields) < 4:
                    continue
                try:
                    params.append(DeviceParam(
                        index=int(fields[0]),
                        name=fields[1],
                        min_value=float(fields[2]),
                        max_value=float(fields[3]),
                        is_quantized=len(fields) > 4 and fields[4] == "1",
                    ))
                except ValueError:
                    continue
        return params

    def _get_param_values(self, param_count: int) -> Optional[list[float]]:
        values: list[float] = []
        for start in range(0, param_count, self._chunk_size):
            count = min(self._chunk_size, param_count - start)
            payload = self._client.send_and_expect(f"GET_PARAM_VALUES|{start}|{count}", "PARAM_VALUES")
            if payload is None:
                return None
            for v in payload.split(","):
                try:
                    values.append(float(v))
                except ValueError:
                    values.append(0.0)
        return values


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactively gather custom device mappings from Ableton.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--server-port", type=int, default=40844)
    parser.add_argument("--client-port", type=int, default=22021)
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--interval", type=float, default=0.2, help="Polling interval in seconds")
    parser.add_argument("--chunk-size", type=int, default=20)
    parser.add_argument(
        "--output",
        default=str(Path(__file__).parent.parent / "data" / "custom_device_mappings.json"),
        help="Output file path (default: data/custom_device_mappings.json)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = Path(args.output)

    try:
        client = UDPClient(args.host, args.server_port, args.client_port, args.timeout)
    except OSError as exc:
        print(f"Error: Could not bind UDP client port {args.client_port}: {exc}", file=sys.stderr)
        return 1

    try:
        response = client.send_and_receive("PING")
        if response != "PONG":
            print(f"Error: No PONG from Ableton (got: {response!r}). Is Live running with the UDP server?", file=sys.stderr)
            return 1
        print("Connected to Ableton.\n")

        gatherer = CustomJsonGatherer(client, output_path, args.chunk_size)
        gatherer.run(args.interval)
    except KeyboardInterrupt:
        print("\nExiting.")
        return 0
    finally:
        client.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
