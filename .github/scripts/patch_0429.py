from pathlib import Path
import re

# Android should follow the user's device orientation naturally; do not lock it.
manifest = Path("app/src/main/AndroidManifest.xml")
s = manifest.read_text(encoding="utf-8")
s2, count = re.subn(r'\s+android:screenOrientation="fullUser"', "", s, count=1)
if count != 1:
    raise SystemExit(f"Expected exactly one fullUser orientation attribute, found {count}")
manifest.write_text(s2, encoding="utf-8")

# Use the AndroidX KTX SharedPreferences editor extension.
prefs = Path("app/src/main/java/com/chiyuri/player/CustomEqualizerPresets.kt")
s = prefs.read_text(encoding="utf-8")
if "import androidx.core.content.edit" not in s:
    s = s.replace("import android.content.Context\n", "import android.content.Context\nimport androidx.core.content.edit\n", 1)
old = 'context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().putString(KEY,array.toString()).apply()'
new = 'context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit { putString(KEY, array.toString()) }'
if s.count(old) != 1:
    raise SystemExit("Custom preset preferences KTX migration anchor mismatch")
prefs.write_text(s.replace(old, new, 1), encoding="utf-8")

# Align wrapper and CI Gradle with the current stable patch release reported by lint.
wrapper = Path("gradle/wrapper/gradle-wrapper.properties")
s = wrapper.read_text(encoding="utf-8")
s2, count = re.subn(r"gradle-9\.9\.0-(bin|all)\.zip", r"gradle-9.9.1-\1.zip", s)
if count != 1:
    raise SystemExit(f"Expected one Gradle 9.9.0 wrapper URL, found {count}")
wrapper.write_text(s2, encoding="utf-8")

workflow = Path(".github/workflows/android.yml")
s = workflow.read_text(encoding="utf-8")
s2, count = re.subn(r'gradle-version: "9\.9\.0"', 'gradle-version: "9.9.1"', s)
if count != 1:
    raise SystemExit(f"Expected one Gradle setup version 9.9.0, found {count}")
workflow.write_text(s2, encoding="utf-8")
print("PATCH_0429_OK: zero-finding lint remediations (KTX, orientation, Gradle 9.9.1).")
