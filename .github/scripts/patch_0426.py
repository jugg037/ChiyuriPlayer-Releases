from pathlib import Path
import shutil, zipfile
from PIL import Image, ImageDraw, ImageChops
ROOT=Path("."); BASE=ROOT/"app/src/main/java/com/chiyuri/player"; RES=ROOT/"app/src/main/res"
def read(p): return p.read_text(encoding="utf-8")
def write(p,s): p.write_text(s,encoding="utf-8")
def once(s,a,b,label):
 n=s.count(a)
 if n!=1: raise SystemExit(f"{label}: expected one anchor, found {n}: {a[:90]!r}")
 return s.replace(a,b,1)
def imp(s,value):
 if value not in s: s=s.replace("package com.chiyuri.player\n","package com.chiyuri.player\n\n"+value+"\n",1)
 return s
p=ROOT/"app/build.gradle.kts"; s=read(p)
for a,b,n in [
 ("compileSdk = 36","compileSdk = 37","compile SDK"),
 ("targetSdk = 35","targetSdk = 37","target SDK"),
 ('versionCode = providers.gradleProperty("VERSION_CODE").orElse("336")','versionCode = providers.gradleProperty("VERSION_CODE").orElse("337")',"versionCode"),
 ('abiFilters += listOf("arm64-v8a")','abiFilters += listOf("arm64-v8a", "x86_64")',"ABI"),
 ("androidx.lifecycle:lifecycle-runtime-ktx:2.10.0","androidx.lifecycle:lifecycle-runtime-ktx:2.11.0","Lifecycle KTX"),
 ("androidx.work:work-runtime-ktx:2.10.5","androidx.work:work-runtime-ktx:2.12.0","Work KTX")]: s=once(s,a,b,n)
if 'versionName = "0.2.1"' in s:
 s=s.replace('versionName = "0.2.1"','versionName = "0.5.2"',1)
elif 'versionName = "0.5.0"' in s:
 s=s.replace('versionName = "0.5.0"','versionName = "0.5.2"',1)
elif 'versionName = "0.5.1"' in s:
 s=s.replace('versionName = "0.5.1"','versionName = "0.5.2"',1)
elif 'versionName = "0.5.2"' not in s:
 raise SystemExit("Unexpected Gradle versionName; expected source baseline or 0.5.0/0.5.1/0.5.2")
s=s.replace('orElse("337")','orElse("338")')
write(p,s)
wrapper=ROOT/"gradle/wrapper/gradle-wrapper.properties"
if wrapper.exists(): write(wrapper,once(read(wrapper),"gradle-9.3.1-bin.zip","gradle-9.9.0-bin.zip","Gradle wrapper"))
p=ROOT/"app/src/main/AndroidManifest.xml"; s=read(p)
s=once(s,'    <uses-permission android:name="android.permission.INTERNET" />','    <uses-permission android:name="android.permission.INTERNET" />\n    <uses-permission android:name="android.permission.ACCESS_LOCAL_NETWORK" />',"Android 17 local network permission")
s=once(s,'            android:screenOrientation="unspecified">','            >',"orientation")
s=once(s,'            android:exported="true"\n            android:foregroundServiceType="mediaPlayback">',
 '            android:exported="true"\n            android:foregroundServiceType="mediaPlayback"\n            tools:ignore="ExportedService">',"MediaSession service")
write(p,s)
p=BASE/"PlaybackService.kt"; s=read(p)
s=once(s,"    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaSession? {\n        return mediaSession\n    }",
 "    override fun onGetSession(controllerInfo: MediaSession.ControllerInfo): MediaSession? {\n        // Keep exported for System UI, Bluetooth and Android Auto discovery.\n        // Only trusted media/system controllers and this app may bind to the session.\n        return mediaSession.takeIf { controllerInfo.isTrusted || controllerInfo.packageName == packageName }\n    }","trusted MediaSession clients")
