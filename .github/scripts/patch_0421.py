from pathlib import Path

p = Path("app/src/main/java/com/chiyuri/player")

# Publish database mutations so an already-open Playlists screen refreshes immediately.
r = p / "PlaylistRepository.kt"
s = r.read_text(encoding="utf-8")
if "MutableStateFlow" not in s:
    s = s.replace("import android.net.Uri\n", "import android.net.Uri\nimport kotlinx.coroutines.flow.MutableStateFlow\n")

def replace_once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return source.replace(old, new, 1)

s = replace_once(
    s,
    """        return id.takeIf { it > 0L }
    }

    fun renamePlaylist""",
    """        if (id > 0L) revision.value = revision.value + 1L
        return id.takeIf { it > 0L }
    }

    fun renamePlaylist""",
    "playlist creation revision"
)
s = replace_once(
    s,
    """        return try {
            writableDatabase.update(
                "playlists",
                values,
                "id = ?",
                arrayOf(playlistId.toString())
            ) > 0
        } catch (_: SQLiteConstraintException) {
            false
        }
    }

    fun deletePlaylist""",
    """        return try {
            val updated = writableDatabase.update(
                "playlists",
                values,
                "id = ?",
                arrayOf(playlistId.toString())
            ) > 0
            if (updated) revision.value = revision.value + 1L
            updated
        } catch (_: SQLiteConstraintException) {
            false
        }
    }

    fun deletePlaylist""",
    "playlist rename revision"
)
s = replace_once(
    s,
    """    fun deletePlaylist(playlistId: Long): Boolean =
        writableDatabase.delete(
            "playlists",
            "id = ?",
            arrayOf(playlistId.toString())
        ) > 0
""",
    """    fun deletePlaylist(playlistId: Long): Boolean {
        val deleted = writableDatabase.delete(
            "playlists",
            "id = ?",
            arrayOf(playlistId.toString())
        ) > 0
        if (deleted) revision.value = revision.value + 1L
        return deleted
    }
""",
    "playlist deletion revision"
)
s = replace_once(
    s,
    """        return writableDatabase.insertWithOnConflict(
            "playlist_tracks",
            null,
            values,
            SQLiteDatabase.CONFLICT_IGNORE
        ) > 0L
    }

    fun removeTrack(trackId: Long): Boolean =
        writableDatabase.delete(
            "playlist_tracks",
            "id = ?",
            arrayOf(trackId.toString())
        ) > 0

    companion object {
        private const val DATABASE_NAME = "chiyuri_library.db"
        private const val DATABASE_VERSION = 1
    }
""",
    """        val inserted = writableDatabase.insertWithOnConflict(
            "playlist_tracks",
            null,
            values,
            SQLiteDatabase.CONFLICT_IGNORE
        ) > 0L
        if (inserted) revision.value = revision.value + 1L
        return inserted
    }

    fun removeTrack(trackId: Long): Boolean {
        val deleted = writableDatabase.delete(
            "playlist_tracks",
            "id = ?",
            arrayOf(trackId.toString())
        ) > 0
        if (deleted) revision.value = revision.value + 1L
        return deleted
    }

    companion object {
        internal val revision = MutableStateFlow(0L)
        private const val DATABASE_NAME = "chiyuri_library.db"
        private const val DATABASE_VERSION = 1
    }
""",
    "playlist track mutation revision"
)
r.write_text(s, encoding="utf-8")

# Refresh both playlist counts and the open playlist's tracks after external changes.
m = p / "MainActivity.kt"
s = m.read_text(encoding="utf-8")
s = replace_once(
    s,
    """    LaunchedEffect(repository) {
        refreshPlaylists()
    }
""",
    """    val playlistRevision by PlaylistRepository.revision.collectAsState()
    LaunchedEffect(repository, playlistRevision) {
        refreshPlaylists()
        selectedPlaylist?.id?.let(::refreshTracks)
    }
""",
    "reactive playlist screen refresh"
)

