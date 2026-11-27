from pathlib import Path
ROOT = Path.cwd()
PKG = ROOT / "app/src/main/java/com/chiyuri/player"
TEST = ROOT / "app/src/test/java/com/chiyuri/player"

p = PKG / "MediaLibrarySorting.kt"
s = p.read_text(encoding="utf-8")
s += '''

/** Returns IDs of likely duplicate recordings (same normalized title/artist, duration within 2 seconds). */
internal fun findPotentialDuplicateIds(items: List<MediaSortKey>): Set<Long> {
    val groups = items.filter { it.durationMs > 0L && it.title.isNotBlank() }.groupBy { item ->
        val title = item.title.lowercase().filter { it.isLetterOrDigit() }
        val artist = item.artist.orEmpty().lowercase().filter { it.isLetterOrDigit() }
        "$title|$artist"
    }
    val duplicates = mutableSetOf<Long>()
    groups.values.forEach { group ->
        val sorted = group.sortedBy { it.durationMs }
        var cluster = mutableListOf<MediaSortKey>()
        sorted.forEach { item ->
            if (cluster.isEmpty() || item.durationMs - cluster.first().durationMs <= 2_000L) {
                cluster += item
            } else {
                if (cluster.size > 1) duplicates += cluster.map { it.id }
                cluster = mutableListOf(item)
            }
        }
        if (cluster.size > 1) duplicates += cluster.map { it.id }
    }
    return duplicates
}
'''
p.write_text(s, encoding="utf-8")

p = PKG / "MainActivity.kt"
s = p.read_text(encoding="utf-8")
s = s.replace('''    var favoritesOnly by remember(isVideo) { mutableStateOf(false) }

    val folders''', '''    var favoritesOnly by remember(isVideo) { mutableStateOf(false) }
    var duplicatesOnly by remember(isVideo) { mutableStateOf(false) }
    val potentialDuplicateIds = remember(mediaItems) {
        findPotentialDuplicateIds(mediaItems.map { MediaSortKey(it.id, it.title, it.artist, it.durationMs, it.album, it.dateAddedSeconds) })
    }

    val folders''', 1)
s = s.replace('''    val visibleItems = remember(mediaItems, searchQuery, selectedFolder, favorites, favoritesOnly) {''', '''    val visibleItems = remember(mediaItems, searchQuery, selectedFolder, favorites, favoritesOnly, duplicatesOnly, potentialDuplicateIds) {''', 1)
s = s.replace('''            val matchesFavorite = isVideo || !favoritesOnly || item.uri.toString() in favorites
            matchesQuery && matchesFavorite && (selectedFolder == null || itemFolder == selectedFolder)''', '''            val matchesFavorite = isVideo || !favoritesOnly || item.uri.toString() in favorites
            val matchesDuplicate = !duplicatesOnly || item.id in potentialDuplicateIds
            matchesQuery && matchesFavorite && matchesDuplicate && (selectedFolder == null || itemFolder == selectedFolder)''', 1)
anchor = '''                        DropdownMenuItem(
                            text = { Text("Дата добавления" + if (sortOrder == MediaSortOrder.DATE_ADDED) " ✓" else "") },
                            onClick = { sortOrder = MediaSortOrder.DATE_ADDED; filtersMenuExpanded = false }
                        )
                        DropdownMenuItem('''
replacement = '''                        DropdownMenuItem(
                            text = { Text("Дата добавления" + if (sortOrder == MediaSortOrder.DATE_ADDED) " ✓" else "") },
                            onClick = { sortOrder = MediaSortOrder.DATE_ADDED; filtersMenuExpanded = false }
                        )
                        DropdownMenuItem(
                            text = { Text(if (duplicatesOnly) "Показывать все файлы ✓" else "Вероятные дубликаты") },
                            onClick = { duplicatesOnly = !duplicatesOnly; filtersMenuExpanded = false }
                        )
                        DropdownMenuItem('''
if anchor not in s: raise SystemExit("patch_0443: duplicate filter menu anchor missing")
s = s.replace(anchor, replacement, 1)
s = s.replace('''                if (favoritesOnly) "В избранном пока нет композиций." else "Ничего не найдено в выбранной папке или по этому запросу.",''', '''                when {
                    favoritesOnly -> "В избранном пока нет композиций."
                    duplicatesOnly -> "Вероятные дубликаты не найдены."
                    else -> "Ничего не найдено в выбранной папке или по этому запросу."
                },''', 1)
p.write_text(s, encoding="utf-8")

p = PKG / "PlaybackHistoryScreen.kt"
s = p.read_text(encoding="utf-8")
s = s.replace('import androidx.compose.foundation.layout.padding\n', 'import androidx.compose.foundation.layout.padding\nimport androidx.compose.foundation.horizontalScroll\nimport androidx.compose.foundation.rememberScrollState\n', 1)
s = s.replace('private enum class HistoryFilter { RECENT, MOST_PLAYED, FAVORITES }', 'private enum class HistoryFilter { RECENT, MOST_PLAYED, FAVORITES, RECENTLY_ADDED }', 1)
old = '''    val favorites = remember(context) { FavoriteTracksStore.load(context) }
    val visible = when (filter) {
        HistoryFilter.RECENT -> entries.sortedByDescending { it.lastPlayedAt }
        HistoryFilter.MOST_PLAYED -> entries.sortedWith(compareByDescending<PlaybackHistoryEntry> { it.playCount }.thenByDescending { it.lastPlayedAt })
        HistoryFilter.FAVORITES -> entries.filter { it.uri in favorites }.sortedByDescending { it.lastPlayedAt }
    }'''
