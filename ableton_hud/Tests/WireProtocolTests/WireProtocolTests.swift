import XCTest
@testable import AbletonHUDCore

final class WireProtocolTests: XCTestCase {

    // MARK: - DEVICE

    func test_device_line() {
        let msg = WireProtocol.parse(line: "DEVICE|main|EQ Eight")
        XCTAssertEqual(msg, .device("EQ Eight"))
    }

    func test_device_empty_name() {
        let msg = WireProtocol.parse(line: "DEVICE|main|")
        XCTAssertEqual(msg, .device(""))
    }

    func test_device_missing_name_is_unknown() {
        let msg = WireProtocol.parse(line: "DEVICE|main")
        XCTAssertEqual(msg, .unknown)
    }

    func test_device_missing_arg_is_unknown() {
        let msg = WireProtocol.parse(line: "DEVICE")
        XCTAssertEqual(msg, .unknown)
    }

    // MARK: - SLOT

    func test_slot_dial() {
        let msg = WireProtocol.parse(line: "SLOT|main|dial|3|Resonance|0.5|0.0|1.0")
        XCTAssertEqual(msg, .slot(.dial, 3, Slot(name: "Resonance", value: 0.5, min: 0.0, max: 1.0)))
    }

    func test_slot_button() {
        let msg = WireProtocol.parse(line: "SLOT|main|button|0|On/Off|1.0|0.0|1.0")
        XCTAssertEqual(msg, .slot(.button, 0, Slot(name: "On/Off", value: 1.0, min: 0.0, max: 1.0)))
    }

    func test_slot_unknown_kind() {
        let msg = WireProtocol.parse(line: "SLOT|main|knob|0|Freq|0.5|0.0|1.0")
        XCTAssertEqual(msg, .unknown)
    }

    func test_slot_malformed_index() {
        let msg = WireProtocol.parse(line: "SLOT|main|dial|x|Freq|0.5|0.0|1.0")
        XCTAssertEqual(msg, .unknown)
    }

    func test_slot_malformed_value() {
        let msg = WireProtocol.parse(line: "SLOT|main|dial|0|Freq|bad|0.0|1.0")
        XCTAssertEqual(msg, .unknown)
    }

    func test_slot_too_few_fields() {
        let msg = WireProtocol.parse(line: "SLOT|main|dial|0|Freq|0.5|0.0")
        XCTAssertEqual(msg, .unknown)
    }

    // MARK: - COMMIT

    func test_commit() {
        let msg = WireProtocol.parse(line: "COMMIT|main|8")
        XCTAssertEqual(msg, .commit(8))
    }

    func test_commit_malformed() {
        let msg = WireProtocol.parse(line: "COMMIT|main|x")
        XCTAssertEqual(msg, .unknown)
    }

    // MARK: - UPDATE (live single-slot update)

    func test_update_dial() {
        let msg = WireProtocol.parse(line: "UPDATE|main|dial|2|Resonance|0.75|0.0|1.0")
        XCTAssertEqual(msg, .update(.dial, 2, Slot(name: "Resonance", value: 0.75, min: 0.0, max: 1.0)))
    }

    func test_update_button() {
        let msg = WireProtocol.parse(line: "UPDATE|main|button|0|On/Off|1.0|0.0|1.0")
        XCTAssertEqual(msg, .update(.button, 0, Slot(name: "On/Off", value: 1.0, min: 0.0, max: 1.0)))
    }

    func test_update_malformed_index() {
        let msg = WireProtocol.parse(line: "UPDATE|main|dial|x|Freq|0.5|0.0|1.0")
        XCTAssertEqual(msg, .unknown)
    }

    func test_update_too_few_fields() {
        let msg = WireProtocol.parse(line: "UPDATE|main|dial|0|Freq|0.5")
        XCTAssertEqual(msg, .unknown)
    }

    // MARK: - MODE

    func test_mode_shift() {
        let msg = WireProtocol.parse(line: "MODE|main|shift")
        XCTAssertEqual(msg, .mode(isShift: true))
    }

    func test_mode_normal() {
        let msg = WireProtocol.parse(line: "MODE|main|normal")
        XCTAssertEqual(msg, .mode(isShift: false))
    }

