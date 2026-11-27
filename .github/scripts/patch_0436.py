from pathlib import Path

ROOT = Path.cwd()
PKG = ROOT / "app/src/main/java/com/chiyuri/player"
TEST = ROOT / "app/src/test/java/com/chiyuri/player"

def replace_once(path: Path, old: str, new: str, label: str):
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"patch_0436: missing anchor {label}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

(PKG / "PlaybackHistoryStore.kt").write_text('''package com.chiyuri.player

import android.content.Context
import androidx.core.content.edit
import androidx.media3.common.MediaItem
import org.json.JSONArray
import org.json.JSONObject

data class PlaybackHistoryEntry(
    val uri: String,
    val title: String,
    val artist: String?,
    val durationMs: Long,
    val lastPlayedAt: Long,
    val playCount: Int
)

/** Keeps a bounded, local-only history; no listening data leaves the device. */
object PlaybackHistoryStore {
    private const val PREFS = "playback_history"
    private const val KEY_ENTRIES = "entries"
    private const val MAX_ENTRIES = 100

    fun load(context: Context): List<PlaybackHistoryEntry> {
        val raw = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(KEY_ENTRIES, "[]") ?: "[]"
        return runCatching {
            val array = JSONArray(raw)
            buildList {
                for (index in 0 until array.length()) {
                    val item = array.optJSONObject(index) ?: continue
                    val uri = item.optString("uri").takeIf { it.isNotBlank() } ?: continue
                    add(PlaybackHistoryEntry(
                        uri = uri,
                        title = item.optString("title").ifBlank { "Без названия" },
                        artist = item.optString("artist").takeIf { it.isNotBlank() && it != "null" },
                        durationMs = item.optLong("duration_ms", 0L).coerceAtLeast(0L),
                        lastPlayedAt = item.optLong("last_played_at", 0L).coerceAtLeast(0L),
                        playCount = item.optInt("play_count", 1).coerceAtLeast(1)
                    ))
                }
            }.sortedByDescending { it.lastPlayedAt }.take(MAX_ENTRIES)
        }.getOrDefault(emptyList())
    }

    fun record(context: Context, item: MediaItem?, durationMs: Long) {
        val uri = item?.localConfiguration?.uri?.toString()?.takeIf { it.isNotBlank() } ?: return
        val metadata = item.mediaMetadata
        val incoming = PlaybackHistoryEntry(
            uri = uri,
            title = metadata.title?.toString()?.takeIf { it.isNotBlank() } ?: uri.substringAfterLast('/'),
            artist = metadata.artist?.toString()?.takeIf { it.isNotBlank() },
            durationMs = durationMs.coerceAtLeast(0L),
            lastPlayedAt = System.currentTimeMillis(),
            playCount = 1
        )
        val merged = mergePlaybackHistory(load(context), incoming, MAX_ENTRIES)
        val array = JSONArray()
        merged.forEach { entry ->
            array.put(JSONObject()
                .put("uri", entry.uri)
                .put("title", entry.title)
                .put("artist", entry.artist ?: JSONObject.NULL)
                .put("duration_ms", entry.durationMs)
                .put("last_played_at", entry.lastPlayedAt)
                .put("play_count", entry.playCount))
        }
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit {
            putString(KEY_ENTRIES, array.toString())
        }
    }

    fun clear(context: Context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit { remove(KEY_ENTRIES) }
    }
}

/** Pure merge function shared by storage and tests. */
internal fun mergePlaybackHistory(
    existing: List<PlaybackHistoryEntry>,
    incoming: PlaybackHistoryEntry,
    maxEntries: Int = 100
): List<PlaybackHistoryEntry> {
    if (maxEntries <= 0 || incoming.uri.isBlank()) return emptyList()
    val previous = existing.firstOrNull { it.uri == incoming.uri }
    val updated = incoming.copy(playCount = (previous?.playCount ?: 0) + 1)
    return (listOf(updated) + existing.filterNot { it.uri == incoming.uri })
        .sortedByDescending { it.lastPlayedAt }
        .take(maxEntries)
}
''', encoding="utf-8")

