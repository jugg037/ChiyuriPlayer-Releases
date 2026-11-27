from pathlib import Path
p=Path("app/src/main/java/com/chiyuri/player")
main=p/"MainActivity.kt"; s=main.read_text(encoding="utf-8")
def once(old,new,label):
 global s
 n=s.count(old)
 if n!=1: raise SystemExit(f"patch_0462: {label}: expected 1, found {n}")
 s=s.replace(old,new,1)
once('''    var currentMediaUri by remember { mutableStateOf(player.currentMediaItem?.localConfiguration?.uri?.toString()) }
    var expandedMiniPlayer by rememberSaveable { mutableStateOf(false) }''','''    var currentMediaUri by remember { mutableStateOf(player.currentMediaItem?.localConfiguration?.uri?.toString()) }
    val currentUriScheme = player.currentMediaItem?.localConfiguration?.uri?.scheme?.lowercase().orEmpty()
    val isCurrentNetworkMedia = currentUriScheme in setOf("http", "https", "smb", "webdav")
    val currentMediaPath = player.currentMediaItem?.localConfiguration?.uri?.lastPathSegment?.lowercase().orEmpty()
    val isCurrentVideoMedia = player.currentMediaItem?.localConfiguration?.mimeType?.startsWith("video/") == true ||
        listOf(".mp4", ".m4v", ".mkv", ".webm", ".mov", ".avi", ".3gp", ".ts", ".mpg", ".mpeg").any { currentMediaPath.substringBefore('?').endsWith(it) }
    var networkPage by rememberSaveable { mutableStateOf("Источники") }
    var expandedMiniPlayer by rememberSaveable { mutableStateOf(false) }''',"media type state")
once('''                if (tab != "Ещё") MiniPlayerBar(
                    player = player,''','''                if (tab == "Музыка" && !isCurrentNetworkMedia && !isCurrentVideoMedia) MiniPlayerBar(
                    player = player,''',"audio tab player")
once('''                    playbackSpeed = playbackSpeed,
                    onPlaybackSpeedChange = { player.setPlaybackParameters(PlaybackParameters(it)) }
                )
                NavigationBar''','''                    playbackSpeed = playbackSpeed,
                    onPlaybackSpeedChange = { player.setPlaybackParameters(PlaybackParameters(it)) }
                )
                if (tab == "Видео" && isCurrentVideoMedia && !isCurrentNetworkMedia && !isVideoFullscreen) {
                    VideoMiniPlayerSurface(player, videoPlayerView, expandedMiniPlayer,
                        { expandedMiniPlayer = !expandedMiniPlayer }, { isVideoFullscreen = true })
                }
                if (tab == "Сеть" && isCurrentNetworkMedia) {
                    NetworkMiniPlayerSurface(player, videoPlayerView, expandedMiniPlayer,
                        { expandedMiniPlayer = !expandedMiniPlayer }, { isVideoFullscreen = true })
                }
                NavigationBar''',"video and network mini-players")
once('''                    listOf("Музыка", "Видео", "Плейлисты", "Ещё").forEach { item ->''','''                    listOf("Музыка", "Видео", "Сеть", "Плейлисты", "Ещё").forEach { item ->''',"navigation items")
once('''                                        "Видео" -> Icons.Default.Movie
                                        "Плейлисты" -> Icons.Default.QueueMusic''','''                                        "Видео" -> Icons.Default.Movie
                                        "Сеть" -> Icons.Default.Cloud
                                        "Плейлисты" -> Icons.Default.QueueMusic''',"network icon")
once('''                      selectedIconColor = MaterialTheme.colorScheme.onPrimary,
                      selectedTextColor = MaterialTheme.colorScheme.primary,
                      indicatorColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.22f),
                      unselectedIconColor = MaterialTheme.colorScheme.secondary,
                      unselectedTextColor = MaterialTheme.colorScheme.onSurfaceVariant''','''                      selectedIconColor = Color.White,
                      selectedTextColor = Color.White,
                      indicatorColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.22f),
                      unselectedIconColor = Color.White,
                      unselectedTextColor = Color.White''',"navigation white tint")