new = '''    var favorites by remember(context) { mutableStateOf(FavoriteTracksStore.load(context)) }
    var libraryItems by remember(context) { mutableStateOf(LocalMediaRepository.loadCached(context, false)) }
    androidx.compose.runtime.DisposableEffect(context) {
        val preferences = context.getSharedPreferences("favorite_tracks", android.content.Context.MODE_PRIVATE)
        val listener = android.content.SharedPreferences.OnSharedPreferenceChangeListener { _, _ ->
            favorites = FavoriteTracksStore.load(context)
        }
        preferences.registerOnSharedPreferenceChangeListener(listener)
        onDispose { preferences.unregisterOnSharedPreferenceChangeListener(listener) }
    }
    LaunchedEffect(Unit) {
        libraryItems = LocalMediaRepository.loadCached(context, false)
    }
    val favoriteItems = libraryItems.filter { it.uri.toString() in favorites }
    val recentlyAddedItems = libraryItems.sortedByDescending { it.dateAddedSeconds }
    val visible = when (filter) {
        HistoryFilter.RECENT -> entries.sortedByDescending { it.lastPlayedAt }
        HistoryFilter.MOST_PLAYED -> entries.sortedWith(compareByDescending<PlaybackHistoryEntry> { it.playCount }.thenByDescending { it.lastPlayedAt })
        HistoryFilter.FAVORITES, HistoryFilter.RECENTLY_ADDED -> emptyList()
    }'''
if old not in s: raise SystemExit("patch_0443: smart collections source anchor missing")
s = s.replace(old, new, 1)
old = '''        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            FilterChip(selected = filter == HistoryFilter.RECENT, onClick = { filter = HistoryFilter.RECENT }, label = { Text("Недавние") })
            FilterChip(selected = filter == HistoryFilter.MOST_PLAYED, onClick = { filter = HistoryFilter.MOST_PLAYED }, label = { Text("Частые") })
            FilterChip(selected = filter == HistoryFilter.FAVORITES, onClick = { filter = HistoryFilter.FAVORITES }, label = { Text("Избранное") })
        }
        if (visible.isEmpty()) {'''
new = '''        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            FilterChip(selected = filter == HistoryFilter.RECENT, onClick = { filter = HistoryFilter.RECENT }, label = { Text("Недавние") })
            FilterChip(selected = filter == HistoryFilter.MOST_PLAYED, onClick = { filter = HistoryFilter.MOST_PLAYED }, label = { Text("Частые") })
            FilterChip(selected = filter == HistoryFilter.FAVORITES, onClick = { filter = HistoryFilter.FAVORITES }, label = { Text("Избранное") })
            FilterChip(selected = filter == HistoryFilter.RECENTLY_ADDED, onClick = { filter = HistoryFilter.RECENTLY_ADDED }, label = { Text("Добавленные") })
        }
        val localCollection = when (filter) {
            HistoryFilter.FAVORITES -> favoriteItems
            HistoryFilter.RECENTLY_ADDED -> recentlyAddedItems
            else -> emptyList()
        }
        if (filter == HistoryFilter.FAVORITES || filter == HistoryFilter.RECENTLY_ADDED) {
            if (localCollection.isEmpty()) {
                Text(if (filter == HistoryFilter.FAVORITES) "Избранных композиций пока нет" else "Недавно добавленных композиций пока нет", color = MaterialTheme.colorScheme.onSurfaceVariant)
            } else {
                LazyColumn(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    items(localCollection, key = { it.id }) { item ->
                        Surface(
                            color = MaterialTheme.colorScheme.surface,
                            shape = MaterialTheme.shapes.medium,
                            modifier = Modifier.fillMaxWidth().clickable {
                                val metadata = MediaMetadata.Builder().setTitle(item.title).setArtist(item.artist).setAlbumTitle(item.album).build()
                                val mediaItem = MediaItem.Builder().setUri(item.uri).setMimeType(item.mimeType).setMediaMetadata(metadata).build()
                                player.setMediaItem(mediaItem, PlaybackQueueStore.savedPosition(context, item.uri.toString()))
                                player.prepare()
                                player.play()
                            }
                        ) {
                            Column(Modifier.padding(horizontal = 14.dp, vertical = 11.dp)) {
                                Text(item.title, color = MaterialTheme.colorScheme.onSurface, maxLines = 1)
                                Text(listOfNotNull(item.artist, item.album).joinToString(" • ").ifBlank { item.mimeType.orEmpty() }, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall, maxLines = 1)
                            }
                        }
                    }
                }
            }
        } else if (visible.isEmpty()) {'''
if old not in s: raise SystemExit("patch_0443: smart collections UI anchor missing")
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

(TEST / "MediaLibrarySortingTest.kt").write_text('''package com.chiyuri.player

import org.junit.Assert.assertEquals
import org.junit.Test

class MediaLibraryDuplicateDetectionTest {
    @Test fun likelyDuplicatesRequireSameTitleArtistAndNearDuration() {
        val items = listOf(
            MediaSortKey(1, "Song", "Artist", 180_000),
            MediaSortKey(2, " song ", "Artist", 181_500),
            MediaSortKey(3, "Song", "Other", 180_000),
            MediaSortKey(4, "Song", "Artist", 190_000)
        )
        assertEquals(setOf(1L, 2L), findPotentialDuplicateIds(items))
    }

    @Test fun emptyTitlesAndUnknownDurationsAreIgnored() {
        val items = listOf(
            MediaSortKey(1, "", "Artist", 1000),
            MediaSortKey(2, "", "Artist", 1000),
            MediaSortKey(3, "Song", "Artist", 0),
            MediaSortKey(4, "Song", "Artist", 0)
        )
        assertEquals(emptySet<Long>(), findPotentialDuplicateIds(items))
    }
}
''', encoding="utf-8")

print("patch_0443: probable duplicate filter and complete smart collections applied")
