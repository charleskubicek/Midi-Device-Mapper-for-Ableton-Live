import Foundation

/// Leveled debug logging shared by both targets (hud-protocol-instrumentation-plan,
/// Part B). `.info` lines are always written; `.fine` lines only when
/// `hudFineEnabled` is on. Both go to `/tmp/ableton_hud_debug.log`, which can be
/// tailed in a terminal alongside the Ableton log (`./bin/tail_logs.sh`) so the
/// HUD receiver trace correlates with the surface sender trace by wall clock.
public enum HudLogLevel {
    case info
    case fine
}

/// Gate for `.fine` logging. The HUD is launched via `open AbletonHUD.app`, which
/// inherits neither the shell environment nor `UserDefaults.standard`'s domain —
/// so the robust, launch-agnostic switch is a **file sentinel**: tracing is on
/// while `/tmp/ableton_hud_fine` exists. This also gives runtime on/off (matching
/// the surface's `hudtrace` command) instead of relaunch-to-toggle:
///
///     touch /tmp/ableton_hud_fine    # tracing on
///     rm    /tmp/ableton_hud_fine    # tracing off
///
/// `hudFineEnabled` is the live stored gate; `refreshHudFineEnabled()` re-reads
/// the sentinel (called once per datagram from the recv loop, so a touch/rm takes
/// effect within one message). `HUD_FINE=1` stays a fallback for `swift run`. A
/// plain global is adequate for a debug flag — reads on the recv thread and main
/// actor tolerate a benign race. Tests set this directly to exercise the gate.
public var hudFineEnabled: Bool = false

private let hudFineSentinelPath = "/tmp/ableton_hud_fine"

/// Re-evaluate the gate from the sentinel file (+ env fallback) and store it.
@discardableResult
public func refreshHudFineEnabled() -> Bool {
    hudFineEnabled = FileManager.default.fileExists(atPath: hudFineSentinelPath)
        || ProcessInfo.processInfo.environment["HUD_FINE"] == "1"
    return hudFineEnabled
}

/// The actual emission sink. Defaults to the file writer; tests swap it for a
/// capturing closure so the gate logic is unit-testable without touching disk.
public var hudLogSink: (String) -> Void = hudLogWriteToFile

private let hudLogURL = URL(fileURLWithPath: "/tmp/ableton_hud_debug.log")
private let hudLogQueue = DispatchQueue(label: "com.local.AbletonHUD.finelog")

/// Serialised append so the recv thread and main actor don't interleave writes.
public func hudLogWriteToFile(_ line: String) {
    hudLogQueue.async {
        guard let data = line.data(using: .utf8) else { return }
        if let fh = try? FileHandle(forUpdating: hudLogURL) {
            fh.seekToEndOfFile(); fh.write(data); try? fh.close()
        } else {
            try? data.write(to: hudLogURL)
        }
    }
}

public func hudLog(_ msg: String, level: HudLogLevel = .info) {
    if level == .fine && !hudFineEnabled { return }
    let tag = level == .fine ? "[fine] " : ""
    hudLogSink("[\(Date())] \(tag)\(msg)\n")
}
