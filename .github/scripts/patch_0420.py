from pathlib import Path

ROOT = Path("app/src/main/java/com/chiyuri/player")

def replace_once(path, old, new, label):
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

# Bounded artwork decoding prevents full-resolution allocations from huge covers.
(ROOT / "ArtworkDecoder.kt").write_text("""package com.chiyuri.player

import android.graphics.Bitmap
import android.graphics.BitmapFactory

internal const val MAX_ARTWORK_BYTES = 12 * 1024 * 1024
internal const val MAX_ARTWORK_DIMENSION = 2048

internal fun artworkSampleSize(width: Int, height: Int, maxDimension: Int = MAX_ARTWORK_DIMENSION): Int {
    if (width <= 0 || height <= 0 || maxDimension <= 0) return 1
    var sample = 1
    while (width / sample > maxDimension || height / sample > maxDimension) {
        if (sample > Int.MAX_VALUE / 2) break
        sample *= 2
    }
    return sample.coerceAtLeast(1)
}

internal fun decodeArtworkBitmap(bytes: ByteArray): Bitmap? {
    if (bytes.isEmpty() || bytes.size > MAX_ARTWORK_BYTES) return null
    return try {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size, bounds)
        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return null
        val options = BitmapFactory.Options().apply {
            inSampleSize = artworkSampleSize(bounds.outWidth, bounds.outHeight)
            inPreferredConfig = Bitmap.Config.ARGB_8888
        }
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size, options)
    } catch (_: OutOfMemoryError) {
        null
    } catch (_: RuntimeException) {
        null
    }
}
""", encoding="utf-8")

backdrop = ROOT / "TrackArtworkBackdrop.kt"
source = backdrop.read_text(encoding="utf-8").replace("import android.graphics.BitmapFactory\n", "")
backdrop.write_text(source, encoding="utf-8")
replace_once(backdrop,
    """                                while (total < 12 * 1024 * 1024) {
                                    val count = input.read(buffer, 0, minOf(buffer.size, 12 * 1024 * 1024 - total))
                                    if (count <= 0) break
                                    output.write(buffer, 0, count)
                                    total += count
                                }
                                output.toByteArray()""",
    """                                if (connection.contentLengthLong > MAX_ARTWORK_BYTES) return@use null
                                while (true) {
                                    val count = input.read(buffer)
                                    if (count < 0) break
                                    if (total + count > MAX_ARTWORK_BYTES) return@use null
                                    output.write(buffer, 0, count)
                                    total += count
                                }
                                output.toByteArray()""",
    "bounded remote artwork read")
replace_once(backdrop,
    "bitmap = bytes?.let { BitmapFactory.decodeByteArray(it, 0, it.size) }",
    "bitmap = bytes?.let(::decodeArtworkBitmap)",
    "bounded artwork decode")

# Persist the playback modes as well as the queue and correct current index if
# an invalid URI was skipped during serialization.
queue = ROOT / "PlaybackQueueStore.kt"
source = queue.read_text(encoding="utf-8")
if "import androidx.media3.common.PlaybackParameters\n" not in source:
    source = source.replace("import androidx.media3.common.Player\n",
                            "import androidx.media3.common.Player\nimport androidx.media3.common.PlaybackParameters\n", 1)
    queue.write_text(source, encoding="utf-8")
replace_once(queue,
    """        val array = JSONArray()
        for (index in 0 until player.mediaItemCount) {
            val item = player.getMediaItemAt(index)
            val uri = item.localConfiguration?.uri?.toString() ?: continue
            val metadata = item.mediaMetadata
            array.put(""",
    """        val array = JSONArray()
        var persistedCurrentIndex = -1
        for (index in 0 until player.mediaItemCount) {
            val item = player.getMediaItemAt(index)
            val uri = item.localConfiguration?.uri?.toString() ?: continue
            if (index == player.currentMediaItemIndex) persistedCurrentIndex = array.length()
            val metadata = item.mediaMetadata
            array.put(""",
    "queue current index mapping")