    func test_mode_unknown_value() {
        let msg = WireProtocol.parse(line: "MODE|main|bogus")
        XCTAssertEqual(msg, .unknown)
    }

    func test_mode_missing_arg() {
        let msg = WireProtocol.parse(line: "MODE|main")
        XCTAssertEqual(msg, .unknown)
    }

    // MARK: - PAGE

    func test_page_message_short_6_fields() {
        let msg = WireProtocol.parse(line: "PAGE|main|2|4|1|2")
        XCTAssertEqual(msg, .page(encPage: 2, encTotal: 4, btnPage: 1, btnTotal: 2,
                                  encLabel: "", btnLabel: ""))
    }

    func test_page_message_with_labels() {
        let msg = WireProtocol.parse(line: "PAGE|main|2|3|1|1|Amplitude / Filter|")
        XCTAssertEqual(msg, .page(encPage: 2, encTotal: 3, btnPage: 1, btnTotal: 1,
                                  encLabel: "Amplitude / Filter", btnLabel: ""))
    }

    func test_page_too_few_fields() {
        let msg = WireProtocol.parse(line: "PAGE|main|1|3|1")
        XCTAssertEqual(msg, .unknown)
    }

    func test_page_malformed_int() {
        let msg = WireProtocol.parse(line: "PAGE|main|x|3|1|2")
        XCTAssertEqual(msg, .unknown)
    }

    // MARK: - HIDE

    func test_hide() {
        let msg = WireProtocol.parse(line: "HIDE|main")
        XCTAssertEqual(msg, .hide)
    }

    func test_hide_without_source_is_unknown() {
        let msg = WireProtocol.parse(line: "HIDE")
        XCTAssertEqual(msg, .unknown)
    }

    func test_hide_with_trailing_field_is_unknown() {
        let msg = WireProtocol.parse(line: "HIDE|main|x")
        XCTAssertEqual(msg, .unknown)
    }

    // MARK: - PING

    func test_ping() {
        let msg = WireProtocol.parse(line: "PING|main")
        XCTAssertEqual(msg, .ping)
    }

    func test_ping_without_source_is_unknown() {
        let msg = WireProtocol.parse(line: "PING")
        XCTAssertEqual(msg, .unknown)
    }

    // MARK: - LAYOUT

    func test_layout() {
        let msg = WireProtocol.parse(line: "LAYOUT|main|main|0|2|0|0|dial|8|0|2|0|button|4|0")
        XCTAssertEqual(msg, .layout([
            HudCell(gridRow: 0, gridCol: 0, kind: .dial, count: 8, startIndex: 0),
            HudCell(gridRow: 2, gridCol: 0, kind: .button, count: 4, startIndex: 0),
        ]))
    }

    func test_layout_field_count_mismatch_is_unknown() {
        // claims 2 cells but only one cell of fields follows
        let msg = WireProtocol.parse(line: "LAYOUT|main|main|0|2|0|0|dial|8|0")
        XCTAssertEqual(msg, .unknown)
    }

    // MARK: - source / group / order identity (parseLine)

    func test_parseLine_carries_source() {
        let pm = WireProtocol.parseLine(line: "DEVICE|parks_btns|EQ Eight")
        XCTAssertEqual(pm.message, .device("EQ Eight"))
        XCTAssertEqual(pm.source, "parks_btns")
    }

    func test_parseLine_layout_carries_group_and_order() {
        let pm = WireProtocol.parseLine(line: "LAYOUT|parks_btns|lc_parks|1|1|0|0|button|4|0")
        XCTAssertEqual(pm.source, "parks_btns")
        XCTAssertEqual(pm.group, "lc_parks")
        XCTAssertEqual(pm.order, 1)
        XCTAssertEqual(pm.message, .layout([
            HudCell(gridRow: 0, gridCol: 0, kind: .button, count: 4, startIndex: 0),
        ]))
    }

    func test_parseLine_slot_carries_source() {
        let pm = WireProtocol.parseLine(line: "SLOT|aux|dial|3|Q|0.5|0.0|1.0")
        XCTAssertEqual(pm.source, "aux")
        XCTAssertEqual(pm.message, .slot(.dial, 3, Slot(name: "Q", value: 0.5, min: 0, max: 1)))
    }