write(p,s)
p=BASE/"AppUpdates.kt"; s=imp(read(p),"import androidx.core.content.edit"); s=imp(s,"import androidx.core.net.toUri")
s=once(s,'context.getSharedPreferences(PREFS, 0).edit()\n            .putBoolean(KEY_ENABLED, enabled).putBoolean(KEY_WIFI_ONLY, wifiOnly)\n            .putInt(KEY_INTERVAL, intervalHours).apply()',
 'context.getSharedPreferences(PREFS, 0).edit {\n            putBoolean(KEY_ENABLED, enabled)\n            putBoolean(KEY_WIFI_ONLY, wifiOnly)\n            putInt(KEY_INTERVAL, intervalHours)\n        }',"update preferences")
s=s.replace('Uri.parse("package:${context.packageName}")','"package:${context.packageName}".toUri()')
for a,b,n in [
 ("val flags = if (Build.VERSION.SDK_INT >= P) PackageManager.GET_SIGNING_CERTIFICATES else PackageManager.GET_SIGNATURES","val flags = PackageManager.GET_SIGNING_CERTIFICATES","signing flags"),
 ("val installedSignatures = if (Build.VERSION.SDK_INT >= P) installed.signingInfo?.apkContentsSigners else installed.signatures","val installedSignatures = installed.signingInfo?.apkContentsSigners","installed signer"),
 ("val archiveSignatures = if (Build.VERSION.SDK_INT >= P) archive.signingInfo?.apkContentsSigners else archive.signatures","val archiveSignatures = archive.signingInfo?.apkContentsSigners","archive signer"),
 ("if (Build.VERSION.SDK_INT >= 26 && !context.packageManager.canRequestPackageInstalls())","if (!context.packageManager.canRequestPackageInstalls())","installer permission"),
 ('if (Build.VERSION.SDK_INT >= 26) manager.createNotificationChannel(\n            android.app.NotificationChannel(CHANNEL, "Обновления приложения", android.app.NotificationManager.IMPORTANCE_DEFAULT)\n        )','manager.createNotificationChannel(\n            android.app.NotificationChannel(CHANNEL, "Обновления приложения", android.app.NotificationManager.IMPORTANCE_DEFAULT)\n        )',"update channel"),
 ('@Suppress("DEPRECATION")\n        val notification = if (Build.VERSION.SDK_INT >= 26) android.app.Notification.Builder(context, CHANNEL) else android.app.Notification.Builder(context)','val notification = android.app.Notification.Builder(context, CHANNEL)',"update notification builder"),
 ("    private const val P = Build.VERSION_CODES.P\n","","obsolete SDK constant"),
 ('        if (Build.VERSION.SDK_INT >= 26) {\n            val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager\n            manager.createNotificationChannel(\n                NotificationChannel(CHANNEL_ID, "Загрузка обновлений ChiyuriPlayer", NotificationManager.IMPORTANCE_LOW).apply {\n                    description = "Ход загрузки и проверки обновлений"\n                    setShowBadge(false)\n                }\n            )\n        }',
 '        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager\n        manager.createNotificationChannel(\n            NotificationChannel(CHANNEL_ID, "Загрузка обновлений ChiyuriPlayer", NotificationManager.IMPORTANCE_LOW).apply {\n                description = "Ход загрузки и проверки обновлений"\n                setShowBadge(false)\n            }\n        )',"download channel")]: s=once(s,a,b,n)