replace_once(queue,
    """            .putInt(CURRENT_INDEX, player.currentMediaItemIndex)
            .putLong(POSITION, player.currentPosition.coerceAtLeast(0L))
            .apply()""",
    """            .putInt(CURRENT_INDEX, persistedCurrentIndex.coerceAtLeast(0))
            .putLong(POSITION, player.currentPosition.coerceAtLeast(0L))
            .putBoolean("shuffle_enabled", player.shuffleModeEnabled)
            .putInt("repeat_mode", player.repeatMode)
            .putFloat("playback_speed", player.playbackParameters.speed.coerceIn(0.25f, 4f))
            .apply()""",
    "queue settings persistence")
replace_once(queue,
    """            player.setMediaItems(items, savedIndex, savedPosition)
            player.prepare()
            player.pause()""",
    """            player.setMediaItems(items, savedIndex, savedPosition)
            player.shuffleModeEnabled = prefs.getBoolean("shuffle_enabled", false)
            player.repeatMode = prefs.getInt("repeat_mode", Player.REPEAT_MODE_OFF)
                .takeIf { it in Player.REPEAT_MODE_OFF..Player.REPEAT_MODE_ALL } ?: Player.REPEAT_MODE_OFF
            val savedSpeed = prefs.getFloat("playback_speed", 1f).takeIf { it.isFinite() }
                ?.coerceIn(0.25f, 4f) ?: 1f
            player.playbackParameters = PlaybackParameters(savedSpeed)
            player.prepare()
            player.pause()""",
    "queue settings restore")

# Do not crash when installation permission is missing: return an actionable
# message instead of throwing after launching Android settings.
updates = ROOT / "AppUpdates.kt"
replace_once(updates,
    """    fun install(context: Context, apk: File) {
        if (Build.VERSION.SDK_INT >= 26 && !context.packageManager.canRequestPackageInstalls()) {
            val settings = Intent(android.provider.Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:${context.packageName}"))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(settings)
            error("Разрешите установку неизвестных приложений для ChiyuriPlayer и повторите установку")
        }
        val uri: Uri = FileProvider.getUriForFile(context, "${context.packageName}.updates", apk)
        val intent = Intent(Intent.ACTION_VIEW).setDataAndType(uri, "application/vnd.android.package-archive")
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(intent)
    }""",
    """    fun install(context: Context, apk: File): String {
        return try {
            if (!apk.isFile || apk.length() <= 0L) {
                return "Файл обновления не найден или пуст. Скачайте его заново."
            }
            if (Build.VERSION.SDK_INT >= 26 && !context.packageManager.canRequestPackageInstalls()) {
                val settings = Intent(
                    android.provider.Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                    Uri.parse("package:${context.packageName}")
                ).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(settings)
                return "Разрешите установку неизвестных приложений для ChiyuriPlayer в настройках, вернитесь сюда и нажмите «Установить» ещё раз."
            }
            val uri = FileProvider.getUriForFile(context, "${context.packageName}.updates", apk)
            val intent = Intent(Intent.ACTION_VIEW)
                .setDataAndType(uri, "application/vnd.android.package-archive")
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
            "Открыт системный установщик Android. Завершите установку в его окне."
        } catch (error: Exception) {
            "Не удалось открыть установщик: " + (error.localizedMessage ?: error.javaClass.simpleName)
        }
    }""",
    "safe updater installation")
replace_once(updates,
    """    override suspend fun doWork(): Result = try {
        val update = AppUpdates.checkLatest()
        if (update != null) UpdateNotifications.show(applicationContext, update)
        Result.success()
    } catch (_: Exception) { Result.retry() }""",
    """    override suspend fun doWork(): Result = try {
        val update = AppUpdates.checkLatest()
        if (update != null) UpdateNotifications.show(applicationContext, update)
        Result.success()
    } catch (cancelled: CancellationException) {
        throw cancelled
    } catch (_: Exception) {
        Result.retry()
    }""",
    "update worker cancellation")