    // MARK: - Unknown commands

    func test_unknown_command_ignored() {
        let msg = WireProtocol.parse(line: "FUTURE|main|foo")
        XCTAssertEqual(msg, .unknown)
    }

    func test_empty_line() {
        let msg = WireProtocol.parse(line: "")
        XCTAssertEqual(msg, .unknown)
    }

    // MARK: - parseAll / multi-line burst

    func test_parse_all_full_burst() {
        let data = """
        DEVICE|main|EQ Eight
        SLOT|main|dial|0|Frequency|440.0|20.0|20000.0
        SLOT|main|dial|1|Resonance|0.5|0.0|1.0
        COMMIT|main|2
        """.data(using: .utf8)!

        let msgs = WireProtocol.parseAll(data: data).map { $0.message }
        XCTAssertEqual(msgs.count, 4)
        XCTAssertEqual(msgs[0], .device("EQ Eight"))
        XCTAssertEqual(msgs[3], .commit(2))
    }

    func test_parse_all_carries_per_message_source() {
        let data = """
        DEVICE|main|Amp
        SLOT|aux|button|0|Type|1|0|2
        """.data(using: .utf8)!
        let msgs = WireProtocol.parseAll(data: data)
        XCTAssertEqual(msgs.map { $0.source }, ["main", "aux"])
    }

    func test_parse_all_with_unknown_line() {
        let data = "DEVICE|main|Test\nFUTURE|whatever\nCOMMIT|main|0\n".data(using: .utf8)!
        let msgs = WireProtocol.parseAll(data: data).map { $0.message }
        XCTAssertEqual(msgs, [.device("Test"), .unknown, .commit(0)])
    }
}

// MARK: - DeviceState burst tests

@MainActor
final class DeviceStateBurstTests: XCTestCase {

    func makeState() -> DeviceState { DeviceState() }

    func test_clean_burst_populates_slots() async {
        let state = makeState()
        state.apply(message: .layout([HudCell(gridRow: 0, gridCol: 0, kind: .dial, count: 3, startIndex: 0)]))
        state.apply(message: .device("Reverb"))
        state.apply(message: .slot(.dial, 0, Slot(name: "Size", value: 0.5, min: 0, max: 1)))
        state.apply(message: .slot(.dial, 2, Slot(name: "Damp", value: 0.3, min: 0, max: 1)))
        state.apply(message: .commit(2))

        XCTAssertEqual(state.deviceName, "Reverb")
        XCTAssertEqual(state.dialSlots[0]?.name, "Size")
        XCTAssertNil(state.dialSlots[1])
        XCTAssertEqual(state.dialSlots[2]?.name, "Damp")
    }

    func test_second_burst_clears_first() async {
        let state = makeState()
        state.apply(message: .layout([HudCell(gridRow: 0, gridCol: 0, kind: .dial, count: 1, startIndex: 0)]))
        state.apply(message: .device("Device A"))
        state.apply(message: .slot(.dial, 0, Slot(name: "Param", value: 0.5, min: 0, max: 1)))
        state.apply(message: .commit(1))

        // Second burst
        state.apply(message: .device("Device B"))
        state.apply(message: .commit(0))

        XCTAssertEqual(state.deviceName, "Device B")
        XCTAssertNil(state.dialSlots[0]) // cleared
    }

    func test_out_of_range_index_ignored() async {
        let state = makeState()
        state.apply(message: .device("X"))
        state.apply(message: .slot(.dial, 8, Slot(name: "Overflow", value: 0, min: 0, max: 1)))
        state.apply(message: .slot(.dial, -1, Slot(name: "Underflow", value: 0, min: 0, max: 1)))
        state.apply(message: .commit(0))

        XCTAssertTrue(state.dialSlots.allSatisfy { $0 == nil })
    }

    // MARK: - UPDATE applies immediately without COMMIT

    func test_update_writes_slot_directly() async {
        let state = makeState()
        state.apply(message: .layout([HudCell(gridRow: 0, gridCol: 0, kind: .dial, count: 4, startIndex: 0)]))
        state.apply(message: .device("EQ Eight"))
        state.apply(message: .commit(0))

        // Now a live knob-turn update arrives
        state.apply(message: .update(.dial, 3, Slot(name: "Freq", value: 0.8, min: 0, max: 1)))

        XCTAssertEqual(state.dialSlots[3]?.name, "Freq")
        XCTAssertEqual(state.dialSlots[3]?.value, 0.8)
    }

