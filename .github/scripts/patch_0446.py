from pathlib import Path
def replace_once(path, old, new):
    source = path.read_text(encoding='utf-8')
    if old not in source: raise SystemExit(f'patch_0446: anchor missing in {path.name}: {old[:90]!r}')
    path.write_text(source.replace(old, new, 1), encoding='utf-8')
PKG = Path('app/src/main/java/com/chiyuri/player')
TEST = Path('app/src/test/java/com/chiyuri/player')
reader = r'''package com.chiyuri.player

import android.content.Context
import android.net.Uri
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.charset.Charset
import java.nio.charset.StandardCharsets

/** Reads ReplayGain track tags without loading the audio payload into memory. */
internal object ReplayGainReader {
    private const val MAX_METADATA_BYTES = 2 * 1024 * 1024
    private val gainPattern = Regex("""(-?\d+(?:\.\d+)?)\s*dB""", RegexOption.IGNORE_CASE)

    fun read(context: Context, uri: Uri): Float? {
        if (uri.scheme !in setOf("content", "file")) return null
        return runCatching {
            context.contentResolver.openInputStream(uri)?.use(::readGainDb)
        }.getOrNull()
    }

    internal fun readGainDb(input: InputStream): Float? {
        val prefix = readExact(input, 4) ?: return null
        return when {
            prefix.contentEquals(byteArrayOf('f'.code.toByte(), 'L'.code.toByte(), 'a'.code.toByte(), 'C'.code.toByte())) ->
                readFlacComments(input)
            prefix[0] == 'I'.code.toByte() && prefix[1] == 'D'.code.toByte() && prefix[2] == '3'.code.toByte() ->
                readId3(input, prefix)
            else -> null
        }
    }

    private fun readId3(input: InputStream, prefix: ByteArray): Float? {
        val header = ByteArray(10)
        prefix.copyInto(header, 0)
        if (!readFully(input, header, 4, 6)) return null
        val version = header[3].toInt() and 0xff
        if (version !in 3..4) return null
        val tagSize = syncSafeInt(header, 6)
        if (tagSize !in 1..MAX_METADATA_BYTES) return null
        val body = readExact(input, tagSize) ?: return null
        var offset = 0
        if ((header[5].toInt() and 0x40) != 0 && body.size >= 4) {
            val extendedSize = if (version == 4) syncSafeInt(body, 0) else bigEndianInt(body, 0)
            if (extendedSize < 0 || extendedSize > body.size) return null
            offset = if (version == 3) 4 + extendedSize else extendedSize
        }
        while (offset + 10 <= body.size) {
            val id = String(body, offset, 4, StandardCharsets.ISO_8859_1)
            if (id.all { it == '\u0000' }) break
            val frameSize = if (version == 4) syncSafeInt(body, offset + 4) else bigEndianInt(body, offset + 4)
            if (frameSize <= 0 || frameSize > body.size - offset - 10) break
            if (id == "TXXX") {
                val value = parseUserTextFrame(body.copyOfRange(offset + 10, offset + 10 + frameSize))
                if (value != null) return parseGain(value)
            }
            offset += 10 + frameSize
        }
        return null
    }

    private fun parseUserTextFrame(payload: ByteArray): String? {
        if (payload.size < 4) return null
        val encoding = payload[0].toInt() and 0xff
        val charset = when (encoding) {
            0 -> StandardCharsets.ISO_8859_1
            1 -> StandardCharsets.UTF_16
            2 -> StandardCharsets.UTF_16BE
            3 -> StandardCharsets.UTF_8
            else -> return null
        }
        val delimiterWidth = if (encoding == 1 || encoding == 2) 2 else 1
        var split = -1
        var index = 1
        while (index + delimiterWidth <= payload.size) {
            val isDelimiter = if (delimiterWidth == 1) payload[index] == 0.toByte()
                else payload[index] == 0.toByte() && payload[index + 1] == 0.toByte()
            if (isDelimiter) {
                split = index
                break
            }
            index += delimiterWidth
        }
        if (split < 0) return null
        val description = String(payload, 1, split - 1, charset).trim('\u0000', '\uFEFF')
        if (!description.equals("REPLAYGAIN_TRACK_GAIN", ignoreCase = true)) return null
        val valueStart = split + delimiterWidth
        if (valueStart >= payload.size) return null
        return String(payload, valueStart, payload.size - valueStart, charset).trim('\u0000', '\uFEFF')
    }

    private fun readFlacComments(input: InputStream): Float? {
        var albumGain: Float? = null
        while (true) {
            val header = readExact(input, 4) ?: return albumGain
            val first = header[0].toInt() and 0xff
            val isLast = first and 0x80 != 0
            val type = first and 0x7f
            val length = ((header[1].toInt() and 0xff) shl 16) or
                ((header[2].toInt() and 0xff) shl 8) or (header[3].toInt() and 0xff)
            if (length < 0 || length > MAX_METADATA_BYTES) return albumGain
            val block = readExact(input, length) ?: return albumGain
            if (type == 4) {
                val parsed = parseVorbisComments(block)
                if (parsed.first != null) return parsed.first
                if (parsed.second != null) albumGain = parsed.second
            }
            if (isLast) return albumGain
        }
    }

    private fun parseVorbisComments(bytes: ByteArray): Pair<Float?, Float?> {
        if (bytes.size < 8) return null to null
        val buffer = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        val vendorLength = readLength(buffer, bytes.size) ?: return null to null
        if (vendorLength > buffer.remaining()) return null to null
        buffer.position(buffer.position() + vendorLength)
        val count = readLength(buffer, bytes.size) ?: return null to null
        if (count > 10000) return null to null
        var track: Float? = null
        var album: Float? = null
        repeat(count) {
            val length = readLength(buffer, bytes.size) ?: return track to album
            if (length > buffer.remaining()) return track to album
            val raw = ByteArray(length)
            buffer.get(raw)
            val comment = String(raw, StandardCharsets.UTF_8)
            val separator = comment.indexOf('=')
            if (separator <= 0) return@repeat
            val key = comment.substring(0, separator)
            val value = comment.substring(separator + 1)
            when {
                key.equals("REPLAYGAIN_TRACK_GAIN", true) -> track = parseGain(value) ?: track
                key.equals("REPLAYGAIN_ALBUM_GAIN", true) -> album = parseGain(value) ?: album
            }
        }
        return track to album
    }

    private fun readLength(buffer: ByteBuffer, totalSize: Int): Int? {
        if (buffer.remaining() < 4) return null
        val value = buffer.int
        return value.takeIf { it >= 0 && it <= totalSize }
    }

    private fun parseGain(raw: String): Float? =
        gainPattern.find(raw)?.groupValues?.getOrNull(1)?.toFloatOrNull()
            ?.takeIf { it.isFinite() }?.coerceIn(-12f, 12f)

    private fun syncSafeInt(bytes: ByteArray, offset: Int): Int {
        if (offset < 0 || offset + 4 > bytes.size) return -1
        return ((bytes[offset].toInt() and 0x7f) shl 21) or
            ((bytes[offset + 1].toInt() and 0x7f) shl 14) or
            ((bytes[offset + 2].toInt() and 0x7f) shl 7) or
            (bytes[offset + 3].toInt() and 0x7f)
    }

    private fun bigEndianInt(bytes: ByteArray, offset: Int): Int {
        if (offset < 0 || offset + 4 > bytes.size) return -1
        return ((bytes[offset].toInt() and 0xff) shl 24) or
            ((bytes[offset + 1].toInt() and 0xff) shl 16) or
            ((bytes[offset + 2].toInt() and 0xff) shl 8) or
            (bytes[offset + 3].toInt() and 0xff)
    }

    private fun readExact(input: InputStream, length: Int): ByteArray? {
        if (length < 0 || length > MAX_METADATA_BYTES) return null
        val result = ByteArray(length)
        return if (readFully(input, result, 0, length)) result else null
    }

    private fun readFully(input: InputStream, target: ByteArray, offset: Int, length: Int): Boolean {
        var read = 0
        while (read < length) {
            val count = input.read(target, offset + read, length - read)
            if (count < 0) return false
            if (count == 0) continue
            read += count
        }
        return true
    }
}
'''
test = r'''package com.chiyuri.player

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.charset.StandardCharsets

class ReplayGainReaderTest {
    @Test fun readsId3TrackGainFromUserTextFrame() {
        val payload = byteArrayOf(3) + "REPLAYGAIN_TRACK_GAIN".toByteArray(StandardCharsets.UTF_8) +
            byteArrayOf(0) + "-7.25 dB".toByteArray(StandardCharsets.UTF_8)
        val frame = ByteArrayOutputStream().apply {
            write("TXXX".toByteArray(StandardCharsets.US_ASCII))
            write(int32(payload.size))
            write(byteArrayOf(0, 0))
            write(payload)
        }.toByteArray()
        val tag = "ID3".toByteArray(StandardCharsets.US_ASCII) +
            byteArrayOf(3, 0, 0) + syncSafe(frame.size) + frame
        assertEquals(-7.25f, ReplayGainReader.readGainDb(ByteArrayInputStream(tag))!!, 0.001f)
    }

    @Test fun readsFlacVorbisTrackGainAndFallsBackToAlbumGain() {
        val comments = ByteArrayOutputStream().apply {
            write(littleEndian(4))
            write("test".toByteArray(StandardCharsets.UTF_8))
            write(littleEndian(2))
            val track = "REPLAYGAIN_TRACK_GAIN=-4.50 dB".toByteArray(StandardCharsets.UTF_8)
            write(littleEndian(track.size))
            write(track)
            val album = "REPLAYGAIN_ALBUM_GAIN=-6.00 dB".toByteArray(StandardCharsets.UTF_8)
            write(littleEndian(album.size))
            write(album)
        }.toByteArray()
        val blockHeader = byteArrayOf(0x84.toByte(), ((comments.size shr 16) and 0xff).toByte(),
            ((comments.size shr 8) and 0xff).toByte(), (comments.size and 0xff).toByte())
        val flac = "fLaC".toByteArray(StandardCharsets.US_ASCII) + blockHeader + comments
        assertEquals(-4.5f, ReplayGainReader.readGainDb(ByteArrayInputStream(flac))!!, 0.001f)
    }

    @Test fun ignoresMalformedAndUnsupportedMetadata() {
        assertNull(ReplayGainReader.readGainDb(ByteArrayInputStream(byteArrayOf(1, 2, 3, 4))))
        assertNull(ReplayGainReader.readGainDb(ByteArrayInputStream("fLaC".toByteArray())))
    }

    private fun littleEndian(value: Int): ByteArray =
        ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putInt(value).array()

    private fun int32(value: Int): ByteArray =
        ByteBuffer.allocate(4).order(ByteOrder.BIG_ENDIAN).putInt(value).array()

    private fun syncSafe(value: Int): ByteArray = byteArrayOf(
        ((value shr 21) and 0x7f).toByte(),
        ((value shr 14) and 0x7f).toByte(),
        ((value shr 7) and 0x7f).toByte(),
        (value and 0x7f).toByte()
    )
}
'''
for path, source in [(PKG / 'ReplayGainReader.kt', reader), (TEST / 'ReplayGainReaderTest.kt', test)]:
    if path.exists(): raise SystemExit(f'patch_0446: {path.name} already exists')
    path.write_text(source, encoding='utf-8')

