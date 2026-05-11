// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "AbletonHUD",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "AbletonHUD", targets: ["AbletonHUD"]),
    ],
    targets: [
        // Testable core: wire protocol + device state (no AppKit/SwiftUI)
        .target(
            name: "AbletonHUDCore",
            path: "Sources/AbletonHUDCore"
        ),
        // Main executable: overlay UI
        .executableTarget(
            name: "AbletonHUD",
            dependencies: ["AbletonHUDCore"],
            path: "Sources/AbletonHUD",
            exclude: ["../../Info.plist"]
        ),
        // Unit tests for wire protocol and burst logic
        .testTarget(
            name: "WireProtocolTests",
            dependencies: ["AbletonHUDCore"],
            path: "Tests/WireProtocolTests"
        ),
    ]
)
