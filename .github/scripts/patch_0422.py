from pathlib import Path

ROOT = Path("app/src/main/java/com/chiyuri/player")

def replace_once(path: Path, old: str, new: str, label: str):
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match in {path}, found {count}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

settings = ROOT / "AudioEffectsSettings.kt"
replace_once(settings, "playerVolume = bounded(config.playerVolume, 1f, 2f, 1f)", "playerVolume = bounded(config.playerVolume, 1f, 3f, 1f)", "player volume normalization ceiling")
replace_once(settings, "playerVolume.coerceIn(1f, 2f)", "playerVolume.coerceIn(1f, 3f)", "loudness enhancer multiplier ceiling")
replace_once(settings, "(2000f * kotlin.math.log10(multiplier)).roundToInt().coerceIn(0, 602)", "(2000f * kotlin.math.log10(multiplier)).roundToInt().coerceIn(0, 954)", "loudness enhancer gain ceiling")

main = ROOT / "MainActivity.kt"
replace_once(main, "val boost = (config.playerVolume + 0.1f).coerceAtMost(2f)", "val boost = (config.playerVolume + 0.1f).coerceAtMost(3f)", "hardware volume key ceiling")
replace_once(main, 'Text("${(config.playerVolume * 100f).roundToInt()}%", color = MaterialTheme.colorScheme.primary)', 'Text("+${((config.playerVolume - 1f) * 100f).roundToInt()}%", color = MaterialTheme.colorScheme.primary)', "volume boost percentage label")
replace_once(main, "(config.playerVolume - 1f).coerceIn(0f, 1f)", "(config.playerVolume - 1f).coerceIn(0f, 2f)", "volume slider current range")
replace_once(main, "valueRange = 0f..1f,\n                    steps = 19", "valueRange = 0f..2f,\n                    steps = 39", "volume slider maximum")
replace_once(main,
    '"Единая шкала: системная громкость до 100%, усиление плеера до 200% от текущего уровня. Общий предел плеера — 2x. Кнопки громкости телефона управляют обоими уровнями.",',
    '"Системная громкость телефона — до 100%; дополнительное усиление плеера — до +200% (до 300% общей громкости, 3x). Кнопки громкости телефона управляют обоими уровнями.",',
    "volume boost description")

indicator = ROOT / "VolumeIndicator.kt"
source = indicator.read_text(encoding="utf-8")
boost_bound = "((AudioEffectsSettings.load(context).playerVolume - 1f) * 100f)\n                .roundToInt().coerceIn(0, 100)"
if source.count(boost_bound) != 2 or source.count("boostPercent / 100f") != 1:
    raise SystemExit("Unexpected VolumeIndicator baseline; refusing unsafe volume range patch.")
source = source.replace(boost_bound, boost_bound.replace("coerceIn(0, 100)", "coerceIn(0, 200)"))
source = source.replace("boostPercent / 100f", "boostPercent / 200f")
indicator.write_text(source, encoding="utf-8")

tests = Path("app/src/test/java/com/chiyuri/player/PlaceholderTest.kt")
replace_once(tests, "assertEquals(2f, normalized.playerVolume, 0f)\n        assertEquals(true, normalized.equalizerEnabled)", "assertEquals(2.5f, normalized.playerVolume, 0f)\n        assertEquals(true, normalized.equalizerEnabled)", "volume normalization test expectation")
replace_once(tests, "fun boostIsClampedToTwoHundredPercentTotal()", "fun boostIsClampedToTwoHundredPercentAboveBaseVolume()", "volume boost test name")
replace_once(tests,
    "assertEquals(2f, normalized.playerVolume, 0f)\n    }\n\n    @Test\n    fun mapsVolumeBoostToLoudnessEnhancerGain()",
    "assertEquals(3f, normalized.playerVolume, 0f)\n    }\n\n    @Test\n    fun mapsVolumeBoostToLoudnessEnhancerGain()",
    "volume +200 percent clamp expectation")
replace_once(tests, "assertEquals(602, volumeBoostToMillibels(3f))", "assertEquals(954, volumeBoostToMillibels(3f))", "3x loudness enhancer gain expectation")

replace_once(main,
    "    val currentTrackUri = player.currentMediaItem?.localConfiguration?.uri\n    var isFavorite by remember(currentTrackUri) {",
    "    val currentTrackUri = player.currentMediaItem?.localConfiguration?.uri\n    var playlistTrackIds by remember(currentTrackUri) { mutableStateOf<Map<Long, Long>>(emptyMap()) }\n    var isFavorite by remember(currentTrackUri) {",
    "playlist membership state")