replace_once(updates,
    """    val downloadedPath = currentWorkInfo?.outputData?.getString("apk_path")
    val downloadError""",
    """    val downloadedPath = currentWorkInfo?.outputData?.getString("apk_path")
    var installMessage by androidx.compose.runtime.remember { androidx.compose.runtime.mutableStateOf<String?>(null) }
    val downloadError""",
    "updater install message state")
replace_once(updates,
    """                downloadError?.let { androidx.compose.material3.Text(it, color = MaterialTheme.colorScheme.error) }
                notificationPermissionMessage""",
    """                downloadError?.let { androidx.compose.material3.Text(it, color = MaterialTheme.colorScheme.error) }
                installMessage?.let { androidx.compose.material3.Text(it, color = MaterialTheme.colorScheme.tertiary) }
                notificationPermissionMessage""",
    "updater install message UI")
replace_once(updates,
    "onClick = { AppUpdates.install(context, java.io.File(downloadedPath)) },",
    "onClick = { installMessage = AppUpdates.install(context, java.io.File(downloadedPath)) },",
    "updater install click")

# The metadata editor preview used URL.openStream().readBytes() and a full-size
# BitmapFactory decode. Reuse the bounded decoder and explicit HTTPS/time limits.
details = ROOT / "TrackDetailsComponents.kt"
source = details.read_text(encoding="utf-8")
source = source.replace("import android.graphics.BitmapFactory" + chr(10), "")
details.write_text(source, encoding="utf-8")
replace_once(details,
    """            val bytes = embedded ?: if (artworkUrl?.startsWith("https://") == true) {
                runCatching { URL(artworkUrl).openStream().use { it.readBytes() } }.getOrNull()
            } else null
            bytes?.let { BitmapFactory.decodeByteArray(it, 0, it.size) }""",
    """            val bytes = embedded ?: artworkUrl?.takeIf { it.startsWith("https://") }
                ?.let(::downloadArtworkPreview)
            bytes?.let(::decodeArtworkBitmap)""",
    "bounded metadata editor artwork preview")
source = details.read_text(encoding="utf-8")
helper = """private fun downloadArtworkPreview(address: String): ByteArray? {
    val connection = URL(address).openConnection() as java.net.HttpURLConnection
    return try {
        connection.connectTimeout = 7000
        connection.readTimeout = 10000
        connection.instanceFollowRedirects = true
        if (connection.responseCode !in 200..299 || !connection.url.protocol.equals("https", true)) return null
        if (connection.contentLengthLong > MAX_ARTWORK_BYTES) return null
        connection.inputStream.use { input ->
            val output = java.io.ByteArrayOutputStream()
            val buffer = ByteArray(8192)
            var total = 0
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                if (total + count > MAX_ARTWORK_BYTES) return@use null
                output.write(buffer, 0, count)
                total += count
            }
            output.toByteArray()
        }
    } catch (_: Exception) {
        null
    } finally {
        connection.disconnect()
    }
}

"""
track_marker = "@Composable" + chr(10) + "internal fun TrackArtwork("
if source.count(track_marker) != 1:
    raise SystemExit("TrackArtwork insertion marker is missing or ambiguous")
source = source.replace(track_marker, helper + track_marker, 1)
details.write_text(source, encoding="utf-8")

# Bound M3U import size and entry count to prevent huge files from exhausting memory.
m3u = ROOT / "M3uPlaylistCodec.kt"
replace_once(m3u,
    """object M3uPlaylistCodec {
    fun parse(content: String): List<M3uEntry> {
        val entries = mutableListOf<M3uEntry>()""",
    """object M3uPlaylistCodec {
    const val MAX_PLAYLIST_BYTES = 4 * 1024 * 1024
    const val MAX_PLAYLIST_ENTRIES = 10000

    fun read(input: java.io.InputStream): String {
        val output = java.io.ByteArrayOutputStream()
        val buffer = ByteArray(8192)
        var total = 0
        while (true) {
            val count = input.read(buffer)
            if (count < 0) break
            require(total + count <= MAX_PLAYLIST_BYTES) {
                "Файл плейлиста превышает допустимый размер 4 МБ."
            }
            output.write(buffer, 0, count)
            total += count
        }
        return String(output.toByteArray(), Charsets.UTF_8)
    }

    fun parse(content: String): List<M3uEntry> {
        require(content.length <= MAX_PLAYLIST_BYTES) { "Текст плейлиста слишком большой." }
        val entries = mutableListOf<M3uEntry>()""",
    "bounded M3U parser")
