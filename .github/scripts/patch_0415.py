from pathlib import Path

base = Path("app/src/main/java/com/chiyuri/player")
main = base / "MainActivity.kt"
s = main.read_text(encoding="utf-8")

# Correct alpha values: alpha is opacity (not transparency).
pairs = [
    ("if (expanded) 1f else 0.25f", "if (expanded) 0.05f else 0.50f"),
    ("if (expanded) 0.9f else 1f", "if (expanded) 0.05f else 0.50f"),
    ("surface.copy(alpha = 0.90f)", "surface.copy(alpha = 0.05f)"),
    ("adaptiveBackground.copy(alpha = 0.90f)", "adaptiveBackground.copy(alpha = 0.05f)"),
    ("adaptiveSurface.copy(alpha = 0.90f)", "adaptiveSurface.copy(alpha = 0.05f)"),
]
for old, new in pairs:
    if old in s:
        s = s.replace(old, new)

s = s.replace(
    "NavigationBar(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.90f))",
    "NavigationBar(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.05f))"
)
if "if (expanded) 0.05f else 0.50f" not in s:
    raise SystemExit("Mini-player alpha marker not found")
if "adaptiveBackground.copy(alpha = 0.05f)" not in s or "adaptiveSurface.copy(alpha = 0.05f)" not in s:
    raise SystemExit("Dynamic background/surface alpha markers not found")

# Use the actual optimized WebP binary committed beside this script.
image_source = Path(".github/assets/chiyuri_background.webp")
if not image_source.is_file() or image_source.stat().st_size < 1000:
    raise SystemExit("Missing or invalid .github/assets/chiyuri_background.webp")
drawable = Path("app/src/main/res/drawable-nodpi")
drawable.mkdir(parents=True, exist_ok=True)
image_target = drawable / "chiyuri_background.webp"
image_target.write_bytes(image_source.read_bytes())

# Install it as the window background. Track artwork is rendered above it
# when present; when artwork is absent, this persistent image remains visible.
xml_dir = Path("app/src/main/res/drawable")
xml_dir.mkdir(parents=True, exist_ok=True)
(xml_dir / "chiyuri_background.xml").write_text(
    '<bitmap xmlns:android="http://schemas.android.com/apk/res/android" '
    'android:src="@drawable/chiyuri_background" android:gravity="fill" />\n',
    encoding="utf-8"
)
marker = "super.onCreate(savedInstanceState)"
if marker not in s:
    raise SystemExit("MainActivity onCreate insertion point not found")
window_line = "window.setBackgroundDrawableResource(R.drawable.chiyuri_background)"
if window_line not in s:
    s = s.replace(marker, marker + "\n        " + window_line, 1)
main.write_text(s, encoding="utf-8")

assert "if (expanded) 0.05f else 0.50f" in s
assert "surface.copy(alpha = 0.05f)" in s
assert window_line in s
assert image_target.is_file() and image_target.stat().st_size > 1000
assert ".blur(2.dp)" in (base / "TrackArtworkBackdrop.kt").read_text(encoding="utf-8")
print("0.4.15 verified: collapsed mini-player opacity 50%, expanded mini-player 5%, main surfaces 5%, embedded user background image, artwork blur 2.dp.")
