from pathlib import Path

base = Path("app/src/main/java/com/chiyuri/player")
main = base / "MainActivity.kt"
source = main.read_text(encoding="utf-8")

old = 'androidx.compose.ui.res.painterResource(com.chiyuri.player.R.mipmap.ic_launcher)'
new = 'androidx.compose.ui.res.painterResource(com.chiyuri.player.R.drawable.chiyuri_launcher_foreground)'
count = source.count(old)
if count != 1:
    raise SystemExit(f"Expected one Compose adaptive-icon reference, found {count}")
source = source.replace(old, new, 1)
main.write_text(source, encoding="utf-8")

print("PATCH_0427_OK: Compose uses raster foreground resource; app version is set by platform patch.")