replace_once(main,
    "    DisposableEffect(playlistRepository) {\n        onDispose { playlistRepository.close() }\n    }\n\n    fun addCurrentTrackToPlaylist",
    """    DisposableEffect(playlistRepository) {
        onDispose { playlistRepository.close() }
    }

    suspend fun refreshPlaylistPicker() {
        val uriString = player.currentMediaItem?.localConfiguration?.uri?.toString()
        val snapshot = withContext(Dispatchers.IO) {
            val playlists = playlistRepository.getPlaylists()
            val memberships = if (uriString == null) emptyMap() else playlists.mapNotNull { playlist ->
                playlistRepository.getTracks(playlist.id)
                    .firstOrNull { it.uri == uriString }
                    ?.let { playlist.id to it.id }
            }.toMap()
            playlists to memberships
        }
        availablePlaylists = snapshot.first
        playlistTrackIds = snapshot.second
    }

    fun removeCurrentTrackFromPlaylist(playlist: Playlist, trackId: Long) {
        scope.launch {
            val removed = withContext(Dispatchers.IO) { playlistRepository.removeTrack(trackId) }
            if (removed) {
                android.widget.Toast.makeText(
                    context,
                    "Трек удалён из «\x24{playlist.name}»",
                    android.widget.Toast.LENGTH_SHORT
                ).show()
                refreshPlaylistPicker()
            } else {
                playlistDialogError = "Не удалось удалить трек из плейлиста."
            }
        }
    }

    fun addCurrentTrackToPlaylist""",
    "playlist picker membership refresh and removal action")
replace_once(main,
    "                availablePlaylists = withContext(Dispatchers.IO) { playlistRepository.getPlaylists() }\n                showPlaylistDialog = false\n                createPlaylistMode = false",
    "                refreshPlaylistPicker()\n                createPlaylistMode = false",
    "keep playlist picker open after adding")
replace_once(main,
    "                        scope.launch {\n                            availablePlaylists = withContext(Dispatchers.IO) { playlistRepository.getPlaylists() }\n                        }",
    "                        scope.launch { refreshPlaylistPicker() }",
    "load membership on picker open")
replace_once(main,
    """                        availablePlaylists.forEach { playlist ->
                            TextButton(
                                onClick = { addCurrentTrackToPlaylist(playlist.id) },
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                GothicIcon(Icons.Default.QueueMusic, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                                Spacer(Modifier.width(10.dp))
                                Column(Modifier.weight(1f)) {
                                    Text(playlist.name, maxLines = 1)
                                    Text("\x24{playlist.trackCount} трек(ов)", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }
                        }""",
    """                        availablePlaylists.forEach { playlist ->
                            val currentEntryId = playlistTrackIds[playlist.id]
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                TextButton(
                                    onClick = { addCurrentTrackToPlaylist(playlist.id) },
                                    enabled = currentEntryId == null,
                                    modifier = Modifier.weight(1f)
                                ) {
                                    GothicIcon(
                                        if (currentEntryId == null) Icons.Default.QueueMusic else Icons.Default.Check,
                                        contentDescription = null,
                                        tint = MaterialTheme.colorScheme.primary
                                    )
                                    Spacer(Modifier.width(10.dp))
                                    Column(Modifier.weight(1f)) {
                                        Text(playlist.name, maxLines = 1)
                                        Text(
                                            if (currentEntryId == null) "\x24{playlist.trackCount} трек(ов) · Добавить текущий" else "\x24{playlist.trackCount} трек(ов) · Текущий трек здесь",
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }
                                }
                                if (currentEntryId != null) {
                                    GothicIconButton(
                                        onClick = { removeCurrentTrackFromPlaylist(playlist, currentEntryId) }
                                    ) {
                                        GothicIcon(
                                            Icons.Default.Close,
                                            contentDescription = "Удалить текущий трек из плейлиста \x24{playlist.name}",
                                            tint = MaterialTheme.colorScheme.error
                                        )
                                    }
                                }
                            }
                        }""",
    "mini-player playlist add/remove rows")

gradle = Path("app/build.gradle.kts")
replace_once(gradle,
    'versionCode = providers.gradleProperty("VERSION_CODE").orElse("332").get().toInt()',
    'versionCode = providers.gradleProperty("VERSION_CODE").orElse("333").get().toInt()',
    "Gradle versionCode fallback")

print("Mini-player playlist removal and +200% player gain applied.")