s=s.replace("modifier: androidx.compose.ui.Modifier = androidx.compose.ui.Modifier)","modifier: Modifier = Modifier)")
write(p,s)
p=BASE/"AudioVisualizer.kt"; s=once(read(p),"internal fun AudioVisualizerMiniDisplay(player: Player, modifier: Modifier = Modifier.height(54.dp)) {","internal fun AudioVisualizerMiniDisplay(player: Player, modifier: Modifier = Modifier) {","visualizer modifier"); write(p,s)
p=BASE/"MainActivity.kt"; s=imp(read(p),"import androidx.core.net.toUri")
s=once(s,"AudioVisualizerMiniDisplay(player)\n","AudioVisualizerMiniDisplay(player, Modifier.height(54.dp))\n","visualizer height")
s=once(s,"WindowCompat.setDecorFitsSystemWindows(window, !isVideoFullscreen)","WindowCompat.setDecorFitsSystemWindows(window, false)","edge-to-edge")
s=once(s,"WindowCompat.setDecorFitsSystemWindows(window, true)","WindowCompat.setDecorFitsSystemWindows(window, false)","edge-to-edge cleanup")
for a,b in [("Uri.parse(it)","it.toUri()"),("Uri.parse(entry.location)","entry.location.toUri()"),("Uri.parse(track.uri)","track.uri.toUri()"),("Uri.parse(entry.uri)","entry.uri.toUri()")]: s=s.replace(a,b)
s=once(s,"var queueVersion by remember { mutableStateOf(0) }","var queueVersion by remember { mutableIntStateOf(0) }","Int state"); write(p,s)
p=BASE/"BloodLoadingIndicator.kt"; s=imp(read(p),"import androidx.core.graphics.createBitmap"); s=imp(s,"import androidx.core.graphics.withClip")
s=once(s,"fun BloodLoader(progress: Float? = null, modifier: Modifier = Modifier) {","fun BloodLoader(modifier: Modifier = Modifier, progress: Float? = null) {","BloodLoader signature")
s=s.replace("Bitmap.createBitmap(512, 512, Bitmap.Config.ARGB_8888)","createBitmap(512, 512, Bitmap.Config.ARGB_8888)").replace("Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)","createBitmap(width, height, Bitmap.Config.ARGB_8888)")
s=once(s,"            canvas.save()\n            canvas.clipPath(wedge)\n            val layer = canvas.saveLayer(dst, null)\n            canvas.drawBitmap(blood, null, dst, NativePaint(NativePaint.ANTI_ALIAS_FLAG or NativePaint.FILTER_BITMAP_FLAG).apply { alpha = 226 })\n            val mask = NativePaint(NativePaint.ANTI_ALIAS_FLAG or NativePaint.FILTER_BITMAP_FLAG).apply {\n                xfermode = PorterDuffXfermode(PorterDuff.Mode.DST_IN)\n            }\n            canvas.drawBitmap(emblem, null, dst, mask)\n            mask.xfermode = null\n            canvas.restoreToCount(layer)\n            canvas.restore()",
 "            canvas.withClip(wedge) {\n                val layer = saveLayer(dst, null)\n                drawBitmap(blood, null, dst, NativePaint(NativePaint.ANTI_ALIAS_FLAG or NativePaint.FILTER_BITMAP_FLAG).apply { alpha = 226 })\n                val mask = NativePaint(NativePaint.ANTI_ALIAS_FLAG or NativePaint.FILTER_BITMAP_FLAG).apply {\n                    xfermode = PorterDuffXfermode(PorterDuff.Mode.DST_IN)\n                }\n                drawBitmap(emblem, null, dst, mask)\n                mask.xfermode = null\n                restoreToCount(layer)\n            }","Canvas.withClip blood mask")
s=once(s,"            canvas.save()\n            canvas.clipPath(wedge)\n            canvas.drawBitmap(emblem, null, dst, NativePaint(NativePaint.ANTI_ALIAS_FLAG or NativePaint.FILTER_BITMAP_FLAG).apply { alpha = 62 })\n            canvas.restore()",
 "            canvas.withClip(wedge) {\n                drawBitmap(emblem, null, dst, NativePaint(NativePaint.ANTI_ALIAS_FLAG or NativePaint.FILTER_BITMAP_FLAG).apply { alpha = 62 })\n            }","Canvas.withClip"); write(p,s)
def replace_file(name,old,new,label,imports=("import androidx.core.content.edit",)):
 p=BASE/name; s=read(p)
 for x in imports: s=imp(s,x)
 write(p,once(s,old,new,label))
