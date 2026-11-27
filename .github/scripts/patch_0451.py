from pathlib import Path

def replace_once(path: Path, old: str, new: str, label: str):
    source = path.read_text(encoding="utf-8")
    if old not in source:
        raise SystemExit(f"patch_0451: missing {label}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

PKG = Path("app/src/main/java/com/chiyuri/player")
TEST = Path("app/src/test/java/com/chiyuri/player")

(PKG / "MediaFileInfo.kt").write_text('''package com.chiyuri.player

import android.content.Context
import android.media.MediaExtractor
import android.media.MediaFormat
import android.net.Uri
import android.provider.OpenableColumns
import java.io.File
import java.util.Locale
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

data class MediaTrackInfo(
    val kind: String,
    val mimeType: String?,
    val bitrate: Int?,
    val sampleRate: Int?,
    val channelCount: Int?,
    val width: Int?,
    val height: Int?,
    val frameRate: Float?,
    val language: String?
)

data class MediaFileInfo(
    val name: String,
    val uri: String,
    val containerMimeType: String?,
    val sizeBytes: Long?,
    val durationMs: Long,
    val tracks: List<MediaTrackInfo>,
    val inspectionError: String? = null
)

internal fun formatMediaFileSize(bytes: Long?): String {
    if (bytes == null || bytes < 0L) return "Неизвестно"
    if (bytes < 1024L) return "$bytes Б"
    val units = listOf("КБ", "МБ", "ГБ", "ТБ")
    var value = bytes.toDouble()
    var unitIndex = -1
    while (value >= 1024.0 && unitIndex < units.lastIndex) {
        value /= 1024.0
        unitIndex++
    }
    return String.format(Locale.ROOT, "%.2f %s", value, units[unitIndex])
}

internal fun formatMediaBitrate(bitsPerSecond: Int?): String =
    bitsPerSecond?.takeIf { it > 0 }?.let { "${(it + 500) / 1000} кбит/с" } ?: "Неизвестно"

internal fun readMediaFileInfo(
    context: Context,
    uri: Uri,
    fallbackName: String,
    durationMs: Long
): MediaFileInfo {
    var name = fallbackName.ifBlank { uri.lastPathSegment ?: "Медиафайл" }
    var size: Long? = null
    runCatching {
        context.contentResolver.query(
            uri,
            arrayOf(OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE),
            null, null, null
        )?.use { cursor ->
            if (cursor.moveToFirst()) {
                val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                val sizeIndex = cursor.getColumnIndex(OpenableColumns.SIZE)
                if (nameIndex >= 0) name = cursor.getString(nameIndex)?.takeIf { it.isNotBlank() } ?: name
                if (sizeIndex >= 0 && !cursor.isNull(sizeIndex)) size = cursor.getLong(sizeIndex).takeIf { it >= 0L }
            }
        }
    }
    if (size == null && uri.scheme.equals("file", true)) {
        size = runCatching { uri.path?.let(::File)?.length() }.getOrNull()?.takeIf { it >= 0L }
    }
    val containerMime = runCatching { context.contentResolver.getType(uri) }.getOrNull()
    val tracks = mutableListOf<MediaTrackInfo>()
    var inspectionError: String? = null
    if (uri.scheme in setOf("content", "file")) {
        val extractor = MediaExtractor()
        try {
            extractor.setDataSource(context, uri, null)
            for (index in 0 until extractor.trackCount.coerceAtMost(64)) {
                val format = extractor.getTrackFormat(index)
                val mime = runCatching { format.getString(MediaFormat.KEY_MIME) }.getOrNull()
                val kind = when {
                    mime?.startsWith("audio/") == true -> "Аудио"
                    mime?.startsWith("video/") == true -> "Видео"
                    mime?.startsWith("text/") == true || mime?.contains("subtitle") == true -> "Субтитры"
                    else -> "Дорожка"
                }
                fun intValue(key: String): Int? =
                    if (format.containsKey(key)) runCatching { format.getInteger(key) }.getOrNull() else null
                val frameRate = intValue(MediaFormat.KEY_FRAME_RATE)?.toFloat()?.takeIf { it > 0f }
                tracks += MediaTrackInfo(
                    kind = kind,
                    mimeType = mime,
                    bitrate = intValue(MediaFormat.KEY_BIT_RATE),
                    sampleRate = intValue(MediaFormat.KEY_SAMPLE_RATE),
                    channelCount = intValue(MediaFormat.KEY_CHANNEL_COUNT),
                    width = intValue(MediaFormat.KEY_WIDTH),
                    height = intValue(MediaFormat.KEY_HEIGHT),
                    frameRate = frameRate,
                    language = runCatching { format.getString(MediaFormat.KEY_LANGUAGE) }.getOrNull()
                )
            }
        } catch (error: Exception) {
            inspectionError = error.localizedMessage?.take(180) ?: "Не удалось прочитать параметры дорожек"
        } finally {
            runCatching { extractor.release() }
        }
    } else {
        inspectionError = "Для сетевого потока подробные параметры зависят от сервера и не запрашиваются отдельно."
    }
    return MediaFileInfo(name, uri.toString(), containerMime, size, durationMs.coerceAtLeast(0L), tracks, inspectionError)
}

@androidx.compose.runtime.Composable
internal fun MediaFileInfoDialog(player: androidx.media3.common.Player, onDismiss: () -> Unit) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val item = player.currentMediaItem
    val uri = item?.localConfiguration?.uri
    var info by androidx.compose.runtime.remember(uri) {
        androidx.compose.runtime.mutableStateOf<MediaFileInfo?>(null)
    }
    var loading by androidx.compose.runtime.remember(uri) { androidx.compose.runtime.mutableStateOf(true) }
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
        loading = false
    }
    androidx.compose.material3.AlertDialog(
        onDismissRequest = onDismiss,
        title = { androidx.compose.material3.Text("Сведения о файле") },
        text = {
            androidx.compose.foundation.layout.Column(
                Modifier.heightIn(max = 480.dp).verticalScroll(rememberScrollState()),
                verticalArrangement = androidx.compose.foundation.layout.Arrangement.spacedBy(6.dp)
            ) {
                if (loading) {
                    androidx.compose.material3.Text("Чтение параметров…")
                } else if (info == null) {
                    androidx.compose.material3.Text("Нет выбранного файла.")
                } else {
                    val value = info!!
                    InfoLine("Имя", value.name)
                    InfoLine("Размер", formatMediaFileSize(value.sizeBytes))
                    InfoLine("Длительность", formatPlaybackTime(value.durationMs))
                    InfoLine("Тип контейнера", value.containerMimeType ?: "Неизвестно")
                    InfoLine("Адрес", value.uri)
                    if (value.tracks.isNotEmpty()) {
                        androidx.compose.material3.HorizontalDivider()
                        androidx.compose.material3.Text("Медиадорожки", style = androidx.compose.material3.MaterialTheme.typography.titleSmall)
                        value.tracks.forEachIndexed { index, track ->
                            androidx.compose.material3.Text("${index + 1}. ${track.kind}", style = androidx.compose.material3.MaterialTheme.typography.titleSmall)
                            InfoLine("Кодек", track.mimeType ?: "Неизвестно")
                            InfoLine("Битрейт", formatMediaBitrate(track.bitrate))
                            track.sampleRate?.let { InfoLine("Частота", "$it Гц") }
                            track.channelCount?.let { InfoLine("Каналы", it.toString()) }
                            if (track.width != null && track.height != null) InfoLine("Разрешение", "${track.width} × ${track.height}")
                            track.frameRate?.let { InfoLine("Кадровая частота", String.format(Locale.ROOT, "%.2f FPS", it)) }
                            track.language?.takeIf { it.isNotBlank() }?.let { InfoLine("Язык", it) }
                        }
                    }
                    value.inspectionError?.let {
                        androidx.compose.material3.Text(it, color = androidx.compose.material3.MaterialTheme.colorScheme.onSurfaceVariant, style = androidx.compose.material3.MaterialTheme.typography.bodySmall)
                    }
                }
            }
        },
        confirmButton = {
            androidx.compose.material3.TextButton(onClick = onDismiss) {
                androidx.compose.material3.Text("Закрыть")
            }
        }
    )
}

@androidx.compose.runtime.Composable
private fun InfoLine(label: String, value: String) {
    androidx.compose.foundation.layout.Column {
        androidx.compose.material3.Text(label, style = androidx.compose.material3.MaterialTheme.typography.labelSmall, color = androidx.compose.material3.MaterialTheme.colorScheme.onSurfaceVariant)
        androidx.compose.material3.Text(value, style = androidx.compose.material3.MaterialTheme.typography.bodyMedium, color = androidx.compose.material3.MaterialTheme.colorScheme.onSurface)
    }
}
''', encoding="utf-8")

p = PKG / "MainActivity.kt"
replace_once(
    p,
    '    var showMetadataEditor by remember { mutableStateOf(false) }',
    '    var showMetadataEditor by remember { mutableStateOf(false) }\n    var showMediaInfo by remember { mutableStateOf(false) }',
    "media info state"
)
replace_once(
    p,
    '                    onEditMetadata = { showMetadataEditor = true },\n                    onDeleteTrack = { showDeleteConfirmation = true },',
    '                    onEditMetadata = { showMetadataEditor = true },\n                    onShowInfo = { showMediaInfo = true },\n                    onDeleteTrack = { showDeleteConfirmation = true },',
    "mini-player media info callback"
)
replace_once(
    p,
    '    onEditMetadata: () -> Unit,\n    onDeleteTrack: () -> Unit,',
    '    onEditMetadata: () -> Unit,\n    onShowInfo: () -> Unit,\n    onDeleteTrack: () -> Unit,',
    "mini-player callback signature"
)
replace_once(
    p,
    '    if (showMetadataEditor) {\n        TrackMetadataEditorDialog(',
    '    if (showMediaInfo) {\n        MediaFileInfoDialog(player, onDismiss = { showMediaInfo = false })\n    }\n\n    if (showMetadataEditor) {\n        TrackMetadataEditorDialog(',
    "media info dialog placement"
)
replace_once(
    p,
    '''                        DropdownMenuItem(
                            text = { Text("Редактировать информацию") },''',
    '''                        DropdownMenuItem(
                            text = { Text("Сведения о файле") },
                            leadingIcon = { GothicIcon(Icons.Default.Info, contentDescription = null) },
                            onClick = { moreActionsExpanded = false; onShowInfo() }
                        )
                        DropdownMenuItem(
                            text = { Text("Редактировать информацию") },''',
    "media info action"
)

(TEST / "MediaFileInfoFormattingTest.kt").write_text('''package com.chiyuri.player

import org.junit.Assert.assertEquals
import org.junit.Test

class MediaFileInfoFormattingTest {
    @Test fun formatsByteUnitsAndUnknownSizes() {
        assertEquals("0 Б", formatMediaFileSize(0L))
        assertEquals("1.00 КБ", formatMediaFileSize(1024L))
        assertEquals("1.00 МБ", formatMediaFileSize(1024L * 1024L))
        assertEquals("Неизвестно", formatMediaFileSize(null))
        assertEquals("Неизвестно", formatMediaFileSize(-1L))
    }

    @Test fun formatsBitrateSafely() {
        assertEquals("320 кбит/с", formatMediaBitrate(320_000))
        assertEquals("Неизвестно", formatMediaBitrate(null))
        assertEquals("Неизвестно", formatMediaBitrate(0))
    }
}
''', encoding="utf-8")

print("patch_0451: current-track file inspector added to the mini-player actions menu")
