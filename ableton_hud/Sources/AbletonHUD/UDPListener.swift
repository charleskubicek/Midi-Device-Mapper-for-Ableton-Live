import Foundation
import AbletonHUDCore
import os

private let log = OSLog(subsystem: "com.local.AbletonHUD", category: "UDPListener")

// File-based debug log (`hudLog`) now lives in AbletonHUDCore/FineLog.swift so
// both targets — and the no-AppKit Core (DeviceState) — share one leveled,
// gateable sink. Verbose per-datagram lines use `level: .fine`.

/// POSIX-based UDP receiver — simpler and more reliable than NWListener for
/// one-way push on loopback.
class UDPListener {
    private let port: UInt16 = 5006
    private var fd: Int32 = -1
    private var thread: Thread?
    private var running = false

    func start() {
        // Seed the fine-trace gate from the sentinel at launch (the recv loop
        // re-reads it per datagram thereafter).
        refreshHudFineEnabled()
        fd = socket(AF_INET, SOCK_DGRAM, 0)
        guard fd >= 0 else {
            os_log("socket() failed: %{public}s", log: log, type: .error, String(cString: strerror(errno)))
            return
        }

        var yes: Int32 = 1
        setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &yes, socklen_t(MemoryLayout<Int32>.size))
        setsockopt(fd, SOL_SOCKET, SO_REUSEPORT, &yes, socklen_t(MemoryLayout<Int32>.size))

        var addr = sockaddr_in()
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = port.bigEndian
        addr.sin_addr.s_addr = INADDR_ANY

        let bindResult = withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                bind(fd, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }

        guard bindResult == 0 else {
            os_log("bind() failed: %{public}s", log: log, type: .error, String(cString: strerror(errno)))
            close(fd); fd = -1
            return
        }

        os_log("listening on UDP :%d", log: log, type: .info, Int(port))
        hudLog("UDPListener: bound to *:\(port)")
        running = true

        thread = Thread { [weak self] in self?.recvLoop() }
        thread?.name = "UDPListenerThread"
        thread?.start()
    }

    func stop() {
        running = false
        if fd >= 0 { close(fd); fd = -1 }
    }

    private func recvLoop() {
        var buf = [UInt8](repeating: 0, count: 4096)
        while running {
            let n = recv(fd, &buf, buf.count, 0)
            if n <= 0 { break }
            let data = Data(buf[0..<n])
            let text = String(data: data, encoding: .utf8) ?? "(non-utf8)"
            // Re-read the /tmp/ableton_hud_fine sentinel each datagram so a
            // touch/rm toggles tracing at runtime within one message.
            refreshHudFineEnabled()
            os_log("recv %d bytes", log: log, type: .debug, n)
            hudLog("recv \(n) bytes: \(text.prefix(120))", level: .fine)
            let messages = WireProtocol.parseAll(data: data)
            DispatchQueue.main.async {
                for msg in messages {
                    hudLog("recv parsed -> \(msg)", level: .fine)
                    DeviceState.shared.apply(message: msg)
                }
            }
        }
        os_log("recv loop ended", log: log, type: .info)
    }
}