replace_file("AppearanceSettings.kt",'context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)\n            .edit()\n            .putString(KEY_THEME_MODE, config.themeMode.storageValue)\n            .putBoolean(KEY_DYNAMIC_COLORS, config.dynamicColors)\n            .apply()','context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit {\n            putString(KEY_THEME_MODE, config.themeMode.storageValue)\n            putBoolean(KEY_DYNAMIC_COLORS, config.dynamicColors)\n        }',"appearance prefs")
replace_file("AudioEffectsSettings.kt",'context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)\n            .edit()\n            .putBoolean(KEY_EQUALIZER_ENABLED, normalized.equalizerEnabled)\n            .putFloat(KEY_PLAYER_VOLUME, normalized.playerVolume)\n            .apply {\n                normalized.bandsDb.forEachIndexed { index, value ->\n                    putFloat(KEY_BAND_PREFIX + index, value)\n                }\n            }\n            .apply()','context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE).edit {\n            putBoolean(KEY_EQUALIZER_ENABLED, normalized.equalizerEnabled)\n            putFloat(KEY_PLAYER_VOLUME, normalized.playerVolume)\n            normalized.bandsDb.forEachIndexed { index, value ->\n                putFloat(KEY_BAND_PREFIX + index, value)\n            }\n        }',"audio prefs")
replace_file("AudioVisualizer.kt",'context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putBoolean("enabled", enabled).apply()','context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit { putBoolean("enabled", enabled) }',"visualizer enabled")
replace_file("AudioVisualizer.kt",'context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString("mode", mode.storageValue).apply()','context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit { putString("mode", mode.storageValue) }',"visualizer mode")
replace_file("FavoriteTracksStore.kt",'context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)\n            .edit()\n            .putStringSet(KEY_URIS, snapshot)\n            .apply()','context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit {\n            putStringSet(KEY_URIS, snapshot)\n        }',"favorites prefs")
replace_file("LocalMediaRepository.kt",'context.getSharedPreferences(CACHE_PREFS, Context.MODE_PRIVATE)\n            .edit()\n            .putString(cacheKey(isVideo), array.toString())\n            .putLong(scanTimeKey(isVideo), System.currentTimeMillis())\n            .apply()','context.getSharedPreferences(CACHE_PREFS, Context.MODE_PRIVATE).edit {\n            putString(cacheKey(isVideo), array.toString())\n            putLong(scanTimeKey(isVideo), System.currentTimeMillis())\n        }',"media cache",("import androidx.core.content.edit","import androidx.core.net.toUri"))
replace_file("LyricsSyncOffsetStore.kt",'context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)\n            .edit()\n            .putInt(KEY_PREFIX + uri.toString(), normalize(offsetMs))\n            .apply()','context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE).edit {\n            putInt(KEY_PREFIX + uri.toString(), normalize(offsetMs))\n        }',"lyrics offset")
replace_file("PlaybackQueueStore.kt",'context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)\n            .edit()\n            .putString(ITEMS, array.toString())\n            .putInt(CURRENT_INDEX, persistedCurrentIndex.coerceAtLeast(0))\n            .putLong(POSITION, player.currentPosition.coerceAtLeast(0L))\n            .putBoolean("shuffle_enabled", player.shuffleModeEnabled)\n            .putInt("repeat_mode", player.repeatMode)\n            .putFloat("playback_speed", player.playbackParameters.speed.coerceIn(0.25f, 4f))\n            .apply()','context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit {\n            putString(ITEMS, array.toString())\n            putInt(CURRENT_INDEX, persistedCurrentIndex.coerceAtLeast(0))\n            putLong(POSITION, player.currentPosition.coerceAtLeast(0L))\n            putBoolean("shuffle_enabled", player.shuffleModeEnabled)\n            putInt("repeat_mode", player.repeatMode)\n            putFloat("playback_speed", player.playbackParameters.speed.coerceIn(0.25f, 4f))\n        }',"queue prefs",("import androidx.core.content.edit","import androidx.core.net.toUri"))
replace_file("TrackArtworkBackdrop.kt",'context.getSharedPreferences(PREFS, android.content.Context.MODE_PRIVATE).edit()\n            .putInt("primary", palette.primary.toArgb())\n            .putInt("secondary", palette.secondary.toArgb())\n            .putInt("background", palette.background.toArgb())\n            .putInt("surface", palette.surface.toArgb())\n            .apply()','context.getSharedPreferences(PREFS, android.content.Context.MODE_PRIVATE).edit {\n            putInt("primary", palette.primary.toArgb())\n            putInt("secondary", palette.secondary.toArgb())\n            putInt("background", palette.background.toArgb())\n            putInt("surface", palette.surface.toArgb())\n        }',"palette prefs",("import androidx.core.content.edit","import androidx.core.graphics.scale","import androidx.core.graphics.get"))
replace_file("TrackMetadataRepository.kt",'prefs.edit().putString("items", all.toString()).apply()','prefs.edit { putString("items", all.toString()) }',"metadata prefs",("import androidx.core.content.edit","import androidx.core.net.toUri"))
for name in ["LocalMediaRepository.kt","PlaybackQueueStore.kt","TrackMetadataRepository.kt"]:
 p=BASE/name; s=read(p).replace("Uri.parse(uri)","uri.toUri()").replace("Uri.parse(metadata.artworkUrl)","metadata.artworkUrl.toUri()"); write(p,s)
