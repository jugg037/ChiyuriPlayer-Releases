from pathlib import Path\nimport re

def replace_once(path: Path, old: str, new: str, label: str):
    source = path.read_text(encoding="utf-8")
    if old not in source:
        raise SystemExit(f"patch_0460: missing {label}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

PKG = Path("app/src/main/java/com/chiyuri/player")
TEST = Path("app/src/test/java/com/chiyuri/player")

(PKG / "DlnaDiscoveryClient.kt").write_text('''package com.chiyuri.player

import android.content.Context
import android.net.wifi.WifiManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.SocketTimeoutException
import java.net.URI
import java.nio.charset.StandardCharsets

data class DlnaServerEndpoint(
    val location: String,
    val host: String,
    val serverHeader: String,
    val uniqueServiceName: String,
    val searchTarget: String
)

internal fun parseSsdpResponse(raw: String): DlnaServerEndpoint? {
    val lines = raw.lineSequence().toList()
    val status = lines.firstOrNull().orEmpty()
    if (!status.startsWith("HTTP/1.1 200", ignoreCase = true) &&
        !status.startsWith("HTTP/1.0 200", ignoreCase = true)) return null
    val headers = lines.drop(1).mapNotNull { line ->
        val separator = line.indexOf(':')
        if (separator <= 0) null
        else line.substring(0, separator).trim().lowercase() to line.substring(separator + 1).trim()
    }.toMap()
    val location = headers["location"] ?: return null
    val uri = runCatching { URI(location) }.getOrNull() ?: return null
    val scheme = uri.scheme?.lowercase()
    val host = uri.host ?: return null
    if (scheme !in setOf("http", "https") || !requiresLocalNetworkPermission(host)) return null
    return DlnaServerEndpoint(
        location = location,
        host = host,
        serverHeader = headers["server"].orEmpty(),
        uniqueServiceName = headers["usn"].orEmpty(),
        searchTarget = headers["st"].orEmpty()
    )
}

object DlnaDiscoveryClient {
    private const val SSDP_ADDRESS = "239.255.255.250"
    private const val SSDP_PORT = 1900
    private const val SEARCH_WINDOW_MS = 3_000L

    suspend fun discover(context: Context): List<DlnaServerEndpoint> = withContext(Dispatchers.IO) {
        val wifi = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
        val multicastLock = runCatching {
            wifi?.createMulticastLock("ChiyuriPlayer.DLNA")?.apply {
                setReferenceCounted(false)
                acquire()
            }
        }.getOrNull()
        val found = linkedMapOf<String, DlnaServerEndpoint>()
        val message = (
            "M-SEARCH * HTTP/1.1\\r\\n" +
                "HOST: $SSDP_ADDRESS:$SSDP_PORT\\r\\n" +
                "MAN: \\"ssdp:discover\\"\\r\\n" +
                "MX: 2\\r\\n" +
                "ST: urn:schemas-upnp-org:device:MediaServer:1\\r\\n" +
                "USER-AGENT: Android UPnP/1.1 ChiyuriPlayer\\r\\n\\r\\n"
            ).toByteArray(StandardCharsets.US_ASCII)
        val socket = DatagramSocket()
        try {
            socket.soTimeout = 300
            val destination = InetAddress.getByName(SSDP_ADDRESS)
            repeat(2) {
                socket.send(DatagramPacket(message, message.size, destination, SSDP_PORT))
            }
            val deadline = System.currentTimeMillis() + SEARCH_WINDOW_MS
            while (System.currentTimeMillis() < deadline) {
                val buffer = ByteArray(8192)
                val packet = DatagramPacket(buffer, buffer.size)
                try {
                    socket.receive(packet)
                    val response = String(packet.data, packet.offset, packet.length, StandardCharsets.UTF_8)
                    parseSsdpResponse(response)?.let { found.putIfAbsent(it.location, it) }
                } catch (_: SocketTimeoutException) {
                    // Continue until the bounded discovery window expires.
                }
            }
        } finally {
            runCatching { socket.close() }
            runCatching { if (multicastLock?.isHeld == true) multicastLock.release() }
        }
        found.values.sortedBy { it.host }
    }
}
''', encoding="utf-8")

(PKG / "DlnaDiscoveryScreen.kt").write_text('''package com.chiyuri.player

import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Cloud
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
internal fun DlnaDiscoveryScreen(modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var servers by remember { mutableStateOf<List<DlnaServerEndpoint>>(emptyList()) }
    var scanning by remember { mutableStateOf(false) }
    var scanned by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }

    fun scan() {
        scope.launch {
            scanning = true
            error = null
            val result = withContext(Dispatchers.IO) {
                runCatching { DlnaDiscoveryClient.discover(context) }
            }
            result.onSuccess {
                servers = it
                scanned = true
            }.onFailure {
                error = it.message ?: "Не удалось выполнить поиск DLNA/UPnP устройств."
            }
            scanning = false
        }
    }

    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) scan() else error = "Для поиска медиасерверов разреши доступ к локальной сети Android."
    }

    Column(modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("Обнаружение DLNA/UPnP", style = MaterialTheme.typography.titleLarge)
        Text(
            "Поиск медиасерверов в локальной сети через SSDP. Содержимое устройств и сетевые URL не загружаются.",
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            style = MaterialTheme.typography.bodySmall
        )
        Button(
            onClick = {
                if (Build.VERSION.SDK_INT >= 37 &&
                    ContextCompat.checkSelfPermission(context, "android.permission.ACCESS_LOCAL_NETWORK") != android.content.pm.PackageManager.PERMISSION_GRANTED
                ) {
                    permissionLauncher.launch("android.permission.ACCESS_LOCAL_NETWORK")
                } else scan()
            },
            enabled = !scanning,
            modifier = Modifier.fillMaxWidth()
        ) {
            androidx.compose.material3.Icon(Icons.Default.Cloud, contentDescription = null)
            Text("  Найти медиасерверы")
        }
        if (scanning) Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            CircularProgressIndicator()
            Text("Поиск устройств в сети…")
        }
        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        if (scanned && servers.isEmpty() && !scanning) {
            Text("Медиасерверы не обнаружены. Проверь, что устройство и сервер находятся в одной локальной сети.")
        }
        Text("Найдено: ${servers.size}", style = MaterialTheme.typography.titleMedium)
        LazyColumn(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            items(servers, key = { it.location }) { server ->
                Surface(
                    color = MaterialTheme.colorScheme.surface,
                    shape = MaterialTheme.shapes.medium,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(server.host, color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.titleSmall)
                        if (server.serverHeader.isNotBlank()) Text(server.serverHeader, color = MaterialTheme.colorScheme.onSurface, style = MaterialTheme.typography.bodySmall)
                        if (server.searchTarget.isNotBlank()) Text(server.searchTarget, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.labelSmall)
                        Text(server.location, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }
    }
}
''', encoding="utf-8")

p = PKG / "MainActivity.kt"
replace_once(
    p,
    '''                        "WebDAV" -> WebDavLibraryScreen(player, Modifier.weight(1f))''',
    '''                        "WebDAV" -> WebDavLibraryScreen(player, Modifier.weight(1f))
                        "DLNA" -> DlnaDiscoveryScreen(Modifier.weight(1f))''',
    "DLNA navigation route"
)
replace_once(
    p,
    '''                                ActionCard("Сетевые папки WebDAV", "Защищённое подключение к NAS и облачным хранилищам", Icons.Default.Cloud) { morePage = "WebDAV" }''',
    '''                                ActionCard("Сетевые папки WebDAV", "Защищённое подключение к NAS и облачным хранилищам", Icons.Default.Cloud) { morePage = "WebDAV" }
                                ActionCard("DLNA / UPnP", "Поиск медиасерверов в локальной сети", Icons.Default.Cloud) { morePage = "DLNA" }''',
    "DLNA action card"
)

manifest = Path("app/src/main/AndroidManifest.xml")
ms = manifest.read_text(encoding="utf-8")
for permission in [
    '    <uses-permission android:name="android.permission.ACCESS_WIFI_STATE" />',
    '    <uses-permission android:name="android.permission.CHANGE_WIFI_MULTICAST_STATE" />'
]:
    if permission not in ms:
        ms = ms.replace('    <uses-permission android:name="android.permission.INTERNET" />',
                        '    <uses-permission android:name="android.permission.INTERNET" />\n' + permission, 1)
manifest.write_text(ms, encoding="utf-8")

gradle = Path("app/build.gradle.kts")
gs = gradle.read_text(encoding="utf-8")
gs = gs.replace('versionName = "0.5.8"', 'versionName = "0.5.9"')
gs = gs.replace("versionCode = 344", "versionCode = 345")
gs = gs.replace('orElse("344")', 'orElse("345")')
gs, _ = re.subn(r'orElse\("\d+"\)', 'orElse("345")', gs)
if 'orElse("345")' not in gs:
    raise SystemExit("patch_0460: Gradle fallback version code was not updated")
gradle.write_text(gs, encoding="utf-8")

(TEST / "DlnaSsdpParserTest.kt").write_text('''package com.chiyuri.player

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class DlnaSsdpParserTest {
    @Test fun parsesLocalMediaServerResponseCaseInsensitively() {
        val response = listOf(
            "HTTP/1.1 200 OK",
            "LOCATION: http://192.168.1.25:1400/rootDesc.xml",
            "SERVER: Example DLNA/1.0",
            "USN: uuid:media-server-1",
            "ST: urn:schemas-upnp-org:device:MediaServer:1",
            "",
            ""
        ).joinToString("\\n")
        val parsed = parseSsdpResponse(response)
        assertEquals("192.168.1.25", parsed?.host)
        assertEquals("Example DLNA/1.0", parsed?.serverHeader)
        assertEquals("uuid:media-server-1", parsed?.uniqueServiceName)
    }

    @Test fun rejectsPublicAndMalformedLocations() {
        val publicResponse = listOf("HTTP/1.1 200 OK", "LOCATION: https://example.com/device.xml", "", "").joinToString("\\n")
        val malformedResponse = listOf("HTTP/1.1 200 OK", "SERVER: Missing location", "", "").joinToString("\\n")
        assertNull(parseSsdpResponse(publicResponse))
        assertNull(parseSsdpResponse(malformedResponse))
    }
}
''', encoding="utf-8")

print("patch_0460: safe SSDP-only DLNA/UPnP discovery, local-network permission, UI and tests added; version 0.5.9/345")
