import SwiftUI
import AbletonHUDCore

private struct ContentSizeKey: PreferenceKey {
    static let defaultValue: CGSize = .zero
    static func reduce(value: inout CGSize, nextValue: () -> CGSize) {
        value = nextValue()
    }
}

/// Captures the grid's intrinsic width so the device title can shrink/truncate
/// against it without itself driving the panel width.
private struct GridWidthKey: PreferenceKey {
    static let defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = max(value, nextValue())
    }
}

struct HUDView: View {
    @ObservedObject var state: DeviceState
    @ObservedObject var chrome: HUDChrome

    var body: some View {
        let scale = CGFloat(chrome.zoom)
        // One region rendered from the single committed state. The `lc_parks`
        // compositor merges any secondary controller's slots into this one
        // stream; each cell carries a `section` so the view lays each controller
        // out as its own sub-grid (secondary as a separate block to the right),
        // while the slot indices stay in one flat space.
        let region = RegionSnapshot(from: state)

        ZStack(alignment: .topTrailing) {
            SourceRegionView(region: region, zoom: chrome.zoom)
            .padding(.horizontal, 16 * scale)
            .padding(.vertical, 12 * scale)
            .fixedSize()
            .background(
                RoundedRectangle(cornerRadius: 14 * scale)
                    .fill(Color(red: 0.08, green: 0.08, blue: 0.11))
            )
            .background(
                GeometryReader { geo in
                    Color.clear.preference(key: ContentSizeKey.self, value: geo.size)
                }
            )
            .onPreferenceChange(ContentSizeKey.self) { newSize in
                guard newSize.width > 0, newSize.height > 0 else { return }
                chrome.baseSize = CGSize(width: newSize.width / chrome.zoom,
                                          height: newSize.height / chrome.zoom)
            }

            if chrome.isMouseOver {
                ConfigBar(chrome: chrome)
                    .padding(.trailing, 8 * scale)
                    .padding(.top, 8 * scale)
            }
        }
        .frame(width: max(1, chrome.baseSize.width) * chrome.zoom,
               height: max(1, chrome.baseSize.height) * chrome.zoom)
    }
}

/// Equatable value snapshot of the published HUD state, so the region view
/// re-renders whenever its content changes.
private struct RegionSnapshot: Equatable {
    let deviceName: String
    let dialSlots: [Slot?]
    let buttonSlots: [Slot?]
    let hudCells: [HudCell]
    let isShiftMode: Bool
    let encoderPage: Int
    let pageTotal: Int
    let bankLabel: String
    let dialColors: [Int: String]
    let buttonColors: [Int: String]

    @MainActor
    init(from s: DeviceState) {
        deviceName = s.deviceName
        dialSlots = s.dialSlots
        buttonSlots = s.buttonSlots
        hudCells = s.hudCells
        isShiftMode = s.isShiftMode
        encoderPage = s.encoderPage
        pageTotal = s.pageTotal
        bankLabel = s.bankLabel
        dialColors = s.dialColors
        buttonColors = s.buttonColors
    }
}

/// Renders one sender's header + control grid from an Equatable snapshot.
private struct SourceRegionView: View {
    let region: RegionSnapshot
    let zoom: Double
    @State private var gridWidth: CGFloat = 0

    private var scale: CGFloat { CGFloat(zoom) }

    /// Distinct section ids in ascending order. Each section is an independently
    /// laid-out block (primary = 0, secondary = 1, …), rendered side-by-side.
    private var sections: [Int] {
        Array(Set(region.hudCells.map(\.section))).sorted()
    }

    /// Build a self-contained sub-grid for one section, sized from that section's
    /// OWN row/col extents so its layout is independent of the other sections.
    private func grid(forSection section: Int) -> [[HudCell?]] {
        let cells = region.hudCells.filter { $0.section == section }
        guard !cells.isEmpty else { return [] }
        let maxRow = cells.map(\.gridRow).max()!
        let maxCol = cells.map(\.gridCol).max()!
        var g = Array(repeating: Array(repeating: HudCell?.none, count: maxCol + 1), count: maxRow + 1)
        for cell in cells { g[cell.gridRow][cell.gridCol] = cell }
        return g
    }

