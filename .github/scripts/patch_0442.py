from pathlib import Path
ROOT = Path.cwd()
PKG = ROOT / "app/src/main/java/com/chiyuri/player"
MANIFEST = ROOT / "app/src/main/AndroidManifest.xml"
TEST = ROOT / "app/src/test/java/com/chiyuri/player"

p = PKG / "PlaybackService.kt"
s = p.read_text(encoding="utf-8")
imports = """import androidx.media3.session.MediaLibraryService
import androidx.media3.session.MediaLibraryService.MediaLibrarySession
import androidx.media3.session.LibraryResult
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.core.net.toUri
import com.google.common.collect.ImmutableList
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture
"""
if "import androidx.media3.session.MediaSessionService\n" not in s:
    raise SystemExit("patch_0442: MediaSessionService import anchor missing")
s = s.replace("import androidx.media3.session.MediaSessionService\n", imports, 1)
s = s.replace("class PlaybackService : MediaSessionService() {", "class PlaybackService : MediaLibraryService() {", 1)
s = s.replace("private var mediaSession: MediaSession? = null", "private var mediaSession: MediaLibrarySession? = null", 1)
s = s.replace("mediaSession = MediaSession.Builder(this, player).build()", "mediaSession = MediaLibrarySession.Builder(this, player, LibraryCallback()).build()", 1)

old = '''    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaSession? {
        // Keep exported for System UI, Bluetooth and Android Auto discovery.
        // Only trusted media/system controllers and this app may bind to the session.
        return mediaSession.takeIf { controllerInfo.isTrusted || controllerInfo.packageName == packageName }
    }'''
new = '''    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaLibrarySession? {
        // Browseable library for Android Auto and other trusted MediaBrowser clients.
        return mediaSession.takeIf { controllerInfo.isTrusted || controllerInfo.packageName == packageName }
    }

    private inner class LibraryCallback : MediaLibrarySession.Callback {
        override fun onGetLibraryRoot(
            session: MediaLibrarySession,
            browser: MediaSession.ControllerInfo,
            params: MediaLibraryService.LibraryParams?
        ): ListenableFuture<LibraryResult<MediaItem>> =
            Futures.immediateFuture(LibraryResult.ofItem(rootItem(), params))

        override fun onGetChildren(
            session: MediaLibrarySession,
            browser: MediaSession.ControllerInfo,
            parentId: String,
            page: Int,
            pageSize: Int,
            params: MediaLibraryService.LibraryParams?
        ): ListenableFuture<LibraryResult<ImmutableList<MediaItem>>> {
            val children = when (parentId) {
                ROOT_ID -> listOf(
                    categoryItem(MUSIC_ID, "Музыка"),
                    categoryItem(FAVORITES_ID, "Избранное"),
                    categoryItem(HISTORY_ID, "Недавно воспроизведённое")
                )
                MUSIC_ID -> (LocalMediaRepository.loadCached(this@PlaybackService, false).ifEmpty { LocalMediaRepository.loadAudio(this@PlaybackService) }).map(::localAudioItem)
                FAVORITES_ID -> {
                    val favorites = FavoriteTracksStore.load(this@PlaybackService)
                    (LocalMediaRepository.loadCached(this@PlaybackService, false).ifEmpty { LocalMediaRepository.loadAudio(this@PlaybackService) })
                        .filter { it.uri.toString() in favorites }
                        .map(::localAudioItem)
                }
                HISTORY_ID -> PlaybackHistoryStore.load(this@PlaybackService).map(::historyItem)
                else -> emptyList()
            }
            return Futures.immediateFuture(LibraryResult.ofItemList(paginateLibraryItems(children, page, pageSize), params))
        }

        override fun onGetItem(
            session: MediaLibrarySession,
            browser: MediaSession.ControllerInfo,
            mediaId: String
        ): ListenableFuture<LibraryResult<MediaItem>> {
            val item = when (mediaId) {
                ROOT_ID -> rootItem()
                MUSIC_ID -> categoryItem(MUSIC_ID, "Музыка")
                FAVORITES_ID -> categoryItem(FAVORITES_ID, "Избранное")
                HISTORY_ID -> categoryItem(HISTORY_ID, "Недавно воспроизведённое")
                else -> {
                    val local = (LocalMediaRepository.loadCached(this@PlaybackService, false)
                        .ifEmpty { LocalMediaRepository.loadAudio(this@PlaybackService) })
                        .firstOrNull { it.uri.toString() == mediaId }
                    if (local != null) localAudioItem(local) else {
                        PlaybackHistoryStore.load(this@PlaybackService)
                            .firstOrNull { it.uri == mediaId }?.let(::historyItem)
                    }
                }
            }
            return Futures.immediateFuture(
                if (item != null) LibraryResult.ofItem(item, null)
                else LibraryResult.ofError(LibraryResult.RESULT_ERROR_BAD_VALUE)
            )
        }
    }

    private fun rootItem(): MediaItem = MediaItem.Builder()
        .setMediaId(ROOT_ID)
        .setMediaMetadata(MediaMetadata.Builder().setTitle("ChiyuriPlayer").setIsBrowsable(true).setIsPlayable(false).build())
        .build()

    private fun categoryItem(id: String, title: String): MediaItem = MediaItem.Builder()
        .setMediaId(id)
        .setMediaMetadata(MediaMetadata.Builder().setTitle(title).setIsBrowsable(true).setIsPlayable(false).build())
        .build()

    private fun localAudioItem(item: LocalMedia): MediaItem = MediaItem.Builder()
        .setMediaId(item.uri.toString())
        .setUri(item.uri)
        .setMimeType(item.mimeType)
        .setMediaMetadata(MediaMetadata.Builder()
            .setTitle(item.title)
            .setArtist(item.artist)
            .setAlbumTitle(item.album)
            .setIsBrowsable(false)
            .setIsPlayable(true)
            .build())
        .build()

    private fun historyItem(entry: PlaybackHistoryEntry): MediaItem = MediaItem.Builder()
        .setMediaId(entry.uri)
        .setUri(entry.uri.toUri())
        .setMediaMetadata(MediaMetadata.Builder()
            .setTitle(entry.title)
            .setArtist(entry.artist)
            .setIsBrowsable(false)
            .setIsPlayable(true)
            .build())
        .build()
'''
if old not in s:
    raise SystemExit("patch_0442: onGetSession replacement anchor missing")
