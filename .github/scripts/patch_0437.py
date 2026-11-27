from pathlib import Path
ROOT = Path.cwd()
PKG = ROOT / "app/src/main/java/com/chiyuri/player"
TEST = ROOT / "app/src/test/java/com/chiyuri/player"

def replace_once(path, old, new, label):
    s = path.read_text(encoding="utf-8")
    if old not in s: raise SystemExit(f"patch_0437: missing {label}")
    path.write_text(s.replace(old, new, 1), encoding="utf-8")

p = PKG / "MediaLibrarySorting.kt"
s = p.read_text(encoding="utf-8")
s = s.replace('''    TITLE,
    ARTIST,
    DURATION
}''', '''    TITLE,
    ARTIST,
    ALBUM,
    DURATION,
    DATE_ADDED
}''', 1)
s = s.replace('''    val artist: String?,
    val durationMs: Long
)''', '''    val artist: String?,
    val durationMs: Long,
    val album: String? = null,
    val dateAddedSeconds: Long = 0L
)''', 1)
s = s.replace('''        MediaSortOrder.DURATION -> compareBy<MediaSortKey> { it.durationMs }
            .thenBy { it.title.lowercase() }
            .thenBy { it.id }''', '''        MediaSortOrder.ALBUM -> compareBy<MediaSortKey> { it.album.orEmpty().lowercase() }
            .thenBy { it.title.lowercase() }
            .thenBy { it.id }
        MediaSortOrder.DURATION -> compareBy<MediaSortKey> { it.durationMs }
            .thenBy { it.title.lowercase() }
            .thenBy { it.id }
        MediaSortOrder.DATE_ADDED -> compareBy<MediaSortKey> { it.dateAddedSeconds }
            .thenBy { it.title.lowercase() }
            .thenBy { it.id }''', 1)
s = s.replace('MediaSortKey(it.id, it.title, it.artist, it.durationMs)', 'MediaSortKey(it.id, it.title, it.artist, it.durationMs, it.album, it.dateAddedSeconds)', 1)
p.write_text(s, encoding="utf-8")

p = PKG / "LocalMediaRepository.kt"
s = p.read_text(encoding="utf-8")
s = s.replace('''    val isVideo: Boolean,
    val relativePath: String? = null
)''', '''    val isVideo: Boolean,
    val relativePath: String? = null,
    val dateAddedSeconds: Long = 0L
)''', 1)
s = s.replace('''                MediaStore.MediaColumns.RELATIVE_PATH
            ),
            isVideo = false''', '''                MediaStore.MediaColumns.RELATIVE_PATH,
                MediaStore.MediaColumns.DATE_ADDED
            ),
            isVideo = false''', 1)
s = s.replace('''                MediaStore.MediaColumns.RELATIVE_PATH
            ),
            isVideo = true''', '''                MediaStore.MediaColumns.RELATIVE_PATH,
                MediaStore.MediaColumns.DATE_ADDED
            ),
            isVideo = true''', 1)
s = s.replace('''                        relativePath = item.optNullableString("relativePath")
                    ))''', '''                        relativePath = item.optNullableString("relativePath"),
                        dateAddedSeconds = item.optLong("dateAddedSeconds", 0L).coerceAtLeast(0L)
                    ))''', 1)
s = s.replace('''.put("relativePath", media.relativePath ?: JSONObject.NULL))''', '''.put("relativePath", media.relativePath ?: JSONObject.NULL)
                .put("dateAddedSeconds", media.dateAddedSeconds))''', 1)
s = s.replace('''                val relativePathColumn = cursor.getColumnIndex(MediaStore.MediaColumns.RELATIVE_PATH)

                while''', '''                val relativePathColumn = cursor.getColumnIndex(MediaStore.MediaColumns.RELATIVE_PATH)
                val dateAddedColumn = cursor.getColumnIndex(MediaStore.MediaColumns.DATE_ADDED)

                while''', 1)
s = s.replace('''                        relativePath = if (relativePathColumn >= 0) cursor.getString(relativePathColumn) else null
                    )''', '''                        relativePath = if (relativePathColumn >= 0) cursor.getString(relativePathColumn) else null,
                        dateAddedSeconds = if (dateAddedColumn >= 0) cursor.getLong(dateAddedColumn).coerceAtLeast(0L) else 0L
                    )''', 1)
p.write_text(s, encoding="utf-8")

p = PKG / "MainActivity.kt"
s = p.read_text(encoding="utf-8")
anchor = '''                        if (!isVideo) {
                            DropdownMenuItem(
                                text = { Text("Исполнитель" + if (sortOrder == MediaSortOrder.ARTIST) " ✓" else "") },
                                onClick = { sortOrder = MediaSortOrder.ARTIST; filtersMenuExpanded = false }
                            )
                        }
                        DropdownMenuItem(
                            text = { Text("Длительность"'''
replacement = '''                        if (!isVideo) {
                            DropdownMenuItem(
                                text = { Text("Исполнитель" + if (sortOrder == MediaSortOrder.ARTIST) " ✓" else "") },
                                onClick = { sortOrder = MediaSortOrder.ARTIST; filtersMenuExpanded = false }
                            )
                            DropdownMenuItem(
                                text = { Text("Альбом" + if (sortOrder == MediaSortOrder.ALBUM) " ✓" else "") },
                                onClick = { sortOrder = MediaSortOrder.ALBUM; filtersMenuExpanded = false }
                            )
                        }
                        DropdownMenuItem(
                            text = { Text("Дата добавления" + if (sortOrder == MediaSortOrder.DATE_ADDED) " ✓" else "") },
                            onClick = { sortOrder = MediaSortOrder.DATE_ADDED; filtersMenuExpanded = false }
                        )
                        DropdownMenuItem(
                            text = { Text("Длительность"'''
if anchor not in s: raise SystemExit("patch_0437: library sorting menu anchor missing")
s = s.replace(anchor, replacement, 1)
s = s.replace('''                                item.artist?.takeIf { it.isNotBlank() },
                                if (isVideo) formatMediaDuration(item.durationMs) else formatMediaDuration(item.durationMs),''', '''                                item.artist?.takeIf { it.isNotBlank() },
                                item.album?.takeIf { it.isNotBlank() },
                                formatMediaDuration(item.durationMs),''', 1)
p.write_text(s, encoding="utf-8")

p = TEST / "PlaceholderTest.kt"
s = p.read_text(encoding="utf-8")
anchor = '''    @Test
    fun doesNotMutateOriginalList() {'''
insert = '''    @Test
    fun sortsByAlbumAndDateAdded() {
        val input = listOf(
            MediaSortKey(1, "Track A", "Artist", 1000, "Z Album", 100L),
            MediaSortKey(2, "Track B", "Artist", 1000, "A Album", 300L),
            MediaSortKey(3, "Track C", "Artist", 1000, "A Album", 200L)
        )
        assertEquals(listOf(2L, 3L, 1L), sortMediaKeys(input, MediaSortOrder.ALBUM).map { it.id })
        assertEquals(listOf(1L, 3L, 2L), sortMediaKeys(input, MediaSortOrder.DATE_ADDED).map { it.id })
        assertEquals(listOf(2L, 3L, 1L), sortMediaKeys(input, MediaSortOrder.DATE_ADDED, descending = true).map { it.id })
    }

'''
if anchor not in s: raise SystemExit("patch_0437: sorting test insertion anchor missing")
s = s.replace(anchor, insert + anchor, 1)
p.write_text(s, encoding="utf-8")

print("patch_0437: album/date sorting and cached MediaStore DATE_ADDED metadata applied")
