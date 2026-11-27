from pathlib import Path

def replace_once(path: Path, old: str, new: str, label: str):
    source = path.read_text(encoding="utf-8")
    if old not in source:
        raise SystemExit(f"patch_0456: missing {label}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

PKG = Path("app/src/main/java/com/chiyuri/player")

# AndroidX Lint requires its Java-visible opt-in marker in addition to Kotlin's opt-in.
p = PKG / "SmbDataSource.kt"
s = p.read_text(encoding="utf-8")
marker = "@OptIn(androidx.media3.common.util.UnstableApi::class)"
s = s.replace(
    marker,
    "@androidx.annotation.OptIn(markerClass = [androidx.media3.common.util.UnstableApi::class])\n" + marker
)
p.write_text(s, encoding="utf-8")

p = PKG / "PlaybackService.kt"
s = p.read_text(encoding="utf-8")
if "import androidx.media3.session.SessionError" not in s:
    s = s.replace("import androidx.media3.session.LibraryResult", "import androidx.media3.session.LibraryResult\nimport androidx.media3.session.SessionError", 1)
s = s.replace("LibraryResult.RESULT_ERROR_BAD_VALUE", "SessionError.ERROR_BAD_VALUE")
p.write_text(s, encoding="utf-8")

p = PKG / "PartyModeScreen.kt"
s = p.read_text(encoding="utf-8")
if "import androidx.compose.runtime.mutableIntStateOf" not in s:
    s = s.replace("import androidx.compose.runtime.mutableStateOf", "import androidx.compose.runtime.mutableIntStateOf\nimport androidx.compose.runtime.mutableStateOf", 1)
s = s.replace("var refreshToken by remember { mutableStateOf(0) }", "var refreshToken by remember { mutableIntStateOf(0) }")
p.write_text(s, encoding="utf-8")

p = PKG / "LibraryBackupManager.kt"
s = p.read_text(encoding="utf-8")
s = s.replace("import android.net.Uri\n", "")
if "import androidx.core.net.toUri" not in s:
    s = s.replace("import androidx.core.content.edit", "import androidx.core.content.edit\nimport androidx.core.net.toUri", 1)
s = s.replace("Uri.parse(rawUri)", "rawUri.toUri()")
p.write_text(s, encoding="utf-8")

p = PKG / "MainActivity.kt"
replace_once(
    p,
    '''                        android.widget.Toast.makeText(context, message, android.widget.Toast.LENGTH_SHORT).show()
                        }
                        completedMode != 0''',
    '''                        android.widget.Toast.makeText(context, message, android.widget.Toast.LENGTH_SHORT).show()
                        }
                        if (event.actionMasked == MotionEvent.ACTION_UP && completedMode == 0) view.performClick()
                        completedMode != 0''',
    "video gesture accessibility click"
)

# OkHttp 5 is the maintained release detected by dependency lint; API usage here is compatible.
gradle = Path("app/build.gradle.kts")
gs = gradle.read_text(encoding="utf-8").replace(
    'implementation("com.squareup.okhttp3:okhttp:4.12.0")',
    'implementation("com.squareup.okhttp3:okhttp:5.5.1")'
)
gradle.write_text(gs, encoding="utf-8")

print("patch_0456: fixed AndroidX Media3 lint opt-ins, SessionError code, Compose primitive state, KTX URI and video accessibility; updated OkHttp")