s = s.replace(old, new, 1)

s = s.replace('''    private companion object {
        const val SAVE_INTERVAL_MS = 5_000L
        const val OUTPUT_RECONNECT_RESUME_DELAY_MS = 900L
    }''', '''    private companion object {
        const val ROOT_ID = "chiyuri_root"
        const val MUSIC_ID = "chiyuri_music"
        const val FAVORITES_ID = "chiyuri_favorites"
        const val HISTORY_ID = "chiyuri_history"
        const val SAVE_INTERVAL_MS = 5_000L
        const val OUTPUT_RECONNECT_RESUME_DELAY_MS = 900L
    }''', 1)
if s.count("private companion object") > 1:
    raise SystemExit("patch_0442: duplicate companion object generated")
p.write_text(s, encoding="utf-8")

manifest = MANIFEST.read_text(encoding="utf-8")
old_action = '<action android:name="androidx.media3.session.MediaSessionService" />'
new_action = old_action + '\n                <action android:name="androidx.media3.session.MediaLibraryService" />'
if old_action not in manifest:
    raise SystemExit("patch_0442: manifest media service action missing")
manifest = manifest.replace(old_action, new_action, 1)
MANIFEST.write_text(manifest, encoding="utf-8")

(PKG / "MediaLibraryPaging.kt").write_text('''package com.chiyuri.player

internal fun <T> paginateLibraryItems(items: List<T>, page: Int, pageSize: Int): List<T> {
    if (page < 0 || pageSize <= 0) return emptyList()
    val start = (page.toLong() * pageSize).coerceAtMost(items.size.toLong()).toInt()
    val end = (start + pageSize).coerceAtMost(items.size)
    return items.subList(start, end)
}
''', encoding="utf-8")

(TEST / "MediaLibraryPaginationTest.kt").write_text('''package com.chiyuri.player

import org.junit.Assert.assertEquals
import org.junit.Test

class MediaLibraryPaginationTest {
    @Test fun pageBoundsAreClamped() {
        val values = listOf("a", "b", "c", "d", "e")
        assertEquals(listOf("c", "d"), paginateLibraryItems(values, 1, 2))
        assertEquals(listOf("e"), paginateLibraryItems(values, 99, 2))
        assertEquals(emptyList<String>(), paginateLibraryItems(values, 0, 0))
    }
}
''', encoding="utf-8")

print("patch_0442: MediaLibraryService browsing for Android Auto, local music, favorites and history applied")
