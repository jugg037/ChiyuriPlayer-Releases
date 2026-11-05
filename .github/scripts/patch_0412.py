from pathlib import Path
base = Path("src/main/java/com/chiyuri/player")

p = base / "AudioEffectsSettings.kt"
s = p.read_text(encoding="utf-8")
s = s.replace("import android.content.SharedPreferences\n", "import android.content.SharedPreferences\nimport kotlin.math.roundToInt\n")
s = s.replace("    val bassBoostStrength: Float = 0f,\n", "")
s = s.replace("        bassBoostStrength = bounded(config.bassBoostStrength, 0f, 1000f, 0f),\n", "")
s = s.replace("playerVolume = bounded(config.playerVolume, 1f, 2f, 1f)", "playerVolume = bounded(config.playerVolume, 1f, 3f, 1f)")
s = s.replace('    private const val KEY_BASS_STRENGTH = "bass_strength"\n', "")
s = s.replace("                bassBoostStrength = preferences.getFloat(KEY_BASS_STRENGTH, 0f),\n", "")
s = s.replace("            .putFloat(KEY_BASS_STRENGTH, normalized.bassBoostStrength)\n", "")
s += """
internal fun volumeBoostToMillibels(playerVolume: Float): Int {
    val multiplier = if (playerVolume.isFinite()) playerVolume.coerceIn(1f, 3f) else 1f
    return if (multiplier > 1f) {
        (2000f * kotlin.math.log10(multiplier)).roundToInt().coerceIn(0, 954)
    } else 0
}
"""
assert "bassBoostStrength" not in s and "KEY_BASS_STRENGTH" not in s
assert "1f, 3f, 1f" in s
p.write_text(s, encoding="utf-8")

p = base / "AudioEffectsController.kt"
s = p.read_text(encoding="utf-8")
s = s.replace("import android.media.audiofx.BassBoost\n", "")
s = s.replace("import kotlin.math.roundToInt\n", "")
s = s.replace("    private var bassBoost: BassBoost? = null\n", "")
s = s.replace("        bassBoost = runCatching { BassBoost(0, audioSessionId) }.getOrNull()\n", "")
s = s.replace("(2000f * kotlin.math.log10(config.playerVolume)).roundToInt().coerceIn(0, 602)", "volumeBoostToMillibels(config.playerVolume)")
start = s.find("        bassBoost?.let { effect ->")
if start >= 0:
    end = s.find("\n        }", start) + len("\n        }")
    s = s[:start] + s[end:]
s = s.replace("        runCatching { bassBoost?.release() }\n", "")
s = s.replace("        bassBoost = null\n", "")
assert "BassBoost" not in s and "bassBoost" not in s
p.write_text(s, encoding="utf-8")

p = base / "MainActivity.kt"
s = p.read_text(encoding="utf-8")
s = s.replace("config.playerVolume + 0.1f).coerceAtMost(2f)", "config.playerVolume + 0.1f).coerceAtMost(3f)")
start = s.find('        Surface(color = MaterialTheme.colorScheme.surface, shape = RoundedCornerShape(16.dp), modifier = Modifier.fillMaxWidth()) {\n            Column(Modifier.padding(16.dp)) {\n                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {\n                    Text("Усиление басов"')
assert start >= 0, "Bass Boost card not found"
end = s.find("\n        Surface(color = MaterialTheme.colorScheme.surface, shape = RoundedCornerShape(16.dp), modifier = Modifier.fillMaxWidth()) {", start + 20)
assert end > start, "End of Bass Boost card not found"
s = s[:start] + s[end:]
s = s.replace("(config.playerVolume - 1f).coerceIn(0f, 1f)", "(config.playerVolume - 1f).coerceIn(0f, 2f)")
s = s.replace("valueRange = 0f..1f,\n                    steps = 9", "valueRange = 0f..2f,\n                    steps = 19")
s = s.replace("от 0 до +100%. Кнопки громкости телефона управляют обоими уровнями.", "от 0 до +200%. Кнопки громкости телефона управляют обоими уровнями.")
s = s.replace("Доступность эквалайзера и усиления басов зависит от аудиодрайвера телефона. Регулятор громкости плеера работает независимо от них.", "Эквалайзер работает через аудиодрайвер телефона. Усиление громкости плеера работает независимо от эквалайзера.")
assert "Усиление басов" not in s and "coerceAtMost(3f)" in s and "valueRange = 0f..2f" in s
p.write_text(s, encoding="utf-8")