replace_once(m3u,
    """                else -> {
                    val fallbackTitle = line.substringAfterLast('/')""",
    """                else -> {
                    require(entries.size < MAX_PLAYLIST_ENTRIES) {
                        "Плейлист содержит больше 10000 записей."
                    }
                    val fallbackTitle = line.substringAfterLast('/')""",
    "M3U entry limit")
replace_once(ROOT / "MainActivity.kt",
    """                        val content = context.contentResolver.openInputStream(source)
                            ?.bufferedReader(Charsets.UTF_8)
                            ?.use { it.readText() }
                            ?: throw IllegalStateException("Не удалось прочитать выбранный файл")""",
    """                        val content = context.contentResolver.openInputStream(source)?.use {
                            M3uPlaylistCodec.read(it)
                        } ?: throw IllegalStateException("Не удалось прочитать выбранный файл")""",
    "bounded M3U import")

(Path("app/src/test/java/com/chiyuri/player") / "M3uPlaylistCodecTest.kt").write_text("""package com.chiyuri.player

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test
import java.io.ByteArrayInputStream

class M3uPlaylistLimitsTest {
    @Test fun readsUtf8PlaylistWithinLimit() {
        val content = "#EXTM3U\\n#EXTINF:120,Track\\ncontent://media/1\\n"
        assertEquals(content, M3uPlaylistCodec.read(ByteArrayInputStream(content.toByteArray(Charsets.UTF_8))))
        assertEquals(1, M3uPlaylistCodec.parse(content).size)
    }

    @Test fun rejectsPlaylistLargerThanLimit() {
        val bytes = ByteArray(M3uPlaylistCodec.MAX_PLAYLIST_BYTES + 1)
        assertThrows(IllegalArgumentException::class.java) {
            M3uPlaylistCodec.read(ByteArrayInputStream(bytes))
        }
    }

    @Test fun rejectsTooManyEntries() {
        val content = (1..(M3uPlaylistCodec.MAX_PLAYLIST_ENTRIES + 1)).joinToString("\\n") { "content://media/$it" }
        assertThrows(IllegalArgumentException::class.java) {
            M3uPlaylistCodec.parse(content)
        }
    }
}
""", encoding="utf-8")

# Decode the sampled bitmap off the main thread as well as fetching bytes off-thread.
replace_once(backdrop,
    "bitmap = bytes?.let(::decodeArtworkBitmap)",
    "bitmap = bytes?.let { artworkBytes -> withContext(Dispatchers.Default) { decodeArtworkBitmap(artworkBytes) } }",
    "background artwork decode dispatcher")

# Bounded in-memory lyric cache avoids repeated provider requests; propagate
# cancellation instead of swallowing it as a normal network failure.
lyrics = ROOT / "LyricsRepository.kt"
source = lyrics.read_text(encoding="utf-8")
if "import kotlinx.coroutines.CancellationException\n" not in source:
    source = source.replace("import kotlinx.coroutines.Dispatchers\n",
                            "import kotlinx.coroutines.Dispatchers\nimport kotlinx.coroutines.CancellationException\n", 1)
    lyrics.write_text(source, encoding="utf-8")
