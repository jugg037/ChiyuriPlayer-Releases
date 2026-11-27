from pathlib import Path
p=Path("app/src/main/java/com/chiyuri/player/MainActivity.kt")
s=p.read_text(encoding="utf-8")
old='''                if (tab == "Сеть" && isCurrentNetworkMedia) {
                    NetworkMiniPlayerSurface(player, videoPlayerView, expandedMiniPlayer,
                        { expandedMiniPlayer = !expandedMiniPlayer }, { isVideoFullscreen = true })
                }'''
new='''                if (tab == "Сеть") {
                    NetworkMiniPlayerSurface(player, videoPlayerView, expandedMiniPlayer,
                        { expandedMiniPlayer = !expandedMiniPlayer }, { isVideoFullscreen = true })
                }'''
if s.count(old)!=1: raise SystemExit("patch_0465 network mini-player tab condition mismatch")
s=s.replace(old,new,1)
old='''    val source = when (uri?.scheme?.lowercase()) { "smb" -> "SMB"; "webdav" -> "WebDAV"; "http", "https" -> "Интернет"; else -> "Сетевой источник" }'''
new='''    val isNetworkCurrent = uri?.scheme?.lowercase() in setOf("smb", "webdav", "http", "https")
    val source = when (uri?.scheme?.lowercase()) { "smb" -> "SMB"; "webdav" -> "WebDAV"; "http", "https" -> "Интернет"; else -> "Сетевой источник" }'''
if s.count(old)!=1: raise SystemExit("patch_0465 source classification mismatch")
s=s.replace(old,new,1)
s=s.replace('''Text(current?.mediaMetadata?.title?.toString() ?: "Сетевое воспроизведение", color = Color.White, maxLines = 1)''','''Text(if (isNetworkCurrent) current?.mediaMetadata?.title?.toString() ?: "Сетевое воспроизведение" else "Нет активного сетевого потока", color = Color.White, maxLines = 1)''',1)
s=s.replace('''GothicIconButton(onClick = { if (player.isPlaying) player.pause() else player.play() }, enabled = current != null)''','''GothicIconButton(onClick = { if (player.isPlaying) player.pause() else player.play() }, enabled = isNetworkCurrent)''',1)
s=s.replace('''GothicIconButton(onClick = { if (player.hasNextMediaItem()) player.seekToNextMediaItem() }, enabled = player.hasNextMediaItem())''','''GothicIconButton(onClick = { if (player.hasNextMediaItem()) player.seekToNextMediaItem() }, enabled = isNetworkCurrent && player.hasNextMediaItem())''',1)
s=s.replace('''if (expanded && current?.localConfiguration?.mimeType?.startsWith("video/") == true)''','''if (expanded && isNetworkCurrent && current?.localConfiguration?.mimeType?.startsWith("video/") == true)''',1)
p.write_text(s,encoding="utf-8")
print("patch_0465: network mini-player remains available on its tab when idle and never controls a local audio/video session")
