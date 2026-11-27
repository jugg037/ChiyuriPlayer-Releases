from pathlib import Path
ROOT = Path.cwd()
PKG = ROOT / "app/src/main/java/com/chiyuri/player"
TEST = ROOT / "app/src/test/java/com/chiyuri/player"

(PKG / "RadioStationStore.kt").write_text('''package com.chiyuri.player

import android.content.Context
import androidx.core.content.edit
import org.json.JSONArray
import org.json.JSONObject
import java.net.URI

data class RadioStation(val name: String, val url: String, val addedAt: Long)

/** Strict HTTPS-only station bookmarks stored privately on the device. */
object RadioStationStore {
    private const val PREFS = "radio_stations"
    private const val KEY = "stations"
    private const val MAX_STATIONS = 50

    fun load(context: Context): List<RadioStation> {
        val raw = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY, "[]") ?: "[]"
        return runCatching {
            val array = JSONArray(raw)
            buildList {
                for (index in 0 until array.length()) {
                    val item = array.optJSONObject(index) ?: continue
                    val url = normalizeRadioStationUrl(item.optString("url")) ?: continue
                    val name = normalizeRadioStationName(item.optString("name"), url) ?: continue
                    add(RadioStation(name, url, item.optLong("added_at", 0L).coerceAtLeast(0L)))
                }
            }.distinctBy { it.url }.take(MAX_STATIONS)
        }.getOrDefault(emptyList())
    }

    fun add(context: Context, rawName: String, rawUrl: String): List<RadioStation> {
        val url = normalizeRadioStationUrl(rawUrl) ?: return load(context)
        val name = normalizeRadioStationName(rawName, url) ?: return load(context)
        val updated = (listOf(RadioStation(name, url, System.currentTimeMillis())) + load(context).filterNot { it.url == url })
            .take(MAX_STATIONS)
        persist(context, updated)
        return updated
    }

    fun remove(context: Context, url: String): List<RadioStation> {
        val updated = load(context).filterNot { it.url == url }
        persist(context, updated)
        return updated
    }

    private fun persist(context: Context, stations: List<RadioStation>) {
        val array = JSONArray()
        stations.forEach { array.put(JSONObject().put("name", it.name).put("url", it.url).put("added_at", it.addedAt)) }
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit { putString(KEY, array.toString()) }
    }
}

internal fun normalizeRadioStationUrl(raw: String): String? = runCatching {
    val uri = URI(raw.trim())
    if (!uri.scheme.equals("https", true) || uri.host.isNullOrBlank() || uri.userInfo != null) return null
    uri.normalize().toASCIIString()
}.getOrNull()

internal fun normalizeRadioStationName(raw: String, normalizedUrl: String): String? {
    val name = raw.trim().replace(Regex("\\\\s+"), " ").take(80)
    if (name.isNotBlank()) return name
    return runCatching { URI(normalizedUrl).host?.take(80) }.getOrNull()?.takeIf { it.isNotBlank() }
}
''', encoding="utf-8")

p = PKG / "NetworkStreamCard.kt"
s = p.read_text(encoding="utf-8")
s = s.replace('import androidx.compose.material3.Surface\n', 'import androidx.compose.material3.Surface\nimport androidx.compose.material3.TextButton\nimport androidx.compose.material3.IconButton\n', 1)
old_state = '''    var address by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    var pendingLocalUri by remember { mutableStateOf<Uri?>(null) }
    val context = LocalContext.current'''
new_state = '''    var address by remember { mutableStateOf("") }
    val context = LocalContext.current
    var error by remember { mutableStateOf<String?>(null) }
    var stationName by remember { mutableStateOf("") }
    var stations by remember(context) { mutableStateOf(RadioStationStore.load(context)) }
    var pendingLocalUri by remember { mutableStateOf<Uri?>(null) }'''
if old_state not in s: raise SystemExit("patch_0438: network card state anchor missing")
s = s.replace(old_state, new_state, 1)
anchor = '''    val localNetworkPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        val pending = pendingLocalUri
        pendingLocalUri = null
        if (granted && pending != null) startPlayback(pending)
        else if (pending != null) error = "Для доступа к локальному потоку разреши доступ к локальной сети в настройках Android."
    }
    Surface('''
