from pathlib import Path
import re

base = Path("app/src/main/java/com/chiyuri/player")
terms = re.compile(r"PlayerView|AndroidView|ExoPlayer|StyledPlayerView|AspectRatioFrameLayout|fullscreen|FullScreen|requestedOrientation|setRequestedOrientation|VideoScreen|VideoPlayer|isVideo|videoUri", re.I)
files = sorted(base.rglob("*.kt"))
hits = 0
print("===== VIDEO / ORIENTATION SOURCE AUDIT =====")
for path in files:
    lines = path.read_text(encoding="utf-8").splitlines()
    indices = [i for i, line in enumerate(lines) if terms.search(line)]
    if not indices:
        continue
    print(f"\n### {path} ({len(indices)} matches)")
    shown = set()
    for i in indices:
        lo, hi = max(0, i-5), min(len(lines), i+8)
        if any(k in shown for k in range(lo, hi)):
            continue
        for k in range(lo, hi):
            shown.add(k)
            print(f"{k+1:5}: {lines[k]}")
        print("-----")
        hits += 1
        if hits >= 80:
            break
    if hits >= 80:
        break
manifest = Path("app/src/main/AndroidManifest.xml")
print("\n===== ACTIVITY MANIFEST =====")
for i, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
    if "activity" in line.lower() or "orientation" in line.lower() or "configChanges" in line:
        print(f"{i:5}: {line}")
print(f"\nAUDIT_COMPLETE: {hits} context blocks from {len(files)} Kotlin files.")