# Add mini-player actions and their picker state.
s = replace_once(
    s,
    """    playbackSpeed: Float,
    onPlaybackSpeedChange: (Float) -> Unit
) {
    Surface(
""",
    """    playbackSpeed: Float,
    onPlaybackSpeedChange: (Float) -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val playlistRepository = remember(context) { PlaylistRepository(context) }
    var showPlaylistDialog by remember { mutableStateOf(false) }
    var availablePlaylists by remember { mutableStateOf<List<Playlist>>(emptyList()) }
    var createPlaylistMode by remember { mutableStateOf(false) }
    var newPlaylistName by remember { mutableStateOf("") }
    var playlistDialogError by remember { mutableStateOf<String?>(null) }
    val currentTrackUri = player.currentMediaItem?.localConfiguration?.uri
    var isFavorite by remember(currentTrackUri) {
        mutableStateOf(currentTrackUri?.let { FavoriteTracksStore.contains(context, it) } ?: false)
    }
    DisposableEffect(playlistRepository) {
        onDispose { playlistRepository.close() }
    }

    fun addCurrentTrackToPlaylist(playlistId: Long, createName: String? = null) {
        val uri = player.currentMediaItem?.localConfiguration?.uri
        if (uri == null) {
            playlistDialogError = "Сейчас нет воспроизводимого аудиофайла."
            return
        }
        val mediaMetadata = player.currentMediaItem?.mediaMetadata
        val trackTitle = mediaMetadata?.title?.toString()?.takeIf { it.isNotBlank() } ?: title
        val trackArtist = mediaMetadata?.artist?.toString()?.takeIf { it.isNotBlank() } ?: artist
        val duration = player.duration.takeIf { it > 0L } ?: 0L
        val mimeType = runCatching { context.contentResolver.getType(uri) }.getOrNull()
        scope.launch {
            val result = withContext(Dispatchers.IO) {
                val targetId = if (createName != null) playlistRepository.createPlaylist(createName) else playlistId
                if (targetId == null) null else targetId to playlistRepository.addTrack(
                    playlistId = targetId,
                    uri = uri,
                    title = trackTitle,
                    artist = trackArtist.takeIf { it.isNotBlank() },
                    durationMs = duration,
                    mimeType = mimeType
                )
            }
            if (result == null) {
                playlistDialogError = "Не удалось создать плейлист. Проверь название: оно должно быть уникальным и не длиннее 80 символов."
            } else {
                val (targetId, added) = result
                val targetName = withContext(Dispatchers.IO) {
                    playlistRepository.getPlaylists().firstOrNull { it.id == targetId }?.name
                }
                android.widget.Toast.makeText(
                    context,
                    if (added) "«${trackTitle}» добавлен в «${targetName ?: "плейлист"}»" else "Этот трек уже есть в «${targetName ?: "плейлисте"}»",
                    android.widget.Toast.LENGTH_SHORT
                ).show()
                availablePlaylists = withContext(Dispatchers.IO) { playlistRepository.getPlaylists() }
                showPlaylistDialog = false
                createPlaylistMode = false
                newPlaylistName = ""
                playlistDialogError = null
            }
        }
    }

    Surface(
""",
    "mini-player playlist state"
)

s = replace_once(
    s,
    """                Column(Modifier.weight(1f)) {
                    Text(title, maxLines = 1, color = MaterialTheme.colorScheme.onSurface)
                    Text(artist.ifBlank { if (playing) "Воспроизводится" else "Пауза" }, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 12.sp, maxLines = 1)
                }
                GothicIcon(Icons.Default.ExpandLess.takeIf { expanded } ?: Icons.Default.ExpandMore, contentDescription = if (expanded) "Свернуть плеер" else "Развернуть плеер", tint = MaterialTheme.colorScheme.onSurfaceVariant)
""",
    """                Column(Modifier.weight(1f)) {
                    Text(title, maxLines = 1, color = MaterialTheme.colorScheme.onSurface)
                    Text(artist.ifBlank { if (playing) "Воспроизводится" else "Пауза" }, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 12.sp, maxLines = 1)
                }
                GothicIconButton(
                    onClick = {
                        currentTrackUri?.let { uri ->
                            isFavorite = FavoriteTracksStore.toggle(context, uri).contains(uri.toString())
                        }
                    },
                    enabled = currentTrackUri != null
                ) {
                    GothicIcon(
                        if (isFavorite) Icons.Default.Favorite else Icons.Default.FavoriteBorder,
                        contentDescription = if (isFavorite) "Убрать из избранного" else "Добавить в избранное",
                        tint = if (isFavorite) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface
                    )
                }
                GothicIconButton(
                    onClick = {
                        playlistDialogError = null
                        createPlaylistMode = false
                        newPlaylistName = ""
                        showPlaylistDialog = true
                        scope.launch {
                            availablePlaylists = withContext(Dispatchers.IO) { playlistRepository.getPlaylists() }
                        }
                    },
                    enabled = currentTrackUri != null
                ) {
                    GothicIcon(Icons.Default.PlaylistAdd, contentDescription = "Добавить трек в плейлист", tint = MaterialTheme.colorScheme.primary)
                }
                GothicIcon(Icons.Default.ExpandLess.takeIf { expanded } ?: Icons.Default.ExpandMore, contentDescription = if (expanded) "Свернуть плеер" else "Развернуть плеер", tint = MaterialTheme.colorScheme.onSurfaceVariant)
""",
    "mini-player favorite and playlist buttons"
)