p = PKG / "PlaybackQueueStore.kt"
s = p.read_text(encoding="utf-8")
s = s.replace('    private const val POSITION = "position_ms"\n', '    private const val POSITION = "position_ms"\n    private const val ITEM_POSITIONS = "item_positions"\n', 1)
old = '''        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit {
            putString(ITEMS, array.toString())
            putInt(CURRENT_INDEX, persistedCurrentIndex.coerceAtLeast(0))
            putLong(POSITION, player.currentPosition.coerceAtLeast(0L))'''
new = '''        val preferences = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val positions = runCatching { JSONObject(preferences.getString(ITEM_POSITIONS, "{}") ?: "{}") }
            .getOrDefault(JSONObject())
        val currentUri = player.currentMediaItem?.localConfiguration?.uri?.toString()
        if (!currentUri.isNullOrBlank()) {
            val duration = player.duration
            if (duration > 0L && player.currentPosition >= duration - 2_000L) {
                positions.remove(currentUri)
            } else {
                positions.put(currentUri, player.currentPosition.coerceAtLeast(0L))
            }
        }
        while (positions.length() > 100) {
            val iterator = positions.keys()
            if (iterator.hasNext()) positions.remove(iterator.next()) else break
        }
        preferences.edit {
            putString(ITEMS, array.toString())
            putString(ITEM_POSITIONS, positions.toString())
            putInt(CURRENT_INDEX, persistedCurrentIndex.coerceAtLeast(0))
            putLong(POSITION, player.currentPosition.coerceAtLeast(0L))'''
if old not in s:
    raise SystemExit("patch_0436: PlaybackQueueStore.save anchor missing")
s = s.replace(old, new, 1)
anchor = '    /** Restores a saved queue without starting playback automatically. */\n'
insert = '''    /** Last saved position for an individual local or network media URI. */
    fun savedPosition(context: Context, uri: String): Long {
        if (uri.isBlank()) return 0L
        val raw = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(ITEM_POSITIONS, "{}") ?: "{}"
        return runCatching { JSONObject(raw).optLong(uri, 0L).coerceAtLeast(0L) }.getOrDefault(0L)
    }

'''
if anchor not in s:
    raise SystemExit("patch_0436: PlaybackQueueStore restore anchor missing")
s = s.replace(anchor, insert + anchor, 1)
p.write_text(s, encoding="utf-8")

p = PKG / "PlaybackService.kt"
replace_once(p,
'''            override fun onMediaItemTransition(
                mediaItem: androidx.media3.common.MediaItem?,
                reason: Int
            ) {
                PlaybackQueueStore.save(this@PlaybackService, player)
            }''',
'''            override fun onMediaItemTransition(
                mediaItem: androidx.media3.common.MediaItem?,
                reason: Int
            ) {
                PlaybackQueueStore.save(this@PlaybackService, player)
                PlaybackHistoryStore.record(this@PlaybackService, mediaItem, player.duration)
            }''',
"service media transition")

p = PKG / "MainActivity.kt"
s = p.read_text(encoding="utf-8")
old = '''            controller?.setMediaItem(
                MediaItem.Builder().setUri(uri).setMediaMetadata(metadataBuilder.build()).build()
            )'''
new = '''            val mediaItem = MediaItem.Builder()
                .setUri(uri)
                .setMimeType(contentResolver.getType(uri))
                .setMediaMetadata(metadataBuilder.build())
                .build()
            controller?.setMediaItem(mediaItem, PlaybackQueueStore.savedPosition(this@MainActivity, uri.toString()))'''
if old not in s:
    raise SystemExit("patch_0436: single item playback anchor missing")
s = s.replace(old, new, 1)

