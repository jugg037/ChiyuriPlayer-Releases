from pathlib import Path
p=Path("app/src/main/java/com/chiyuri/player")
def rep(file,old,new,label):
 f=p/file; s=f.read_text(encoding="utf-8"); n=s.count(old)
 if n!=1: raise SystemExit(f"patch_0463 {label}: expected 1, found {n}")
 f.write_text(s.replace(old,new,1),encoding="utf-8")
rep("MainActivity.kt",'''                                if (queued.isNotEmpty()) {
                                    player.setMediaItems(queued, 0, PlaybackQueueStore.savedPosition(context, queued.first().localConfiguration?.uri?.toString().orEmpty()))''','''                                if (queued.isNotEmpty()) {
                                    PlaybackSessionQueues.save(context, "audio", queued, 0)
                                    player.setMediaItems(queued, 0, PlaybackQueueStore.savedPosition(context, queued.first().localConfiguration?.uri?.toString().orEmpty()))''',"audio queue persistence")
rep("MainActivity.kt",'''                                if (queued.isNotEmpty()) {
                                    val firstUri = queued.first().localConfiguration?.uri?.toString().orEmpty()''','''                                if (queued.isNotEmpty()) {
                                    PlaybackSessionQueues.save(context, "video", queued, 0)
                                    val firstUri = queued.first().localConfiguration?.uri?.toString().orEmpty()''',"video queue persistence")
rep("SmbLibraryScreen.kt",'''                            player.setMediaItem(item)''','''                            PlaybackSessionQueues.save(context, "network", listOf(item), 0)
                            player.setMediaItem(item)''',"SMB network queue")
rep("WebDavLibraryScreen.kt",'''                            player.setMediaItem(item)''','''                            PlaybackSessionQueues.save(context, "network", listOf(item), 0)
                            player.setMediaItem(item)''',"WebDAV network queue")
rep("NetworkStreamCard.kt",'''            player.setMediaItem(MediaItem.fromUri(uri))''','''            val item = MediaItem.fromUri(uri)
            PlaybackSessionQueues.save(context, "network", listOf(item), 0)
            player.setMediaItem(item)''',"internet stream queue")
# The network mini-player displays the separately persisted network queue, not another tab's current queue.
f=p/"MainActivity.kt"; s=f.read_text(encoding="utf-8")
old='''    val current = player.currentMediaItem
    val uri = current?.localConfiguration?.uri
    val source = when (uri?.scheme?.lowercase())'''
new='''    val context = LocalContext.current
    val current = player.currentMediaItem
    val uri = current?.localConfiguration?.uri
    val savedNetworkQueue = remember(uri) { PlaybackSessionQueues.load(context, "network") }
    val source = when (uri?.scheme?.lowercase())'''
if s.count(old)!=1: raise SystemExit("patch_0463 network queue state anchor mismatch")
s=s.replace(old,new,1)
old='''                Column(Modifier.fillMaxWidth().heightIn(max = 132.dp).verticalScroll(rememberScrollState())) {
                    if (player.mediaItemCount == 0) Text("Очередь пуста", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    for (index in 0 until player.mediaItemCount) {
                        val item = player.getMediaItemAt(index); val itemUri = item.localConfiguration?.uri
                        if (itemUri?.scheme?.lowercase() in setOf("http", "https", "smb", "webdav")) {
                            TextButton(onClick = { player.seekTo(index, 0L) }, modifier = Modifier.fillMaxWidth()) {
                                Text((if (index == player.currentMediaItemIndex) "▶  " else "    ") + (item.mediaMetadata.title?.toString() ?: itemUri.lastPathSegment ?: "Сетевой файл"), color = Color.White, maxLines = 1)
                            }
                        }
                    }
                }'''
new='''                Column(Modifier.fillMaxWidth().heightIn(max = 132.dp).verticalScroll(rememberScrollState())) {
                    if (savedNetworkQueue.isEmpty()) Text("Очередь пуста", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    savedNetworkQueue.forEach { item ->
                        val itemUri = item.localConfiguration?.uri
                        TextButton(onClick = {
                            player.setMediaItem(item)
                            player.prepare()
                            player.play()
                        }, modifier = Modifier.fillMaxWidth()) {
                            Text((if (uri == itemUri) "▶  " else "    ") + (item.mediaMetadata.title?.toString() ?: itemUri?.lastPathSegment ?: "Сетевой файл"), color = Color.White, maxLines = 1)
                        }
                    }
                }'''
if s.count(old)!=1: raise SystemExit("patch_0463 network queue UI anchor mismatch")
s=s.replace(old,new,1); f.write_text(s,encoding="utf-8")
# Explicitly white-tint Material icons that bypass GothicIcon inside button surfaces.
replacements={
"DlnaDiscoveryScreen.kt":[('androidx.compose.material3.Icon(Icons.Default.Cloud, contentDescription = null)','androidx.compose.material3.Icon(Icons.Default.Cloud, contentDescription = null, tint = androidx.compose.ui.graphics.Color.White)')],
"AppUpdates.kt":[('androidx.compose.material3.Icon(androidx.compose.material.icons.Icons.Default.Download, null)','androidx.compose.material3.Icon(androidx.compose.material.icons.Icons.Default.Download, null, tint = androidx.compose.ui.graphics.Color.White)'),('androidx.compose.material3.Icon(androidx.compose.material.icons.Icons.Default.Refresh, null)','androidx.compose.material3.Icon(androidx.compose.material.icons.Icons.Default.Refresh, null, tint = androidx.compose.ui.graphics.Color.White)')],
"MediaLibraryHealthScreen.kt":[('androidx.compose.material3.Icon(Icons.Default.HealthAndSafety, contentDescription = null)','androidx.compose.material3.Icon(Icons.Default.HealthAndSafety, contentDescription = null, tint = androidx.compose.ui.graphics.Color.White)')],
"PlaybackHistoryScreen.kt":[('androidx.compose.material3.Icon(Icons.Default.DeleteSweep, contentDescription = "Очистить историю")','androidx.compose.material3.Icon(Icons.Default.DeleteSweep, contentDescription = "Очистить историю", tint = androidx.compose.ui.graphics.Color.White)'),('androidx.compose.material3.Icon(Icons.Default.History, contentDescription = null, tint = MaterialTheme.colorScheme.primary)','androidx.compose.material3.Icon(Icons.Default.History, contentDescription = null, tint = androidx.compose.ui.graphics.Color.White)')],
"PartyModeScreen.kt":[('androidx.compose.material3.Icon(Icons.Default.Shuffle, contentDescription = null)','androidx.compose.material3.Icon(Icons.Default.Shuffle, contentDescription = null, tint = androidx.compose.ui.graphics.Color.White)'),('androidx.compose.material3.Icon(Icons.Default.AutoAwesome, contentDescription = null)','androidx.compose.material3.Icon(Icons.Default.AutoAwesome, contentDescription = null, tint = androidx.compose.ui.graphics.Color.White)')],
"WebDavLibraryScreen.kt":[('tint = MaterialTheme.colorScheme.primary','tint = androidx.compose.ui.graphics.Color.White')]
}
for file,pairs in replacements.items():
 f=p/file; s=f.read_text(encoding="utf-8")
 for old,new in pairs:
  if old not in s: raise SystemExit(f"patch_0463 icon anchor missing: {file}: {old[:80]}")
  s=s.replace(old,new,1)
 f.write_text(s,encoding="utf-8")
print("patch_0463: persisted tab-specific audio/video/network queue snapshots and white-tinted direct button icons")
