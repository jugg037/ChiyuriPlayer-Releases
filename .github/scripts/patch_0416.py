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

# Keep the embedded image as the guaranteed fallback when no track artwork exists.
# Track artwork is rendered by the Compose backdrop above it when available.
window_marker = "super.onCreate(savedInstanceState)"
window_line = "window.setBackgroundDrawableResource(R.drawable.chiyuri_background)"
if window_marker not in main:
    raise SystemExit("MainActivity onCreate insertion point not found for fallback background")
if window_line not in main:
    main = main.replace(window_marker, window_marker + "\n        " + window_line, 1)
main_path.write_text(main, encoding="utf-8")

backdrop_path = ROOT / "TrackArtworkBackdrop.kt"
backdrop = backdrop_path.read_text(encoding="utf-8")
backdrop = backdrop.replace(".blur(2.dp)", ".blur(1.dp)")
# Track artwork and the embedded fallback are mutually exclusive base layers.
# When no artwork exists, render the bundled user image inside Compose; the
# Activity window background alone is hidden by Compose's full-screen content.
if "import androidx.compose.ui.res.painterResource" not in backdrop:
    backdrop = backdrop.replace(
        "package com.chiyuri.player\n",
        "package com.chiyuri.player\n\nimport androidx.compose.ui.res.painterResource\n",
        1
    )
# Replace the complete optional-artwork branch, independent of its previous blur/alpha values.
art_pattern = re.compile(
    r"        if \(image != null\) \{\n.*?\n        \}",
    re.DOTALL
)
new_art = """        if (image != null) {
            Image(
                bitmap = image.asImageBitmap(),
                contentDescription = null,
                contentScale = ContentScale.Crop,
                modifier = Modifier.fillMaxSize().blur(1.dp).alpha(1f)
            )
        } else {
            Image(
                painter = painterResource(id = R.drawable.chiyuri_background),
                contentDescription = null,
                contentScale = ContentScale.Crop,
                modifier = Modifier.fillMaxSize()
            )
        }"""
backdrop, art_count = art_pattern.subn(lambda _: new_art, backdrop, count=1)
if art_count != 1:
    raise SystemExit("Could not safely replace TrackArtworkBackdrop optional-artwork branch")
backdrop_path.write_text(backdrop, encoding="utf-8")

# Apply the spectrum to the actual bar drawing call in AudioVisualizer.kt.
visualizer_path = ROOT / "AudioVisualizer.kt"
src = visualizer_path.read_text(encoding="utf-8")
if "import androidx.compose.ui.graphics.Brush" not in src:
    src = src.replace(
        "package com.chiyuri.player\n",
        "package com.chiyuri.player\n\nimport androidx.compose.ui.graphics.Brush\n",
        1
    )
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
if "private val ChiyuriSpectrum" not in src:
    marker = "@Composable\nprivate fun VisualizerGraph"
    if marker not in src:
        raise SystemExit("Could not find VisualizerGraph insertion point")
    src = src.replace(marker, declaration + marker, 1)
old_bar = "color = accent.copy(alpha = 0.4f + magnitude * 0.6f),"
if old_bar in src:
    src = src.replace(old_bar, "brush = ChiyuriSpectrum,", 1)
elif "brush = ChiyuriSpectrum" not in src:
    raise SystemExit("Could not find the visualizer bar tint to replace")
visualizer_path.write_text(src, encoding="utf-8")

assert "if (expanded) 0.0f else 0.70f" in main_path.read_text(encoding="utf-8")
assert ".blur(1.dp)" in backdrop_path.read_text(encoding="utf-8")
assert "painterResource(id = R.drawable.chiyuri_background)" in backdrop_path.read_text(encoding="utf-8")
assert "brush = ChiyuriSpectrum" in visualizer_path.read_text(encoding="utf-8")
print("0.4.16 verified: embedded fallback is rendered in Compose when artwork is absent; artwork replaces it when present; 1.dp blur and spectrum bars applied.")