p = base / "VolumeIndicator.kt"
s = p.read_text(encoding="utf-8")
s = s.replace("((AudioEffectsSettings.load(context).playerVolume - 1f) * 100f)\n                .roundToInt().coerceIn(0, 100)", "((AudioEffectsSettings.load(context).playerVolume - 1f) * 100f)\n                .roundToInt().coerceIn(0, 200)")
s = s.replace("boostPercent / 100f", "boostPercent / 200f")
assert s.count("coerceIn(0, 200)") == 2 and "boostPercent / 200f" in s
p.write_text(s, encoding="utf-8")

p = base / "TrackMetadataRepository.kt"
s = p.read_text(encoding="utf-8")
marker = '''    /**
     * Writes metadata into the selected MP3, FLAC, or M4A/MP4 audio file.
'''
insert = r'''    fun hasWriteAccess(context: Context, uri: Uri): Boolean {
        val runtimeGrant = context.checkUriPermission(
            uri,
            android.os.Process.myPid(),
            android.os.Process.myUid(),
            android.content.Intent.FLAG_GRANT_WRITE_URI_PERMISSION
        ) == android.content.pm.PackageManager.PERMISSION_GRANTED
        val persistedGrant = runCatching {
            context.contentResolver.persistedUriPermissions.any { it.uri == uri && it.isWritePermission }
        }.getOrDefault(false)
        return runtimeGrant || persistedGrant
    }

    fun suggestedCopyName(context: Context, uri: Uri): String {
        val providerName = runCatching {
            context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
                if (cursor.moveToFirst()) {
                    val index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                    if (index >= 0) cursor.getString(index) else null
                } else null
            }
        }.getOrNull()
        val name = (providerName ?: uri.lastPathSegment?.substringAfterLast('/') ?: "track.mp3")
            .substringAfterLast('/')
            .replace(Regex("[\\\\/:*?\"<>|]"), "_")
            .ifBlank { "track.mp3" }
        if (name.contains('.') && name.substringAfterLast('.').lowercase() in setOf("mp3", "flac", "m4a", "mp4")) return name
        val mime = runCatching { context.contentResolver.getType(uri).orEmpty().lowercase() }.getOrDefault("")
        val extension = when (mime) {
            "audio/flac", "audio/x-flac" -> "flac"
            "audio/mp4", "audio/x-m4a", "video/mp4" -> "m4a"
            "audio/mpeg" -> "mp3"
            else -> throw IllegalArgumentException("Формат выбранного файла не поддерживается для сохранения копии.")
        }
        return "$name.$extension"
    }

    suspend fun prepareMetadataCopy(context: Context, uri: Uri, metadata: TrackMetadata): java.io.File =
        kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
            val displayName = suggestedCopyName(context, uri)
            val format = displayName.substringAfterLast('.', "mp3").lowercase()
            val workDir = java.io.File(context.cacheDir, "media-tag-write").apply {
                if (!exists() && !mkdirs()) throw java.io.IOException("Не удалось создать временную папку.")
                if (!isDirectory || !canWrite()) throw java.io.IOException("Временная папка недоступна для записи.")
            }
            val original = java.io.File.createTempFile("copy-original-", ".$format", workDir)
            val rewritten = java.io.File.createTempFile("copy-ready-", ".$format", workDir)
            try {
                val input = context.contentResolver.openInputStream(uri)
                    ?: throw java.io.IOException("Нет разрешения на чтение выбранного файла.")
                java.io.FileOutputStream(original).use { output ->
                    input.use { it.copyTo(output) }
                    output.fd.sync()
                }
                require(original.length() > 0L) { "Исходный файл пуст или недоступен." }
                val artwork = downloadArtwork(metadata.artworkUrl)
                when (format) {
                    "mp3" -> Mp3Id3TagWriter.rewrite(original, rewritten, metadata, artwork)
                    "flac" -> FlacMetadataWriter.rewrite(original, rewritten, metadata, artwork)
                    "m4a", "mp4" -> Mp4MetadataWriter.rewrite(original, rewritten, metadata, artwork)
                    else -> throw IllegalArgumentException("Формат файла не поддерживается для копирования.")
                }
                require(rewritten.isFile && rewritten.length() > 0L) { "Не удалось подготовить копию с метаданными." }
                rewritten
            } catch (cancelled: kotlinx.coroutines.CancellationException) {
                rewritten.delete()
                throw cancelled
            } catch (error: Exception) {
                rewritten.delete()
                throw error
            } finally {
                original.delete()
            }
        }

    suspend fun writePreparedCopy(context: Context, destination: Uri, prepared: java.io.File): String? =
        kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
            try {
                val output = context.contentResolver.openOutputStream(destination, "w")
                    ?: throw java.io.IOException("Провайдер не разрешил создать файл.")
                output.use { stream ->
                    prepared.inputStream().use { input -> input.copyTo(stream) }
                    stream.flush()
                    if (stream is java.io.FileOutputStream) stream.fd.sync()
                }
                if (!contentMatches(context, destination, prepared)) {
                    throw java.io.IOException("Проверка копии не пройдена: записанные данные отличаются.")
                }
                null
            } catch (cancelled: kotlinx.coroutines.CancellationException) {
                throw cancelled
            } catch (error: Exception) {
                "Не удалось сохранить копию: " + describeMetadataFailure(error)
            } finally {
                prepared.delete()
            }
        }

'''
assert marker in s and "fun hasWriteAccess(" not in s
s = s.replace(marker, insert + marker, 1)
p.write_text(s, encoding="utf-8")