old_video = '                        LocalMediaBrowser(isVideo = true, onPlay = onPickVideo)'
new_video = '''                        LocalMediaBrowser(
                            isVideo = true,
                            onPlay = onPickVideo,
                            currentMediaUri = currentMediaUri,
                            onPlayQueue = { items, selectedIndex ->
                                val queued = items.drop(selectedIndex).map { item ->
                                    MediaItem.Builder()
                                        .setUri(item.uri)
                                        .setMimeType(item.mimeType)
                                        .setMediaMetadata(MediaMetadata.Builder().setTitle(item.title).build())
                                        .build()
                                }
                                if (queued.isNotEmpty()) {
                                    val firstUri = queued.first().localConfiguration?.uri?.toString().orEmpty()
                                    player.setMediaItems(queued, 0, PlaybackQueueStore.savedPosition(context, firstUri))
                                    player.prepare()
                                    player.play()
                                }
                            }
                        )'''
if old_video not in s:
    raise SystemExit("patch_0436: video browser call anchor missing")
s = s.replace(old_video, new_video, 1)
s = s.replace(
    'player.setMediaItems(queued, 0, 0L)\n                                    player.prepare()',
    'player.setMediaItems(queued, 0, PlaybackQueueStore.savedPosition(context, queued.first().localConfiguration?.uri?.toString().orEmpty()))\n                                    player.prepare()',
    1
)
s = s.replace('''                        "Автообновление" -> AutoUpdateSettingsScreen(Modifier.weight(1f))
                        else -> {''', '''                        "Автообновление" -> AutoUpdateSettingsScreen(Modifier.weight(1f))
                        "История" -> PlaybackHistoryScreen(player, Modifier.weight(1f))
                        else -> {''', 1)
s = s.replace('''                                ActionCard("Автообновление", "Фоновая проверка новых версий", Icons.Default.Update) { morePage = "Автообновление" }
                                ActionCard("Открыть аудиофайл",''', '''                                ActionCard("Автообновление", "Фоновая проверка новых версий", Icons.Default.Update) { morePage = "Автообновление" }
                                ActionCard("История и подборки", "Недавно воспроизведённое, частые прослушивания и избранное", Icons.Default.History) { morePage = "История" }
                                ActionCard("Открыть аудиофайл",''', 1)
if 'PlaybackHistoryScreen(player, Modifier.weight(1f))' not in s:
    raise SystemExit("patch_0436: history screen routing verification failed")
p.write_text(s, encoding="utf-8")