    var body: some View {
        VStack(alignment: .center, spacing: 6 * scale) {
            // Header: close (hides this source only), device name, page, bank.
            ZStack {
                HStack(spacing: 6 * scale) {
                    Button {
                        DeviceState.shared.apply(message: .hide)
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 8 * scale, weight: .medium))
                            .foregroundColor(.white.opacity(0.45))
                            .frame(width: 12 * scale, height: 12 * scale)
                            .contentShape(Rectangle())
                    }
                    .buttonStyle(.borderless)

                    Text(region.deviceName.isEmpty ? "—" : region.deviceName)
                        .font(.system(size: 10 * scale, weight: .semibold, design: .rounded))
                        .foregroundColor(.white)
                        .lineLimit(1)
                        .truncationMode(.tail)
                        .minimumScaleFactor(0.5)

                    Spacer(minLength: 4 * scale)

                    if region.pageTotal > 1 {
                        Text("\(region.encoderPage)/\(region.pageTotal)")
                            .font(.system(size: 9 * scale, weight: .medium, design: .rounded))
                            .foregroundColor(.white.opacity(0.5))
                    }
                }

                if !region.bankLabel.isEmpty {
                    Text(region.bankLabel)
                        .font(.system(size: 9 * scale, weight: .regular, design: .rounded))
                        .foregroundColor(.white.opacity(0.6))
                        .lineLimit(1)
                        .truncationMode(.tail)
                        .minimumScaleFactor(0.6)
                }
            }
            .frame(maxWidth: gridWidth > 0 ? gridWidth : nil)
            .padding(.bottom, 4 * scale)

            // Each section is laid out as its own independent sub-grid; sections
            // sit side-by-side with a vertical divider, so the secondary
            // controller reads as a separate unit to the right of the primary.
            HStack(alignment: .top, spacing: 12 * scale) {
                ForEach(Array(sections.enumerated()), id: \.element) { idx, section in
                    if idx > 0 {
                        // Explicit rule (not `Divider()`): the whole region is
                        // wrapped in `.fixedSize()`, under which a Divider has no
                        // intrinsic length and collapses. A flexible Rectangle
                        // fills the height set by the (concrete-height) section
                        // grids beside it. See layout_principles.md.
                        Rectangle()
                            .fill(Color.white.opacity(0.12))
                            .frame(width: 1)
                            .frame(maxHeight: .infinity)
                    }
                    sectionGrid(forSection: section)
                }
            }
            .background(
                GeometryReader { geo in
                    Color.clear.preference(key: GridWidthKey.self, value: geo.size.width)
                }
            )
        }
        .onPreferenceChange(GridWidthKey.self) { gridWidth = $0 }
    }

    @ViewBuilder
    private func sectionGrid(forSection section: Int) -> some View {
        VStack(alignment: .leading, spacing: 10 * scale) {
            ForEach(Array(grid(forSection: section).enumerated()), id: \.offset) { _, row in
                HStack(alignment: .top, spacing: 10 * scale) {
                    ForEach(Array(row.enumerated()), id: \.offset) { _, cell in
                        if let cell = cell {
                            cellView(cell)
                        } else {
                            Color.clear.frame(width: 0)
                        }
                    }
                }
            }
        }
    }

    @ViewBuilder
    private func cellView(_ cell: HudCell) -> some View {
        switch cell.kind {
        case .dial:
            HStack(spacing: 8 * scale) {
                ForEach(0..<cell.count, id: \.self) { i in
                    let idx = cell.startIndex + i
                    let slot: Slot? = (cell.startIndex >= 0 && idx < region.dialSlots.count)
                        ? region.dialSlots[idx] : nil
                    DialSlotView(slot: slot, zoom: zoom, zoneHex: region.dialColors[idx])
                }
            }
        case .button:
            HStack(spacing: 8 * scale) {
                ForEach(0..<cell.count, id: \.self) { i in
                    let idx = cell.startIndex + i
                    let slot: Slot? = (cell.startIndex >= 0 && idx < region.buttonSlots.count)
                        ? region.buttonSlots[idx] : nil
                    ButtonSlotView(slot: slot, zoom: zoom, isShiftMode: region.isShiftMode,
                                   zoneHex: region.buttonColors[idx])
                }
            }
        }
    }
}

