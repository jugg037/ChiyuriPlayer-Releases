from pathlib import Path

wrapper = Path("gradle/wrapper/gradle-wrapper.properties")
if not wrapper.exists():
    raise SystemExit("Gradle wrapper properties not found")
w = wrapper.read_text(encoding="utf-8")
old_url = "gradle-9.9.2-bin.zip"
new_url = "gradle-9.9.3-bin.zip"
if old_url in w:
    w = w.replace(old_url, new_url, 1)
elif new_url not in w:
    raise SystemExit("Unexpected Gradle distribution version; refusing blind upgrade")
wrapper.write_text(w, encoding="utf-8")

gradle = Path("app/build.gradle.kts")
if not gradle.exists():
    raise SystemExit("app/build.gradle.kts not found")
g = gradle.read_text(encoding="utf-8")
old_dep = 'implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.11.0")'
new_dep = 'implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.11.1")'
if old_dep in g:
    g = g.replace(old_dep, new_dep, 1)
elif new_dep not in g:
    raise SystemExit("Unexpected lifecycle-runtime-ktx version; refusing blind upgrade")
gradle.write_text(g, encoding="utf-8")

if new_url not in w or new_dep not in g:
    raise SystemExit("Dependency update verification failed")
print("PATCH_0432_OK: Gradle 9.9.3 and lifecycle-runtime-ktx 2.11.1")
