from pathlib import Path
import re

BASE = Path("app/src/main/java/com/chiyuri/player")
mini = BASE / "LyricsMiniPanel.kt"
s = mini.read_text(encoding="utf-8")
old = "embeddedResult ?: LyricsRepository.search(artist, title, durationMs)"
if s.count(old) != 1:
    raise SystemExit("Expected automatic lyrics network search anchor not found exactly once")
s = s.replace(old, "embeddedResult")
s = s.replace("Ищу текст и загружаю сохранённую версию…", "Загружаю текст из файла и сохранённых данных…")
if "LyricsRepository.search(" in s:
    raise SystemExit("Automatic internet lyrics search remains in mini-player")
mini.write_text(s, encoding="utf-8")

updates = BASE / "AppUpdates.kt"
u = updates.read_text(encoding="utf-8")
pattern = re.compile(
    r"(?m)^(?P<i>[ \t]*)androidx\.compose\.material3\.Icon\(\n"
    r"(?P=i)    androidx\.compose\.material\.icons\.Icons\.Default\.SystemUpdate,\n"
    r"(?P=i)    null,\n"
    r"(?P=i)    tint = MaterialTheme\.colorScheme\.primary,\n"
    r"(?P=i)    modifier = Modifier\.size\(42\.dp\)\n"
    r"(?P=i)\)"
)
def header(match):
    i = match.group("i")
    return "\n".join([
        i + "androidx.compose.foundation.layout.Box(",
        i + "    modifier = Modifier.fillMaxWidth().height(190.dp),",
        i + "    contentAlignment = androidx.compose.ui.Alignment.Center",
        i + ") {",
        i + "    androidx.compose.foundation.Image(",
        i + "        painter = androidx.compose.ui.res.painterResource(R.drawable.chiyuri_emblem),",
        i + "        contentDescription = null,",
        i + "        modifier = Modifier.fillMaxWidth().height(190.dp),",
        i + "        contentScale = androidx.compose.ui.layout.ContentScale.Fit,",
        i + "        alpha = 0.16f",
        i + "    )",
        i + "    if (checking || downloading) {",
        i + "        BloodLoader(",
        i + "            progress = if (downloading) progress / 100f else null,",
        i + "            modifier = Modifier.fillMaxWidth().height(190.dp)",
        i + "        )",
        i + "    }",
        i + "}"
    ])
u, count = pattern.subn(header, u, count=1)
if count != 1:
    raise SystemExit("Update-center SystemUpdate icon anchor not found exactly once")

old_version = '"Установлена версия " + AppUpdates.CURRENT_VERSION,'
new_version = '"Установлена версия " + AppUpdates.CURRENT_VERSION + " - " + AppUpdates.CURRENT_VERSION_CODE,'
if u.count(old_version) != 1:
    raise SystemExit("Update-center version label anchor not found exactly once")
u = u.replace(old_version, new_version)
if "R.drawable.chiyuri_emblem" not in u or "ContentScale.Fit" not in u or "CURRENT_VERSION_CODE" not in u:
    raise SystemExit("Update-center artwork/version verification failed")
updates.write_text(u, encoding="utf-8")

loader = BASE / "BloodLoadingIndicator.kt"
b = loader.read_text(encoding="utf-8")
replacements = {
    "(38f + depth * 170f)": "(18f + depth * 190f)",
    "(1f + depth * 24f + shine * 70f)": "(0f + depth * 7f + shine * 24f)",
    "(9f + depth * 39f + shine * 32f)": "(2f + depth * 13f + shine * 18f)",
    "0xFFFFA0AD.toInt()": "0xFFFF263F.toInt()",
    "0xFFB20B2C.toInt()": "0xFF9E001B.toInt()",
    "0xFF43000D.toInt()": "0xFF240008.toInt()",
    "0x99FFD1D8.toInt()": "0x99FF4054.toInt()",
    "0x66FF899A": "0x66FF1E36",
}
for old, new in replacements.items():
    if b.count(old) != 1:
        raise SystemExit(f"Blood texture color anchor mismatch: {old!r}, count={b.count(old)}")
    b = b.replace(old, new)
loader.write_text(b, encoding="utf-8")

gradle = Path("app/build.gradle.kts")
g = gradle.read_text(encoding="utf-8")
if g.count('orElse("335")') != 1:
    raise SystemExit("Expected versionCode fallback 335 not found exactly once")
g = g.replace('orElse("335")', 'orElse("336")')
gradle.write_text(g, encoding="utf-8")

print("v0.5.0 changes applied: centered fit emblem in update center, dark scarlet blood texture, no mini-player internet lyrics search, versionName/versionCode display.")
