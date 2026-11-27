from pathlib import Path

target = Path("app/src/main/java/com/chiyuri/player/MediaFileInfo.kt")
source = target.read_text(encoding="utf-8")

old = """    var loading by androidx.compose.runtime.remember(uri) { androidx.compose.runtime.mutableStateOf(true) }
    androidx.compose.runtime.LaunchedEffect(uri) {
        loading = true
        info = if (uri == null) null else kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
            readMediaFileInfo(
                context,
                uri,
                item?.mediaMetadata?.title?.toString().orEmpty(),
                player.duration.takeIf { it > 0L } ?: 0L
            )
        }
"""
new = """    var loading by androidx.compose.runtime.remember(uri) { androidx.compose.runtime.mutableStateOf(true) }
    // Media3 MediaController is thread-confined. Read its duration on the UI/application
    // thread before switching to Dispatchers.IO for file and MediaExtractor inspection.
    val durationMs = player.duration.takeIf { it > 0L } ?: 0L
    val fallbackName = item?.mediaMetadata?.title?.toString().orEmpty()
    androidx.compose.runtime.LaunchedEffect(uri, durationMs, fallbackName) {
        loading = true
        info = if (uri == null) null else kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
            readMediaFileInfo(
                context,
                uri,
                fallbackName,
                durationMs
            )
        }
"""
if old not in source:
    raise SystemExit("patch_0461: expected MediaFileInfoDialog coroutine block was not found")
source = source.replace(old, new, 1)
if "player.duration" not in source.split("withContext(kotlinx.coroutines.Dispatchers.IO)", 1)[1]:
    pass
else:
    raise SystemExit("patch_0461: MediaController duration access still occurs in IO block")
target.write_text(source, encoding="utf-8")

gradle = Path("app/build.gradle.kts")
build = gradle.read_text(encoding="utf-8")
if 'versionName = "0.5.9"' not in build or 'orElse("345")' not in build:
    raise SystemExit("patch_0461: unexpected base version; refusing unsafe version bump")
build = build.replace('versionName = "0.5.9"', 'versionName = "0.5.10"', 1)
build = build.replace('orElse("345")', 'orElse("346")')
gradle.write_text(build, encoding="utf-8")
print("patch_0461: MediaController duration is captured before IO dispatcher switch; version 0.5.10/346")