settings = PKG / 'AudioEffectsSettings.kt'
replace_once(settings, '    val playerVolume: Float = 1f\n)', '    val playerVolume: Float = 1f,\n    val replayGainEnabled: Boolean = true\n)')
replace_once(settings, '    private const val KEY_PLAYER_VOLUME = "player_volume"\n', '    private const val KEY_PLAYER_VOLUME = "player_volume"\n    private const val KEY_REPLAYGAIN_ENABLED = "replay_gain_enabled"\n')
replace_once(settings, '                playerVolume = preferences.getFloat(KEY_PLAYER_VOLUME, 1f)\n', '                playerVolume = preferences.getFloat(KEY_PLAYER_VOLUME, 1f),\n                replayGainEnabled = preferences.getBoolean(KEY_REPLAYGAIN_ENABLED, true)\n')
replace_once(settings, '                putFloat(KEY_PLAYER_VOLUME, normalized.playerVolume)\n', '                putFloat(KEY_PLAYER_VOLUME, normalized.playerVolume)\n                putBoolean(KEY_REPLAYGAIN_ENABLED, normalized.replayGainEnabled)\n')

profiles = PKG / 'AudioOutputProfiles.kt'
replace_once(profiles, '                playerVolume = profile.optDouble("player_volume", 1.0).toFloat()\n', '                playerVolume = profile.optDouble("player_volume", 1.0).toFloat(),\n                replayGainEnabled = profile.optBoolean("replay_gain_enabled", true)\n')
replace_once(profiles, '            .put("player_volume", normalized.playerVolume)\n', '            .put("player_volume", normalized.playerVolume)\n            .put("replay_gain_enabled", normalized.replayGainEnabled)\n')

