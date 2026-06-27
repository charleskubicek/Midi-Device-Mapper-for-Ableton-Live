import XCTest
@testable import AbletonHUDCore

/// Gate tests for the shared leveled logger (hud-protocol-instrumentation-plan,
/// Part B). `.info` is always emitted; `.fine` only when `hudFineEnabled` is on.
final class FineLogTests: XCTestCase {

    private var captured: [String] = []
    private var savedSink: ((String) -> Void)!
    private var savedEnabled: Bool!

    override func setUp() {
        super.setUp()
        savedSink = hudLogSink
        savedEnabled = hudFineEnabled
        captured = []
        hudLogSink = { [weak self] line in self?.captured.append(line) }
    }

    override func tearDown() {
        hudLogSink = savedSink
        hudFineEnabled = savedEnabled
        super.tearDown()
    }

    func test_fine_suppressed_when_disabled() {
        hudFineEnabled = false
        hudLog("nav enter", level: .fine)
        XCTAssertTrue(captured.isEmpty)
    }

    func test_fine_emitted_when_enabled() {
        hudFineEnabled = true
        hudLog("apply MODE isShift=false->true", level: .fine)
        XCTAssertEqual(captured.count, 1)
        XCTAssertTrue(captured[0].contains("apply MODE"))
    }

    func test_info_always_emitted_regardless_of_flag() {
        hudFineEnabled = false
        hudLog("listening on UDP", level: .info)
        XCTAssertEqual(captured.count, 1)
    }

    func test_info_is_the_default_level() {
        hudFineEnabled = false
        hudLog("plain line")
        XCTAssertEqual(captured.count, 1)
    }

    // The arming path that actually ships: a /tmp file sentinel, launch-agnostic
    // (the HUD is opened via `open App.app`, which inherits no env/UserDefaults).
    func test_sentinel_file_arms_and_disarms_tracing() {
        let path = "/tmp/ableton_hud_fine"
        let fm = FileManager.default
        let preexisting = fm.fileExists(atPath: path)
        defer { if !preexisting { try? fm.removeItem(atPath: path) } }

        try? fm.removeItem(atPath: path)
        XCTAssertFalse(refreshHudFineEnabled(), "absent sentinel -> off")

        fm.createFile(atPath: path, contents: nil)
        XCTAssertTrue(refreshHudFineEnabled(), "present sentinel -> on")
        hudLog("apply HIDE", level: .fine)
        XCTAssertEqual(captured.count, 1)

        try? fm.removeItem(atPath: path)
        XCTAssertFalse(refreshHudFineEnabled(), "removed sentinel -> off again")
    }
}