replacement = '''    val localNetworkPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        val pending = pendingLocalUri
        pendingLocalUri = null
        if (granted && pending != null) startPlayback(pending)
        else if (pending != null) error = "Для доступа к локальному потоку разреши доступ к локальной сети в настройках Android."
    }
    fun requestPlayback(uri: Uri) {
        if (Build.VERSION.SDK_INT >= 37 && requiresLocalNetworkPermission(uri.host.orEmpty()) &&
            ContextCompat.checkSelfPermission(context, "android.permission.ACCESS_LOCAL_NETWORK") != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            pendingLocalUri = uri
            localNetworkPermission.launch("android.permission.ACCESS_LOCAL_NETWORK")
        } else startPlayback(uri)
    }
    Surface('''
if anchor not in s: raise SystemExit("patch_0438: local network permission anchor missing")
s = s.replace(anchor, replacement, 1)
old_button = '''            Button(
                onClick = {
                    val uri = runCatching { address.trim().toUri() }.getOrNull()
                    if (uri == null || uri.host.isNullOrBlank() || uri.scheme != "https") {
                        error = "Для сетевого воспроизведения нужна корректная HTTPS-ссылка."
                    } else if (Build.VERSION.SDK_INT >= 37 && requiresLocalNetworkPermission(uri.host.orEmpty()) &&
                        ContextCompat.checkSelfPermission(context, "android.permission.ACCESS_LOCAL_NETWORK") != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                        pendingLocalUri = uri
                        localNetworkPermission.launch("android.permission.ACCESS_LOCAL_NETWORK")
                    } else {
                        startPlayback(uri)
                    }
                },
                enabled = address.isNotBlank(),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Воспроизвести ссылку")
            }
            error?.let {'''
new_button = '''            Button(
                onClick = {
                    val normalized = normalizeRadioStationUrl(address)
                    if (normalized == null) {
                        error = "Для сетевого воспроизведения нужна корректная HTTPS-ссылка без логина и пароля в URL."
                    } else requestPlayback(normalized.toUri())
                },
                enabled = address.isNotBlank(),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Воспроизвести ссылку")
            }
            OutlinedTextField(
                value = stationName,
                onValueChange = { stationName = it.take(80) },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                label = { Text("Название радиостанции") },
                placeholder = { Text("Например, Chiyuri Radio") }
            )
            TextButton(
                onClick = {
                    val normalized = normalizeRadioStationUrl(address)
                    if (normalized == null) error = "Сначала укажи корректную HTTPS-ссылку."
                    else {
                        stations = RadioStationStore.add(context, stationName, normalized)
                        stationName = ""
                        error = null
                    }
                },
                enabled = address.isNotBlank(),
                modifier = Modifier.fillMaxWidth()
            ) { Text("Сохранить радиостанцию") }
            if (stations.isNotEmpty()) {
                Text("Избранные станции", color = MaterialTheme.colorScheme.onSurface, style = MaterialTheme.typography.titleSmall)
                stations.forEach { station ->
                    Row(Modifier.fillMaxWidth(), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(station.name, color = MaterialTheme.colorScheme.onSurface, maxLines = 1)
                            Text(station.url, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall, maxLines = 1)
                        }
                        TextButton(onClick = { address = station.url; requestPlayback(station.url.toUri()) }) { Text("▶") }
                        IconButton(onClick = { stations = RadioStationStore.remove(context, station.url) }) {
                            Text("×", color = MaterialTheme.colorScheme.error)
                        }
                    }
                }
            }
            error?.let {'''
if old_button not in s: raise SystemExit("patch_0438: stream playback button anchor missing")
s = s.replace(old_button, new_button, 1)
p.write_text(s, encoding="utf-8")

(TEST / "RadioStationStoreTest.kt").write_text('''package com.chiyuri.player

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class RadioStationStoreTest {
    @Test fun acceptsHttpsUrlsAndNormalizesPath() {
        assertEquals("https://radio.example/live", normalizeRadioStationUrl("https://radio.example/a/../live"))
    }

    @Test fun rejectsInsecureOrCredentialBearingUrls() {
        assertNull(normalizeRadioStationUrl("http://radio.example/live"))
        assertNull(normalizeRadioStationUrl("https:///live"))
        assertNull(normalizeRadioStationUrl("https://user:pass@radio.example/live"))
    }

    @Test fun stationNamesAreTrimmedAndFallBackToHost() {
        assertEquals("My Radio", normalizeRadioStationName("  My   Radio ", "https://radio.example/live"))
        assertEquals("radio.example", normalizeRadioStationName(" ", "https://radio.example/live"))
        assertTrue(normalizeRadioStationName("x".repeat(100), "https://radio.example/live")!!.length <= 80)
    }
}
''', encoding="utf-8")

print("patch_0438: local HTTPS radio bookmarks with persistent favorites and validation applied")
