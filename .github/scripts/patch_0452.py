from pathlib import Path

def replace_once(path: Path, old: str, new: str, label: str):
    source = path.read_text(encoding="utf-8")
    if old not in source:
        raise SystemExit(f"patch_0452: missing {label}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

PKG = Path("app/src/main/java/com/chiyuri/player")
TEST = Path("app/src/test/java/com/chiyuri/player")

# The five-band legacy curve is interpolated into ten bands; verify representative points with tolerance.
p = TEST / "PlaceholderTest.kt"
replace_once(
    p,
    "assertEquals(12f, normalized.bandsDb.last(), 0f)",
    "assertEquals(-12f, normalized.bandsDb[1], 0.001f)\n        assertEquals(-8.666666f, normalized.bandsDb[2], 0.001f)\n        assertEquals(-4f, normalized.bandsDb[3], 0.001f)\n        assertEquals(1.7777786f, normalized.bandsDb[5], 0.001f)\n        assertEquals(10.444446f, normalized.bandsDb[7], 0.001f)",
    "ten-band normalized legacy assertion"
)

# Restore the tonal curve from old five-band backups and profile records.
p = PKG / "LibraryBackupManager.kt"
s = p.read_text(encoding="utf-8")
s = s.replace(
    "bandsDb = (0 until bands.length()).map { bands.optDouble(it, 0.0).toFloat() },",
    "bandsDb = resampleEqualizerBands((0 until bands.length()).map { bands.optDouble(it, 0.0).toFloat() }, 10),",
    1
)
if "internal fun sanitizeBackupHistoryEntries" not in s:
    start = s.find("    internal fun sanitizePlaybackHistory(raw: JSONArray): JSONArray {")
    end = s.find("    private fun InputStream.readBytesLimited(limit: Int): ByteArray {", start)
    if start < 0 or end < 0:
        raise SystemExit("patch_0452: backup sanitizer block anchors missing")
    block = '''    internal fun sanitizePlaybackHistory(raw: JSONArray): JSONArray {
        val parsed = buildList {
            for (index in 0 until minOf(raw.length(), 100)) {
                val item = raw.optJSONObject(index) ?: continue
                add(PlaybackHistoryEntry(
                    uri = item.optString("uri"),
                    title = item.optString("title"),
                    artist = item.optString("artist").takeIf { it.isNotBlank() && it != "null" },
                    durationMs = item.optLong("duration_ms", 0L),
                    lastPlayedAt = item.optLong("last_played_at", 0L),
                    playCount = item.optInt("play_count", 1)
                ))
            }
        }
        val safe = JSONArray()
        sanitizeBackupHistoryEntries(parsed).forEach { entry ->
            safe.put(JSONObject()
                .put("uri", entry.uri)
                .put("title", entry.title)
                .put("artist", entry.artist ?: JSONObject.NULL)
                .put("duration_ms", entry.durationMs)
                .put("last_played_at", entry.lastPlayedAt)
                .put("play_count", entry.playCount))
        }
        return safe
    }

    internal fun sanitizeAudioOutputProfiles(raw: JSONObject): JSONObject {
        val safe = JSONObject()
        val keys = raw.keys()
        var accepted = 0
        while (keys.hasNext() && accepted < 20) {
            val key = keys.next()
            val item = raw.optJSONObject(key) ?: continue
            val bands = item.optJSONArray("bands") ?: JSONArray()
            val config = AudioEffectsConfig(
                equalizerEnabled = item.optBoolean("equalizer_enabled", false),
                bandsDb = resampleEqualizerBands((0 until minOf(bands.length(), 10)).map { bands.optDouble(it, 0.0).toFloat() }, 10),
                playerVolume = item.optDouble("player_volume", 1.0).toFloat(),
                replayGainEnabled = item.optBoolean("replay_gain_enabled", true)
            )
            val normalized = sanitizeBackupAudioProfile(key, config) ?: continue
            safe.put(normalized.first, JSONObject()
                .put("equalizer_enabled", normalized.second.equalizerEnabled)
                .put("player_volume", normalized.second.playerVolume)
                .put("replay_gain_enabled", normalized.second.replayGainEnabled)
                .put("bands", JSONArray(normalized.second.bandsDb)))
            accepted++
        }
        return safe
    }

'''
    s = s[:start] + block + s[end:]
p.write_text(s, encoding="utf-8")

# Reuse one compatibility path for profiles loaded from preferences.
p = PKG / "AudioOutputProfiles.kt"
replace_once(
    p,
    "bandsDb = (0 until bands.length()).map { bands.optDouble(it, 0.0).toFloat() },",
    "bandsDb = resampleEqualizerBands((0 until bands.length()).map { bands.optDouble(it, 0.0).toFloat() }, 10),",
    "legacy profile band migration"
)

# Pure sanitizers keep security/compatibility tests independent of Android org.json stubs.
manager = PKG / "LibraryBackupManager.kt"
s = manager.read_text(encoding="utf-8")
if "internal fun sanitizeBackupHistoryEntries" not in s:
    s += '''

internal fun sanitizeBackupHistoryEntries(
    entries: List<PlaybackHistoryEntry>
): List<PlaybackHistoryEntry> =
    entries.asSequence()
        .filter { LibraryBackupManager.isAllowedBackupUri(it.uri) }
        .distinctBy { it.uri }
        .take(100)
        .map { entry ->
            entry.copy(
                title = entry.title.take(200).ifBlank { "Без названия" },
                artist = entry.artist?.take(200),
                durationMs = entry.durationMs.coerceIn(0L, 86_400_000L),
                lastPlayedAt = entry.lastPlayedAt.coerceAtLeast(0L),
                playCount = entry.playCount.coerceIn(1, 100_000)
            )
        }
        .toList()

internal fun sanitizeBackupAudioProfile(
    profileKey: String,
    config: AudioEffectsConfig
): Pair<String, AudioEffectsConfig>? {
    if (!profileKey.matches(Regex("^[0-9]+_[a-z0-9а-я_-]{1,48}$"))) return null
    val compatible = config.copy(bandsDb = resampleEqualizerBands(config.bandsDb, 10))
    return profileKey to normalizeAudioEffectsConfig(compatible)
}
'''
manager.write_text(s, encoding="utf-8")

# Replace JSON-based tests with pure model tests that run on the JVM.
p = TEST / "LibraryBackupManagerTest.kt"
s = p.read_text(encoding="utf-8")
if "import org.junit.Assert.assertEquals" not in s:
    s = s.replace("import org.junit.Assert.assertFalse", "import org.junit.Assert.assertEquals\nimport org.junit.Assert.assertFalse", 1)
start = s.find("    @Test fun playbackHistoryExportFiltersUnsafeUrisAndBoundsFields() {")
end = s.find("    @Test fun rejectsWhitespaceAndOversizedUris() {", start)
if start < 0 or end < 0:
    raise SystemExit("patch_0452: backup test block anchors missing")
tests = '''    @Test fun playbackHistorySanitizerFiltersUnsafeUrisAndBoundsFields() {
        val safe = sanitizeBackupHistoryEntries(listOf(
            PlaybackHistoryEntry("content://media/audio/1", "S".repeat(300), "A".repeat(300), Long.MAX_VALUE, -1L, 0),
            PlaybackHistoryEntry("https://user:pass@example.com/private.mp3", "Unsafe", null, 1L, 1L, 1)
        ))
        assertEquals(1, safe.size)
        assertEquals(200, safe.single().title.length)
        assertEquals(200, safe.single().artist?.length)
        assertEquals(86_400_000L, safe.single().durationMs)
        assertEquals(0L, safe.single().lastPlayedAt)
        assertEquals(1, safe.single().playCount)
    }

    @Test fun outputProfileSanitizerNormalizesLegacyBandsAndRejectsUnsafeKeys() {
        val safe = sanitizeBackupAudioProfile(
            "7_sony_wh-1000xm5",
            AudioEffectsConfig(playerVolume = 9f, bandsDb = listOf(-10f, -5f, 0f, 5f, 10f))
        )
        assertEquals("7_sony_wh-1000xm5", safe?.first)
        assertEquals(2f, safe?.second?.playerVolume ?: 0f, 0f)
        assertEquals(10, safe?.second?.bandsDb?.size)
        assertEquals(-10f, safe?.second?.bandsDb?.first() ?: 0f, 0f)
        assertEquals(10f, safe?.second?.bandsDb?.last() ?: 0f, 0f)
        assertEquals(null, sanitizeBackupAudioProfile("../unsafe", AudioEffectsConfig()))
    }

'''
s = s[:start] + tests + s[end:]
p.write_text(s, encoding="utf-8")

print("patch_0452: fixed the remaining EQ expectation, preserved legacy five-band curves, and made backup sanitizer tests JVM-safe")
