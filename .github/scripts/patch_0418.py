from pathlib import Path

source_path = Path("app/src/main/java/com/chiyuri/player/MainActivity.kt")
source = source_path.read_text(encoding="utf-8")

def replace_once(old: str, new: str, label: str) -> None:
    global source
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one source match, found {count}")
    source = source.replace(old, new, 1)

# Imports for a queue list that can be positioned at the active item.
replace_once(
    "import androidx.compose.foundation.background\n",
    "import androidx.compose.foundation.BorderStroke\nimport androidx.compose.foundation.background\n",
    "BorderStroke import"
)
replace_once(
    "import androidx.compose.foundation.lazy.LazyColumn\n",
    "import androidx.compose.foundation.lazy.LazyColumn\nimport androidx.compose.foundation.lazy.rememberLazyListState\n",
    "LazyListState import"
)

# Keep the current media URI as observable Compose state so the library row
# follows transitions initiated from the queue, playlists, notifications or UI.
replace_once(
    '    var artist by remember { mutableStateOf(player.currentMediaItem?.mediaMetadata?.artist?.toString().orEmpty()) }\n',
    '    var artist by remember { mutableStateOf(player.currentMediaItem?.mediaMetadata?.artist?.toString().orEmpty()) }\n'
    '    var currentMediaUri by remember { mutableStateOf(player.currentMediaItem?.localConfiguration?.uri?.toString()) }\n',
    "current media URI state"
)
replace_once(
    '    var showQueue by remember { mutableStateOf(false) }\n',
    '    var showQueue by remember { mutableStateOf(false) }\n',
    "queue dialog state"
)
replace_once(
    '    if (showQueue) {\n'
    '        val queuedItems = remember(showQueue, queueVersion) {\n',
    '    if (showQueue) {\n'
    '        val queueListState = rememberLazyListState(\n'
    '            initialFirstVisibleItemIndex = player.currentMediaItemIndex.coerceAtLeast(0)\n'
    '        )\n'
    '        val queuedItems = remember(showQueue, queueVersion) {\n',
    "queue initial active position"
)
replace_once(
    '                val uri = mediaItem?.localConfiguration?.uri\n'
    '                title = mediaItem?.mediaMetadata?.title?.toString()\n',
    '                val uri = mediaItem?.localConfiguration?.uri\n'
    '                currentMediaUri = uri?.toString()\n'
    '                title = mediaItem?.mediaMetadata?.title?.toString()\n',
    "track transition URI update"
)

# Queue: make the active row unmistakable and scroll to it whenever the dialog opens.
replace_once(
    '                    LazyColumn(\n'
    '                        modifier = Modifier.fillMaxWidth().heightIn(max = 420.dp),\n'
    '                        verticalArrangement = Arrangement.spacedBy(6.dp)\n'
    '                    ) {\n',
    '                    LazyColumn(\n'
    '                        state = queueListState,\n'
    '                        modifier = Modifier.fillMaxWidth().heightIn(max = 420.dp),\n'
    '                        verticalArrangement = Arrangement.spacedBy(6.dp)\n'
    '                    ) {\n',
    "queue LazyColumn state"
)
replace_once(
    '                            val itemTitle = queuedItem.mediaMetadata.title?.toString()\n'
    '                                ?: queuedItem.localConfiguration?.uri?.lastPathSegment\n'
    '                                ?: "Медиафайл ${index + 1}"\n'
    '                            Surface(\n'
    '                                color = if (index == player.currentMediaItemIndex) MaterialTheme.colorScheme.primary.copy(alpha = 0.18f) else MaterialTheme.colorScheme.surface,\n'
    '                                shape = RoundedCornerShape(10.dp),\n',
    '                            val itemTitle = queuedItem.mediaMetadata.title?.toString()\n'
    '                                ?: queuedItem.localConfiguration?.uri?.lastPathSegment\n'
    '                                ?: "Медиафайл ${index + 1}"\n'
    '                            val isCurrentItem = index == player.currentMediaItemIndex\n'
    '                            Surface(\n'
    '                                color = if (isCurrentItem) MaterialTheme.colorScheme.primary.copy(alpha = 0.22f) else MaterialTheme.colorScheme.surface,\n'
    '                                shape = RoundedCornerShape(10.dp),\n'
    '                                border = if (isCurrentItem) BorderStroke(1.5.dp, MaterialTheme.colorScheme.primary) else null,\n',
    "queue active item emphasis"
)
replace_once(
    '                                        Text("${index + 1}.", color = MaterialTheme.colorScheme.primary)\n'
    '                                        Spacer(Modifier.width(8.dp))\n'
    '                                        Text(itemTitle, color = MaterialTheme.colorScheme.onSurface, maxLines = 2)\n',
    '                                        GothicIcon(\n'
    '                                            if (isCurrentItem) Icons.Default.PlayArrow else Icons.Default.MusicNote,\n'
    '                                            contentDescription = if (isCurrentItem) "Сейчас воспроизводится" else null,\n'
    '                                            tint = MaterialTheme.colorScheme.primary\n'
    '                                        )\n'
    '                                        Spacer(Modifier.width(8.dp))\n'
    '                                        Column(Modifier.weight(1f)) {\n'
    '                                            Text("${index + 1}. $itemTitle", color = MaterialTheme.colorScheme.onSurface, maxLines = 2)\n'
    '                                            if (isCurrentItem) {\n'
    '                                                Text("СЕЙЧАС ВОСПРОИЗВОДИТСЯ", color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.labelSmall)\n'
    '                                            }\n'
    '                                        }\n',
    "queue current item label"
)