replace_once(lyrics,
    """object LyricsRepository {
    suspend fun search(artist: String, title: String, durationMs: Long): LyricsResult? =
        withContext(Dispatchers.IO) {""",
    """object LyricsRepository {
    private data class CacheEntry(val savedAt: Long, val result: LyricsResult)
    private const val CACHE_TTL_MS = 12L * 60L * 60L * 1000L
    private const val CACHE_MAX_ENTRIES = 120
    private val cache = object : LinkedHashMap<String, CacheEntry>(CACHE_MAX_ENTRIES, 0.75f, true) {
        override fun removeEldestEntry(eldest: MutableMap.MutableEntry<String, CacheEntry>?): Boolean =
            size > CACHE_MAX_ENTRIES
    }

    suspend fun search(artist: String, title: String, durationMs: Long): LyricsResult? {
        val key = listOf(normalizeLyricsText(artist), normalizeLyricsText(title), (durationMs / 5000L).toString())
            .joinToString("|")
        synchronized(cache) {
            val cached = cache[key]
            if (cached != null && System.currentTimeMillis() - cached.savedAt < CACHE_TTL_MS) return cached.result
            if (cached != null) cache.remove(key)
        }
        val result = searchUncached(artist, title, durationMs)
        if (result != null) synchronized(cache) {
            cache[key] = CacheEntry(System.currentTimeMillis(), result)
        }
        return result
    }

    private suspend fun searchUncached(artist: String, title: String, durationMs: Long): LyricsResult? =
        withContext(Dispatchers.IO) {""",
    "lyrics cache wrapper")
replace_once(lyrics,
    """        } catch (_: Exception) {
            null
        } finally {
            connection.disconnect()
        }
    }

    private fun encodePath""",
    """        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (_: Exception) {
            null
        } finally {
            connection.disconnect()
        }
    }

    private fun encodePath""",
    "lyrics cancellation")

# Other cancellable UI jobs must not turn cancellation into false failures.
replace_once(ROOT / "LyricsScreen.kt",
    """                    } catch (_: Exception) {
                        message = "Не удалось выполнить поиск. Проверь подключение к интернету и попробуй снова.""",
    """                    } catch (cancelled: kotlinx.coroutines.CancellationException) {
                        throw cancelled
                    } catch (_: Exception) {
                        message = "Не удалось выполнить поиск. Проверь подключение к интернету и попробуй снова.""",
    "lyrics screen cancellation")
replace_once(ROOT / "LyricsScreen.kt",
    """                    } catch (_: Exception) {
                        message = "Не удалось прочитать файл или выполнить онлайн-поиск.""",
    """                    } catch (cancelled: kotlinx.coroutines.CancellationException) {
                        throw cancelled
                    } catch (_: Exception) {
                        message = "Не удалось прочитать файл или выполнить онлайн-поиск.""",
    "embedded lyrics cancellation")

metadata = ROOT / "TrackMetadataRepository.kt"
source = metadata.read_text(encoding="utf-8")
if "import kotlinx.coroutines.CancellationException\n" not in source:
    source = source.replace("import kotlinx.coroutines.async\n",
                            "import kotlinx.coroutines.async\nimport kotlinx.coroutines.CancellationException\n", 1)
    metadata.write_text(source, encoding="utf-8")
replace_once(metadata,
    """            } catch (_: Exception) {
                null
            } finally {
                connection.disconnect()
            }
        }

    /**
     * Queries independent metadata catalogues""",
    """            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (_: Exception) {
                null
            } finally {
                connection.disconnect()
            }
        }

    /**
     * Queries independent metadata catalogues""",
    "iTunes metadata cancellation")
replace_once(metadata,
    "            listOfNotNull(runCatching { itunes.await() }.getOrNull(), runCatching { deezer.await() }.getOrNull())",
    """            try {
                listOfNotNull(itunes.await(), deezer.await())
            } catch (cancelled: CancellationException) {
                itunes.cancel()
                deezer.cancel()
                throw cancelled
            }""",
    "parallel metadata cancellation")
replace_once(metadata,
    """            } catch (_: Exception) {
                null
            } finally {
                connection.disconnect()
            }
        }
    fun hasWriteAccess""",
    """            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (_: Exception) {
                null
            } finally {
                connection.disconnect()
            }
        }
    fun hasWriteAccess""",
    "Deezer metadata cancellation")