    func test_update_does_not_affect_other_slots() async {
        let state = makeState()
        state.apply(message: .layout([HudCell(gridRow: 0, gridCol: 0, kind: .dial, count: 3, startIndex: 0)]))
        state.apply(message: .device("Rev"))
        state.apply(message: .slot(.dial, 0, Slot(name: "Size", value: 0.5, min: 0, max: 1)))
        state.apply(message: .commit(1))

        state.apply(message: .update(.dial, 2, Slot(name: "Damp", value: 0.2, min: 0, max: 1)))

        XCTAssertEqual(state.dialSlots[0]?.name, "Size")  // untouched
        XCTAssertEqual(state.dialSlots[2]?.name, "Damp")  // updated
        XCTAssertNil(state.dialSlots[1])                  // still nil
    }

    func test_update_button_slot() async {
        let state = makeState()
        state.apply(message: .layout([HudCell(gridRow: 0, gridCol: 0, kind: .button, count: 2, startIndex: 0)]))
        state.apply(message: .device("Filter"))
        state.apply(message: .commit(0))

        state.apply(message: .update(.button, 1, Slot(name: "On/Off", value: 1, min: 0, max: 1)))

        XCTAssertEqual(state.buttonSlots[1]?.name, "On/Off")
        XCTAssertEqual(state.buttonSlots[1]?.value, 1.0)
    }

    func test_update_out_of_range_ignored() async {
        let state = makeState()
        state.apply(message: .device("X"))
        state.apply(message: .commit(0))

        state.apply(message: .update(.dial, 8, Slot(name: "OOB", value: 0, min: 0, max: 1)))
        XCTAssertTrue(state.dialSlots.allSatisfy { $0 == nil })
    }

    func test_update_fires_commitReceived() async {
        let state = makeState()
        var firedCount = 0
        let cancellable = state.commitReceived.sink { firedCount += 1 }
        defer { cancellable.cancel() }

        state.apply(message: .update(.dial, 0, Slot(name: "X", value: 0.5, min: 0, max: 1)))
        XCTAssertEqual(firedCount, 1)
    }

    // MARK: - Dense-symmetric emission (sender fills empty slots)
    //
    // The Python sender now emits one SLOT per cell position for both
    // dials AND buttons. Empty positions carry the sentinel
    // `||0|0|1` (empty name, value 0, min 0, max 1). The receiver must
    // treat this as a real `.slot` message and render it as an empty slot.

    func test_empty_slot_sentinel_parses_as_slot() {
        let msg = WireProtocol.parse(line: "SLOT|main|button|1||0|0|1")
        XCTAssertEqual(msg, .slot(.button, 1, Slot(name: "", value: 0, min: 0, max: 1)))
    }

    func test_empty_dial_sentinel_parses_as_slot() {
        let msg = WireProtocol.parse(line: "SLOT|main|dial|3||0|0|1")
        XCTAssertEqual(msg, .slot(.dial, 3, Slot(name: "", value: 0, min: 0, max: 1)))
    }

    func test_dense_burst_produces_named_and_empty_slots() async {
        let state = makeState()
        state.apply(message: .layout([HudCell(gridRow: 0, gridCol: 0, kind: .dial, count: 4, startIndex: 0)]))
        state.apply(message: .device("Dev"))
        // Dense emission: positions 0 and 2 named, 1 and 3 empty (sentinel)
        state.apply(message: .slot(.dial, 0, Slot(name: "Freq", value: 0.5, min: 0, max: 1)))
        state.apply(message: .slot(.dial, 1, Slot(name: "", value: 0, min: 0, max: 1)))
        state.apply(message: .slot(.dial, 2, Slot(name: "Q", value: 0.7, min: 0, max: 1)))
        state.apply(message: .slot(.dial, 3, Slot(name: "", value: 0, min: 0, max: 1)))
        state.apply(message: .commit(4))

        XCTAssertEqual(state.dialSlots.count, 4)
        XCTAssertEqual(state.dialSlots[0]?.name, "Freq")
        XCTAssertEqual(state.dialSlots[1]?.name, "")  // empty sentinel renders as named-empty slot
        XCTAssertEqual(state.dialSlots[2]?.name, "Q")
        XCTAssertEqual(state.dialSlots[3]?.name, "")
    }

