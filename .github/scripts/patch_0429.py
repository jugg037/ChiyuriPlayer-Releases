from pathlib import Path
import re

manifest = Path("app/src/main/AndroidManifest.xml")
text = manifest.read_text(encoding="utf-8")
text, n = re.subn(r'\s+android:screenOrientation="fullUser"', "", text, count=1)
if n != 1 and 'screenOrientation=' in text:
    raise SystemExit("Could not safely remove fullUser orientation")
manifest.write_text(text, encoding="utf-8")

prefs = Path("app/src/main/java/com/chiyuri/player/CustomEqualizerPresets.kt")
text = prefs.read_text(encoding="utf-8")
if "import androidx.core.content.edit" not in text:
    text = text.replace("import android.content.Context\n", "import android.content.Context\nimport androidx.core.content.edit\n", 1)
old = 'context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().putString(KEY,array.toString()).apply()'
new = 'context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit { putString(KEY, array.toString()) }'
if old in text:
    text = text.replace(old, new, 1)
elif new not in text:
    raise SystemExit("Custom preset KTX migration anchor mismatch")
prefs.write_text(text, encoding="utf-8")

wrapper = Path("gradle/wrapper/gradle-wrapper.properties")
text = wrapper.read_text(encoding="utf-8")
text, n = re.subn(r"gradle-9\.9\.0-(bin|all)\.zip", r"gradle-9.9.1-\1.zip", text)
if n == 0 and "gradle-9.9.2-" not in text:
    raise SystemExit("Gradle wrapper must be 9.9.0 or 9.9.1")
wrapper.write_text(text, encoding="utf-8")

workflow = Path(".github/workflows/android.yml")
text = workflow.read_text(encoding="utf-8")
if 'gradle-version: "9.9.2"' not in text:
    text, n = re.subn(r'gradle-version: "9\.9\.0"', 'gradle-version: "9.9.1"', text)
    if n != 1 and 'gradle-version: "9.9.2"' not in text:
        raise SystemExit("Gradle setup must be 9.9.0 or 9.9.1")
    workflow.write_text(text, encoding="utf-8")
print("PATCH_0429_OK: KTX preferences, adaptive orientation, Gradle 9.9.2.")
