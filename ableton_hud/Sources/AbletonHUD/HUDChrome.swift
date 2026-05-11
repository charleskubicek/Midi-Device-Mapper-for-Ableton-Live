import SwiftUI

@MainActor
final class HUDChrome: ObservableObject {
    @Published var isMouseOver = false
    @Published var zoom: Double = 1.0 {
        didSet {
            UserDefaults.standard.set(zoom, forKey: kZoomKey)
        }
    }
    @Published var baseSize: CGSize = CGSize(width: 960, height: 280)

    private let kZoomKey = "hudZoomLevel"

    init() {
        let saved = UserDefaults.standard.double(forKey: kZoomKey)
        let allowed: Set<Double> = [1.0, 1.125, 1.25, 1.375, 1.5]
        zoom = allowed.contains(saved) ? saved : 1.0
    }
}
