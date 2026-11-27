from pathlib import Path

def replace_once(path: Path, old: str, new: str, label: str):
    source = path.read_text(encoding="utf-8")
    if old not in source:
        raise SystemExit(f"patch_0455: missing {label}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

PKG = Path("app/src/main/java/com/chiyuri/player")
TEST = Path("app/src/test/java/com/chiyuri/player")

(PKG / "VideoFrameCapture.kt").write_text('''package com.chiyuri.player

import android.content.ContentValues
import android.content.Context
import android.graphics.Bitmap
import android.media.MediaMetadataRetriever
import android.net.Uri
import android.os.Environment
import android.provider.MediaStore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.IOException

internal fun buildVideoFrameFileName(timestampMs: Long): String =
    "Chiyuri_Frame_${timestampMs.coerceAtLeast(0L)}.jpg"

object VideoFrameCapture {
    suspend fun save(context: Context, source: Uri, positionMs: Long): Result<Uri> =
        withContext(Dispatchers.IO) {
            runCatching {
                if (source.scheme !in setOf("content", "file")) {
                    throw IOException("Снимок кадра пока доступен для локальных видеофайлов.")
                }
                val retriever = MediaMetadataRetriever()
                var bitmap: Bitmap? = null
                try {
                    retriever.setDataSource(context, source)
                    bitmap = retriever.getFrameAtTime(
                        positionMs.coerceAtLeast(0L) * 1_000L,
                        MediaMetadataRetriever.OPTION_CLOSEST_SYNC
                    ) ?: throw IOException("Не удалось получить кадр из видео.")
                    val values = ContentValues().apply {
                        put(MediaStore.Images.Media.DISPLAY_NAME, buildVideoFrameFileName(System.currentTimeMillis()))
                        put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg")
                        put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/ChiyuriPlayer")
                        put(MediaStore.Images.Media.IS_PENDING, 1)
                    }
                    val destination = context.contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
                        ?: throw IOException("Android не разрешил сохранить снимок.")
                    try {
                        val output = context.contentResolver.openOutputStream(destination)
                            ?: throw IOException("Не удалось открыть файл снимка.")
                        output.use {
                            if (!bitmap!!.compress(Bitmap.CompressFormat.JPEG, 94, it)) {
                                throw IOException("Не удалось записать изображение.")
                            }
                        }
                        val published = ContentValues().apply { put(MediaStore.Images.Media.IS_PENDING, 0) }
                        context.contentResolver.update(destination, published, null, null)
                        destination
                    } catch (error: Exception) {
                        runCatching { context.contentResolver.delete(destination, null, null) }
                        throw error
                    }
                } finally {
                    bitmap?.recycle()
                    runCatching { retriever.release() }
                }
            }
        }
}
''', encoding="utf-8")

p = PKG / "MainActivity.kt"
replace_once(
    p,
    '                    onShowInfo = { showMediaInfo = true },',
    '''                    onShowInfo = { showMediaInfo = true },
                    onCaptureFrame = {
                        val source = player.currentMediaItem?.localConfiguration?.uri
                        if (source == null) {
                            android.widget.Toast.makeText(context, "Нет выбранного видео.", android.widget.Toast.LENGTH_SHORT).show()
                        } else {
                            coroutineScope.launch {
                                VideoFrameCapture.save(context, source, player.currentPosition)
                                    .onSuccess {
                                        android.widget.Toast.makeText(context, "Кадр сохранён в Pictures/ChiyuriPlayer.", android.widget.Toast.LENGTH_SHORT).show()
                                    }
                                    .onFailure {
                                        android.widget.Toast.makeText(context, it.message ?: "Не удалось сохранить кадр.", android.widget.Toast.LENGTH_LONG).show()
                                    }
                            }
                        }
                    },''',
    "frame capture callback"
)
replace_once(
    p,
    '    onShowInfo: () -> Unit,',
    '    onShowInfo: () -> Unit,\n    onCaptureFrame: () -> Unit,',
    "frame capture callback signature"
)
replace_once(
    p,
    '''                        DropdownMenuItem(
                            text = { Text("Редактировать информацию") },''',
    '''                        DropdownMenuItem(
                            text = { Text("Сохранить кадр видео") },
                            leadingIcon = { GothicIcon(Icons.Default.PhotoCamera, contentDescription = null) },
                            enabled = player.currentMediaItem?.localConfiguration?.mimeType?.startsWith("video/") == true,
                            onClick = { moreActionsExpanded = false; onCaptureFrame() }
                        )
                        DropdownMenuItem(
                            text = { Text("Редактировать информацию") },''',
    "video frame menu item"
)

(TEST / "VideoFrameCaptureTest.kt").write_text('''package com.chiyuri.player

import org.junit.Assert.assertEquals
import org.junit.Test

class VideoFrameCaptureTest {
    @Test fun frameFileNamesUseSafeNonNegativeTimestamps() {
        assertEquals("Chiyuri_Frame_12345.jpg", buildVideoFrameFileName(12345L))
        assertEquals("Chiyuri_Frame_0.jpg", buildVideoFrameFileName(-1L))
    }
}
''', encoding="utf-8")

print("patch_0455: local video frame capture to MediaStore added to mini-player actions")