    func test_dense_burst_with_only_dials_publishes_empty_buttons() async {
        let state = makeState()
        state.apply(message: .layout([HudCell(gridRow: 0, gridCol: 0, kind: .dial, count: 2, startIndex: 0)]))
        state.apply(message: .device("Dev"))
        state.apply(message: .slot(.dial, 0, Slot(name: "A", value: 0.1, min: 0, max: 1)))
        state.apply(message: .slot(.dial, 1, Slot(name: "B", value: 0.2, min: 0, max: 1)))
        state.apply(message: .commit(2))

        XCTAssertEqual(state.dialSlots.count, 2)
        XCTAssertEqual(state.buttonSlots.count, 0)
    }

    // MARK: - PAGE message burst

    func test_page_published_on_commit() async {
        let state = makeState()
        state.apply(message: .layout([HudCell(gridRow: 0, gridCol: 0, kind: .dial, count: 3, startIndex: 0)]))
        state.apply(message: .device("Dev"))
        state.apply(message: .page(encPage: 2, encTotal: 4, btnPage: 1, btnTotal: 2,
                                   encLabel: "", btnLabel: ""))
        state.apply(message: .commit(0))

        XCTAssertEqual(state.encoderPage, 2)
        XCTAssertEqual(state.pageTotal, 4) // max(encTotal=4, btnTotal=2)
    }

    func test_bank_label_published_on_commit_and_reset_on_device() async {
        let state = makeState()
        state.apply(message: .layout([HudCell(gridRow: 0, gridCol: 0, kind: .dial, count: 3, startIndex: 0)]))
        state.apply(message: .device("Simpler"))
        state.apply(message: .page(encPage: 2, encTotal: 3, btnPage: 1, btnTotal: 1,
                                   encLabel: "Amplitude / Filter", btnLabel: ""))
        state.apply(message: .commit(0))
        XCTAssertEqual(state.bankLabel, "Amplitude / Filter")

        state.apply(message: .device("Other"))
        state.apply(message: .commit(0))
        XCTAssertEqual(state.bankLabel, "")
    }

    func test_bank_label_falls_back_to_btn_label_when_enc_empty() async {
        let state = makeState()
        state.apply(message: .layout([HudCell(gridRow: 0, gridCol: 0, kind: .button, count: 4, startIndex: 0)]))
        state.apply(message: .device("Dev"))
        state.apply(message: .page(encPage: 1, encTotal: 1, btnPage: 2, btnTotal: 3,
                                   encLabel: "", btnLabel: "Routing"))
        state.apply(message: .commit(0))
        XCTAssertEqual(state.bankLabel, "Routing")
    }

    func test_page_resets_on_device() async {
        let state = makeState()
        state.apply(message: .layout([HudCell(gridRow: 0, gridCol: 0, kind: .dial, count: 3, startIndex: 0)]))
        state.apply(message: .device("Dev"))
        state.apply(message: .page(encPage: 2, encTotal: 3, btnPage: 1, btnTotal: 1,
                                   encLabel: "Amplitude / Filter", btnLabel: ""))
        state.apply(message: .commit(0))
        XCTAssertEqual(state.encoderPage, 2)

        state.apply(message: .device("Other"))
        state.apply(message: .commit(0))
        XCTAssertEqual(state.encoderPage, 1)
        XCTAssertEqual(state.pageTotal, 1)
    }

    func test_page_total_is_max_of_encoder_and_button_totals() async {
        let state = makeState()
        state.apply(message: .layout([HudCell(gridRow: 0, gridCol: 0, kind: .dial, count: 2, startIndex: 0)]))
        state.apply(message: .device("Dev"))
        // 3 encoder pages, 5 button pages → total should show 5
        state.apply(message: .page(encPage: 1, encTotal: 3, btnPage: 1, btnTotal: 5,
                                   encLabel: "", btnLabel: ""))
        state.apply(message: .commit(0))

        XCTAssertEqual(state.encoderPage, 1)
XCTAssertEqual(state.pageTotal, 5)
    }