once('''                        Box(Modifier.fillMaxWidth().padding(top = 12.dp)) {
                            AndroidView(
                                factory = { videoPlayerView },
                                update = { it.player = player },
                                modifier = Modifier.fillMaxWidth().heightIn(max = 480.dp).aspectRatio(16f / 9f)
                            )
                            GothicIconButton(
                                onClick = { isVideoFullscreen = true },
                                modifier = Modifier.align(Alignment.BottomEnd).padding(8.dp)
                                    .background(Color.Black.copy(alpha = 0.55f), RoundedCornerShape(50))
                            ) {
                                GothicIcon(Icons.Default.Fullscreen, contentDescription = "Полноэкранный режим", tint = Color.White)
                            }
                        }
''','''                        // Video surface is hosted by the Video tab mini-player.
''',"move video surface")
once('''                "Плейлисты" -> PlaylistScreen(player = player, modifier = Modifier.weight(1f))
                else -> {''','''                "Сеть" -> {
                    Column(Modifier.weight(1f).fillMaxWidth()) {
                        Text("Сетевое воспроизведение", color = Color.White, style = MaterialTheme.typography.titleMedium)
                        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            listOf("Источники", "SMB", "WebDAV", "DLNA").forEach { source ->
                                FilterChip(selected = networkPage == source, onClick = { networkPage = source },
                                    label = { Text(source, color = Color.White) })
                            }
                        }
                        when (networkPage) {
                            "SMB" -> SmbLibraryScreen(player, Modifier.weight(1f))
                            "WebDAV" -> WebDavLibraryScreen(player, Modifier.weight(1f))
                            "DLNA" -> DlnaDiscoveryScreen(Modifier.weight(1f))
                            else -> Column(Modifier.weight(1f).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                Text("Выбери сетевой источник или медиасервер.", color = Color.White)
                                ActionCard("SMB 2/3", "Подключение к NAS и общим папкам", Icons.Default.FolderShared) { networkPage = "SMB" }
                                ActionCard("WebDAV", "Подключение к сетевым каталогам", Icons.Default.Cloud) { networkPage = "WebDAV" }
                                ActionCard("DLNA / UPnP", "Поиск медиасерверов в локальной сети", Icons.Default.Cast) { networkPage = "DLNA" }
                                Text("Интернет-потоки отображаются в сетевом мини-плеере после запуска.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                    }
                }
                "Плейлисты" -> PlaylistScreen(player = player, modifier = Modifier.weight(1f))
                else -> {''',"network tab content")
for old in [
'''                                ActionCard("Сетевые папки SMB", "Подключение к NAS и общим папкам по SMB 2/3", Icons.Default.FolderShared) { morePage = "SMB" }
''',
'''                                ActionCard("Сетевые папки WebDAV", "Защищённое подключение к NAS и облачным хранилищам", Icons.Default.Cloud) { morePage = "WebDAV" }
''',
'''                                ActionCard("DLNA / UPnP", "Поиск медиасерверов в локальной сети", Icons.Default.Cloud) { morePage = "DLNA" }
'''
]:
 if s.count(old)!=1: raise SystemExit("patch_0462: legacy network card mismatch")
 s=s.replace(old,"",1)
main.write_text(s,encoding="utf-8")
g=p/"GothicUi.kt"; gs=g.read_text(encoding="utf-8")
old='''        Icon(imageVector = imageVector, contentDescription = contentDescription,
            modifier = Modifier.fillMaxSize(), tint = tint)'''
if gs.count(old)!=1: raise SystemExit("patch_0462: GothicIcon tint anchor mismatch")
g.write_text(gs.replace(old,'''        Icon(imageVector = imageVector, contentDescription = contentDescription,
            modifier = Modifier.fillMaxSize(), tint = Color.White)''',1),encoding="utf-8")
