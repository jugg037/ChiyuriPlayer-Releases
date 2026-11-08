from pathlib import Path

ROOT = Path("app/src/main/java/com/chiyuri/player")

def replace_once(path: Path, old: str, new: str, label: str) -> None:
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one source match, found {count}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

# External subtitle MIME detection, isolated for unit testing.
(ROOT / "SubtitleSupport.kt").write_text(r'''package com.chiyuri.player

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns

internal fun externalSubtitleMimeTypeFromName(fileName: String): String? =
    when (fileName.substringAfterLast('.', "").lowercase()) {
        "srt" -> "application/x-subrip"
        "vtt" -> "text/vtt"
        "ass", "ssa" -> "text/x-ssa"
        "ttml", "xml" -> "application/ttml+xml"
        else -> null
    }

internal fun externalSubtitleMimeType(context: Context, uri: Uri): String? {
    val displayName = runCatching {
        context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
            if (cursor.moveToFirst()) {
                val column = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (column >= 0) cursor.getString(column) else null
            } else null
        }
    }.getOrNull() ?: uri.lastPathSegment.orEmpty()

    return externalSubtitleMimeTypeFromName(displayName)
        ?: when (context.contentResolver.getType(uri)?.lowercase()) {
            "application/x-subrip" -> "application/x-subrip"
            "text/vtt" -> "text/vtt"
            "text/x-ssa" -> "text/x-ssa"
            "application/ttml+xml" -> "application/ttml+xml"
            else -> null
        }
}
''', encoding="utf-8")

main = ROOT / "MainActivity.kt"
replace_once(
    main,
    '''    val videoPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            try {
                context.contentResolver.takePersistableUriPermission(
                    uri,
                    android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION
                )
            } catch (_: SecurityException) {
                // MediaStore and some providers do not support persistable grants.
            }
            title = uri.lastPathSegment?.substringAfterLast('/') ?: "Видеофайл"
            onPickVideo(uri)
        }
    }
''',
    '''    val videoPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            try {
                context.contentResolver.takePersistableUriPermission(
                    uri,
                    android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION
                )
            } catch (_: SecurityException) {
                // MediaStore and some providers do not support persistable grants.
            }
            title = uri.lastPathSegment?.substringAfterLast('/') ?: "Видеофайл"
            onPickVideo(uri)
        }
    }
    val subtitlePicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { subtitleUri ->
        if (subtitleUri != null) {
            try {
                val mimeType = externalSubtitleMimeType(context, subtitleUri)
                if (mimeType == null) {
                    android.widget.Toast.makeText(context, "Поддерживаются SRT, VTT, ASS, SSA и TTML.", android.widget.Toast.LENGTH_LONG).show()
                } else {
                    runCatching {
                        context.contentResolver.takePersistableUriPermission(
                            subtitleUri,
                            android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION
                        )
                    }
                    val currentItem = player.currentMediaItem
                    val currentIndex = player.currentMediaItemIndex
                    val local = currentItem?.localConfiguration
                    val mediaUri = local?.uri
                    if (currentItem == null || currentIndex < 0 || mediaUri == null) {
                        android.widget.Toast.makeText(context, "Сначала открой видеофайл.", android.widget.Toast.LENGTH_LONG).show()
                    } else {
                        val subtitle = MediaItem.SubtitleConfiguration.Builder(subtitleUri)
                            .setMimeType(mimeType)
                            .setLanguage("und")
                            .setSelectionFlags(C.SELECTION_FLAG_DEFAULT)
                            .build()
                        val configurations = local.subtitleConfigurations.filterNot { it.uri == subtitleUri } + subtitle
                        val builder = MediaItem.Builder()
                            .setMediaId(currentItem.mediaId)
                            .setUri(mediaUri)
                            .setMediaMetadata(currentItem.mediaMetadata)
                            .setSubtitleConfigurations(configurations)
                        local.mimeType?.let { builder.setMimeType(it) }
                        val wasPlaying = player.isPlaying
                        val position = player.currentPosition
                        player.replaceMediaItem(currentIndex, builder.build())
                        player.prepare()
                        player.seekTo(currentIndex, position)
                        if (wasPlaying) player.play()
                        android.widget.Toast.makeText(context, "Внешние субтитры подключены.", android.widget.Toast.LENGTH_SHORT).show()
                    }
                }
            } catch (error: Exception) {
                android.widget.Toast.makeText(
                    context,
                    "Не удалось подключить субтитры: " + (error.message ?: "ошибка файла"),
                    android.widget.Toast.LENGTH_LONG
                ).show()
            }
        }
    }
''',
    "external subtitle picker"
)