p=BASE/"NetworkStreamCard.kt"; s=imp(read(p),"import androidx.core.net.toUri")
for x in ["import android.os.Build","import androidx.activity.compose.rememberLauncherForActivityResult","import androidx.activity.result.contract.ActivityResultContracts","import androidx.compose.ui.platform.LocalContext","import androidx.core.content.ContextCompat"]: s=imp(s,x)
old_fun='''@Composable
internal fun NetworkStreamCard(player: Player) {
    var address by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }'''
new_fun='''@Composable
internal fun NetworkStreamCard(player: Player) {
    var address by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    var pendingLocalUri by remember { mutableStateOf<Uri?>(null) }
    val context = LocalContext.current
    fun startPlayback(uri: Uri) {
        runCatching {
            player.setMediaItem(MediaItem.fromUri(uri))
            player.prepare()
            player.play()
            error = null
        }.onFailure { error = "Не удалось открыть поток: ${it.localizedMessage ?: "неизвестная ошибка"}" }
    }
    val localNetworkPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        val pending = pendingLocalUri
        pendingLocalUri = null
        if (granted && pending != null) startPlayback(pending)
        else if (pending != null) error = "Для доступа к локальному потоку разреши доступ к локальной сети в настройках Android."
    }'''
s=once(s,old_fun,new_fun,"NetworkStreamCard permission launcher")
old_click='''                    } else {
                        runCatching {
                            player.setMediaItem(MediaItem.fromUri(uri))
                            player.prepare()
                            player.play()
                            error = null
                        }.onFailure {
                            error = "Не удалось открыть поток: ${it.localizedMessage ?: "неизвестная ошибка"}"
                        }
                    }'''
new_click='''                    } else if (Build.VERSION.SDK_INT >= 37 && requiresLocalNetworkPermission(uri.host.orEmpty()) &&
                        ContextCompat.checkSelfPermission(context, "android.permission.ACCESS_LOCAL_NETWORK") != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                        pendingLocalUri = uri
                        localNetworkPermission.launch("android.permission.ACCESS_LOCAL_NETWORK")
                    } else {
                        startPlayback(uri)
                    }'''