components=r'''@Composable
private fun VideoMiniPlayerSurface(player: Player, videoPlayerView: PlayerView, expanded: Boolean, onExpand: () -> Unit, onFullscreen: () -> Unit) {
    Surface(color = MaterialTheme.colorScheme.surface.copy(alpha = if (expanded) 0.0f else 0.70f), shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 6.dp)) {
        Column(Modifier.padding(8.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Text(player.currentMediaItem?.mediaMetadata?.title?.toString() ?: "Видеоплеер", color = Color.White, modifier = Modifier.weight(1f), maxLines = 1)
                GothicIconButton(onClick = onExpand) { GothicIcon(if (expanded) Icons.Default.ExpandMore else Icons.Default.ExpandLess, "Изменить размер видеоплеера") }
                GothicIconButton(onClick = onFullscreen) { GothicIcon(Icons.Default.Fullscreen, "Полноэкранный режим") }
            }
            if (expanded) AndroidView(factory = { videoPlayerView }, update = { it.player = player }, modifier = Modifier.fillMaxWidth().aspectRatio(16f / 9f).heightIn(max = 220.dp))
            else Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Text("Видео", color = Color.White, modifier = Modifier.weight(1f))
                GothicIconButton(onClick = { if (player.isPlaying) player.pause() else player.play() }) {
                    GothicIcon(if (player.isPlaying) Icons.Default.Pause else Icons.Default.PlayArrow, "Воспроизвести или приостановить")
                }
            }
        }
    }
}

@Composable
private fun NetworkMiniPlayerSurface(player: Player, videoPlayerView: PlayerView, expanded: Boolean, onExpand: () -> Unit, onFullscreen: () -> Unit) {
    val current = player.currentMediaItem
    val uri = current?.localConfiguration?.uri
    val source = when (uri?.scheme?.lowercase()) { "smb" -> "SMB"; "webdav" -> "WebDAV"; "http", "https" -> "Интернет"; else -> "Сетевой источник" }
    Surface(color = MaterialTheme.colorScheme.surface.copy(alpha = if (expanded) 0.0f else 0.70f), shape = RoundedCornerShape(18.dp), modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 6.dp)) {
        Column(Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(source, color = Color.White, style = MaterialTheme.typography.labelSmall)
                    Text(current?.mediaMetadata?.title?.toString() ?: "Сетевое воспроизведение", color = Color.White, maxLines = 1)
                    Text(uri?.host ?: uri?.authority ?: "Источник не выбран", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall, maxLines = 1)
                }
                GothicIconButton(onClick = { if (player.isPlaying) player.pause() else player.play() }, enabled = current != null) {
                    GothicIcon(if (player.isPlaying) Icons.Default.Pause else Icons.Default.PlayArrow, "Воспроизвести или приостановить")
                }
                GothicIconButton(onClick = { if (player.hasNextMediaItem()) player.seekToNextMediaItem() }, enabled = player.hasNextMediaItem()) {
                    GothicIcon(Icons.Default.SkipNext, "Следующий сетевой файл")
                }
                GothicIconButton(onClick = onExpand) { GothicIcon(if (expanded) Icons.Default.ExpandMore else Icons.Default.ExpandLess, "Показать сетевую очередь") }
            }
            if (expanded && current?.localConfiguration?.mimeType?.startsWith("video/") == true) {
                AndroidView(factory = { videoPlayerView }, update = { it.player = player }, modifier = Modifier.fillMaxWidth().aspectRatio(16f / 9f).heightIn(max = 220.dp))
                TextButton(onClick = onFullscreen, modifier = Modifier.fillMaxWidth()) {
                    GothicIcon(Icons.Default.Fullscreen, "Полноэкранный режим сетевого видео")
                    Text("Полноэкранный режим", color = Color.White)
                }
            }
            if (expanded) {
                Text("Очередь сетевого воспроизведения", color = Color.White, style = MaterialTheme.typography.labelMedium)
                Column(Modifier.fillMaxWidth().heightIn(max = 132.dp).verticalScroll(rememberScrollState())) {
                    if (player.mediaItemCount == 0) Text("Очередь пуста", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    for (index in 0 until player.mediaItemCount) {
                        val item = player.getMediaItemAt(index); val itemUri = item.localConfiguration?.uri
                        if (itemUri?.scheme?.lowercase() in setOf("http", "https", "smb", "webdav")) {
                            TextButton(onClick = { player.seekTo(index, 0L) }, modifier = Modifier.fillMaxWidth()) {
                                Text((if (index == player.currentMediaItemIndex) "▶  " else "    ") + (item.mediaMetadata.title?.toString() ?: itemUri.lastPathSegment ?: "Сетевой файл"), color = Color.White, maxLines = 1)
                            }
                        }
                    }
                }
            }
        }
    }
}

'''
anchor='''@Composable
private fun MiniPlayerBar('''
if s.count(anchor)!=1: raise SystemExit("patch_0462: mini-player insertion anchor mismatch")
s=s.replace(anchor,components+anchor,1)
# Add independent logical queue snapshot model; integrated into source-specific selection patches in a follow-up.
(p/"PlaybackSessionQueues.kt").write_text(r'''package com.chiyuri.player

import android.content.Context
import androidx.core.content.edit
import androidx.media3.common.MediaItem
import org.json.JSONArray
import org.json.JSONObject

/** Persisted queue snapshots kept separately for the Music, Video and Network tabs. */
object PlaybackSessionQueues {
    private const val PREFS = "playback_session_queues"
    private val kinds = setOf("audio", "video", "network")
    fun save(context: Context, kind: String, items: List<MediaItem>, currentIndex: Int = 0) {
        require(kind in kinds)
        val array = JSONArray()
        items.forEach { item ->
            val uri = item.localConfiguration?.uri?.toString() ?: return@forEach
            val meta = item.mediaMetadata
            array.put(JSONObject().put("uri", uri).put("title", meta.title?.toString() ?: JSONObject.NULL)
                .put("artist", meta.artist?.toString() ?: JSONObject.NULL)
                .put("mime", item.localConfiguration?.mimeType ?: JSONObject.NULL))
        }
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit {
            putString("queue_$kind", array.toString())
            putInt("index_$kind", currentIndex.coerceIn(0, (items.size - 1).coerceAtLeast(0)))
        }
    }
    fun load(context: Context, kind: String): List<MediaItem> {
        require(kind in kinds)
        val raw = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString("queue_$kind", null) ?: return emptyList()
        return runCatching {
            val array = JSONArray(raw)
            buildList {
                for (i in 0 until array.length()) {
                    val o = array.optJSONObject(i) ?: continue
                    val uri = o.optString("uri").takeIf { it.isNotBlank() } ?: continue
                    val meta = androidx.media3.common.MediaMetadata.Builder()
                        .setTitle(o.optString("title").takeIf { it.isNotBlank() && it != "null" })
                        .setArtist(o.optString("artist").takeIf { it.isNotBlank() && it != "null" }).build()
                    add(MediaItem.Builder().setUri(uri).setMimeType(o.optString("mime").takeIf { it.isNotBlank() && it != "null" }).setMediaMetadata(meta).build())
                }
            }
        }.getOrDefault(emptyList())
    }
    fun currentIndex(context: Context, kind: String): Int =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getInt("index_$kind", 0)
}
''',encoding="utf-8")
gradle=Path("app/build.gradle.kts"); gs=gradle.read_text(encoding="utf-8")
if 'versionName = "0.5.10"' not in gs or 'orElse("346")' not in gs: raise SystemExit("patch_0462: expected baseline 0.5.10/346")
gradle.write_text(gs.replace('versionName = "0.5.10"','versionName = "0.6.0"',1).replace('orElse("346")','orElse("444")'),encoding="utf-8")
print("patch_0462: tab-bound mini-player surfaces, Network tab, relocated video surface, white Gothic icons, logical queue snapshot store, version 0.6.0/444")
