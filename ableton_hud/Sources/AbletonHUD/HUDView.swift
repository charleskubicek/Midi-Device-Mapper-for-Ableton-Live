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
    @State private var gridWidth: CGFloat = 0

    private var grid: [[HudCell?]] {
        guard !state.hudCells.isEmpty else { return [] }
        let maxRow = state.hudCells.map(\.gridRow).max()!
        let maxCol = state.hudCells.map(\.gridCol).max()!
        var g = Array(repeating: Array(repeating: HudCell?.none, count: maxCol + 1), count: maxRow + 1)
        for cell in state.hudCells { g[cell.gridRow][cell.gridCol] = cell }
        return g
    }

    var body: some View {
        let scale = CGFloat(chrome.zoom)

        ZStack(alignment: .topTrailing) {
            VStack(alignment: .center, spacing: 6 * scale) {
                // Header row: device name (top-left), bank label, page indicator
                // (top-right) all on the same line. Pinned to the grid width
                // below so long device names truncate instead of expanding the
                // panel.
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

                        Text(state.deviceName.isEmpty ? "—" : state.deviceName)
                            .font(.system(size: 10 * scale, weight: .semibold, design: .rounded))
                            .foregroundColor(.white)
                            .lineLimit(1)
                            .truncationMode(.tail)
                            .minimumScaleFactor(0.5)

                        Spacer(minLength: 4 * scale)

                        if state.pageTotal > 1 {
                            Text("\(state.encoderPage)/\(state.pageTotal)")
                                .font(.system(size: 9 * scale, weight: .medium, design: .rounded))
                                .foregroundColor(.white.opacity(0.5))
                        }
                    }

                    if !state.bankLabel.isEmpty {
                        Text(state.bankLabel)
                            .font(.system(size: 9 * scale, weight: .regular, design: .rounded))
                            .foregroundColor(.white.opacity(0.6))
                            .lineLimit(1)
                            .truncationMode(.tail)
                            .minimumScaleFactor(0.6)
                    }
                }
                .frame(maxWidth: gridWidth > 0 ? gridWidth : nil)
                .padding(.bottom, 4 * scale)

                VStack(alignment: .leading, spacing: 10 * scale) {
                    ForEach(Array(grid.enumerated()), id: \.offset) { _, row in
                        HStack(alignment: .top, spacing: 10 * scale) {
                            ForEach(Array(row.enumerated()), id: \.offset) { _, cell in
                                if let cell = cell {
                                    cellView(cell, zoom: chrome.zoom)
                                } else {
                                    Color.clear.frame(width: 0)
                                }
                            }
                        }
                    }
                }
                .background(
                    GeometryReader { geo in
                        Color.clear.preference(key: GridWidthKey.self, value: geo.size.width)
                    }
                )
            }
            .onPreferenceChange(GridWidthKey.self) { gridWidth = $0 }
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

    @ViewBuilder
    private func cellView(_ cell: HudCell, zoom: Double) -> some View {
        let scale = CGFloat(zoom)
        switch cell.kind {
        case .dial:
            HStack(spacing: 8 * scale) {
                ForEach(0..<cell.count, id: \.self) { i in
                    let idx = cell.startIndex + i
                    let slot: Slot? = (cell.startIndex >= 0 && idx < state.dialSlots.count)
                        ? state.dialSlots[idx] : nil
                    DialSlotView(slot: slot, zoom: zoom)
                }
            }
        case .button:
            HStack(spacing: 8 * scale) {
                ForEach(0..<cell.count, id: \.self) { i in
                    let idx = cell.startIndex + i
                    let slot: Slot? = (cell.startIndex >= 0 && idx < state.buttonSlots.count)
                        ? state.buttonSlots[idx] : nil
                    ButtonSlotView(slot: slot, zoom: zoom, isShiftMode: state.isShiftMode)
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

private struct DialSlotView: View {
    let slot: Slot?
    let zoom: Double

    private var scale: CGFloat { CGFloat(zoom) }

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
                    .stroke(Color.gray.opacity(0.3), lineWidth: 2 * scale)
                    .frame(width: 25 * scale, height: 25 * scale)
                    .rotationEffect(.degrees(rotation))

                if slot != nil {
                    ArcShape(startAngle: .zero, endAngle: .degrees(fillFraction * sweep * 360))
                        .stroke(Color.cyan, lineWidth: 2 * scale)
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

    private var scale: CGFloat { CGFloat(zoom) }

    private var isActive: Bool {
        guard let s = slot, s.max > s.min else { return false }
        return s.value > (s.min + s.max) / 2
    }

    var body: some View {
        VStack(spacing: 4 * scale) {
            RoundedRectangle(cornerRadius: 5 * scale)
                .fill(isActive ? Color.white.opacity(0.35) : Color.clear)
                .overlay(
                    RoundedRectangle(cornerRadius: 5 * scale)
                        .stroke(Color.white.opacity(slot != nil ? 0.35 : 0.25), lineWidth: 1.5 * scale)
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