s=once(s,old_click,new_click,"NetworkStreamCard permission request")
s += '''
private fun requiresLocalNetworkPermission(hostValue: String): Boolean {
    val host = hostValue.trim().trim('[', ']').lowercase()
    if (host == "localhost" || host.endsWith(".local") || host.endsWith(".lan") ||
        host.endsWith(".home") || host.endsWith(".internal") || !host.contains('.')) return true
    val parts = host.split('.').mapNotNull { it.toIntOrNull() }
    if (parts.size == 4 && parts.all { it in 0..255 }) {
        val a = parts[0]; val b = parts[1]
        return a == 10 || a == 127 || (a == 192 && b == 168) ||
            (a == 172 && b in 16..31) || (a == 169 && b == 254) ||
            (a == 100 && b in 64..127)
    }
    if (host.contains(':')) return host == "::1" || host.startsWith("fc") || host.startsWith("fd") || host.startsWith("fe80:")
    return false
}
'''
s=once(s,"Uri.parse(address.trim())","address.trim().toUri()","network stream URI")
write(p,s)
p=BASE/"TrackArtworkBackdrop.kt"; s=read(p); s=once(s,"Bitmap.createScaledBitmap(source, 40, 40, true)","source.scale(40, 40)","bitmap scale"); s=once(s,"sample.getPixel(x, y)","sample[x, y]","bitmap pixel"); write(p,s)
# Remove unused color, retain Media3 resources resolved by library resource name.
p=RES/"values/colors.xml"
if p.exists(): p.unlink()
write(RES/"values/keep.xml",'''<resources xmlns:tools="http://schemas.android.com/tools"\n    tools:keep="@drawable/media3_icon_next,@drawable/media3_icon_pause,@drawable/media3_icon_play,@drawable/media3_icon_previous,@drawable/media3_notification_pause,@drawable/media3_notification_play,@drawable/media3_notification_seek_to_next,@drawable/media3_notification_seek_to_previous,@string/media3_controls_play_description,@string/media3_controls_pause_description,@string/media3_controls_seek_to_previous_description,@string/media3_controls_seek_to_next_description" />\n''')
old=RES/"mipmap-anydpi-v26"; new=RES/"mipmap-anydpi"
if old.exists():
 new.mkdir(parents=True,exist_ok=True)
 for f in old.glob("*"):
  target=new/f.name
  if target.exists(): raise SystemExit(f"Icon target exists: {target}")
  shutil.move(str(f),str(target))
 old.rmdir()
new.mkdir(parents=True,exist_ok=True)
adaptive='''<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@android:color/black" />
    <foreground android:drawable="@drawable/chiyuri_launcher_foreground" />
</adaptive-icon>
'''
write(new/"ic_launcher.xml",adaptive)
write(new/"ic_launcher_round.xml",adaptive)
# Build adaptive icon foreground and monochrome layers, then remove obsolete density PNGs.
foreground=RES/"drawable-nodpi/chiyuri_launcher_foreground.png"
source_icon=Image.open(RES/"mipmap-xxxhdpi/ic_launcher.png").convert("RGBA")
source_icon.save(foreground)
mono=Image.new("RGBA",source_icon.size,(0,0,0,0))
mono_pixels=[]
for r,g,b,a in source_icon.getdata():
 luminance=0.2126*r+0.7152*g+0.0722*b
 alpha=max(0,min(255,int((luminance-48)*3.0)))
 alpha=alpha*a//255
 mono_pixels.append((255,255,255,alpha))
mono.putdata(mono_pixels)
mono.save(RES/"drawable-nodpi/chiyuri_launcher_monochrome.png")
adaptive='''<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@android:color/black" />
    <foreground android:drawable="@drawable/chiyuri_launcher_foreground" />
    <monochrome android:drawable="@drawable/chiyuri_launcher_monochrome" />
</adaptive-icon>
'''
new.mkdir(parents=True,exist_ok=True)
write(new/"ic_launcher.xml",adaptive)
write(new/"ic_launcher_round.xml",adaptive)
for density in ["mipmap-mdpi","mipmap-hdpi","mipmap-xhdpi","mipmap-xxhdpi","mipmap-xxxhdpi"]:
 folder=RES/density
 for name in ["ic_launcher.png","ic_launcher_round.png"]:
  icon=folder/name
  if icon.exists(): icon.unlink()
 try: folder.rmdir()
 except OSError: pass
# Update Gradle wrapper inside the source archive.
archive=ROOT/"ChiyuriPlayer-0.2.0-source-prep.zip"
if archive.exists():
 tmp=archive.with_suffix(".zip.tmp")
 with zipfile.ZipFile(archive,"r") as zin, zipfile.ZipFile(tmp,"w",zipfile.ZIP_DEFLATED) as zout:
  for item in zin.infolist():
   data=zin.read(item.filename)
   if item.filename.endswith("/gradle/wrapper/gradle-wrapper.properties"): data=data.replace(b"gradle-9.3.1-bin.zip",b"gradle-9.9.0-bin.zip")
   zout.writestr(item,data)
 tmp.replace(archive)
print("v0.5.1 lint remediation applied.")
