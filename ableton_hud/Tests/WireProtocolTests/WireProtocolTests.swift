import XCTest
@testable import AbletonHUDCore

final class WireProtocolTests: XCTestCase {

    // MARK: - DEVICE

    func test_device_line() {
        let msg = WireProtocol.parse(line: "DEVICE|EQ Eight")
        XCTAssertEqual(msg, .device("EQ Eight"))
    }

    func test_device_empty_name() {
        let msg = WireProtocol.parse(line: "DEVICE|")
        XCTAssertEqual(msg, .device(""))
    }

    func test_device_missing_arg_is_unknown() {
        let msg = WireProtocol.parse(line: "DEVICE")
        XCTAssertEqual(msg, .unknown)
    }

    // MARK: - SLOT

    func test_slot_dial() {
        let msg = WireProtocol.parse(line: "SLOT|dial|3|Resonance|0.5|0.0|1.0")
        XCTAssertEqual(msg, .slot(.dial, 3, Slot(name: "Resonance", value: 0.5, min: 0.0, max: 1.0)))
    }

    func test_slot_button() {
        let msg = WireProtocol.parse(line: "SLOT|button|0|On/Off|1.0|0.0|1.0")
        XCTAssertEqual(msg, .slot(.button, 0, Slot(name: "On/Off", value: 1.0, min: 0.0, max: 1.0)))
    }

    func test_slot_unknown_kind() {
        let msg = WireProtocol.parse(line: "SLOT|knob|0|Freq|0.5|0.0|1.0")
        XCTAssertEqual(msg, .unknown)
    }

    func test_slot_malformed_index() {
        let msg = WireProtocol.parse(line: "SLOT|dial|x|Freq|0.5|0.0|1.0")
        XCTAssertEqual(msg, .unknown)
    }

    func test_slot_malformed_value() {
        let msg = WireProtocol.parse(line: "SLOT|dial|0|Freq|bad|0.0|1.0")
        XCTAssertEqual(msg, .unknown)
    }

    func test_slot_too_few_fields() {
        let msg = WireProtocol.parse(line: "SLOT|dial|0|Freq|0.5|0.0")
        XCTAssertEqual(msg, .unknown)
    }

    // MARK: - COMMIT

    func test_commit() {
        let msg = WireProtocol.parse(line: "COMMIT|8")
        XCTAssertEqual(msg, .commit(8))
    }

    func test_commit_malformed() {
        let msg = WireProtocol.parse(line: "COMMIT|x")
        XCTAssertEqual(msg, .unknown)
    }

    // MARK: - UPDATE (live single-slot update)

    func test_update_dial() {
        let msg = WireProtocol.parse(line: "UPDATE|dial|2|Resonance|0.75|0.0|1.0")
        XCTAssertEqual(msg, .update(.dial, 2, Slot(name: "Resonance", value: 0.75, min: 0.0, max: 1.0)))
    }

    func test_update_button() {
        let msg = WireProtocol.parse(line: "UPDATE|button|0|On/Off|1.0|0.0|1.0")
        XCTAssertEqual(msg, .update(.button, 0, Slot(name: "On/Off", value: 1.0, min: 0.0, max: 1.0)))
    }

    func test_update_malformed_index() {
        let msg = WireProtocol.parse(line: "UPDATE|dial|x|Freq|0.5|0.0|1.0")
        XCTAssertEqual(msg, .unknown)
    }

    func test_update_too_few_fields() {
        let msg = WireProtocol.parse(line: "UPDATE|dial|0|Freq|0.5")
        XCTAssertEqual(msg, .unknown)
    }

    // MARK: - MODE

    func test_mode_shift() {
        let msg = WireProtocol.parse(line: "MODE|shift")
        XCTAssertEqual(msg, .mode(isShift: true))
    }

    func test_mode_normal() {
        let msg = WireProtocol.parse(line: "MODE|normal")
        XCTAssertEqual(msg, .mode(isShift: false))
    }

    func test_mode_unknown_value() {
        let msg = WireProtocol.parse(line: "MODE|bogus")
        XCTAssertEqual(msg, .unknown)
    }

    func test_mode_missing_arg() {
        let msg = WireProtocol.parse(line: "MODE")
        XCTAssertEqual(msg, .unknown)
    }

    // MARK: - PAGE

    func test_page_message_short_5_fields() {
        let msg = WireProtocol.parse(line: "PAGE|2|4|1|2")
        XCTAssertEqual(msg, .page(encPage: 2, encTotal: 4, btnPage: 1, btnTotal: 2,
                                  encLabel: "", btnLabel: ""))
    }