replace_once(ROOT / "MainActivity.kt",
    """                } catch (error: Exception) {
                    message = "Ошибка экспорта: ${error.localizedMessage ?: "неизвестная ошибка"}"
                }""",
    """                } catch (cancelled: kotlinx.coroutines.CancellationException) {
                    throw cancelled
                } catch (error: Exception) {
                    message = "Ошибка экспорта: ${error.localizedMessage ?: "неизвестная ошибка"}"
                }""",
    "playlist export cancellation")
replace_once(ROOT / "MainActivity.kt",
    """                } catch (error: Exception) {
                    message = "Ошибка импорта: ${error.localizedMessage ?: "неизвестная ошибка"}"
                }""",
    """                } catch (cancelled: kotlinx.coroutines.CancellationException) {
                    throw cancelled
                } catch (error: Exception) {
                    message = "Ошибка импорта: ${error.localizedMessage ?: "неизвестная ошибка"}"
                }""",
    "playlist import cancellation")
replace_once(ROOT / "TrackDetailsComponents.kt",
    """        } catch (error: Exception) {
            message = "Не удалось изменить исходный файл: " + (error.message ?: "неизвестная ошибка")""",
    """        } catch (cancelled: kotlinx.coroutines.CancellationException) {
            writingToFile = false
            throw cancelled
        } catch (error: Exception) {
            message = "Не удалось изменить исходный файл: " + (error.message ?: "неизвестная ошибка")""",
    "metadata save cancellation")
replace_once(ROOT / "TrackDetailsComponents.kt",
    """                            } catch (_: Exception) {
                                message = "Ошибка поиска. Введённые данные не изменены.""",
    """                            } catch (cancelled: kotlinx.coroutines.CancellationException) {
                                throw cancelled
                            } catch (_: Exception) {
                                message = "Ошибка поиска. Введённые данные не изменены.""",
    "metadata search cancellation")

# Compose effects and editor jobs must rethrow cancellation instead of displaying
# stale network/file errors after the screen or request has been cancelled.
replace_once(updates,
    """            } catch (e: Exception) {
                error = e.message ?: "Ошибка проверки обновлений"
                status = "Проверка не завершена"
            } finally {""",
    """            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (e: Exception) {
                error = e.message ?: "Ошибка проверки обновлений"
                status = "Проверка не завершена"
            } finally {""",
    "initial updater check cancellation")
replace_once(updates,
    """                            } catch (e: Exception) {
                                error = e.message ?: "Ошибка проверки обновлений"
                                status = "Проверка не завершена"
                            } finally {""",
    """                            } catch (cancelled: CancellationException) {
                                throw cancelled
                            } catch (e: Exception) {
                                error = e.message ?: "Ошибка проверки обновлений"
                                status = "Проверка не завершена"
                            } finally {""",
    "manual updater check cancellation")

replace_once(ROOT / "TrackDetailsComponents.kt",
    """                } catch (error: Exception) {
                    message = "Не удалось получить доступ к файлу: " + (error.message ?: "неизвестная ошибка")""",
    """                } catch (cancelled: kotlinx.coroutines.CancellationException) {
                    writingToFile = false
                    throw cancelled
                } catch (error: Exception) {
                    message = "Не удалось получить доступ к файлу: " + (error.message ?: "неизвестная ошибка")""",
    "document grant cancellation")
replace_once(ROOT / "TrackDetailsComponents.kt",
    """                            } catch (error: Exception) {
                                message = "Не удалось подготовить копию: " + (error.message ?: "неизвестная ошибка")""",
    """                            } catch (cancelled: kotlinx.coroutines.CancellationException) {
                                writingToFile = false
                                throw cancelled
                            } catch (error: Exception) {
                                message = "Не удалось подготовить копию: " + (error.message ?: "неизвестная ошибка")""",
    "metadata copy cancellation")