// MARK: - Dial (arc edge from 0 to max, cyan segment for current value)

private struct ArcShape: Shape {
    let startAngle: Angle
    let endAngle: Angle

    func path(in rect: CGRect) -> Path {
        let center = CGPoint(x: rect.midX, y: rect.midY)
        let radius = min(rect.width, rect.height) / 2
        var path = Path()
        path.addArc(center: center, radius: radius,
                    startAngle: startAngle, endAngle: endAngle, clockwise: false)
        return path
    }
}

extension Color {
    /// RRGGBB hex -> Color (grid-zone-colour-coding-plan zone tints). Returns
    /// nil on malformed input so callers fall back to the default stroke.
    init?(zoneHex: String) {
        let h = zoneHex.trimmingCharacters(in: .whitespaces)
        guard h.count == 6, let v = UInt32(h, radix: 16) else { return nil }
        self.init(red: Double((v >> 16) & 0xff) / 255,
                  green: Double((v >> 8) & 0xff) / 255,
                  blue: Double(v & 0xff) / 255)
    }
}

private struct DialSlotView: View {
    let slot: Slot?
    let zoom: Double
    /// Zone tint (RRGGBB) for the ring outline; nil = default grey.
    var zoneHex: String? = nil

    private var scale: CGFloat { CGFloat(zoom) }

    /// (full, dull) zone colours for this dial. `full` paints the value arc
    /// (0→current, the primary hue); `dull` is a desaturated, dimmed near-grey
    /// version for the unfilled track. nil when the device isn't zoned, so
    /// non-zoned dials keep the default grey track + cyan value arc.
    private var zoneTint: (full: Color, dull: Color)? {
        guard let hex = zoneHex else { return nil }
        let h = hex.trimmingCharacters(in: .whitespaces)
        guard h.count == 6, let v = UInt32(h, radix: 16) else { return nil }
        let r = Double((v >> 16) & 0xff) / 255
        let g = Double((v >> 8) & 0xff) / 255
        let b = Double(v & 0xff) / 255
        // Pull each channel most of the way to its own luminance (desaturate),
        // then darken — reads as "almost grey with a hint of the hue".
        let lum = 0.299 * r + 0.587 * g + 0.114 * b
        let sat = 0.30, dim = 0.50
        func dull(_ c: Double) -> Double { (c * sat + lum * (1 - sat)) * dim }
        return (Color(red: r, green: g, blue: b),
                Color(red: dull(r), green: dull(g), blue: dull(b)))
    }

    private var fillFraction: Double {
        guard let s = slot, s.max > s.min else { return 0 }
        return Double((s.value - s.min) / (s.max - s.min)).clamped(to: 0...1)
    }

    private let sweep: Double = 5.0 / 6.0
    private let rotation: Double = 120

    var body: some View {
        VStack(spacing: 4 * scale) {
            ZStack {
                ArcShape(startAngle: .zero, endAngle: .degrees(sweep * 360))
                    .stroke(zoneTint?.dull ?? Color.gray.opacity(0.3), lineWidth: 2 * scale)
                    .frame(width: 25 * scale, height: 25 * scale)
                    .rotationEffect(.degrees(rotation))

                if slot != nil {
                    ArcShape(startAngle: .zero, endAngle: .degrees(fillFraction * sweep * 360))
                        .stroke(zoneTint?.full ?? Color.cyan, lineWidth: 2 * scale)
                        .frame(width: 25 * scale, height: 25 * scale)
                        .rotationEffect(.degrees(rotation))
                }
            }

            Text(slot?.name ?? "")
                .font(.system(size: 9 * scale, weight: .light))
                .minimumScaleFactor(0.7)
                .allowsTightening(true)
                .foregroundColor(Color(white: slot != nil ? 0.92 : 0.18))
                .lineLimit(2)
                .multilineTextAlignment(.center)
                .frame(width: 44 * scale, height: 22 * scale, alignment: .top)
        }
    }
}

// MARK: - Button slot

