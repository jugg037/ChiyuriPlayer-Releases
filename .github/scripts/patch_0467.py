from pathlib import Path
p=Path("app/src/main/java/com/chiyuri/player")
f=p/"PlaybackSessionQueues.kt"; s=f.read_text(encoding="utf-8")
if "mutableIntStateOf" not in s:
 s=s.replace("import androidx.core.content.edit","import androidx.core.content.edit\nimport androidx.compose.runtime.mutableIntStateOf",1)
 anchor='''    private val kinds = setOf("audio", "video", "network")'''
 if s.count(anchor)!=1: raise SystemExit("patch_0467 queue revision anchor mismatch")
 s=s.replace(anchor,anchor+"\n    val revision = mutableIntStateOf(0)",1)
 anchor='''        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit {'''
 if s.count(anchor)!=1: raise SystemExit("patch_0467 queue save anchor mismatch")
 s=s.replace(anchor,'''        revision.intValue++
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit {''',1)
 f.write_text(s,encoding="utf-8")
f=p/"MainActivity.kt"; s=f.read_text(encoding="utf-8")
old='''    val savedNetworkQueue = remember(uri) { PlaybackSessionQueues.load(context, "network") }'''
new='''    val networkQueueRevision = PlaybackSessionQueues.revision.intValue
    val savedNetworkQueue = remember(uri, networkQueueRevision) { PlaybackSessionQueues.load(context, "network") }'''
if s.count(old)!=1: raise SystemExit("patch_0467 network queue revision UI anchor mismatch")
s=s.replace(old,new,1)
old='''            if (expanded && isNetworkCurrent && current?.localConfiguration?.mimeType?.startsWith("video/") == true) {'''
new='''            val currentPath = uri?.lastPathSegment?.lowercase().orEmpty()
            val isNetworkVideo = current?.localConfiguration?.mimeType?.startsWith("video/") == true ||
                listOf(".mp4", ".m4v", ".mkv", ".webm", ".mov", ".avi", ".3gp", ".ts", ".mpg", ".mpeg").any { currentPath.substringBefore('?').endsWith(it) }
            if (expanded && isNetworkCurrent && isNetworkVideo) {'''
if s.count(old)!=1: raise SystemExit("patch_0467 network video classification anchor mismatch")
s=s.replace(old,new,1)
old='''                    savedNetworkQueue.forEach { item ->
                        val itemUri = item.localConfiguration?.uri
                        TextButton(onClick = {
                            player.setMediaItem(item)
                            player.prepare()
                            player.play()
                        }, modifier = Modifier.fillMaxWidth()) {'''
new='''                    savedNetworkQueue.forEachIndexed { index, item ->
                        val itemUri = item.localConfiguration?.uri
                        TextButton(onClick = {
                            player.setMediaItems(savedNetworkQueue, index, 0L)
                            player.prepare()
                            player.play()
                        }, modifier = Modifier.fillMaxWidth()) {'''
if s.count(old)!=1: raise SystemExit("patch_0467 network queue playback anchor mismatch")
s=s.replace(old,new,1)
f.write_text(s,encoding="utf-8")
print("patch_0467: network queue updates are reactive, queue selection starts the full ordered list, and network video MIME/extension detection is supported")