s = replace_once(
    s,
    """}

@Composable
private fun AudioEffectsScreen(player: Player, modifier: Modifier = Modifier) {
""",
    """    if (showPlaylistDialog) {
        AlertDialog(
            onDismissRequest = { showPlaylistDialog = false },
            title = { Text("Добавить в плейлист") },
            text = {
                Column(
                    modifier = Modifier.fillMaxWidth().heightIn(max = 420.dp).verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    if (availablePlaylists.isEmpty()) {
                        Text("Плейлистов пока нет. Создай новый, чтобы сохранить этот трек.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    } else {
                        availablePlaylists.forEach { playlist ->
                            TextButton(
                                onClick = { addCurrentTrackToPlaylist(playlist.id) },
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                GothicIcon(Icons.Default.QueueMusic, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                                Spacer(Modifier.width(10.dp))
                                Column(Modifier.weight(1f)) {
                                    Text(playlist.name, maxLines = 1)
                                    Text("${playlist.trackCount} трек(ов)", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }
                        }
                    }
                    HorizontalDivider()
                    if (createPlaylistMode) {
                        OutlinedTextField(
                            value = newPlaylistName,
                            onValueChange = { newPlaylistName = it },
                            label = { Text("Название плейлиста") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )
                        TextButton(
                            onClick = { addCurrentTrackToPlaylist(0L, newPlaylistName) },
                            enabled = newPlaylistName.trim().isNotEmpty(),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            GothicIcon(Icons.Default.Add, contentDescription = null)
                            Spacer(Modifier.width(6.dp))
                            Text("Создать и добавить трек")
                        }
                    } else {
                        TextButton(
                            onClick = { createPlaylistMode = true },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            GothicIcon(Icons.Default.Add, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                            Spacer(Modifier.width(8.dp))
                            Text("Создать новый плейлист")
                        }
                    }
                    playlistDialogError?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
                }
            },
            confirmButton = {
                TextButton(onClick = { showPlaylistDialog = false }) { Text("Готово") }
            }
        )
    }
}

@Composable
private fun AudioEffectsScreen(player: Player, modifier: Modifier = Modifier) {
""",
    "mini-player playlist picker dialog"
)
m.write_text(s, encoding="utf-8")

# Keep the Gradle fallback in sync with the next release.
gradle = Path("app/build.gradle.kts")
gradle_source = gradle.read_text(encoding="utf-8")
gradle_source = replace_once(
    gradle_source,
    'versionCode = providers.gradleProperty("VERSION_CODE").orElse("331").get().toInt()',
    'versionCode = providers.gradleProperty("VERSION_CODE").orElse("332").get().toInt()',
    "Gradle versionCode fallback"
)
gradle.write_text(gradle_source, encoding="utf-8")

# Unit tests cover the same playlist-name rules used by both create flows.
test_path = Path("app/src/test/java/com/chiyuri/player/PlaylistNameValidationTest.kt")
test_path.parent.mkdir(parents=True, exist_ok=True)
test_path.write_text("""package com.chiyuri.player

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class PlaylistNameValidationTest {
    @Test fun trimsPlaylistNames() {
        assertEquals("Road Trip", normalizePlaylistName("  Road Trip  "))
    }

    @Test fun rejectsBlankAndOverlongPlaylistNames() {
        assertNull(normalizePlaylistName("   "))
        assertNull(normalizePlaylistName("x".repeat(81)))
    }

    @Test fun acceptsMaximumLengthPlaylistName() {
        assertEquals(80, normalizePlaylistName("x".repeat(80))?.length)
    }
}
""", encoding="utf-8")

print("Mini-player playlist picker, favorites control and reactive playlist refresh applied.")