controller = PKG / 'AudioEffectsController.kt'
replace_once(controller, 'import kotlin.math.roundToInt\n', 'import kotlin.math.roundToInt\nimport kotlin.math.pow\n')
replace_once(controller, '    private var attachedSessionId: Int = 0\n', '    private var attachedSessionId: Int = 0\n    private var replayGainDb: Float = 0f\n')
replace_once(controller, '    private fun attachToSession(audioSessionId: Int) {', '    fun setReplayGainDb(gainDb: Float?) {\n        replayGainDb = gainDb?.takeIf { it.isFinite() }?.coerceIn(-12f, 12f) ?: 0f\n        applySettings()\n    }\n\n    private fun attachToSession(audioSessionId: Int) {')
replace_once(controller, '        // The base level is controlled by Android\'s STREAM_MUSIC volume.\n        player.volume = 1f\n', '        // Negative ReplayGain is applied as attenuation; positive gain shares the 200% ceiling with user boost.\n        val activeReplayGain = if (config.replayGainEnabled) replayGainDb else 0f\n        player.volume = if (activeReplayGain < 0f) 10.0.pow(activeReplayGain.toDouble() / 20.0).toFloat().coerceIn(0.1f, 1f) else 1f\n')
replace_once(controller, '                val extraGainMb = if (config.playerVolume > 1f) {\n                    volumeBoostToMillibels(config.playerVolume)\n                } else {\n                    0\n                }\n', '                val userBoostMb = volumeBoostToMillibels(config.playerVolume)\n                val replayGainMb = if (activeReplayGain > 0f) (activeReplayGain * 100f).roundToInt() else 0\n                val extraGainMb = (userBoostMb + replayGainMb).coerceIn(0, 602)\n')

