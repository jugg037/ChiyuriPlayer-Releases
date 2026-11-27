from pathlib import Path

def replace_once(path: Path, old: str, new: str, label: str):
    source = path.read_text(encoding="utf-8")
    if old not in source:
        raise SystemExit(f"patch_0454: missing {label}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

PKG = Path("app/src/main/java/com/chiyuri/player")
TEST = Path("app/src/test/java/com/chiyuri/player")

(PKG / "MediaLibraryHealthScanner.kt").write_text('''package com.chiyuri.player

import android.content.Context
import android.media.MediaExtractor
import android.media.MediaFormat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.nio.ByteBuffer

data class MediaHealthIssue(
    val uri: String,
    val title: String,
    val reason: String
)

data class MediaHealthReport(
    val totalFiles: Int,
    val readableFiles: Int,
    val issues: List<MediaHealthIssue>
) {
    val damagedFiles: Int get() = issues.size
}

internal fun buildMediaHealthReport(totalFiles: Int, issues: List<MediaHealthIssue>): MediaHealthReport {
    val safeTotal = totalFiles.coerceAtLeast(0)
    val safeIssues = issues.distinctBy { it.uri }.take(safeTotal)
    return MediaHealthReport(safeTotal, (safeTotal - safeIssues.size).coerceAtLeast(0), safeIssues)
}

object MediaLibraryHealthScanner {
    suspend fun scan(
        context: Context,
        onProgress: (completed: Int, total: Int) -> Unit = { _, _ -> }
    ): MediaHealthReport = withContext(Dispatchers.IO) {
        val audio = runCatching { LocalMediaRepository.loadAudio(context) }.getOrDefault(emptyList())
        val video = runCatching { LocalMediaRepository.loadVideos(context) }.getOrDefault(emptyList())
        val media = (audio + video).distinctBy { it.uri.toString() }.take(10_000)
        val issues = mutableListOf<MediaHealthIssue>()
        media.forEachIndexed { index, item ->
            inspect(context, item)?.let { reason ->
                issues += MediaHealthIssue(item.uri.toString(), item.title, reason)
            }
            withContext(Dispatchers.Main) { onProgress(index + 1, media.size) }
        }
        buildMediaHealthReport(media.size, issues)
    }

    private fun inspect(context: Context, item: LocalMedia): String? {
        val extractor = MediaExtractor()
        return try {
            extractor.setDataSource(context, item.uri, null)
            if (extractor.trackCount <= 0) return "Не обнаружены медиадорожки"
            val formats = (0 until extractor.trackCount.coerceAtMost(32)).map { extractor.getTrackFormat(it) }
            val selectedIndex = formats.indices.firstOrNull { index ->
                val mime = formats[index].getString(MediaFormat.KEY_MIME).orEmpty()
                if (item.isVideo) mime.startsWith("video/") else mime.startsWith("audio/")
            } ?: return "Не найдена дорожка нужного типа"
            val format = formats[selectedIndex]
            extractor.selectTrack(selectedIndex)
            val durationUs = if (format.containsKey(MediaFormat.KEY_DURATION)) {
                runCatching { format.getLong(MediaFormat.KEY_DURATION) }.getOrDefault(0L).coerceAtLeast(0L)
            } else 0L
            val positions = if (durationUs > 0L) {
                listOf(0L, durationUs / 2L, (durationUs - 1L).coerceAtLeast(0L)).distinct()
            } else listOf(0L)
            val buffer = ByteBuffer.allocate(1024 * 1024)
            var readableSamples = 0
            positions.forEach { position ->
                extractor.seekTo(position, MediaExtractor.SEEK_TO_PREVIOUS_SYNC)
                buffer.clear()
                if (runCatching { extractor.readSampleData(buffer, 0) }.getOrDefault(-1) > 0) {
                    readableSamples++
                }
            }
            if (readableSamples == 0) "Не удалось прочитать медиаданные" else null
        } catch (_: SecurityException) {
            "Android не предоставил доступ к файлу"
        } catch (error: Exception) {
            error.localizedMessage?.take(160)?.ifBlank { "Файл недоступен или повреждён" }
                ?: "Файл недоступен или повреждён"
        } finally {
            runCatching { extractor.release() }
        }
    }
}
''', encoding="utf-8")

(PKG / "MediaLibraryHealthScreen.kt").write_text('''package com.chiyuri.player

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.HealthAndSafety
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

@Composable
internal fun MediaLibraryHealthScreen(modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var scanning by remember { mutableStateOf(false) }
    var completed by remember { mutableStateOf(0) }
    var total by remember { mutableStateOf(0) }
    var report by remember { mutableStateOf<MediaHealthReport?>(null) }
    var error by remember { mutableStateOf<String?>(null) }

    Column(modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("Проверка медиатеки", style = MaterialTheme.typography.titleLarge)
        Text(
            "Проверяется доступность файлов, наличие аудио- или видеодорожек и чтение контрольных медиасэмплов. Исходные файлы не изменяются.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Button(
            onClick = {
                scope.launch {
                    scanning = true
                    completed = 0
                    total = 0
                    report = null
                    error = null
                    runCatching {
                        MediaLibraryHealthScanner.scan(context) { done, count ->
                            completed = done
                            total = count
                        }
                    }.onSuccess { report = it }
                        .onFailure { error = it.message ?: "Не удалось проверить медиатеку" }
                    scanning = false
                }
            },
            enabled = !scanning,
            modifier = Modifier.fillMaxWidth()
        ) {
            androidx.compose.material3.Icon(Icons.Default.HealthAndSafety, contentDescription = null)
            Text("  Начать проверку")
        }
        if (scanning) {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                CircularProgressIndicator()
                Text(if (total > 0) "Проверено $completed из $total" else "Сканирование медиатеки…")
            }
        }
        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        report?.let { result ->
            Text("Всего: ${result.totalFiles} • Читаются: ${result.readableFiles} • Проблемы: ${result.damagedFiles}")
            if (result.issues.isEmpty()) {
                Text("Проблемных файлов не обнаружено.", color = MaterialTheme.colorScheme.primary)
            } else {
                Text("Файлы, требующие внимания", style = MaterialTheme.typography.titleMedium)
                LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    items(result.issues, key = { it.uri }) { issue ->
                        Surface(color = MaterialTheme.colorScheme.surface, shape = MaterialTheme.shapes.medium) {
                            Column(Modifier.fillMaxWidth().padding(12.dp)) {
                                Text(issue.title, color = MaterialTheme.colorScheme.onSurface, maxLines = 1)
                                Text(issue.reason, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                                Text(issue.uri, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.labelSmall, maxLines = 2)
                            }
                        }
                    }
                }
            }
        }
    }
}
''', encoding="utf-8")

p = PKG / "MainActivity.kt"
replace_once(
    p,
    '''                        "WebDAV" -> WebDavLibraryScreen(player, Modifier.weight(1f))''',
    '''                        "WebDAV" -> WebDavLibraryScreen(player, Modifier.weight(1f))
                        "Проверка" -> MediaLibraryHealthScreen(Modifier.weight(1f))''',
    "media health navigation route"
)
replace_once(
    p,
    '''                                ActionCard("Рекомендации и вечеринка", "Локальный умный микс с перемешиванием и повтором", Icons.Default.AutoAwesome) { morePage = "Микс" }''',
    '''                                ActionCard("Рекомендации и вечеринка", "Локальный умный микс с перемешиванием и повтором", Icons.Default.AutoAwesome) { morePage = "Микс" }
                                ActionCard("Проверка медиатеки", "Поиск недоступных и нечитаемых аудио- и видеофайлов", Icons.Default.HealthAndSafety) { morePage = "Проверка" }''',
    "media health action card"
)

(TEST / "MediaLibraryHealthTest.kt").write_text('''package com.chiyuri.player

import org.junit.Assert.assertEquals
import org.junit.Test

class MediaLibraryHealthTest {
    @Test fun reportCountsReadableAndProblemFiles() {
        val issues = listOf(
            MediaHealthIssue("content://media/1", "Broken A", "No tracks"),
            MediaHealthIssue("content://media/1", "Duplicate", "Duplicate uri"),
            MediaHealthIssue("content://media/2", "Broken B", "No samples")
        )
        val report = buildMediaHealthReport(5, issues)
        assertEquals(5, report.totalFiles)
        assertEquals(3, report.readableFiles)
        assertEquals(2, report.damagedFiles)
    }

    @Test fun reportBoundsIssuesToLibrarySize() {
        val report = buildMediaHealthReport(1, listOf(
            MediaHealthIssue("a", "A", "bad"),
            MediaHealthIssue("b", "B", "bad")
        ))
        assertEquals(1, report.damagedFiles)
        assertEquals(0, report.readableFiles)
    }
}
''', encoding="utf-8")

print("patch_0454: non-destructive media-library integrity scanner and report screen added")
