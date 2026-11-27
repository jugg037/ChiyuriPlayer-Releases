from pathlib import Path

def replace_once(path: Path, old: str, new: str, label: str):
    source = path.read_text(encoding="utf-8")
    if old not in source:
        raise SystemExit(f"patch_0450: missing {label}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

PKG = Path("app/src/main/java/com/chiyuri/player")
TEST = Path("app/src/test/java/com/chiyuri/player")
# Keep the global baseline separate from the active device profile.
settings = PKG / "AudioEffectsSettings.kt"
settingsSource = settings.read_text(encoding="utf-8")
if "internal fun saveGlobal(context: Context, config: AudioEffectsConfig)" not in settingsSource:
    anchor = "    fun save(context: Context, config: AudioEffectsConfig) {"
    if anchor not in settingsSource:
        raise SystemExit("patch_0450: global audio settings save anchor missing")
    globalSave = """    internal fun saveGlobal(context: Context, config: AudioEffectsConfig) {
        val normalized = normalizeAudioEffectsConfig(config)
        context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE).edit {
            putBoolean(KEY_EQUALIZER_ENABLED, normalized.equalizerEnabled)
            putFloat(KEY_PLAYER_VOLUME, normalized.playerVolume)
            putBoolean(KEY_REPLAYGAIN_ENABLED, normalized.replayGainEnabled)
            normalized.bandsDb.forEachIndexed { index, value ->
                putFloat(KEY_BAND_PREFIX + index, value)
            }
        }
    }

"""
    settingsSource = settingsSource.replace(anchor, globalSave + anchor, 1)
    settings.write_text(settingsSource, encoding="utf-8")

p = PKG / "LibraryBackupManager.kt"
s = p.read_text(encoding="utf-8")

s = s.replace(
'''    val radioStationsRestored: Int
)''',
'''    val radioStationsRestored: Int,
    val historyEntriesRestored: Int = 0,
    val audioProfilesRestored: Int = 0,
    val playbackPreferencesRestored: Boolean = false
)''',
1
)

anchor = '''        var playlistsRestored = 0
        var tracksRestored = 0'''
insert = '''        val historyArray = json.optJSONArray("playback_history")
        val historyRestored = if (historyArray != null) {
            val safeHistory = sanitizePlaybackHistory(historyArray)
            context.getSharedPreferences("playback_history", Context.MODE_PRIVATE).edit {
                putString("entries", safeHistory.toString())
            }
            safeHistory.length()
        } else 0

        val profilesObject = json.optJSONObject("audio_output_profiles")
        val profilesRestored = if (profilesObject != null) {
            val safeProfiles = sanitizeAudioOutputProfiles(profilesObject)
            context.getSharedPreferences(AudioOutputProfiles.PREFERENCES_NAME, Context.MODE_PRIVATE).edit {
                putString("profiles", safeProfiles.toString())
            }
            safeProfiles.length()
        } else 0

        val playbackPreferencesObject = json.optJSONObject("playback_preferences")
        val playbackPreferencesRestored = playbackPreferencesObject != null
        if (playbackPreferencesObject != null) {
            PlaybackPreferencesStore.save(
                context,
                PlaybackPreferences(gaplessPlayback = playbackPreferencesObject.optBoolean("gapless_playback", true))
            )
        }

        var playlistsRestored = 0
        var tracksRestored = 0'''
if anchor not in s: raise SystemExit("patch_0450: restore insertion anchor missing")
s = s.replace(anchor, insert, 1)

replace_once(
    p,
    "return BackupRestoreSummary(playlistsRestored, tracksRestored, favorites.size, presetsRestored, stationsRestored)",
    "return BackupRestoreSummary(playlistsRestored, tracksRestored, favorites.size, presetsRestored, stationsRestored, historyRestored, profilesRestored, playbackPreferencesRestored)",
    "backup restore summary"
)

anchor = '''        val playlists = JSONArray()
        PlaylistRepository(context).use { repository ->'''
insert = '''        val history = JSONArray()
        PlaybackHistoryStore.load(context).filter { isAllowedBackupUri(it.uri) }.take(100).forEach { entry ->
            history.put(JSONObject()
                .put("uri", entry.uri)
                .put("title", entry.title.take(200))
                .put("artist", entry.artist?.take(200) ?: JSONObject.NULL)
                .put("duration_ms", entry.durationMs.coerceIn(0L, 86_400_000L))
                .put("last_played_at", entry.lastPlayedAt.coerceAtLeast(0L))
                .put("play_count", entry.playCount.coerceIn(1, 100_000)))
        }
        val outputProfiles = runCatching {
            JSONObject(context.getSharedPreferences(AudioOutputProfiles.PREFERENCES_NAME, Context.MODE_PRIVATE)
                .getString("profiles", "{}") ?: "{}")
        }.getOrDefault(JSONObject())
        val safeOutputProfiles = sanitizeAudioOutputProfiles(outputProfiles)
        val playbackPreferences = JSONObject()
            .put("gapless_playback", PlaybackPreferencesStore.load(context).gaplessPlayback)

        val playlists = JSONArray()
        PlaylistRepository(context).use { repository ->'''
if anchor not in s: raise SystemExit("patch_0450: export insertion anchor missing")
s = s.replace(anchor, insert, 1)

anchor = '''            .put("radio_stations", stations)
            .put("playlists", playlists)'''
replacement = '''            .put("radio_stations", stations)
            .put("playback_history", history)
            .put("audio_output_profiles", safeOutputProfiles)
            .put("playback_preferences", playbackPreferences)
            .put("playlists", playlists)'''
if anchor not in s: raise SystemExit("patch_0450: export JSON anchor missing")
s = s.replace(anchor, replacement, 1)

# Insert bounded, credential-free sanitizers before the existing ZIP byte limiter.
anchor = '''    private fun InputStream.readBytesLimited(limit: Int): ByteArray {'''
helpers = '''    internal fun sanitizePlaybackHistory(raw: JSONArray): JSONArray {
        val safe = JSONArray()
        for (index in 0 until minOf(raw.length(), 100)) {
            val item = raw.optJSONObject(index) ?: continue
            val uri = item.optString("uri")
            if (!isAllowedBackupUri(uri)) continue
            val title = item.optString("title").take(200).ifBlank { "Без названия" }
            val artist = item.optString("artist").take(200)
            safe.put(JSONObject()
                .put("uri", uri)
                .put("title", title)
                .put("artist", if (artist.isBlank()) JSONObject.NULL else artist)
                .put("duration_ms", item.optLong("duration_ms", 0L).coerceIn(0L, 86_400_000L))
                .put("last_played_at", item.optLong("last_played_at", 0L).coerceAtLeast(0L))
                .put("play_count", item.optInt("play_count", 1).coerceIn(1, 100_000)))
        }
        return safe
    }

    internal fun sanitizeAudioOutputProfiles(raw: JSONObject): JSONObject {
        val safe = JSONObject()
        val keys = raw.keys()
        var accepted = 0
        while (keys.hasNext() && accepted < 20) {
            val key = keys.next()
            if (!key.matches(Regex("^[0-9]+_[a-z0-9а-я_-]{1,48}$"))) continue
            val item = raw.optJSONObject(key) ?: continue
            val bands = item.optJSONArray("bands") ?: JSONArray()
            val config = normalizeAudioEffectsConfig(AudioEffectsConfig(
                equalizerEnabled = item.optBoolean("equalizer_enabled", false),
                bandsDb = (0 until minOf(bands.length(), 10)).map { bands.optDouble(it, 0.0).toFloat() },
                playerVolume = item.optDouble("player_volume", 1.0).toFloat(),
                replayGainEnabled = item.optBoolean("replay_gain_enabled", true)
            ))
            safe.put(key, JSONObject()
                .put("equalizer_enabled", config.equalizerEnabled)
                .put("player_volume", config.playerVolume)
                .put("replay_gain_enabled", config.replayGainEnabled)
                .put("bands", JSONArray(config.bandsDb)))
            accepted++
        }
        return safe
    }

'''
if anchor not in s: raise SystemExit("patch_0450: sanitizer insertion anchor missing")
s = s.replace(anchor, helpers + anchor, 1)
p.write_text(s, encoding="utf-8")

# Expand the user-facing restore summary and backup description.
p = PKG / "LibraryBackupCard.kt"
replace_once(
    p,
    'onSuccess = { "Восстановлено: ${it.playlistsRestored} плейлистов, ${it.tracksRestored} треков, ${it.favoritesRestored} избранных." }',
    'onSuccess = { "Восстановлено: ${it.playlistsRestored} плейлистов, ${it.tracksRestored} треков, ${it.favoritesRestored} избранных, ${it.historyEntriesRestored} записей истории, ${it.audioProfilesRestored} аудиопрофилей." }',
    "backup restore status"
)
replace_once(
    p,
    "Сохраняются плейлисты, избранное, пресеты эквалайзера, настройки звука и избранные радиостанции. Пароли сетевых серверов не экспортируются.",
    "Сохраняются плейлисты, избранное, история, пресеты и профили звука, ReplayGain, Gapless и радиостанции. Пароли сетевых серверов не экспортируются.",
    "backup description"
)

test = TEST / "LibraryBackupManagerTest.kt"
s = test.read_text(encoding="utf-8")
anchor = '''    @Test fun rejectsWhitespaceAndOversizedUris() {'''
insert = '''    @Test fun playbackHistoryExportFiltersUnsafeUrisAndBoundsFields() {
        val raw = org.json.JSONArray()
            .put(org.json.JSONObject()
                .put("uri", "content://media/audio/1")
                .put("title", "Song")
                .put("artist", "Artist")
                .put("duration_ms", Long.MAX_VALUE)
                .put("last_played_at", -1L)
                .put("play_count", 0))
            .put(org.json.JSONObject().put("uri", "https://user:pass@example.com/private.mp3"))
        val safe = LibraryBackupManager.sanitizePlaybackHistory(raw)
        assertEquals(1, safe.length())
        assertEquals(86_400_000L, safe.getJSONObject(0).getLong("duration_ms"))
        assertEquals(0L, safe.getJSONObject(0).getLong("last_played_at"))
        assertEquals(1, safe.getJSONObject(0).getInt("play_count"))
    }

    @Test fun outputProfilesAreNormalizedAndCredentialFree() {
        val raw = org.json.JSONObject().put("7_sony_wh-1000xm5", org.json.JSONObject()
            .put("player_volume", 9.0)
            .put("equalizer_enabled", true)
            .put("bands", org.json.JSONArray().put(99.0)))
            .put("../unsafe", org.json.JSONObject().put("password", "never-export"))
        val safe = LibraryBackupManager.sanitizeAudioOutputProfiles(raw)
        assertEquals(1, safe.length())
        val profile = safe.getJSONObject("7_sony_wh-1000xm5")
        assertEquals(2.0, profile.getDouble("player_volume"), 0.001)
        assertEquals(10, profile.getJSONArray("bands").length())
        assertFalse(profile.has("password"))
    }

'''
if anchor not in s: raise SystemExit("patch_0450: backup test insertion anchor missing")
s = s.replace(anchor, insert + anchor, 1)
test.write_text(s, encoding="utf-8")
if "class LibraryBackupManagerTest" not in test.read_text(encoding="utf-8"):
    raise SystemExit("patch_0450: backup regression tests were not written")
if "internal fun LibraryBackupCard()" not in (PKG / "LibraryBackupCard.kt").read_text(encoding="utf-8"):
    raise SystemExit("patch_0450: backup card source was unexpectedly modified")

print("patch_0450: backup and restore now include bounded history, per-device audio profiles and gapless preference without exporting credentials")
