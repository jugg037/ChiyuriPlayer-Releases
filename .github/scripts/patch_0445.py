from pathlib import Path
ROOT = Path('app/src/main')
PKG = ROOT / 'java/com/chiyuri/player'
TEST = Path('app/src/test/java/com/chiyuri/player')
PKG.mkdir(parents=True, exist_ok=True)
TEST.mkdir(parents=True, exist_ok=True)
def write(path, source):
    if path.exists(): raise SystemExit(f'patch_0445: {path.name} already exists')
    path.write_text(source, encoding='utf-8')
manager = r'''package com.chiyuri.player

import android.content.Context
import android.net.Uri
import androidx.core.content.edit
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedInputStream
import java.io.BufferedOutputStream
import java.io.InputStream
import java.io.OutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipInputStream
import java.util.zip.ZipOutputStream

data class BackupRestoreSummary(
    val playlistsRestored: Int,
    val tracksRestored: Int,
    val favoritesRestored: Int,
    val presetsRestored: Int,
    val radioStationsRestored: Int
)

object LibraryBackupManager {
    private const val ENTRY_NAME = "chiyuri-backup.json"
    private const val SCHEMA_VERSION = 1
    private const val MAX_BACKUP_BYTES = 8 * 1024 * 1024
    private const val MAX_PLAYLISTS = 100
    private const val MAX_TRACKS_PER_PLAYLIST = 2000
    private const val MAX_FAVORITES = 10000

    fun export(context: Context, output: OutputStream) {
        val payload = buildPayload(context).toString().toByteArray(Charsets.UTF_8)
        require(payload.size <= MAX_BACKUP_BYTES) { "Резервная копия превышает допустимый размер" }
        ZipOutputStream(BufferedOutputStream(output)).use { zip ->
            zip.putNextEntry(ZipEntry(ENTRY_NAME))
            zip.write(payload)
            zip.closeEntry()
        }
    }

    fun restore(context: Context, input: InputStream): BackupRestoreSummary {
        var payload: ByteArray? = null
        var total = 0
        ZipInputStream(BufferedInputStream(input)).use { zip ->
            while (true) {
                val entry = zip.nextEntry ?: break
                if (entry.isDirectory || entry.name != ENTRY_NAME || payload != null) {
                    throw IllegalArgumentException("Архив содержит неподдерживаемые записи")
                }
                val bytes = zip.readBytesLimited(MAX_BACKUP_BYTES)
                total += bytes.size
                require(total <= MAX_BACKUP_BYTES) { "Архив слишком большой" }
                payload = bytes
                zip.closeEntry()
            }
        }
        val json = JSONObject(String(payload ?: throw IllegalArgumentException("В архиве нет файла резервной копии"), Charsets.UTF_8))
        require(json.optInt("schema_version", -1) == SCHEMA_VERSION) { "Неподдерживаемая версия резервной копии" }

        val configObject = json.optJSONObject("audio_effects")
        if (configObject != null) {
            val bands = configObject.optJSONArray("bands") ?: JSONArray()
            AudioEffectsSettings.save(context, normalizeAudioEffectsConfig(AudioEffectsConfig(
                equalizerEnabled = configObject.optBoolean("equalizer_enabled", false),
                bandsDb = (0 until bands.length()).map { bands.optDouble(it, 0.0).toFloat() },
                playerVolume = configObject.optDouble("player_volume", 1.0).toFloat()
            )))
        }

        val favoriteArray = json.optJSONArray("favorites") ?: JSONArray()
        val favorites = buildSet {
            for (index in 0 until minOf(favoriteArray.length(), MAX_FAVORITES)) {
                val raw = favoriteArray.optString(index)
                if (isAllowedBackupUri(raw)) add(raw)
            }
        }
        context.getSharedPreferences("favorite_tracks", Context.MODE_PRIVATE).edit {
            putStringSet("uris", favorites)
        }

        var presetsRestored = 0
        val presetArray = json.optJSONArray("equalizer_presets") ?: JSONArray()
        for (index in 0 until minOf(presetArray.length(), 30)) {
            val item = presetArray.optJSONObject(index) ?: continue
            val bands = item.optJSONArray("bands") ?: continue
            val values = (0 until bands.length()).map { bands.optDouble(it, 0.0).toFloat() }
            val name = item.optString("name")
            if (name.isNotBlank() && values.size in 5..10) {
                runCatching { CustomEqualizerPresetStore.save(context, name, resampleEqualizerBands(values, 10)) }
                    .onSuccess { presetsRestored++ }
            }
        }

        var stationsRestored = 0
        val stationArray = json.optJSONArray("radio_stations") ?: JSONArray()
        for (index in 0 until minOf(stationArray.length(), 50)) {
            val item = stationArray.optJSONObject(index) ?: continue
            val before = RadioStationStore.load(context).size
            RadioStationStore.add(context, item.optString("name"), item.optString("url"))
            if (RadioStationStore.load(context).size > before) stationsRestored++
        }

        var playlistsRestored = 0
        var tracksRestored = 0
        val repository = PlaylistRepository(context)
        try {
        val playlistArray = json.optJSONArray("playlists") ?: JSONArray()
        for (index in 0 until minOf(playlistArray.length(), MAX_PLAYLISTS)) {
            val item = playlistArray.optJSONObject(index) ?: continue
            val originalName = normalizePlaylistName(item.optString("name")) ?: continue
            val playlistId = createUniquePlaylist(repository, originalName) ?: continue
            playlistsRestored++
            val tracks = item.optJSONArray("tracks") ?: JSONArray()
            for (trackIndex in 0 until minOf(tracks.length(), MAX_TRACKS_PER_PLAYLIST)) {
                val track = tracks.optJSONObject(trackIndex) ?: continue
                val rawUri = track.optString("uri")
                if (!isAllowedBackupUri(rawUri)) continue
                if (repository.addTrack(
                    playlistId,
                    Uri.parse(rawUri),
                    track.optString("title").take(200),
                    track.optString("artist").take(200).ifBlank { null },
                    track.optLong("duration_ms", 0L).coerceIn(0L, 86_400_000L),
                    track.optString("mime_type").take(120).ifBlank { null }
                )) tracksRestored++
            }
        }
        } finally { repository.close() }
        return BackupRestoreSummary(playlistsRestored, tracksRestored, favorites.size, presetsRestored, stationsRestored)
    }

    internal fun isAllowedBackupUri(raw: String): Boolean {
        if (raw.isBlank() || raw.length > 4096 || raw.any { it.isWhitespace() }) return false
        return runCatching {
            val uri = java.net.URI(raw)
            when (uri.scheme?.lowercase()) {
                "content", "file", "smb" -> uri.userInfo == null
                "https" -> !uri.host.isNullOrBlank() && uri.userInfo == null
                else -> false
            }
        }.getOrDefault(false)
    }

    private fun buildPayload(context: Context): JSONObject {
        val config = AudioEffectsSettings.load(context)
        val configJson = JSONObject()
            .put("equalizer_enabled", config.equalizerEnabled)
            .put("player_volume", config.playerVolume)
            .put("bands", JSONArray(config.bandsDb))
        val favorites = JSONArray(FavoriteTracksStore.load(context).filter(::isAllowedBackupUri).take(MAX_FAVORITES))
        val presets = JSONArray()
        CustomEqualizerPresetStore.load(context).take(30).forEach { preset ->
            presets.put(JSONObject().put("name", preset.name).put("bands", JSONArray(preset.bandsDb)))
        }
        val stations = JSONArray()
        RadioStationStore.load(context).take(50).forEach { station ->
            stations.put(JSONObject().put("name", station.name).put("url", station.url))
        }
        val playlists = JSONArray()
        PlaylistRepository(context).use { repository ->
            repository.getPlaylists().take(MAX_PLAYLISTS).forEach { playlist ->
                val tracks = JSONArray()
                repository.getTracks(playlist.id).take(MAX_TRACKS_PER_PLAYLIST).forEach { track ->
                    if (isAllowedBackupUri(track.uri)) {
                        tracks.put(JSONObject()
                            .put("uri", track.uri)
                            .put("title", track.title)
                            .put("artist", track.artist)
                            .put("duration_ms", track.durationMs)
                            .put("mime_type", track.mimeType))
                    }
                }
                playlists.put(JSONObject().put("name", playlist.name).put("tracks", tracks))
            }
        }
        return JSONObject()
            .put("schema_version", SCHEMA_VERSION)
            .put("created_at", System.currentTimeMillis())
            .put("audio_effects", configJson)
            .put("favorites", favorites)
            .put("equalizer_presets", presets)
            .put("radio_stations", stations)
            .put("playlists", playlists)
    }

    private fun createUniquePlaylist(repository: PlaylistRepository, baseName: String): Long? {
        if (repository.createPlaylist(baseName) != null) return repository.getPlaylists().firstOrNull { it.name.equals(baseName, true) }?.id
        for (index in 2..99) {
            val suffix = " ($index)"
            val candidate = baseName.take(80 - suffix.length) + suffix
            val id = repository.createPlaylist(candidate)
            if (id != null) return id
        }
        return null
    }

    private fun InputStream.readBytesLimited(limit: Int): ByteArray {
        val output = java.io.ByteArrayOutputStream()
        val buffer = ByteArray(8192)
        var total = 0
        while (true) {
            val count = read(buffer)
            if (count < 0) break
            total += count
            require(total <= limit) { "Архив слишком большой" }
            output.write(buffer, 0, count)
        }
        return output.toByteArray()
    }
}
'''
card = r'''package com.chiyuri.player

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
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
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
internal fun LibraryBackupCard() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var status by remember { mutableStateOf<String?>(null) }
    val exportLauncher = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/zip")) { uri ->
        if (uri != null) scope.launch {
            val result = runCatching {
                withContext(Dispatchers.IO) {
                    val output = context.contentResolver.openOutputStream(uri)
                        ?: error("Не удалось открыть файл для записи")
                    LibraryBackupManager.export(context, output)
                }
            }
            status = result.fold(
                onSuccess = { "Резервная копия создана." },
                onFailure = { "Ошибка экспорта: ${it.localizedMessage ?: "неизвестная ошибка"}" }
            )
        }
    }
    val importLauncher = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) scope.launch {
            val result = runCatching {
                withContext(Dispatchers.IO) {
                    val input = context.contentResolver.openInputStream(uri)
                        ?: error("Не удалось открыть архив")
                    LibraryBackupManager.restore(context, input)
                }
            }
            status = result.fold(
                onSuccess = { "Восстановлено: ${it.playlistsRestored} плейлистов, ${it.tracksRestored} треков, ${it.favoritesRestored} избранных." },
                onFailure = { "Ошибка восстановления: ${it.localizedMessage ?: "неизвестная ошибка"}" }
            )
        }
    }
    Surface(
        color = MaterialTheme.colorScheme.surface,
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Резервная копия", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onSurface)
            Text(
                "Сохраняются плейлисты, избранное, пресеты эквалайзера, настройки звука и избранные радиостанции. Пароли сетевых серверов не экспортируются.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                Button(onClick = { exportLauncher.launch("ChiyuriPlayer-backup.zip") }, modifier = Modifier.weight(1f)) {
                    Text("Экспорт")
                }
                Button(onClick = { importLauncher.launch(arrayOf("application/zip", "application/octet-stream")) }, modifier = Modifier.weight(1f)) {
                    Text("Импорт")
                }
            }
            Text(
                "После переноса на другое устройство доступ к исходным локальным файлам может потребовать повторного выбора.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            status?.let { Text(it, color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.bodySmall) }
        }
    }
}
'''
test = r'''package com.chiyuri.player

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LibraryBackupManagerTest {
    @Test fun acceptsOnlySupportedSafeUriSchemes() {
        assertTrue(LibraryBackupManager.isAllowedBackupUri("content://media/external/audio/1"))
        assertTrue(LibraryBackupManager.isAllowedBackupUri("file:///storage/emulated/0/Music/a.mp3"))
        assertTrue(LibraryBackupManager.isAllowedBackupUri("smb://nas/Music/a.mp3"))
        assertTrue(LibraryBackupManager.isAllowedBackupUri("https://example.com/a.mp3"))
        assertFalse(LibraryBackupManager.isAllowedBackupUri("http://example.com/a.mp3"))
        assertFalse(LibraryBackupManager.isAllowedBackupUri("https://user:pass@example.com/a.mp3"))
        assertFalse(LibraryBackupManager.isAllowedBackupUri("javascript:alert(1)"))
        assertFalse(LibraryBackupManager.isAllowedBackupUri(""))
    }

    @Test fun rejectsWhitespaceAndOversizedUris() {
        assertFalse(LibraryBackupManager.isAllowedBackupUri("content://media/audio/1 bad"))
        assertFalse(LibraryBackupManager.isAllowedBackupUri("content://" + "a".repeat(5000)))
    }
}
'''
write(PKG / 'LibraryBackupManager.kt', manager)
write(PKG / 'LibraryBackupCard.kt', card)
write(TEST / 'LibraryBackupManagerTest.kt', test)
main = Path('app/src/main/java/com/chiyuri/player/MainActivity.kt')
source = main.read_text(encoding='utf-8')
anchor = '        NetworkStreamCard(player)\n'
if anchor not in source: raise SystemExit('patch_0445: network card insertion anchor missing')
source = source.replace(anchor, anchor + '        LibraryBackupCard()\n', 1)
main.write_text(source, encoding='utf-8')
print('patch_0445: bounded, validated backup/restore for playlists, favorites, EQ presets, audio settings and radio bookmarks applied')