    func test_page_message_with_labels() {
        let msg = WireProtocol.parse(line: "PAGE|2|3|1|1|Amplitude / Filter|")
        XCTAssertEqual(msg, .page(encPage: 2, encTotal: 3, btnPage: 1, btnTotal: 1,
                                  encLabel: "Amplitude / Filter", btnLabel: ""))
    }

    func test_page_too_few_fields() {
        let msg = WireProtocol.parse(line: "PAGE|1|3|1")
        XCTAssertEqual(msg, .unknown)
    }

    func test_page_malformed_int() {
        let msg = WireProtocol.parse(line: "PAGE|x|3|1|2")
        XCTAssertEqual(msg, .unknown)
    }

    // MARK: - EVENT

    func test_event_message_parses() {
        let msg = WireProtocol.parse(line: "EVENT|button|4|row-3:5 ▼127 → acted")
        XCTAssertEqual(msg, .event(kind: "button", wireIdx: 4, text: "row-3:5 ▼127 → acted"))
    }

    func test_event_text_may_contain_pipe() {
        let msg = WireProtocol.parse(line: "EVENT|info|-1|a|b|c")
        XCTAssertEqual(msg, .event(kind: "info", wireIdx: -1, text: "a|b|c"))
    }

    func test_event_too_few_fields() {
        XCTAssertEqual(WireProtocol.parse(line: "EVENT|info|0"), .unknown)
    }

    func test_event_malformed_index() {
        XCTAssertEqual(WireProtocol.parse(line: "EVENT|info|x|text"), .unknown)
    }

    // MARK: - HIDE

    func test_hide() {
        let msg = WireProtocol.parse(line: "HIDE")
        XCTAssertEqual(msg, .hide)
    }

    func test_hide_with_trailing_field_is_unknown() {
        let msg = WireProtocol.parse(line: "HIDE|x")
        XCTAssertEqual(msg, .unknown)
    }

    // MARK: - PING

    func test_ping() {
        let msg = WireProtocol.parse(line: "PING")
        XCTAssertEqual(msg, .ping)
    }

    func test_ping_with_trailing_field_is_unknown() {
        let msg = WireProtocol.parse(line: "PING|x")
        XCTAssertEqual(msg, .unknown)
    }

    // MARK: - LAYOUT

    func test_layout() {
        let msg = WireProtocol.parse(line: "LAYOUT|2|0|0|dial|8|0|0|2|0|button|4|0|1")
        XCTAssertEqual(msg, .layout([
            HudCell(gridRow: 0, gridCol: 0, kind: .dial, count: 8, startIndex: 0, section: 0),
            HudCell(gridRow: 2, gridCol: 0, kind: .button, count: 4, startIndex: 0, section: 1),
        ]))
    }

    func test_layout_field_count_mismatch_is_unknown() {
        // claims 2 cells but only one cell of fields follows
        let msg = WireProtocol.parse(line: "LAYOUT|2|0|0|dial|8|0")
        XCTAssertEqual(msg, .unknown)
    }

    // MARK: - Unknown commands

    func test_unknown_command_ignored() {
        let msg = WireProtocol.parse(line: "FUTURE|foo")
        XCTAssertEqual(msg, .unknown)
    }

    func test_empty_line() {
        let msg = WireProtocol.parse(line: "")
        XCTAssertEqual(msg, .unknown)
    }

    // MARK: - parseAll / multi-line burst

    func test_parse_all_full_burst() {
        let data = """
        DEVICE|EQ Eight
        SLOT|dial|0|Frequency|440.0|20.0|20000.0
        SLOT|dial|1|Resonance|0.5|0.0|1.0
        COMMIT|2
        """.data(using: .utf8)!

        let msgs = WireProtocol.parseAll(data: data)
        XCTAssertEqual(msgs.count, 4)
        XCTAssertEqual(msgs[0], .device("EQ Eight"))
        XCTAssertEqual(msgs[3], .commit(2))
    }

    func test_parse_all_with_unknown_line() {
        let data = "DEVICE|Test\nFUTURE|whatever\nCOMMIT|0\n".data(using: .utf8)!
        let msgs = WireProtocol.parseAll(data: data)
        XCTAssertEqual(msgs, [.device("Test"), .unknown, .commit(0)])
    }
}

// MARK: - DeviceState burst tests

@MainActor
final class DeviceStateBurstTests: XCTestCase {

    func makeState() -> DeviceState { DeviceState() }

