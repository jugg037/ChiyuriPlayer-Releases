from pathlib import Path
import re

ROOT = Path("app/src/main/java/com/chiyuri/player")
main_path = ROOT / "MainActivity.kt"
main = main_path.read_text(encoding="utf-8")

# Requested alpha values are opacity: collapsed 70%, expanded 0%, app surfaces 5%.
alpha_changes = [
    ("if (expanded) 0.05f else 0.50f", "if (expanded) 0.0f else 0.70f"),
    ("if (expanded) 0.05f else 0.5f", "if (expanded) 0.0f else 0.70f"),
    ("surface.copy(alpha = 0.05f)", "surface.copy(alpha = 0.05f)"),
]
for old, new in alpha_changes:
    main = main.replace(old, new)

if "if (expanded) 0.0f else 0.70f" not in main:
    raise SystemExit("Could not safely locate mini-player alpha expression in MainActivity.kt")

# Remove the window-level drawable: Android stretches window backgrounds to the
# entire window. The Compose backdrop owns image sizing and uses aspect-preserving scale.
main = main.replace(
    "        window.setBackgroundDrawableResource(R.drawable.chiyuri_background)\n", ""
)
main_path.write_text(main, encoding="utf-8")

backdrop_path = ROOT / "TrackArtworkBackdrop.kt"
backdrop = backdrop_path.read_text(encoding="utf-8")
backdrop = backdrop.replace(".blur(2.dp)", ".blur(1.dp)")
# Artwork must be opaque and occupy the backdrop slot rather than being a translucent overlay.
backdrop = backdrop.replace(".blur(1.dp).alpha(0.38f)", ".blur(1.dp).alpha(1f)")
backdrop = backdrop.replace(".blur(1.dp).alpha(0.42f)", ".blur(1.dp).alpha(1f)")
# Avoid stretched bitmap rendering; use aspect-preserving crop for full-screen background.
backdrop = backdrop.replace("contentScale = ContentScale.FillBounds", "contentScale = ContentScale.Crop")
backdrop = backdrop.replace("contentScale = androidx.compose.ui.layout.ContentScale.FillBounds",
                              "contentScale = androidx.compose.ui.layout.ContentScale.Crop")
backdrop_path.write_text(backdrop, encoding="utf-8")

# Give visualizer bars a continuous rainbow spectrum. Find the visualizer source
# by semantic filename/content and apply a horizontal gradient to bar drawing.
candidates = list(ROOT.glob("*Visualizer*.kt")) + list(ROOT.glob("*visualizer*.kt"))
changed = []
for path in candidates:
    src = path.read_text(encoding="utf-8")
    if "Canvas" not in src and "drawRect" not in src and "drawLine" not in src:
        continue
    if "Brush.horizontalGradient" in src and "Color.Red" in src:
        changed.append(path)
        continue
    # Add a reusable spectrum brush next to the first composable declaration.
    if "private val ChiyuriSpectrum" not in src:
        imports = "import androidx.compose.ui.graphics.Brush\n"
        if imports.strip() not in src:
            first_import = src.find("import ")
            if first_import >= 0:
                src = src[:first_import] + imports + src[first_import:]
        declaration = """private val ChiyuriSpectrum = Brush.horizontalGradient(
    colors = listOf(
        androidx.compose.ui.graphics.Color(0xFFFF1744),
        androidx.compose.ui.graphics.Color(0xFFFF9100),
        androidx.compose.ui.graphics.Color(0xFFFFEB3B),
        androidx.compose.ui.graphics.Color(0xFF00E676),
        androidx.compose.ui.graphics.Color(0xFF00B0FF),
        androidx.compose.ui.graphics.Color(0xFF651FFF),
        androidx.compose.ui.graphics.Color(0xFFE040FB)
    )
)

"""
        pos = src.find("@Composable")
        if pos < 0:
            continue
        src = src[:pos] + declaration + src[pos:]
    # Replace uniform primary tint used by visualizer drawing with rainbow gradient where supported.
    src = src.replace("color = MaterialTheme.colorScheme.primary", "brush = ChiyuriSpectrum")
    src = src.replace("color = MaterialTheme.colorScheme.primary.copy(alpha = 0.9f)", "brush = ChiyuriSpectrum")
    path.write_text(src, encoding="utf-8")
    changed.append(path)

if not candidates:
    raise SystemExit("Visualizer source file was not found; refusing to claim spectrum colors were applied")

assert "if (expanded) 0.0f else 0.70f" in main_path.read_text(encoding="utf-8")
assert ".blur(1.dp)" in backdrop_path.read_text(encoding="utf-8")
assert "window.setBackgroundDrawableResource(R.drawable.chiyuri_background)" not in main_path.read_text(encoding="utf-8")
print("0.4.16 requested opacity and 1.dp blur applied; removed stretched window background. Visualizer files found: " + ", ".join(p.name for p in changed))