p = base / "TrackDetailsComponents.kt"
s = p.read_text(encoding="utf-8")
s = s.replace("import androidx.compose.runtime.Composable\n", "import androidx.activity.compose.rememberLauncherForActivityResult\nimport androidx.activity.result.contract.ActivityResultContracts\nimport androidx.compose.runtime.Composable\n", 1)
old = '''    var message by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    AlertDialog('''
new = '''    var message by remember { mutableStateOf<String?>(null) }
    var pendingCopyFile by remember { mutableStateOf<java.io.File?>(null) }
    var pendingCopyMetadata by remember { mutableStateOf<TrackMetadata?>(null) }
    val scope = rememberCoroutineScope()
    val copyLauncher = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("audio/*")) { destination ->
        val prepared = pendingCopyFile
        val edited = pendingCopyMetadata
        pendingCopyFile = null
        pendingCopyMetadata = null
        if (destination == null) {
            prepared?.delete()
            writingToFile = false
            message = "Создание копии отменено. Исходный файл не изменён."
        } else if (prepared != null && edited != null) {
            scope.launch {
                try {
                    val error = TrackMetadataRepository.writePreparedCopy(context, destination, prepared)
                    if (error == null) {
                        TrackMetadataRepository.saveOverride(context, destination, edited)
                        message = "Копия сохранена и проверена. Открой её из библиотеки, чтобы использовать изменённый файл."
                        android.widget.Toast.makeText(context, "Копия файла сохранена", android.widget.Toast.LENGTH_LONG).show()
                    } else {
                        message = error
                        android.widget.Toast.makeText(context, error, android.widget.Toast.LENGTH_LONG).show()
                    }
                } finally {
                    writingToFile = false
                }
            }
        } else {
            prepared?.delete()
            writingToFile = false
        }
    }

    AlertDialog('''
assert old in s and "pendingCopyFile" not in s
s = s.replace(old, new, 1)
old = '''                Text("Найди сведения в интернете, затем проверь и отредактируй их перед сохранением.", color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 12.sp)
                OutlinedTextField(title,'''
