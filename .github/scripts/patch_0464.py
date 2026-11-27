from pathlib import Path
p=Path("app/src/main/java/com/chiyuri/player")
def rep(file,old,new,label):
 old=old.replace("\\\${", "\${"); new=new.replace("\\\${", "\${")
 f=p/file; s=f.read_text(encoding="utf-8"); n=s.count(old)
 if n!=1: raise SystemExit(f"patch_0464 {label}: expected 1, found {n}")
 f.write_text(s.replace(old,new,1),encoding="utf-8")
f=p/"PlaybackSessionQueues.kt"; s=f.read_text(encoding="utf-8")
anchor='''    fun load(context: Context, kind: String): List<MediaItem> {'''
if s.count(anchor)!=1: raise SystemExit("patch_0464 queue API anchor mismatch")
append='''    fun append(context: Context, kind: String, item: MediaItem) {
        require(kind in kinds)
        val uri = item.localConfiguration?.uri?.toString() ?: return
        val current = load(context, kind)
        if (current.none { it.localConfiguration?.uri?.toString() == uri }) save(context, kind, current + item, current.size)
    }
'''
f.write_text(s.replace(anchor,append+anchor,1),encoding="utf-8")
rep("SmbLibraryScreen.kt",'''                    Column(Modifier.padding(horizontal = 12.dp, vertical = 10.dp)) {
                        Text(if (entry.isDirectory) "📁 \${entry.name}" else entry.name, color = MaterialTheme.colorScheme.onSurface, maxLines = 1)
                        if (!entry.isDirectory) Text("\${entry.mimeType ?: "Файл"} • \${entry.sizeBytes / 1024} КБ", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                    }''','''                    Row(Modifier.padding(horizontal = 12.dp, vertical = 10.dp), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(if (entry.isDirectory) "📁 \${entry.name}" else entry.name, color = MaterialTheme.colorScheme.onSurface, maxLines = 1)
                            if (!entry.isDirectory) Text("\${entry.mimeType ?: "Файл"} • \${entry.sizeBytes / 1024} КБ", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                        }
                        if (!entry.isDirectory) GothicIconButton(onClick = {
                            val item = MediaItem.Builder().setUri(entry.uri.toUri()).setMimeType(entry.mimeType)
                                .setMediaMetadata(MediaMetadata.Builder().setTitle(entry.name).build()).build()
                            PlaybackSessionQueues.append(context, "network", item)
                        }) { GothicIcon(Icons.Default.PlaylistAdd, "Добавить в сетевую очередь") }
                    }''',"SMB queue add button")
rep("WebDavLibraryScreen.kt",'''                        Column(Modifier.weight(1f)) {
                            Text(entry.name, color = MaterialTheme.colorScheme.onSurface, maxLines = 1)
                            if (!entry.isDirectory) Text("\${entry.mimeType ?: "Файл"} • \${entry.sizeBytes / 1024} КБ", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                        }''','''                        Column(Modifier.weight(1f)) {
                            Text(entry.name, color = MaterialTheme.colorScheme.onSurface, maxLines = 1)
                            if (!entry.isDirectory) Text("\${entry.mimeType ?: "Файл"} • \${entry.sizeBytes / 1024} КБ", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                        }
                        if (!entry.isDirectory) GothicIconButton(onClick = {
                            val item = MediaItem.Builder().setUri(entry.uri.toUri()).setMimeType(entry.mimeType)
                                .setMediaMetadata(MediaMetadata.Builder().setTitle(entry.name).build()).build()
                            PlaybackSessionQueues.append(context, "network", item)
                        }) { GothicIcon(Icons.Default.PlaylistAdd, "Добавить в сетевую очередь") }''',"WebDAV queue add button")
for file in ["SmbLibraryScreen.kt","WebDavLibraryScreen.kt","NetworkStreamCard.kt"]:
 f=p/file; s=f.read_text(encoding="utf-8")
 s=s.replace('PlaybackSessionQueues.save(context, "network", listOf(item), 0)','PlaybackSessionQueues.append(context, "network", item)')
 f.write_text(s,encoding="utf-8")
rep("MainActivity.kt",'''                                Text("Интернет-потоки отображаются в сетевом мини-плеере после запуска.", color = MaterialTheme.colorScheme.onSurfaceVariant)''','''                                NetworkStreamCard(player)
                                Text("Интернет-потоки и радио управляются отдельным сетевым мини-плеером.", color = MaterialTheme.colorScheme.onSurfaceVariant)''',"network streams card placement")
rep("MainActivity.kt",'''        NetworkStreamCard(player)
        LibraryBackupCard()''','''        LibraryBackupCard()''',"remove stream card from audio settings")
print("patch_0464: network source list can build a persistent multi-item queue; Internet streams moved to Network tab")
