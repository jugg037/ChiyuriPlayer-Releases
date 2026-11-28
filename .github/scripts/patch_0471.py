from pathlib import Path
root=Path(".")
f=root/"build.gradle.kts"; s=f.read_text(encoding="utf-8")
for old,new,label in [
 ('id("com.android.application") version "9.1.1" apply false','id("com.android.application") version "9.5.0" apply false',"Android Gradle Plugin"),
 ('id("org.jetbrains.kotlin.plugin.compose") version "2.2.10" apply false','id("org.jetbrains.kotlin.plugin.compose") version "2.4.10" apply false',"Kotlin Compose plugin")
]:
 if s.count(old)!=1: raise SystemExit(f"patch_0471: {label} version anchor mismatch")
 s=s.replace(old,new,1)
f.write_text(s,encoding="utf-8")
w=root/"gradle/wrapper/gradle-wrapper.properties"; ws=w.read_text(encoding="utf-8")
if "gradle-9.9.3-bin.zip" not in ws:
 old="distributionUrl=https\\://services.gradle.org/distributions/gradle-9.9.0-bin.zip"
 new="distributionUrl=https\\://services.gradle.org/distributions/gradle-9.9.3-bin.zip"
 if ws.count(old)!=1: raise SystemExit("patch_0471: Gradle wrapper version anchor mismatch")
 w.write_text(ws.replace(old,new,1),encoding="utf-8")
else:
 print("patch_0471: Gradle wrapper already at 9.9.3")
print("patch_0471: upgraded AGP to 9.5.0, Kotlin Compose plugin to 2.4.10 and wrapper to Gradle 9.9.3 to remove upstream Gradle 9 deprecations")