(PKG / "PlaybackHistoryScreen.kt").write_text('''package com.chiyuri.player

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DeleteSweep
import androidx.compose.material.icons.filled.History
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.FilterChip
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.Player
import androidx.core.net.toUri

private enum class HistoryFilter { RECENT, MOST_PLAYED, FAVORITES }

@Composable
internal fun PlaybackHistoryScreen(player: Player, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    var entries by remember(context) { mutableStateOf(PlaybackHistoryStore.load(context)) }
    var filter by remember { mutableStateOf(HistoryFilter.RECENT) }
    var confirmClear by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { entries = PlaybackHistoryStore.load(context) }
    androidx.compose.runtime.DisposableEffect(context) {
        val preferences = context.getSharedPreferences("playback_history", android.content.Context.MODE_PRIVATE)
        val listener = android.content.SharedPreferences.OnSharedPreferenceChangeListener { _, _ ->
            entries = PlaybackHistoryStore.load(context)
        }
        preferences.registerOnSharedPreferenceChangeListener(listener)
        onDispose { preferences.unregisterOnSharedPreferenceChangeListener(listener) }
    }
    val favorites = remember(context) { FavoriteTracksStore.load(context) }
    val visible = when (filter) {
        HistoryFilter.RECENT -> entries.sortedByDescending { it.lastPlayedAt }
        HistoryFilter.MOST_PLAYED -> entries.sortedWith(compareByDescending<PlaybackHistoryEntry> { it.playCount }.thenByDescending { it.lastPlayedAt })
        HistoryFilter.FAVORITES -> entries.filter { it.uri in favorites }.sortedByDescending { it.lastPlayedAt }
    }
    Column(modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text("История воспроизведения", style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
            IconButton(onClick = { confirmClear = true }, enabled = entries.isNotEmpty()) {
                androidx.compose.material3.Icon(Icons.Default.DeleteSweep, contentDescription = "Очистить историю")
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            FilterChip(selected = filter == HistoryFilter.RECENT, onClick = { filter = HistoryFilter.RECENT }, label = { Text("Недавние") })
            FilterChip(selected = filter == HistoryFilter.MOST_PLAYED, onClick = { filter = HistoryFilter.MOST_PLAYED }, label = { Text("Частые") })
            FilterChip(selected = filter == HistoryFilter.FAVORITES, onClick = { filter = HistoryFilter.FAVORITES }, label = { Text("Избранное") })
        }
        if (visible.isEmpty()) {
            Column(Modifier.fillMaxWidth().padding(vertical = 28.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                androidx.compose.material3.Icon(Icons.Default.History, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                Text(if (filter == HistoryFilter.FAVORITES) "В истории пока нет избранных композиций" else "История пока пуста", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                items(visible, key = { it.uri }) { entry ->
                    Surface(
                        color = MaterialTheme.colorScheme.surface,
                        shape = MaterialTheme.shapes.medium,
                        modifier = Modifier.fillMaxWidth().clickable {
                            val metadata = MediaMetadata.Builder().setTitle(entry.title).setArtist(entry.artist).build()
                            val item = MediaItem.Builder().setUri(entry.uri.toUri()).setMediaMetadata(metadata).build()
                            player.setMediaItem(item, PlaybackQueueStore.savedPosition(context, entry.uri))
                            player.prepare()
                            player.play()
                        }
                    ) {
                        Column(Modifier.padding(horizontal = 14.dp, vertical = 11.dp)) {
                            Text(entry.title, color = MaterialTheme.colorScheme.onSurface, maxLines = 1)
                            Text(
                                listOfNotNull(entry.artist, "Прослушиваний: ${entry.playCount}", formatPlaybackTime(entry.durationMs)).joinToString(" • "),
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                style = MaterialTheme.typography.bodySmall,
                                maxLines = 1
                            )
                        }
                    }
                }
            }
        }
    }
    if (confirmClear) {
        AlertDialog(
            onDismissRequest = { confirmClear = false },
            title = { Text("Очистить историю?") },
            text = { Text("Список недавно воспроизведённых и счётчики прослушиваний будут удалены. Файлы и плейлисты не затрагиваются.") },
            confirmButton = {
                TextButton(onClick = {
                    PlaybackHistoryStore.clear(context)
                    entries = emptyList()
                    confirmClear = false
                }) { Text("Очистить") }
            },
            dismissButton = { TextButton(onClick = { confirmClear = false }) { Text("Отмена") } }
        )
    }
}
''', encoding="utf-8")

(TEST / "PlaybackHistoryStoreTest.kt").write_text('''package com.chiyuri.player

import org.junit.Assert.assertEquals
import org.junit.Test

class PlaybackHistoryStoreTest {
    private fun entry(uri: String, time: Long, count: Int = 1) = PlaybackHistoryEntry(
        uri = uri, title = uri, artist = null, durationMs = 1000L, lastPlayedAt = time, playCount = count
    )

    @Test fun replayMovesItemToTopAndIncrementsCount() {
        val merged = mergePlaybackHistory(listOf(entry("a", 10L, 2), entry("b", 20L)), entry("a", 30L))
        assertEquals(listOf("a", "b"), merged.map { it.uri })
        assertEquals(3, merged.first().playCount)
        assertEquals(30L, merged.first().lastPlayedAt)
    }

    @Test fun historyIsDeduplicatedAndBounded() {
        val existing = (0 until 5).map { entry("uri-$it", it.toLong()) }
        val merged = mergePlaybackHistory(existing, entry("new", 10L), maxEntries = 3)
        assertEquals(3, merged.size)
        assertEquals("new", merged.first().uri)
    }

    @Test fun invalidIncomingEntryDoesNotCreateHistory() {
        assertEquals(emptyList<PlaybackHistoryEntry>(), mergePlaybackHistory(listOf(entry("a", 1L)), entry("", 2L)))
        assertEquals(emptyList<PlaybackHistoryEntry>(), mergePlaybackHistory(listOf(entry("a", 1L)), entry("b", 2L), 0))
    }
}
''', encoding="utf-8")

print("patch_0436: playback history, smart collection filters, per-file resume, and video auto-queue applied")