# Pass the active URI into the library and visually mark its matching row.
replace_once(
    '                            onPlay = onPickAudio,\n'
    '                            onPlayQueue = { items, selectedIndex ->\n',
    '                            onPlay = onPickAudio,\n'
    '                            currentMediaUri = currentMediaUri,\n'
    '                            onPlayQueue = { items, selectedIndex ->\n',
    "library current URI argument"
)
replace_once(
    'private fun LocalMediaBrowser(\n'
    '    isVideo: Boolean,\n'
    '    onPlay: (Uri) -> Unit,\n'
    '    onPlayQueue: ((List<LocalMedia>, Int) -> Unit)? = null\n'
    ') {\n',
    'private fun LocalMediaBrowser(\n'
    '    isVideo: Boolean,\n'
    '    onPlay: (Uri) -> Unit,\n'
    '    currentMediaUri: String? = null,\n'
    '    onPlayQueue: ((List<LocalMedia>, Int) -> Unit)? = null\n'
    ') {\n',
    "library current URI parameter"
)
replace_once(
    '            items(sortedItems, key = { "${if (isVideo) "video" else "audio"}-${it.id}" }) { item ->\n'
    '                Surface(\n'
    '                    color = MaterialTheme.colorScheme.surface,\n'
    '                    shape = RoundedCornerShape(12.dp),\n',
    '            items(sortedItems, key = { "${if (isVideo) "video" else "audio"}-${it.id}" }) { item ->\n'
    '                val isCurrentTrack = !isVideo && item.uri.toString() == currentMediaUri\n'
    '                Surface(\n'
    '                    color = if (isCurrentTrack) MaterialTheme.colorScheme.primary.copy(alpha = 0.18f) else MaterialTheme.colorScheme.surface,\n'
    '                    shape = RoundedCornerShape(12.dp),\n'
    '                    border = if (isCurrentTrack) BorderStroke(1.5.dp, MaterialTheme.colorScheme.primary) else null,\n',
    "library active track row"
)
replace_once(
    '                        GothicIcon(\n'
    '                            if (isVideo) Icons.Default.Movie else Icons.Default.MusicNote,\n'
    '                            contentDescription = null,\n'
    '                            tint = MaterialTheme.colorScheme.primary\n'
    '                        )\n',
    '                        GothicIcon(\n'
    '                            when {\n'
    '                                isVideo -> Icons.Default.Movie\n'
    '                                isCurrentTrack -> Icons.Default.PlayArrow\n'
    '                                else -> Icons.Default.MusicNote\n'
    '                            },\n'
    '                            contentDescription = if (isCurrentTrack) "Сейчас воспроизводится" else null,\n'
    '                            tint = MaterialTheme.colorScheme.primary\n'
    '                        )\n',
    "library active track icon"
)
replace_once(
    '                            Text(item.title, color = MaterialTheme.colorScheme.onSurface, maxLines = 1)\n'
    '                            val details = listOfNotNull(\n',
    '                            Text(item.title, color = MaterialTheme.colorScheme.onSurface, maxLines = 1)\n'
    '                            if (isCurrentTrack) {\n'
    '                                Text("СЕЙЧАС ВОСПРОИЗВОДИТСЯ", color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.labelSmall)\n'
    '                            }\n'
    '                            val details = listOfNotNull(\n',
    "library active track label"
)

source_path.write_text(source, encoding="utf-8")
print("Applied current-track highlighting in the library and queue, plus open-queue auto-scroll.")
print("Verified exact source anchors; no broad or ambiguous replacements were used.")
