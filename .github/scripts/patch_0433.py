from pathlib import Path

gradle = Path("app/build.gradle.kts").read_text(encoding="utf-8")
wrapper = Path("gradle/wrapper/gradle-wrapper.properties").read_text(encoding="utf-8")
workflow = Path(".github/workflows/android.yml").read_text(encoding="utf-8")

checks = {
    "lifecycle-runtime-ktx 2.11.1": 'lifecycle-runtime-ktx:2.11.1' in gradle,
    "Gradle wrapper 9.9.2": "gradle-9.9.2-bin.zip" in wrapper,
    "CI Gradle 9.9.2": 'gradle-version: "9.9.2"' in workflow,
    "Android 17 audit lifecycle 2.11.1": "lifecycle-runtime-ktx:2.11.1" in workflow,
}
failed = [name for name, passed in checks.items() if not passed]
for name, passed in checks.items():
    print(("PASS: " if passed else "FAIL: ") + name)
if failed:
    raise SystemExit("Dependency/Gradle audit mismatch: " + ", ".join(failed))
print("PATCH_0433_OK: dependency audit and CI Gradle version are aligned.")
