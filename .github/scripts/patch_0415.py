from pathlib import Path
import base64

base = Path("app/src/main/java/com/chiyuri/player")
main = base / "MainActivity.kt"
s = main.read_text(encoding="utf-8")

# Correct alpha values: opacity, not transparency.
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
# Ensure all top-level surfaces that were set to 90% in 0.4.14 are now 5%.
s = s.replace("NavigationBar(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.90f))",
              "NavigationBar(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.05f))")
if "if (expanded) 0.05f else 0.50f" not in s:
    raise SystemExit("Mini-player alpha marker not found after 0.4.14 patch")
if "adaptiveBackground.copy(alpha = 0.05f)" not in s or "adaptiveSurface.copy(alpha = 0.05f)" not in s:
    raise SystemExit("Dynamic background/surface alpha markers not found")
main.write_text(s, encoding="utf-8")

# Install the supplied permanent background as an Android window background.
encoded = Path(".github/assets/chiyuri_background.webp.b64")
if encoded.exists():
    image = base64.b64decode(encoded.read_text(encoding="ascii").strip(), validate=True)
    if len(image) < 1000:
        raise SystemExit("Background image payload is unexpectedly small")
    drawable = Path("app/src/main/res/drawable-nodpi")
    drawable.mkdir(parents=True, exist_ok=True)
    (drawable / "chiyuri_background.webp").write_bytes(image)
    xml_dir = Path("app/src/main/res/drawable")
    xml_dir.mkdir(parents=True, exist_ok=True)
    (xml_dir / "chiyuri_background.xml").write_text(
        '<bitmap xmlns:android="http://schemas.android.com/apk/res/android" '
        'android:src="@drawable/chiyuri_background" android:gravity="fill" />\\n',
        encoding="utf-8"
    )
    marker = "super.onCreate(savedInstanceState)"
    if marker not in s:
        raise SystemExit("MainActivity onCreate insertion point not found")
    if "window.setBackgroundDrawableResource(R.drawable.chiyuri_background)" not in s:
        s = s.replace(marker, marker + "\\n        window.setBackgroundDrawableResource(R.drawable.chiyuri_background)", 1)
        main.write_text(s, encoding="utf-8")
else:
    raise SystemExit("Missing supplied background image payload .github/assets/chiyuri_background.webp.b64")

assert "if (expanded) 0.05f else 0.50f" in s
assert "surface.copy(alpha = 0.05f)" in s
assert "window.setBackgroundDrawableResource(R.drawable.chiyuri_background)" in s
assert (Path("app/src/main/res/drawable-nodpi/chiyuri_background.webp")).is_file()
assert ".blur(2.dp)" in (base / "TrackArtworkBackdrop.kt").read_text(encoding="utf-8")
print("0.4.15 verified: mini-player opacity 50% collapsed / 5% expanded; main surfaces 5%; supplied image installed as permanent window background; artwork blur 2.dp.")