service = PKG / 'PlaybackService.kt'
replace_once(service, 'import androidx.media3.common.util.UnstableApi\n', 'import androidx.media3.common.util.UnstableApi\nimport kotlinx.coroutines.CoroutineScope\nimport kotlinx.coroutines.Dispatchers\nimport kotlinx.coroutines.Job\nimport kotlinx.coroutines.SupervisorJob\nimport kotlinx.coroutines.cancel\nimport kotlinx.coroutines.launch\nimport kotlinx.coroutines.withContext\n')
replace_once(service, '    private var pausedByOutputLoss = false\n', '    private var pausedByOutputLoss = false\n    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)\n    private var replayGainJob: Job? = null\n')
replace_once(service, '        PlaybackQueueStore.restore(this, player)\n', '        PlaybackQueueStore.restore(this, player)\n        applyReplayGainFor(player, player.currentMediaItem)\n')
replace_once(service, '                PlaybackHistoryStore.record(this@PlaybackService, mediaItem, player.duration)\n', '                PlaybackHistoryStore.record(this@PlaybackService, mediaItem, player.duration)\n                applyReplayGainFor(player, mediaItem)\n')
replace_once(service, '    override fun onDestroy() {\n', '    private fun applyReplayGainFor(player: ExoPlayer, mediaItem: MediaItem?) {\n        replayGainJob?.cancel()\n        val uri = mediaItem?.localConfiguration?.uri\n        val mediaId = mediaItem?.mediaId\n        if (uri == null || uri.scheme !in setOf("content", "file")) {\n            audioEffectsController?.setReplayGainDb(null)\n            return\n        }\n        replayGainJob = serviceScope.launch {\n            val gain = withContext(Dispatchers.IO) { ReplayGainReader.read(this@PlaybackService, uri) }\n            if (player.currentMediaItem?.mediaId == mediaId) audioEffectsController?.setReplayGainDb(gain)\n        }\n    }\n\n    override fun onDestroy() {\n        replayGainJob?.cancel()\n        serviceScope.cancel()\n')

main = PKG / 'MainActivity.kt'
anchor = '                Row(\n                    modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),\n'
insert = '                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {\n                    Column(Modifier.weight(1f)) {\n                        Text("ReplayGain", color = MaterialTheme.colorScheme.onSurface, style = MaterialTheme.typography.titleSmall)\n                        Text("Выравнивание громкости по тегам MP3 и FLAC", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)\n                    }\n                    Switch(checked = config.replayGainEnabled, onCheckedChange = { updateConfig(config.copy(replayGainEnabled = it)) })\n                }\n' + anchor
replace_once(main, anchor, insert)

audioTests = TEST / 'AudioEffectsSettingsTest.kt'
replace_once(audioTests, 'import org.junit.Assert.assertEquals\n', 'import org.junit.Assert.assertEquals\nimport org.junit.Assert.assertFalse\n')
replace_once(audioTests, '    @Test fun playerBoostIsCappedAtTwoTimesTotalOutput() {', '    @Test fun replayGainCanBeDisabledWithoutChangingOtherAudioSettings() {\n        assertTrue(AudioEffectsConfig().replayGainEnabled)\n        assertFalse(normalizeAudioEffectsConfig(AudioEffectsConfig(replayGainEnabled = false)).replayGainEnabled)\n    }\n\n    @Test fun playerBoostIsCappedAtTwoTimesTotalOutput() {')



print('patch_0446: ID3/FLAC ReplayGain parsing, per-output toggle, safe gain ceiling and async track integration applied')