    // MARK: - MODE message

    func test_mode_sets_isShiftMode() async {
        let state = makeState()
        XCTAssertFalse(state.isShiftMode)
        state.apply(message: .mode(isShift: true))
        XCTAssertTrue(state.isShiftMode)
        state.apply(message: .mode(isShift: false))
        XCTAssertFalse(state.isShiftMode)
    }

    // MARK: - HIDE / sticky dismiss

    func test_hide_sets_dismissed_and_fires_hideRequested() async {
        let state = makeState()
        var fired = 0
        let cancellable = state.hideRequested.sink { fired += 1 }
        defer { cancellable.cancel() }

        XCTAssertFalse(state.dismissed)
        state.apply(message: .hide)
        XCTAssertTrue(state.dismissed)
        XCTAssertEqual(fired, 1)
    }

    func test_device_clears_dismissed() async {
        let state = makeState()
        state.apply(message: .hide)
        XCTAssertTrue(state.dismissed)
        state.apply(message: .device("Dev"))
        XCTAssertFalse(state.dismissed)
    }

    func test_commit_clears_dismissed() async {
        let state = makeState()
        state.apply(message: .hide)
        XCTAssertTrue(state.dismissed)
        state.apply(message: .commit(0))
        XCTAssertFalse(state.dismissed)
    }

    func test_update_and_ping_leave_dismissed_set() async {
        let state = makeState()
        state.apply(message: .hide)
        state.apply(message: .update(.dial, 0, Slot(name: "X", value: 0.5, min: 0, max: 1)))
        XCTAssertTrue(state.dismissed)
        state.apply(message: .ping)
        XCTAssertTrue(state.dismissed)
    }
}

// MARK: - Multi-source state (no clobber)

@MainActor
final class MultiSourceStateTests: XCTestCase {

    func makeState() -> DeviceState { DeviceState() }

    private func commitBurst(_ state: DeviceState, source: String, group: String = "main",
                             order: Int = 0, device: String, dialName: String) {
        state.apply(message: .layout([HudCell(gridRow: 0, gridCol: 0, kind: .dial, count: 1, startIndex: 0)]),
                    source: source, group: group, order: order)
        state.apply(message: .device(device), source: source)
        state.apply(message: .slot(.dial, 0, Slot(name: dialName, value: 0.5, min: 0, max: 1)), source: source)
        state.apply(message: .commit(1), source: source)
    }

    func test_two_sources_do_not_clobber_each_other() async {
        let state = makeState()
        commitBurst(state, source: "main", device: "EQ Eight", dialName: "Freq")
        commitBurst(state, source: "parks_btns", device: "EQ Eight", dialName: "ParksKnob")

        // Both sources retain their own committed slots — the second burst did
        // not wipe the first (the regression this whole feature fixes).
        XCTAssertEqual(state.sources["main"]?.dialSlots[0]?.name, "Freq")
        XCTAssertEqual(state.sources["parks_btns"]?.dialSlots[0]?.name, "ParksKnob")
    }

    func test_layout_records_group_and_order_per_source() async {
        let state = makeState()
        commitBurst(state, source: "main", group: "lc_parks", order: 0, device: "D", dialName: "A")
        commitBurst(state, source: "parks_btns", group: "lc_parks", order: 1, device: "D", dialName: "B")

        XCTAssertEqual(state.sources["main"]?.group, "lc_parks")
        XCTAssertEqual(state.sources["main"]?.order, 0)
        XCTAssertEqual(state.sources["parks_btns"]?.group, "lc_parks")
        XCTAssertEqual(state.sources["parks_btns"]?.order, 1)
    }

    func test_sources_seen_are_tracked_in_order() async {
        let state = makeState()
        state.apply(message: .ping, source: "main")
        state.apply(message: .ping, source: "parks_btns")
        XCTAssertEqual(state.sourceOrder, ["main", "parks_btns"])
    }

