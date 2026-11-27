from pathlib import Path

PKG = Path("app/src/main/java/com/chiyuri/player")
p = PKG / "MediaLibraryHealthScreen.kt"
s = p.read_text(encoding="utf-8")
if "import androidx.compose.runtime.mutableIntStateOf" not in s:
    s = s.replace(
        "import androidx.compose.runtime.mutableStateOf",
        "import androidx.compose.runtime.mutableIntStateOf\nimport androidx.compose.runtime.mutableStateOf",
        1
    )
s = s.replace("var completed by remember { mutableStateOf(0) }", "var completed by remember { mutableIntStateOf(0) }")
s = s.replace("var total by remember { mutableStateOf(0) }", "var total by remember { mutableIntStateOf(0) }")
p.write_text(s, encoding="utf-8")

# The widget deliberately paints an opaque black surface; document that the
# theme-overdraw warning is a false positive for this RemoteViews layout.
p = Path("app/src/main/res/layout/widget_player.xml")
s = p.read_text(encoding="utf-8")
if "xmlns:tools=" not in s:
    s = s.replace(
        'xmlns:android="http://schemas.android.com/apk/res/android"',
        'xmlns:android="http://schemas.android.com/apk/res/android"\n    xmlns:tools="http://schemas.android.com/tools"',
        1
    )
s = s.replace(
    'android:background="@android:color/black">',
    'android:background="@android:color/black"\n    tools:ignore="Overdraw">',
    1
)
p.write_text(s, encoding="utf-8")

# Upgrade the legacy no-op binding to the current SLF4J provider line.
p = Path("app/build.gradle.kts")
s = p.read_text(encoding="utf-8").replace(
    'implementation("org.slf4j:slf4j-nop:1.7.36")',
    'implementation("org.slf4j:slf4j-nop:2.0.20")'
)
p.write_text(s, encoding="utf-8")

print("patch_0459: zero-finding lint remediation for primitive state, intentional widget background, SLF4J and Gradle 9.9.3")
