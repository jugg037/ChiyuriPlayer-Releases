from pathlib import Path
tests=Path("app/src/test/java/com/chiyuri/player")
for filename in ("Mp3Id3TagWriterTest.kt","FlacAndMp4MetadataWriterTest.kt"):
 f=tests/filename; s=f.read_text(encoding="utf-8")
 if "createTempDir(" not in s: raise SystemExit(f"patch_0469: expected deprecated temp directory use in {filename}")
 s=s.replace("createTempDir(prefix = ", "Files.createTempDirectory(", )
 for prefix in ("id3", "flac", "mp4"):
  token=f'Files.createTempDirectory("chiyuri-{prefix}-")'
  s=s.replace(token, token + ".toFile()")
 if "import java.nio.file.Files" not in s:
  marker="import java.io.File\n"
  if marker not in s: raise SystemExit(f"patch_0469: java.io.File import missing in {filename}")
  s=s.replace(marker,marker+"import java.nio.file.Files\n",1)
 if "createTempDir(" in s: raise SystemExit(f"patch_0469: deprecated temp directory API remains in {filename}")
 f.write_text(s,encoding="utf-8")
f=Path("app/src/main/java/com/chiyuri/player/AudioEffectsController.kt"); s=f.read_text(encoding="utf-8")
anchor="    private fun attachToSession(audioSessionId: Int) {"
if s.count(anchor)!=1: raise SystemExit("patch_0469: virtualizer compatibility method anchor mismatch")
s=s.replace(anchor,"    @Suppress(\\"DEPRECATION\\") // Legacy session effect remains the supported best-effort virtualizer control.\\n"+anchor,1)
f.write_text(s,encoding="utf-8")
print("patch_0469: replaced deprecated createTempDir() test fixtures and isolated the legacy Android Virtualizer deprecation")