    func test_hide_on_one_source_does_not_dismiss_the_other() async {
        let state = makeState()
        commitBurst(state, source: "main", device: "D", dialName: "A")
        commitBurst(state, source: "parks_btns", device: "D", dialName: "B")

        state.apply(message: .hide, source: "parks_btns")

        XCTAssertTrue(state.sources["parks_btns"]?.dismissed ?? false)
        XCTAssertFalse(state.sources["main"]?.dismissed ?? true)
    }

    func test_active_group_is_group_of_most_recent_source() async {
        let state = makeState()
        // A standalone 'main' surface, plus an lc_parks pair.
        commitBurst(state, source: "solo", group: "solo", order: 0, device: "Solo", dialName: "S")
        commitBurst(state, source: "lc", group: "lc_parks", order: 0, device: "Lc", dialName: "L")
        commitBurst(state, source: "parks", group: "lc_parks", order: 1, device: "Pk", dialName: "P")

        // Most recent was 'parks' → active group is lc_parks → two members,
        // ordered by `order` (lc then parks). 'solo' is excluded.
        let members = state.activeMembers().map { $0.id }
        XCTAssertEqual(members, ["lc", "parks"])
    }

    func test_anyActiveVisible_true_while_one_member_not_dismissed() async {
        let state = makeState()
        commitBurst(state, source: "lc", group: "lc_parks", order: 0, device: "Lc", dialName: "L")
        commitBurst(state, source: "parks", group: "lc_parks", order: 1, device: "Pk", dialName: "P")

        state.apply(message: .hide, source: "parks")
        XCTAssertTrue(state.anyActiveVisible)   // 'lc' still visible

        state.apply(message: .hide, source: "lc")
        XCTAssertFalse(state.anyActiveVisible)  // all dismissed → panel may hide
    }

    func test_partner_hide_without_layout_does_not_hijack_active_group() async {
        // Real-world regression: the partner surface's LAYOUT was lost (it is
        // sent once at init, before the HUD app started), so the partner only
        // ever emits HIDE. That HIDE must not become the active source nor pull
        // the active group onto a phantom group that excludes the committed
        // surface — otherwise the HUD never shows.
        let state = makeState()
        commitBurst(state, source: "main", group: "lc_parks", order: 0, device: "Auto Filter", dialName: "Freq")

        // Partner sends only HIDE — never a LAYOUT or burst.
        state.apply(message: .hide, source: "parks_btns")

        XCTAssertTrue(state.anyActiveVisible, "main is committed and not dismissed")
        XCTAssertTrue(state.activeMembers().contains { $0.id == "main" })
    }

    func test_commit_sets_active_source_not_hide() async {
        let state = makeState()
        commitBurst(state, source: "main", group: "lc_parks", order: 0, device: "D", dialName: "A")
        state.apply(message: .hide, source: "parks_btns")
        // The committed surface, not the HIDE-only partner, owns the active group.
        XCTAssertEqual(state.activeSource, "main")
    }

    func test_interleaved_bursts_keep_separate_pending_buffers() async {
        let state = makeState()
        // Two bursts interleaved at the datagram level (worst case under UDP).
        state.apply(message: .layout([HudCell(gridRow: 0, gridCol: 0, kind: .dial, count: 1, startIndex: 0)]), source: "main")
        state.apply(message: .layout([HudCell(gridRow: 0, gridCol: 0, kind: .dial, count: 1, startIndex: 0)]), source: "aux")
        state.apply(message: .device("MainDev"), source: "main")
        state.apply(message: .device("AuxDev"), source: "aux")
        state.apply(message: .slot(.dial, 0, Slot(name: "MainP", value: 0.1, min: 0, max: 1)), source: "main")
        state.apply(message: .slot(.dial, 0, Slot(name: "AuxP", value: 0.2, min: 0, max: 1)), source: "aux")
        state.apply(message: .commit(1), source: "main")
        state.apply(message: .commit(1), source: "aux")

        XCTAssertEqual(state.sources["main"]?.deviceName, "MainDev")
        XCTAssertEqual(state.sources["main"]?.dialSlots[0]?.name, "MainP")
        XCTAssertEqual(state.sources["aux"]?.deviceName, "AuxDev")
        XCTAssertEqual(state.sources["aux"]?.dialSlots[0]?.name, "AuxP")
    }
}