new = '''                Text("Найди сведения в интернете, затем проверь и отредактируй их перед сохранением.", color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 12.sp)
                Text(
                    if (uri != null && TrackMetadataRepository.hasWriteAccess(context, uri))
                        "Разрешение на перезапись файла обнаружено. После записи будет выполнена проверка содержимого."
                    else
                        "У приложения нет явного разрешения на перезапись этого файла. При сохранении будет предложено создать проверенную копию, не изменяя оригинал.",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    style = MaterialTheme.typography.bodySmall
                )
                OutlinedTextField(title,'''
assert old in s
s = s.replace(old, new, 1)
start = s.index("        confirmButton = {", s.index("internal fun TrackMetadataEditorDialog"))
end = s.index("        dismissButton = {", start)
block = r'''        confirmButton = {
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                TextButton(
                    enabled = uri != null && !loading && !writingToFile && title.isNotBlank(),
                    onClick = {
                        val edited = TrackMetadata(
                            title.trim(), artist.trim(), album.trim(), year.trim(),
                            artworkUrl.trim(), plainLyrics, syncedLyrics
                        )
                        if (writingToFile) return@TextButton
                        writingToFile = true
                        message = "Проверяем разрешение и сохраняем метаданные…"
                        scope.launch {
                            try {
                                val targetUri = uri ?: throw IllegalStateException("Не выбран аудиофайл.")
                                if (!TrackMetadataRepository.hasWriteAccess(context, targetUri)) {
                                    message = "Нет разрешения на перезапись исходника. Подготавливаем копию…"
                                    val prepared = TrackMetadataRepository.prepareMetadataCopy(context, targetUri, edited)
                                    pendingCopyFile = prepared
                                    pendingCopyMetadata = edited
                                    copyLauncher.launch(TrackMetadataRepository.suggestedCopyName(context, targetUri))
                                } else {
                                    val error = TrackMetadataRepository.writeMetadataToFile(context, targetUri, edited)
                                    if (error == null) {
                                        TrackMetadataRepository.saveOverride(context, targetUri, edited)
                                        onApply(edited)
                                        message = "Метаданные записаны и проверены."
                                        android.widget.Toast.makeText(context, "Изменения сохранены", android.widget.Toast.LENGTH_SHORT).show()
                                        writingToFile = false
                                    } else if (error.contains("Исходный файл восстановлен", ignoreCase = true)) {
                                        message = "Перезапись не удалась, исходник восстановлен. Подготавливаем отдельную копию…"
                                        val prepared = TrackMetadataRepository.prepareMetadataCopy(context, targetUri, edited)
                                        pendingCopyFile = prepared
                                        pendingCopyMetadata = edited
                                        copyLauncher.launch(TrackMetadataRepository.suggestedCopyName(context, targetUri))
                                    } else {
                                        message = "Не удалось сохранить файл: " + error
                                        android.widget.Toast.makeText(context, message, android.widget.Toast.LENGTH_LONG).show()
                                        writingToFile = false
                                    }
                                }
                            } catch (cancelled: kotlinx.coroutines.CancellationException) {
                                message = "Сохранение отменено. Проверь состояние исходного файла и резервной копии."
                                writingToFile = false
                                throw cancelled
                            } catch (error: Exception) {
                                message = "Не удалось сохранить файл: " + (error.message ?: "неизвестная ошибка")
                                android.widget.Toast.makeText(context, message, android.widget.Toast.LENGTH_LONG).show()
                                writingToFile = false
                            }
                        }
                    }
                ) {
                    if (writingToFile) CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                    else Text("Сохранить")
                }
                OutlinedButton(
                    enabled = uri != null && !loading && !writingToFile && title.isNotBlank(),
                    onClick = {
                        val edited = TrackMetadata(
                            title.trim(), artist.trim(), album.trim(), year.trim(),
                            artworkUrl.trim(), plainLyrics, syncedLyrics
                        )
                        if (writingToFile) return@OutlinedButton
                        writingToFile = true
                        message = "Подготавливаем копию файла…"
                        scope.launch {
                            try {
                                val targetUri = uri ?: throw IllegalStateException("Не выбран аудиофайл.")
                                val prepared = TrackMetadataRepository.prepareMetadataCopy(context, targetUri, edited)
                                pendingCopyFile = prepared
                                pendingCopyMetadata = edited
                                copyLauncher.launch(TrackMetadataRepository.suggestedCopyName(context, targetUri))
                            } catch (error: Exception) {
                                message = "Не удалось подготовить копию: " + (error.message ?: "неизвестная ошибка")
                                android.widget.Toast.makeText(context, message, android.widget.Toast.LENGTH_LONG).show()
                                writingToFile = false
                            }
                        }
                    }
                ) { Text("Сохранить копию…") }
            }
        },
'''
s = s[:start] + block + s[end:]
assert "rememberLauncherForActivityResult" in s and 'CreateDocument("audio/*")' in s
assert "Сохранить копию…" in s and "hasWriteAccess(context, uri)" in s
p.write_text(s, encoding="utf-8")