# Make Media3 unstable API opt-ins explicit to both Kotlin and Android Lint.
for file_name, import_anchor in [
    ("AudioEffectsController.kt", "import androidx.media3.common.Player\n"),
    ("AudioVisualizer.kt", "import androidx.media3.common.Player\n"),
    ("MainActivity.kt", "import androidx.media3.common.Player\n")
]:
    path = ROOT / file_name
    source = path.read_text(encoding="utf-8")
    if "import androidx.media3.common.util.UnstableApi" not in source:
        if import_anchor not in source:
            raise SystemExit("UnstableApi import anchor missing in " + file_name)
        source = source.replace(import_anchor, import_anchor + "import androidx.media3.common.util.UnstableApi\n", 1)
        path.write_text(source, encoding="utf-8")

replace_once(ROOT / "AudioEffectsController.kt",
    "class AudioEffectsController(",
    "@OptIn(UnstableApi::class)\n@androidx.annotation.OptIn(markerClass = [UnstableApi::class])\nclass AudioEffectsController(",
    "AudioEffectsController Media3 opt-in")
replace_once(ROOT / "AudioVisualizer.kt",
    "internal object AudioVisualizerBridge {",
    "@OptIn(UnstableApi::class)\n@androidx.annotation.OptIn(markerClass = [UnstableApi::class])\ninternal object AudioVisualizerBridge {",
    "AudioVisualizerBridge Media3 opt-in")
replace_once(ROOT / "MainActivity.kt",
    "@Composable\nprivate fun PlayerHome(",
    "@Composable\n@OptIn(UnstableApi::class)\n@androidx.annotation.OptIn(markerClass = [UnstableApi::class])\nprivate fun PlayerHome(",
    "PlayerHome Media3 opt-in")
replace_once(ROOT / "PlaybackService.kt",
    "@OptIn(UnstableApi::class)\nclass PlaybackService",
    "@OptIn(UnstableApi::class)\n@androidx.annotation.OptIn(markerClass = [UnstableApi::class])\nclass PlaybackService",
    "PlaybackService Media3 lint opt-in")

replace_once(ROOT / "MainActivity.kt",
    "    override fun dispatchKeyEvent(event: KeyEvent): Boolean {",
    "    @android.annotation.SuppressLint(\"RestrictedApi\")\n    override fun dispatchKeyEvent(event: KeyEvent): Boolean {",
    "volume key event restricted API suppression")

# Android 13+ requires an explicit notification permission check before notify().
replace_once(updates,
    """    fun showComplete(context: Context, version: String) {
        ensureChannel(context)""",
    """    fun showComplete(context: Context, version: String) {
        if (Build.VERSION.SDK_INT >= 33 &&
            androidx.core.content.ContextCompat.checkSelfPermission(
                context,
                android.Manifest.permission.POST_NOTIFICATIONS
            ) != PackageManager.PERMISSION_GRANTED
        ) return
        ensureChannel(context)""",
    "notification permission guard")

# Keep local non-CI builds on the current release code instead of stale 201.
gradle = Path("app/build.gradle.kts")
replace_once(gradle,
    'versionCode = providers.gradleProperty("VERSION_CODE").orElse("201").get().toInt()',
    'versionCode = providers.gradleProperty("VERSION_CODE").orElse("330").get().toInt()',
    "Gradle versionCode fallback")

test_dir = Path("app/src/test/java/com/chiyuri/player")
(test_dir / "ArtworkDecoderTest.kt").write_text("""package com.chiyuri.player

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ArtworkDecoderTest {
    @Test fun leavesSmallImagesAtFullResolution() {
        assertEquals(1, artworkSampleSize(800, 600))
    }

    @Test fun downsamplesLargeImages() {
        val sample = artworkSampleSize(12000, 8000)
        assertEquals(8, sample)
        assertTrue(12000 / sample <= MAX_ARTWORK_DIMENSION)
        assertTrue(8000 / sample <= MAX_ARTWORK_DIMENSION)
    }

    @Test fun handlesInvalidDimensions() {
        assertEquals(1, artworkSampleSize(0, 8000))
        assertEquals(1, artworkSampleSize(-1, 8000))
    }
}
""", encoding="utf-8")

print("0.4.20 reliability, bounded artwork, queue state, lyric cache and cancellation fixes applied.")
