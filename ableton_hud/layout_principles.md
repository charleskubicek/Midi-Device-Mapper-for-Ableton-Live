# Layout Principles — AbletonHUD

## The fundamental tension

When you mix `scaleEffect` (a visual-only GPU transform) with `NSHostingController` sizing, two mechanisms fight:

| Mechanism | What it does |
|---|---|
| `scaleEffect` | GPU transform — **never** changes the view's reported `fittingSize` |
| `NSHostingController.sizingOptions = .preferredContentSize` | Continuously enforces the view's `fittingSize` as the panel size |

Every attempt to call `panel.setContentSize(scaledSize)` while `sizingOptions` was set to `.preferredContentSize` silently failed — the hosting controller immediately reverted to the unscaled `fittingSize`.

## Rule: never use `sizingOptions = .preferredContentSize` with `scaleEffect`

Default sizing behavior (no `sizingOptions`) sizes once at creation and stays out of the way. Manual `setContentSize` calls then stick.

## Rule: the view must report its own scaled size

Instead of making the manager multiply sizes, have the SwiftUI view apply `.frame(width: baseSize × zoom, height: baseSize × zoom)` on the outer container. This way `fittingSize` reflects the scaled dimensions natively.

## Rule: capture the 1.0× base size with PreferenceKey, not @State

Use `GeometryReader` + `PreferenceKey` + `.onPreferenceChange` to communicate the unscaled content size back to an `ObservableObject` (`HUDChrome.baseSize`). This makes the size available to both SwiftUI (for the `.frame`) and AppKit (for manager-driven `setContentSize`).

```
VStack.content
  → .fixedSize()              // hug content, report real intrinsic size
  → .background(GeometryReader → PreferenceKey)  // capture 1.0× size
  → .scaleEffect(zoom)        // visual-only GPU scale
ZStack
  → .frame(baseSize × zoom)   // makes fittingSize report scaled size
```

## Rule: use autoresizing mask for tracking overlays, not Auto Layout

Adding a constraint-based `NSView` subview to an `NSPanel`'s `contentView` conflicts with the hosting controller's view management. Use `autoresizingMask = [.width, .height]` and `addSubview(_, positioned: .above)` instead.

## Rule: tracking area owner must be NSResponder or NSView

`NSTrackingArea` sends Objective-C messages (`mouseEntered:`, `mouseExited:`) to its owner. A plain Swift class (even `@MainActor`) that doesn't inherit from `NSObject`/`NSResponder` will crash with `doesNotRecognizeSelector:`. Use a dedicated `NSView` subclass as the tracking area owner.

## Sizing data flow

```
┌─────────────┐    PreferenceKey     ┌──────────────┐
│  HUDView    │ ──── baseSize ─────→ │  HUDChrome   │
│  Geometry   │                      │  .baseSize   │
│  Reader     │                      │  .zoom       │
└─────────────┘                      └──────┬───────┘
       │                                    │
       │ .frame(baseSize × zoom)            │ Combine $baseSize, $zoom
       ▼                                    ▼
  fittingSize                       HUDOverlayManager
  (scaled) ─────────────────────────→ resizePanel()
                                       setContentSize(baseSize × zoom)
```

## Verification checklist

After any layout change, verify:

1. Panel sizes correctly at 100% zoom (matches content, no clipping, no excess whitespace)
2. Zooming to 110/120/130% grows both the visual content AND the panel window
3. Returning to 100% restores exact original size
4. Panel remains draggable (no subview stealing mouse events)
5. Hover over panel shows config bar and pauses auto-dismiss
6. Esc still dismisses immediately