    func test_event_publishes_last_event_without_touching_slots() async {
        let state = makeState()
        state.apply(message: .layout([HudCell(gridRow: 0, gridCol: 0, kind: .dial, count: 1, startIndex: 0)]))
        state.apply(message: .device("Reverb"))
        state.apply(message: .slot(.dial, 0, Slot(name: "Size", value: 0.5, min: 0, max: 1)))
        state.apply(message: .commit(1))

        state.apply(message: .event(kind: "button", wireIdx: 3, text: "row-3:5 acted"))
        XCTAssertEqual(state.lastEvent?.text, "row-3:5 acted")
        XCTAssertEqual(state.lastEvent?.wireIdx, 3)
        // slot/published state is untouched by an EVENT
        XCTAssertEqual(state.dialSlots[0]?.name, "Size")
    }

    func test_event_seq_increments_so_repeats_retrigger() async {
        let state = makeState()
        state.apply(message: .event(kind: "info", wireIdx: -1, text: "same"))
        let first = state.lastEvent?.seq
        state.apply(message: .event(kind: "info", wireIdx: -1, text: "same"))
        let second = state.lastEvent?.seq
        XCTAssertNotNil(first)
        XCTAssertNotNil(second)
        XCTAssertGreaterThan(second!, first!)
    }

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

    func test_empty_slot_sentinel_parses_as_slot() {
        let msg = WireProtocol.parse(line: "SLOT|button|1||0|0|1")
        XCTAssertEqual(msg, .slot(.button, 1, Slot(name: "", value: 0, min: 0, max: 1)))
    }

    func test_empty_dial_sentinel_parses_as_slot() {
        let msg = WireProtocol.parse(line: "SLOT|dial|3||0|0|1")
        XCTAssertEqual(msg, .slot(.dial, 3, Slot(name: "", value: 0, min: 0, max: 1)))
    }

    func test_dense_burst_produces_named_and_empty_slots() async {
        let state = makeState()
        state.apply(message: .layout([HudCell(gridRow: 0, gridCol: 0, kind: .dial, count: 4, startIndex: 0)]))
        state.apply(message: .device("Dev"))
        state.apply(message: .slot(.dial, 0, Slot(name: "Freq", value: 0.5, min: 0, max: 1)))
        state.apply(message: .slot(.dial, 1, Slot(name: "", value: 0, min: 0, max: 1)))
        state.apply(message: .slot(.dial, 2, Slot(name: "Q", value: 0.7, min: 0, max: 1)))
        state.apply(message: .slot(.dial, 3, Slot(name: "", value: 0, min: 0, max: 1)))
        state.apply(message: .commit(4))

        XCTAssertEqual(state.dialSlots.count, 4)
        XCTAssertEqual(state.dialSlots[0]?.name, "Freq")
        XCTAssertEqual(state.dialSlots[1]?.name, "")
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

    // MARK: - Combined grid (lc_parks compositor side-by-side)

    func test_combined_layout_tags_secondary_as_its_own_section() async {
        // The compositor sends one LAYOUT containing primary cells (section 0)
        // plus the secondary's cells tagged section 1. The secondary keeps its
        // OWN grid (grid_col 0) — the HUD renders section 1 as an independent
        // block to the right — but its slot indices are bumped into the shared
        // flat dial array (start 2).
        let state = makeState()
        state.apply(message: .layout([
            HudCell(gridRow: 0, gridCol: 0, kind: .dial, count: 2, startIndex: 0, section: 0),   // primary
            HudCell(gridRow: 0, gridCol: 0, kind: .dial, count: 1, startIndex: 2, section: 1),   // secondary
        ]))
        state.apply(message: .device("Dev"))
        state.apply(message: .slot(.dial, 0, Slot(name: "P0", value: 0.1, min: 0, max: 1)))
        state.apply(message: .slot(.dial, 1, Slot(name: "P1", value: 0.2, min: 0, max: 1)))
        state.apply(message: .slot(.dial, 2, Slot(name: "Parks", value: 0.3, min: 0, max: 1)))
        state.apply(message: .commit(3))

        XCTAssertEqual(state.dialSlots.count, 3)
        XCTAssertEqual(state.dialSlots[2]?.name, "Parks")
        XCTAssertEqual(state.hudCells.count, 2)
        XCTAssertEqual(state.hudCells[1].section, 1)
        XCTAssertEqual(state.hudCells[1].gridCol, 0)
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

    // MARK: - isVisible

    func test_isVisible_requires_committed_content_and_not_dismissed() async {
        let state = makeState()
        XCTAssertFalse(state.isVisible)  // nothing committed yet
        state.apply(message: .device("Dev"))
        state.apply(message: .commit(0))
        XCTAssertTrue(state.isVisible)
        state.apply(message: .hide)
        XCTAssertFalse(state.isVisible)
    }
}
