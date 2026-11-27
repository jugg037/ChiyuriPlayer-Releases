from pathlib import Path
p=Path("app/src/main/java/com/chiyuri/player/MainActivity.kt")
s=p.read_text(encoding="utf-8")
old='''    var expandedMiniPlayer by rememberSaveable { mutableStateOf(false) }'''
new='''    var expandedAudioMiniPlayer by rememberSaveable { mutableStateOf(false) }
    var expandedVideoMiniPlayer by rememberSaveable { mutableStateOf(false) }
    var expandedNetworkMiniPlayer by rememberSaveable { mutableStateOf(false) }'''
if s.count(old)!=1: raise SystemExit("patch_0468 shared mini-player state anchor mismatch")
s=s.replace(old,new,1)
s=s.replace('''                    expanded = expandedMiniPlayer,
                    onExpand = { expandedMiniPlayer = !expandedMiniPlayer },''','''                    expanded = expandedAudioMiniPlayer,
                    onExpand = { expandedAudioMiniPlayer = !expandedAudioMiniPlayer },''',1)
s=s.replace('''                    VideoMiniPlayerSurface(player, videoPlayerView, expandedMiniPlayer,
                        { expandedMiniPlayer = !expandedMiniPlayer }, { isVideoFullscreen = true })''','''                    VideoMiniPlayerSurface(player, videoPlayerView, expandedVideoMiniPlayer,
                        { expandedVideoMiniPlayer = !expandedVideoMiniPlayer }, { isVideoFullscreen = true })''',1)
s=s.replace('''                    NetworkMiniPlayerSurface(player, videoPlayerView, expandedMiniPlayer,
                        { expandedMiniPlayer = !expandedMiniPlayer }, { isVideoFullscreen = true })''','''                    NetworkMiniPlayerSurface(player, videoPlayerView, expandedNetworkMiniPlayer,
                        { expandedNetworkMiniPlayer = !expandedNetworkMiniPlayer }, { isVideoFullscreen = true })''',1)
if "expandedMiniPlayer" in s: raise SystemExit("patch_0468 found stale shared mini-player state")
p.write_text(s,encoding="utf-8")
print("patch_0468: audio, video and network mini-player expansion states are independent")