replace_once(
    main,
    '''                        TextButton(
                            onClick = {
                                TrackSelectionDialogBuilder(context, "Выбор субтитров", player, C.TRACK_TYPE_TEXT)
                                    .setShowDisableOption(true)
                                    .build()
                                    .show()
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            GothicIcon(Icons.Default.Subtitles, contentDescription = null)
                            Spacer(Modifier.width(8.dp))
                            Text("Выбрать дорожку субтитров")
                        }
''',
    '''                        TextButton(
                            onClick = {
                                TrackSelectionDialogBuilder(context, "Выбор субтитров", player, C.TRACK_TYPE_TEXT)
                                    .setShowDisableOption(true)
                                    .build()
                                    .show()
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            GothicIcon(Icons.Default.Subtitles, contentDescription = null)
                            Spacer(Modifier.width(8.dp))
                            Text("Выбрать дорожку субтитров")
                        }
                        OutlinedButton(
                            onClick = {
                                subtitlePicker.launch(
                                    arrayOf(
                                        "application/x-subrip",
                                        "text/vtt",
                                        "text/x-ssa",
                                        "application/ttml+xml",
                                        "text/plain"
                                    )
                                )
                            },
                            modifier = Modifier.fillMaxWidth(),
                            enabled = player.currentMediaItem != null
                        ) {
                            GothicIcon(Icons.Default.Subtitles, contentDescription = null)
                            Spacer(Modifier.width(8.dp))
                            Text("Загрузить внешний файл субтитров")
                        }
''',
    "external subtitle button"
)

test_path = Path("app/src/test/java/com/chiyuri/player/SubtitleSupportTest.kt")
test_path.write_text(r'''package com.chiyuri.player

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class SubtitleSupportTest {
    @Test
    fun recognizesSupportedSubtitleExtensionsCaseInsensitively() {
        assertEquals("application/x-subrip", externalSubtitleMimeTypeFromName("movie.SRT"))
        assertEquals("text/vtt", externalSubtitleMimeTypeFromName("captions.vtt"))
        assertEquals("text/x-ssa", externalSubtitleMimeTypeFromName("dialogue.ass"))
        assertEquals("text/x-ssa", externalSubtitleMimeTypeFromName("dialogue.ssa"))
        assertEquals("application/ttml+xml", externalSubtitleMimeTypeFromName("captions.ttml"))
        assertEquals("application/ttml+xml", externalSubtitleMimeTypeFromName("captions.xml"))
    }

    @Test
    fun rejectsUnknownSubtitleExtensions() {
        assertNull(externalSubtitleMimeTypeFromName("video.mp4"))
        assertNull(externalSubtitleMimeTypeFromName("captions.txt"))
        assertNull(externalSubtitleMimeTypeFromName("captions"))
    }
}
''', encoding="utf-8")

updates = ROOT / "AppUpdates.kt"
source = updates.read_text(encoding="utf-8")
if "import kotlinx.coroutines.flow.collect\n" not in source:
    anchor = "import kotlinx.coroutines.launch\n"
    if source.count(anchor) != 1:
        raise SystemExit("Flow collect import anchor missing or ambiguous")
    source = source.replace(anchor, anchor + "import kotlinx.coroutines.flow.collect\n", 1)

old = '''            val versionCode = tag.split('.').mapNotNull { it.toIntOrNull() }.let { parts ->
                if (parts.size >= 3) parts[0] * 10000 + parts[1] * 100 + parts[2] else 0
            }
'''
new = '''            val declaredVersionCode = Regex("""(?im)^\\s*versionCode\\s*[:=]\\s*(\\d+)\\s*$""")
                .find(json.optString("body"))
                ?.groupValues
                ?.getOrNull(1)
                ?.toIntOrNull()
            // Older releases do not carry versionCode in their notes. Their semver key
            // is used only to identify the WorkManager task; APK validation uses its manifest.
            val versionCode = declaredVersionCode ?: tag.split('.').mapNotNull { it.toIntOrNull() }.let { parts ->
                if (parts.size >= 3) parts[0] * 1_000_000 + parts[1] * 1_000 + parts[2] else 0
            }
'''
if source.count(old) != 1:
    raise SystemExit("Release versionCode parsing anchor not found exactly once")
source = source.replace(old, new, 1)
if source.count("verifySigner(context, apk)") != 1:
    raise SystemExit("verifySigner call anchor not found exactly once")
source = source.replace("verifySigner(context, apk)", "verifySigner(context, apk, info.version)", 1)