p = base / "MainActivity.kt"
s = p.read_text(encoding="utf-8")
old = '''            try {
                context.contentResolver.takePersistableUriPermission(
                    uri,
                    android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION
                )
            } catch (_: SecurityException) {
                // MediaStore and some providers do not support persistable grants.
            }
            try {
                context.contentResolver.takePersistableUriPermission(
                    uri,
                    android.content.Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                )
            } catch (_: SecurityException) {
                // Read-only providers remain playable; the editor will report that writes are unavailable.
            }'''
new = '''            try {
                context.contentResolver.takePersistableUriPermission(
                    uri,
                    android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION or
                        android.content.Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                )
            } catch (_: SecurityException) {
                try {
                    context.contentResolver.takePersistableUriPermission(
                        uri,
                        android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION
                    )
                } catch (_: SecurityException) {
                    // The temporary picker grant remains usable for this session.
                }
            }'''
assert old in s, "Audio picker URI grant block not found"
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

p = Path("src/test/java/com/chiyuri/player/PlaceholderTest.kt")
s = p.read_text(encoding="utf-8")
s = s.replace("fun clampsEqualizerBassAndVolumeValues()", "fun clampsEqualizerAndVolumeValues()")
s = s.replace("                bassBoostStrength = 1200f,\n", "")
s = s.replace("        assertEquals(1000f, normalized.bassBoostStrength, 0f)\n", "")
s = s.replace("                bassBoostStrength = Float.NaN,\n", "")
s = s.replace("        assertEquals(0f, normalized.bassBoostStrength, 0f)\n", "")
s = s.replace("assertEquals(2f, normalized.playerVolume, 0f)", "assertEquals(2.5f, normalized.playerVolume, 0f)", 1)
s = s.replace("fun boostIsClampedToOneHundredPercentAboveAndroidVolume()", "fun boostIsClampedToTwoHundredPercentAboveAndroidVolume()")
s = s.replace("AudioEffectsConfig(playerVolume = 3f)", "AudioEffectsConfig(playerVolume = 3.5f)")
s = s.replace('''        assertEquals(2f, normalized.playerVolume, 0f)
    }
}''', '''        assertEquals(3f, normalized.playerVolume, 0f)
    }

    @Test
    fun mapsVolumeBoostToLoudnessEnhancerGain() {
        assertEquals(0, volumeBoostToMillibels(1f))
        assertEquals(602, volumeBoostToMillibels(2f))
        assertEquals(954, volumeBoostToMillibels(3f))
        assertEquals(0, volumeBoostToMillibels(Float.NaN))
    }
}''')
assert "bassBoostStrength" not in s and "mapsVolumeBoostToLoudnessEnhancerGain" in s
p.write_text(s, encoding="utf-8")

print("ChiyuriPlayer 0.4.12 patch applied.")