private struct ButtonSlotView: View {
    let slot: Slot?
    let zoom: Double
    let isShiftMode: Bool
    /// Zone tint (RRGGBB) for the border outline; nil = default white. This is
    /// the same hue the physical Grid button LED shows.
    var zoneHex: String? = nil

    private var scale: CGFloat { CGFloat(zoom) }

    private var isActive: Bool {
        guard let s = slot, s.max > s.min else { return false }
        return s.value > (s.min + s.max) / 2
    }

    private var borderColor: Color {
        zoneHex.flatMap { Color(zoneHex: $0) } ?? Color.white.opacity(slot != nil ? 0.35 : 0.25)
    }

    var body: some View {
        VStack(spacing: 4 * scale) {
            RoundedRectangle(cornerRadius: 5 * scale)
                .fill(isActive ? Color.white.opacity(0.35) : Color.clear)
                .overlay(
                    RoundedRectangle(cornerRadius: 5 * scale)
                        .stroke(borderColor, lineWidth: 1.5 * scale)
                )
                .frame(width: 36 * scale, height: 20 * scale)

            if isShiftMode {
                Text(slot?.name ?? "")
                    .font(.system(size: 9 * scale, weight: .light))
                    .minimumScaleFactor(0.7)
                    .allowsTightening(true)
                    .foregroundColor(Color(white: slot != nil ? 0.88 : 0.18))
                    .lineLimit(2)
                    .multilineTextAlignment(.center)
                    .frame(width: 44 * scale, height: 22 * scale, alignment: .top)
            } else {
                Text(slot?.name ?? "")
                    .font(.system(size: 9 * scale, weight: .light).italic())
                    .minimumScaleFactor(0.7)
                    .allowsTightening(true)
                    .foregroundColor(Color(white: slot != nil ? 0.88 : 0.18))
                    .lineLimit(2)
                    .multilineTextAlignment(.center)
                    .frame(width: 44 * scale, height: 22 * scale, alignment: .top)
            }
        }
    }
}

// MARK: - Helpers

private extension Comparable {
    func clamped(to range: ClosedRange<Self>) -> Self {
        min(max(self, range.lowerBound), range.upperBound)
    }
}

// MARK: - ConfigBar

private struct ConfigBar: View {
    @ObservedObject var chrome: HUDChrome

    private let zoomLevels: [Double] = [1.0, 1.125, 1.25, 1.375, 1.5]

    private var currentIndex: Int {
        zoomLevels.firstIndex(of: chrome.zoom) ?? 0
    }

    private var scale: CGFloat { CGFloat(chrome.zoom) }

    var body: some View {
        HStack(spacing: 4 * scale) {
            Button {
                guard currentIndex > 0 else { return }
                chrome.zoom = zoomLevels[currentIndex - 1]
            } label: {
                Text("\u{2212}")
                    .font(.system(size: 10 * scale, weight: .medium, design: .rounded))
                    .frame(width: 18 * scale, height: 18 * scale)
            }
            .buttonStyle(.borderless)
            .disabled(currentIndex == 0)
            .foregroundColor(.white.opacity(currentIndex == 0 ? 0.3 : 0.7))

            Text("\(Int(chrome.zoom * 100))%")
                .font(.system(size: 10 * scale, weight: .medium, design: .rounded))
                .foregroundColor(.white)
                .frame(minWidth: 32 * scale)

            Button {
                guard currentIndex < zoomLevels.count - 1 else { return }
                chrome.zoom = zoomLevels[currentIndex + 1]
            } label: {
                Text("+")
                    .font(.system(size: 10 * scale, weight: .medium, design: .rounded))
                    .frame(width: 18 * scale, height: 18 * scale)
            }
            .buttonStyle(.borderless)
            .disabled(currentIndex == zoomLevels.count - 1)
            .foregroundColor(.white.opacity(currentIndex == zoomLevels.count - 1 ? 0.3 : 0.7))
        }
        .padding(.horizontal, 4 * scale)
        .padding(.vertical, 3 * scale)
        .background(
            RoundedRectangle(cornerRadius: 8 * scale)
                .fill(Color(red: 0.08, green: 0.08, blue: 0.11))
        )
    }
}