old = '''    private fun verifySigner(context: Context, apk: File) {
        val flags = if (Build.VERSION.SDK_INT >= P) PackageManager.GET_SIGNING_CERTIFICATES else PackageManager.GET_SIGNATURES
        val installed = context.packageManager.getPackageInfo(context.packageName, flags)
        val archive = context.packageManager.getPackageArchiveInfo(apk.absolutePath, flags) ?: error("Android не распознал APK")
        val installedSignatures = if (Build.VERSION.SDK_INT >= P) installed.signingInfo?.apkContentsSigners else installed.signatures
        val archiveSignatures = if (Build.VERSION.SDK_INT >= P) archive.signingInfo?.apkContentsSigners else archive.signatures
        val installedHashes = installedSignatures.orEmpty().map { MessageDigest.getInstance("SHA-256").digest(it.toByteArray()).contentToString() }.toSet()
        val archiveHashes = archiveSignatures.orEmpty().map { MessageDigest.getInstance("SHA-256").digest(it.toByteArray()).contentToString() }.toSet()
        check(installedHashes.isNotEmpty() && installedHashes.intersect(archiveHashes).isNotEmpty()) { "Подпись APK не совпадает с установленной версией" }
    }
'''
new = '''    private fun verifySigner(context: Context, apk: File, expectedVersionName: String) {
        val flags = if (Build.VERSION.SDK_INT >= P) PackageManager.GET_SIGNING_CERTIFICATES else PackageManager.GET_SIGNATURES
        val installed = context.packageManager.getPackageInfo(context.packageName, flags)
        val archive = context.packageManager.getPackageArchiveInfo(apk.absolutePath, flags) ?: error("Android не распознал APK")
        check(archive.packageName == context.packageName) {
            "APK принадлежит другому приложению: " + archive.packageName
        }
        check(archive.versionName == expectedVersionName) {
            "Версия APK (" + archive.versionName + ") не совпадает с найденным релизом (" + expectedVersionName + ")"
        }
        check(archive.longVersionCode > installed.longVersionCode) {
            "Загруженный APK не новее установленной версии; установка понижения запрещена."
        }
        val installedSignatures = if (Build.VERSION.SDK_INT >= P) installed.signingInfo?.apkContentsSigners else installed.signatures
        val archiveSignatures = if (Build.VERSION.SDK_INT >= P) archive.signingInfo?.apkContentsSigners else archive.signatures
        val installedHashes = installedSignatures.orEmpty().map { MessageDigest.getInstance("SHA-256").digest(it.toByteArray()).contentToString() }.toSet()
        val archiveHashes = archiveSignatures.orEmpty().map { MessageDigest.getInstance("SHA-256").digest(it.toByteArray()).contentToString() }.toSet()
        check(installedHashes.isNotEmpty() && installedHashes.intersect(archiveHashes).isNotEmpty()) {
            "Подпись APK не совпадает с установленной версией"
        }
    }
'''
if source.count(old) != 1:
    raise SystemExit("APK signature verification block not found exactly once")
source = source.replace(old, new, 1)

old = '''    androidx.compose.runtime.LaunchedEffect(context, update?.versionCode) {
        val targetVersionCode = update?.versionCode
        workInfo = null
        if (targetVersionCode != null) {
            val manager = androidx.work.WorkManager.getInstance(context)
            while (true) {
                workInfo = kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
                    manager.getWorkInfosForUniqueWork(UpdateDownloadWorker.WORK_NAME).get()
                        .firstOrNull { "chiyuri_update_version_" + targetVersionCode in it.tags }
                }
                kotlinx.coroutines.delay(500)
            }
        }
    }
'''
new = '''    androidx.compose.runtime.LaunchedEffect(context, update?.versionCode) {
        val targetVersionCode = update?.versionCode
        workInfo = null
        if (targetVersionCode != null) {
            androidx.work.WorkManager.getInstance(context)
                .getWorkInfosForUniqueWorkFlow(UpdateDownloadWorker.WORK_NAME)
                .collect { items ->
                    workInfo = items.firstOrNull {
                        "chiyuri_update_version_" + targetVersionCode in it.tags
                    }
                }
        }
    }
'''
if source.count(old) != 1:
    raise SystemExit("WorkManager polling block not found exactly once")
source = source.replace(old, new, 1)
updates.write_text(source, encoding="utf-8")

lyrics = ROOT / "LyricsScreen.kt"
replace_once(
    lyrics,
    '''            "Поиск проверяет встроенные теги, LRCLIB, lyrics.ovh, SyncLRC и агрегатор LiriQo с несколькими музыкальными каталогами. Аудиофайл никуда не отправляется. Аудиофайл никуда не отправляется.",''',
    '''            "Поиск проверяет встроенные теги, LRCLIB, lyrics.ovh, SyncLRC и агрегатор LiriQo с несколькими музыкальными каталогами. Аудиофайл никуда не отправляется.",''',
    "duplicate lyrics privacy note"
)

print("0.4.19 reliability and external subtitle update applied.")
