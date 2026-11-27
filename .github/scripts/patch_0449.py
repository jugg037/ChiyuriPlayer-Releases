from pathlib import Path

def replace_once(path: Path, old: str, new: str, label: str):
    source = path.read_text(encoding="utf-8")
    if old not in source:
        raise SystemExit(f"patch_0449: missing {label}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

ROOT = Path("app/src/main")
PKG = ROOT / "java/com/chiyuri/player"
TEST = Path("app/src/test/java/com/chiyuri/player")

(PKG / "PlaybackPreferencesStore.kt").write_text('''package com.chiyuri.player

import android.content.Context
import androidx.core.content.edit

data class PlaybackPreferences(
    val gaplessPlayback: Boolean = true
)

object PlaybackPreferencesStore {
    internal const val PREFERENCES_NAME = "playback_preferences"
    internal const val KEY_GAPLESS = "gapless_playback"

    fun load(context: Context): PlaybackPreferences {
        val prefs = context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)
        return PlaybackPreferences(gaplessPlayback = prefs.getBoolean(KEY_GAPLESS, true))
    }

    fun save(context: Context, preferences: PlaybackPreferences) {
        context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE).edit {
            putBoolean(KEY_GAPLESS, preferences.gaplessPlayback)
        }
    }
}
''', encoding="utf-8")

(PKG / "LocalRecommendations.kt").write_text('''package com.chiyuri.player

data class LocalRecommendationTrack(
    val uri: String,
    val title: String,
    val artist: String?,
    val album: String?,
    val dateAddedSeconds: Long
)

/** Scores only local library metadata and on-device listening history; no network calls. */
internal fun buildLocalRecommendations(
    tracks: List<LocalRecommendationTrack>,
    history: List<PlaybackHistoryEntry>,
    favoriteUris: Set<String>,
    limit: Int = 40
): List<LocalRecommendationTrack> {
    if (limit <= 0) return emptyList()
    val historyByUri = history.associateBy { it.uri }
    val artistPlayCounts = history
        .mapNotNull { entry ->
            entry.artist?.trim()?.lowercase()?.takeIf { it.isNotBlank() }?.let { it to entry.playCount.coerceAtLeast(0) }
        }
        .groupBy({ it.first }, { it.second })
        .mapValues { (_, counts) -> counts.sum().coerceAtMost(10_000) }
    val favoriteArtists = tracks
        .filter { it.uri in favoriteUris }
        .mapNotNull { it.artist?.trim()?.lowercase()?.takeIf { artist -> artist.isNotBlank() } }
        .toSet()

    return tracks.asSequence()
        .filter { it.uri.isNotBlank() && it.title.isNotBlank() }
        .distinctBy { it.uri }
        .sortedWith(
            compareByDescending<LocalRecommendationTrack> { track ->
                val artist = track.artist?.trim()?.lowercase().orEmpty()
                val historyEntry = historyByUri[track.uri]
                (if (track.uri in favoriteUris) 1_000 else 0) +
                    (if (artist.isNotBlank() && artist in favoriteArtists) 300 else 0) +
                    (artistPlayCounts[artist] ?: 0) * 10 +
                    (if (historyEntry == null) 50 else 0)
            }.thenByDescending { it.dateAddedSeconds }
                .thenBy { it.title.lowercase() }
        )
        .take(limit)
        .toList()
}
''', encoding="utf-8")

(PKG / "PartyModeScreen.kt").write_text('''package com.chiyuri.player

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
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Shuffle
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
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
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

@Composable
internal fun PlaybackPreferencesCard() {
    val context = LocalContext.current
    var preferences by remember(context) { mutableStateOf(PlaybackPreferencesStore.load(context)) }
    androidx.compose.runtime.DisposableEffect(context) {
        val store = context.getSharedPreferences(PlaybackPreferencesStore.PREFERENCES_NAME, android.content.Context.MODE_PRIVATE)
        val listener = android.content.SharedPreferences.OnSharedPreferenceChangeListener { _, _ ->
            preferences = PlaybackPreferencesStore.load(context)
        }
        store.registerOnSharedPreferenceChangeListener(listener)
        onDispose { store.unregisterOnSharedPreferenceChangeListener(listener) }
    }
    Surface(
        color = MaterialTheme.colorScheme.surface,
        shape = MaterialTheme.shapes.large,
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Настройки воспроизведения", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onSurface)
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Gapless Playback", color = MaterialTheme.colorScheme.onSurface)
                    Text("Переход между совместимыми композициями без намеренной паузы", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Switch(
                    checked = preferences.gaplessPlayback,
                    onCheckedChange = { enabled ->
                        preferences = preferences.copy(gaplessPlayback = enabled)
                        PlaybackPreferencesStore.save(context, preferences)
                    }
                )
            }
        }
    }
}

@Composable
internal fun PartyModeScreen(player: Player, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    var refreshToken by remember { mutableStateOf(0) }
    var loading by remember { mutableStateOf(true) }
    var recommendations by remember { mutableStateOf<List<LocalRecommendationTrack>>(emptyList()) }
    LaunchedEffect(context, refreshToken) {
        loading = true
        val data = withContext(Dispatchers.IO) {
            val library = LocalMediaRepository.loadAudio(context).ifEmpty {
                LocalMediaRepository.loadCached(context, false)
            }
            buildLocalRecommendations(
                tracks = library.map { item ->
                    LocalRecommendationTrack(
                        uri = item.uri.toString(),
                        title = item.title,
                        artist = item.artist,
                        album = item.album,
                        dateAddedSeconds = item.dateAddedSeconds
                    )
                },
                history = PlaybackHistoryStore.load(context),
                favoriteUris = FavoriteTracksStore.load(context),
                limit = 80
            )
        }
        recommendations = data
        loading = false
    }

    fun startMix() {
        val items = recommendations.map { track ->
            MediaItem.Builder()
                .setUri(track.uri)
                .setMediaMetadata(MediaMetadata.Builder()
                    .setTitle(track.title)
                    .setArtist(track.artist)
                    .setAlbumTitle(track.album)
                    .build())
                .build()
        }
        if (items.isEmpty()) return
        player.setMediaItems(items, 0, 0L)
        player.shuffleModeEnabled = true
        player.repeatMode = Player.REPEAT_MODE_ALL
        player.prepare()
        player.play()
    }

    Column(modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("Локальные рекомендации", style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.onSurface)
        Text(
            "Подборка рассчитывается на устройстве по избранному, истории прослушивания, исполнителям и недавно добавленным файлам. Данные никуда не отправляются.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = ::startMix, enabled = !loading && recommendations.isNotEmpty()) {
                androidx.compose.material3.Icon(Icons.Default.Shuffle, contentDescription = null)
                Text(" Начать вечеринку")
            }
            Button(onClick = { refreshToken++ }, enabled = !loading) {
                androidx.compose.material3.Icon(Icons.Default.AutoAwesome, contentDescription = null)
                Text(" Обновить")
            }
        }
        Text(
            if (loading) "Сканирование медиатеки…" else "В подборке: ${recommendations.size} композиций",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        if (!loading && recommendations.isEmpty()) {
            Text("Не удалось найти локальные аудиофайлы. Сначала добавь музыку в медиатеку.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            items(recommendations, key = { it.uri }) { track ->
                Surface(color = MaterialTheme.colorScheme.surface, shape = MaterialTheme.shapes.medium) {
                    Column(
                        Modifier.fillMaxWidth().clickable {
                            val item = MediaItem.Builder().setUri(track.uri)
                                .setMediaMetadata(MediaMetadata.Builder().setTitle(track.title).setArtist(track.artist).setAlbumTitle(track.album).build())
                                .build()
                            player.setMediaItem(item)
                            player.prepare()
                            player.play()
                        }.padding(horizontal = 12.dp, vertical = 10.dp)
                    ) {
                        Text(track.title, color = MaterialTheme.colorScheme.onSurface, maxLines = 1)
                        Text(listOfNotNull(track.artist, track.album).joinToString(" • "), color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall, maxLines = 1)
                    }
                }
            }
        }
    }
}
''', encoding="utf-8")

# Apply the gapless policy immediately and while the setting is changed in-app.
p = PKG / "PlaybackService.kt"
s = p.read_text(encoding="utf-8")
anchor = """        player.setHandleAudioBecomingNoisy(true)
        audioEffectsController = AudioEffectsController(this, player)"""
replacement = """        player.setHandleAudioBecomingNoisy(true)
        player.setPauseAtEndOfMediaItems(!PlaybackPreferencesStore.load(this).gaplessPlayback)
        val playbackPreferences = getSharedPreferences(PlaybackPreferencesStore.PREFERENCES_NAME, MODE_PRIVATE)
        val playbackPreferencesListener = android.content.SharedPreferences.OnSharedPreferenceChangeListener { _, key ->
            if (key == PlaybackPreferencesStore.KEY_GAPLESS) {
                player.setPauseAtEndOfMediaItems(!PlaybackPreferencesStore.load(this).gaplessPlayback)
            }
        }
        playbackPreferences.registerOnSharedPreferenceChangeListener(playbackPreferencesListener)
        this.playbackPreferencesListener = playbackPreferencesListener
        audioEffectsController = AudioEffectsController(this, player)"""
if anchor not in s: raise SystemExit("patch_0449: player configuration anchor missing")
s = s.replace(anchor, replacement, 1)
s = s.replace("""    private var audioDeviceCallback: AudioDeviceCallback? = null
    private var pausedByOutputLoss = false""", """    private var audioDeviceCallback: AudioDeviceCallback? = null
    private var playbackPreferencesListener: android.content.SharedPreferences.OnSharedPreferenceChangeListener? = null
    private var pausedByOutputLoss = false""", 1)
s = s.replace("""        progressHandler.removeCallbacks(progressSaver)
        audioDeviceCallback?.let { callback ->""", """        progressHandler.removeCallbacks(progressSaver)
        playbackPreferencesListener?.let { listener ->
            getSharedPreferences(PlaybackPreferencesStore.PREFERENCES_NAME, MODE_PRIVATE)
                .unregisterOnSharedPreferenceChangeListener(listener)
        }
        playbackPreferencesListener = null
        audioDeviceCallback?.let { callback ->""", 1)
p.write_text(s, encoding="utf-8")

# Add the Android screen to the existing "More" navigation.
p = PKG / "MainActivity.kt"
s = p.read_text(encoding="utf-8")
replace_once(
    p,
    '''                        "История" -> PlaybackHistoryScreen(player, Modifier.weight(1f))
                        "SMB" -> SmbLibraryScreen(player, Modifier.weight(1f))''',
    '''                        "История" -> PlaybackHistoryScreen(player, Modifier.weight(1f))
                        "Микс" -> PartyModeScreen(player, Modifier.weight(1f))
                        "SMB" -> SmbLibraryScreen(player, Modifier.weight(1f))''',
    "More navigation route"
)
replace_once(
    p,
    '''                                ActionCard("История и подборки", "Недавно воспроизведённое, частые прослушивания и избранное", Icons.Default.History) { morePage = "История" }
                                ActionCard("Сетевые папки SMB"''',
    '''                                ActionCard("История и подборки", "Недавно воспроизведённое, частые прослушивания и избранное", Icons.Default.History) { morePage = "История" }
                                ActionCard("Рекомендации и вечеринка", "Локальный умный микс с перемешиванием и повтором", Icons.Default.AutoAwesome) { morePage = "Микс" }
                                ActionCard("Сетевые папки SMB"''',
    "More party mode action card"
)
replace_once(
    p,
    '''        AppearanceSettingsCard()
        AudioVisualizerScreen(player)''',
    '''        AppearanceSettingsCard()
        PlaybackPreferencesCard()
        AudioVisualizerScreen(player)''',
    "playback preferences card placement"
)

(TEST / "LocalRecommendationsTest.kt").write_text('''package com.chiyuri.player

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class LocalRecommendationsTest {
    private fun track(uri: String, title: String, artist: String?, added: Long = 0L) =
        LocalRecommendationTrack(uri, title, artist, null, added)

    private fun history(uri: String, artist: String?, count: Int) =
        PlaybackHistoryEntry(uri, uri, artist, 1000L, 100L, count)

    @Test fun favoritesAndFrequentlyPlayedArtistsInfluenceRanking() {
        val tracks = listOf(
            track("a", "Unplayed", "Artist A"),
            track("b", "Favorite", "Artist B"),
            track("c", "Related", "Artist A"),
            track("d", "Other", "Artist D")
        )
        val result = buildLocalRecommendations(
            tracks,
            listOf(history("old", "Artist A", 8)),
            setOf("b")
        )
        assertEquals("Favorite", result.first().title)
        assertTrue(result.indexOfFirst { it.title == "Related" } < result.indexOfFirst { it.title == "Other" })
    }

    @Test fun invalidDuplicatesAndLimitsAreHandled() {
        val tracks = listOf(
            track("a", "Song", "Artist"),
            track("a", "Duplicate", "Artist"),
            track("", "Invalid", "Artist"),
            track("b", "", "Artist")
        )
        assertEquals(listOf("a"), buildLocalRecommendations(tracks, emptyList(), emptySet()).map { it.uri })
        assertTrue(buildLocalRecommendations(tracks, emptyList(), emptySet(), limit = 0).isEmpty())
    }

    @Test fun recentAdditionsBreakEqualScoresDeterministically() {
        val tracks = listOf(track("old", "Old", null, 10L), track("new", "New", null, 20L))
        assertEquals(listOf("new", "old"), buildLocalRecommendations(tracks, emptyList(), emptySet()).map { it.uri })
    }
}
''', encoding="utf-8")

print("patch_0449: gapless playback preference, local recommendations and party mix applied")
