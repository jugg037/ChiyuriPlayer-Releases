from pathlib import Path

def replace_once(path: Path, old: str, new: str, label: str):
    source = path.read_text(encoding="utf-8")
    if old not in source:
        raise SystemExit(f"patch_0453: missing {label}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

PKG = Path("app/src/main/java/com/chiyuri/player")
TEST = Path("app/src/test/java/com/chiyuri/player")
GRADLE = Path("app/build.gradle.kts")
gradle = GRADLE.read_text(encoding="utf-8")
if 'implementation("com.squareup.okhttp3:okhttp:4.12.0")' not in gradle:
    anchor = '    implementation("eu.agno3.jcifs:jcifs-ng:2.1.10")'
    if anchor not in gradle:
        raise SystemExit("patch_0453: dependency insertion anchor missing")
    gradle = gradle.replace(anchor, '    implementation("com.squareup.okhttp3:okhttp:4.12.0")\n' + anchor, 1)
    GRADLE.write_text(gradle, encoding="utf-8")

(PKG / "WebDavServerStore.kt").write_text('''package com.chiyuri.player

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import androidx.core.content.edit
import org.json.JSONArray
import org.json.JSONObject
import java.net.URI
import java.net.URLEncoder
import java.security.KeyStore
import java.security.MessageDigest
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

data class WebDavServerConfig(
    val id: String,
    val baseUrl: String,
    val username: String,
    val password: String
)

data class WebDavEntry(
    val name: String,
    val relativePath: String,
    val uri: String,
    val isDirectory: Boolean,
    val sizeBytes: Long,
    val mimeType: String?
)

internal fun normalizeWebDavBaseUrl(raw: String): String? {
    val parsed = runCatching { URI(raw.trim()).normalize() }.getOrNull() ?: return null
    if (!parsed.scheme.equals("https", true) || parsed.host.isNullOrBlank() ||
        parsed.rawUserInfo != null || parsed.rawQuery != null || parsed.rawFragment != null) return null
    val host = parsed.host.lowercase()
    val authority = if (parsed.port >= 0) "$host:${parsed.port}" else host
    val rawPath = parsed.rawPath.orEmpty()
    if (rawPath.split('/').any { it == "." || it == ".." }) return null
    val path = rawPath.trimEnd('/') + "/"
    return "https://$authority$path".takeIf { it.length <= 2048 }
}

internal fun webDavServerId(baseUrl: String): String =
    MessageDigest.getInstance("SHA-256")
        .digest(baseUrl.toByteArray(Charsets.UTF_8))
        .take(8)
        .joinToString("") { "%02x".format(it) }

internal fun buildWebDavItemUri(serverId: String, relativePath: String): String? {
    if (!serverId.matches(Regex("^[a-f0-9]{16}$"))) return null
    val segments = relativePath.split('/').filter { it.isNotBlank() }
    if (segments.any { it == "." || it == ".." || it.contains('\\') }) return null
    val encoded = segments.joinToString("/") {
        URLEncoder.encode(it, "UTF-8").replace("+", "%20")
    }
    return "webdav://$serverId/$encoded"
}

internal fun resolveWebDavRequestUrl(baseUrl: String, relativePath: String): String? {
    val normalized = normalizeWebDavBaseUrl(baseUrl) ?: return null
    val base = URI(normalized)
    val segments = relativePath.split('/').filter { it.isNotBlank() }
    if (segments.any { it == "." || it == ".." || it.contains('\\') }) return null
    val suffix = segments.joinToString("/") {
        URLEncoder.encode(it, "UTF-8").replace("+", "%20")
    }
    val path = base.rawPath.trimEnd('/') + if (suffix.isBlank()) "/" else "/$suffix"
    return "https://${base.rawAuthority}$path"
}

object WebDavServerStore {
    private const val PREFS = "webdav_servers"
    private const val KEY_SERVERS = "servers"
    private const val KEY_ALIAS = "ChiyuriPlayer.WebDAV.Credentials"

    fun loadAll(context: Context): List<WebDavServerConfig> {
        val raw = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_SERVERS, "[]") ?: "[]"
        return runCatching {
            val array = JSONArray(raw)
            buildList {
                for (index in 0 until array.length()) {
                    val item = array.optJSONObject(index) ?: continue
                    val baseUrl = normalizeWebDavBaseUrl(item.optString("base_url")) ?: continue
                    add(WebDavServerConfig(
                        webDavServerId(baseUrl),
                        baseUrl,
                        item.optString("username"),
                        decrypt(item.optString("password"))
                    ))
                }
            }.distinctBy { it.id }.take(20)
        }.getOrDefault(emptyList())
    }

    fun find(context: Context, id: String): WebDavServerConfig? =
        loadAll(context).firstOrNull { it.id == id }

    fun save(context: Context, config: WebDavServerConfig) {
        val baseUrl = normalizeWebDavBaseUrl(config.baseUrl) ?: return
        val normalized = config.copy(id = webDavServerId(baseUrl), baseUrl = baseUrl)
        val updated = (listOf(normalized) + loadAll(context).filterNot { it.id == normalized.id }).take(20)
        val array = JSONArray()
        updated.forEach { server ->
            array.put(JSONObject()
                .put("base_url", server.baseUrl)
                .put("username", server.username.take(128))
                .put("password", encrypt(server.password)))
        }
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit { putString(KEY_SERVERS, array.toString()) }
    }

    private fun secretKey(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(KeyGenParameterSpec.Builder(
            KEY_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
        ).setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setRandomizedEncryptionRequired(true)
            .build())
        return generator.generateKey()
    }

    private fun encrypt(value: String): String {
        if (value.isEmpty()) return ""
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, secretKey())
        return Base64.encodeToString(cipher.iv + cipher.doFinal(value.toByteArray(Charsets.UTF_8)), Base64.NO_WRAP)
    }

    private fun decrypt(value: String): String {
        if (value.isBlank()) return ""
        return runCatching {
            val bytes = Base64.decode(value, Base64.NO_WRAP)
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, secretKey(), GCMParameterSpec(128, bytes.copyOfRange(0, 12)))
            String(cipher.doFinal(bytes.copyOfRange(12, bytes.size)), Charsets.UTF_8)
        }.getOrDefault("")
    }
}
''', encoding="utf-8")

(PKG / "WebDavNetworkClient.kt").write_text('''package com.chiyuri.player

import android.net.Uri
import android.util.Xml
import okhttp3.Credentials
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.xmlpull.v1.XmlPullParser
import java.io.IOException
import java.io.StringReader
import java.net.URI
import java.util.concurrent.TimeUnit

internal object WebDavHttp {
    val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(12, TimeUnit.SECONDS)
        .readTimeout(25, TimeUnit.SECONDS)
        .writeTimeout(12, TimeUnit.SECONDS)
        .followRedirects(false)
        .build()
}

object WebDavNetworkClient {
    private const val PROPFIND_BODY = """<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:"><d:prop><d:resourcetype/><d:getcontentlength/><d:getcontenttype/><d:getlastmodified/></d:prop></d:propfind>"""

    fun list(server: WebDavServerConfig, relativePath: String): List<WebDavEntry> {
        val url = resolveWebDavRequestUrl(server.baseUrl, relativePath)
            ?: throw IOException("Некорректный WebDAV-путь")
        val request = Request.Builder()
            .url(url)
            .header("Depth", "1")
            .header("Content-Type", "application/xml; charset=utf-8")
            .method("PROPFIND", PROPFIND_BODY.toRequestBody("application/xml; charset=utf-8".toMediaType()))
            .apply {
                if (server.username.isNotBlank()) {
                    header("Authorization", Credentials.basic(server.username, server.password))
                }
            }
            .build()
        WebDavHttp.client.newCall(request).execute().use { response ->
            if (response.code != 207 && response.code != 200) {
                throw IOException("WebDAV вернул HTTP ${response.code}")
            }
            val xml = response.body?.string() ?: throw IOException("WebDAV не вернул список файлов")
            return parseWebDavMultiStatus(xml, server, relativePath)
        }
    }

    internal fun parseWebDavMultiStatus(
        xml: String,
        server: WebDavServerConfig,
        currentPath: String
    ): List<WebDavEntry> {
        val parser = Xml.newPullParser()
        parser.setFeature(XmlPullParser.FEATURE_PROCESS_NAMESPACES, true)
        parser.setInput(StringReader(xml))
        val entries = mutableListOf<WebDavEntry>()
        var event = parser.eventType
        var inResponse = false
        var href: String? = null
        var directory = false
        var size = 0L
        var mime: String? = null
        while (event != XmlPullParser.END_DOCUMENT) {
            when (event) {
                XmlPullParser.START_TAG -> when (parser.name.substringAfter(':')) {
                    "response" -> {
                        inResponse = true
                        href = null
                        directory = false
                        size = 0L
                        mime = null
                    }
                    "href" -> if (inResponse) href = parser.nextText()
                    "collection" -> if (inResponse) directory = true
                    "getcontentlength" -> if (inResponse) size = parser.nextText().toLongOrNull()?.coerceAtLeast(0L) ?: 0L
                    "getcontenttype" -> if (inResponse) mime = parser.nextText().substringBefore(';').takeIf { it.isNotBlank() }
                }
                XmlPullParser.END_TAG -> if (parser.name.substringAfter(':') == "response" && inResponse) {
                    val resolved = href?.let { runCatching { URI(server.baseUrl).resolve(it) }.getOrNull() }
                    val base = runCatching { URI(server.baseUrl) }.getOrNull()
                    if (resolved != null && base != null &&
                        resolved.scheme.equals(base.scheme, true) &&
                        resolved.host.equals(base.host, true) &&
                        resolved.port == base.port) {
                        val basePath = base.path.trimEnd('/') + "/"
                        val responsePath = resolved.path
                        if (responsePath.startsWith(basePath)) {
                            val relative = responsePath.removePrefix(basePath).trim('/').let { Uri.decode(it) }
                            if (relative.isNotBlank() && relative != currentPath.trim('/')) {
                                val name = relative.substringAfterLast('/')
                                val itemUri = buildWebDavItemUri(server.id, relative)
                                if (name.isNotBlank() && itemUri != null) {
                                    entries += WebDavEntry(name, relative, itemUri, directory, if (directory) 0L else size, mime)
                                }
                            }
                        }
                    }
                    inResponse = false
                }
            }
            event = parser.next()
        }
        return entries.distinctBy { it.uri }
            .sortedWith(compareByDescending<WebDavEntry> { it.isDirectory }.thenBy { it.name.lowercase() })
    }
}
''', encoding="utf-8")

(PKG / "WebDavDataSource.kt").write_text('''package com.chiyuri.player

import android.content.Context
import android.net.Uri
import androidx.media3.common.C
import androidx.media3.common.util.UnstableApi
import androidx.media3.datasource.BaseDataSource
import androidx.media3.datasource.DataSource
import androidx.media3.datasource.DataSpec
import okhttp3.Credentials
import okhttp3.Request
import java.io.IOException
import java.io.InputStream

@UnstableApi
class WebDavDataSource(context: Context) : BaseDataSource(true) {
    private val appContext = context.applicationContext
    private var response: okhttp3.Response? = null
    private var input: InputStream? = null
    private var currentUri: Uri? = null
    private var bytesRemaining = C.LENGTH_UNSET.toLong()
    private var transferIsStarted = false

    override fun open(dataSpec: DataSpec): Long {
        transferInitializing(dataSpec)
        try {
            val uri = dataSpec.uri
            val id = uri.host ?: uri.authority ?: throw IOException("В WebDAV-ссылке отсутствует идентификатор сервера")
            val server = WebDavServerStore.find(appContext, id)
                ?: throw IOException("Сначала сохраните подключение WebDAV-сервера в приложении")
            val relativePath = uri.pathSegments.joinToString("/")
            val url = resolveWebDavRequestUrl(server.baseUrl, relativePath)
                ?: throw IOException("Некорректный WebDAV-путь")
            val request = Request.Builder().url(url).get().apply {
                if (server.username.isNotBlank()) {
                    header("Authorization", Credentials.basic(server.username, server.password))
                }
                if (dataSpec.position > 0L || dataSpec.length != C.LENGTH_UNSET.toLong()) {
                    val end = if (dataSpec.length == C.LENGTH_UNSET.toLong()) "" else (dataSpec.position + dataSpec.length - 1L).toString()
                    header("Range", "bytes=${dataSpec.position}-$end")
                }
            }.build()
            val opened = WebDavHttp.client.newCall(request).execute()
            response = opened
            if (!opened.isSuccessful) {
                opened.close()
                throw IOException("Не удалось открыть WebDAV-файл: HTTP ${opened.code}")
            }
            val body = opened.body ?: run {
                opened.close()
                throw IOException("WebDAV вернул пустой файл")
            }
            val stream = body.byteStream()
            if (opened.code == 200 && dataSpec.position > 0L) skipFully(stream, dataSpec.position)
            input = stream
            val contentLength = body.contentLength().takeIf { it >= 0L } ?: C.LENGTH_UNSET.toLong()
            bytesRemaining = if (contentLength == C.LENGTH_UNSET.toLong()) contentLength
                else (contentLength - if (opened.code == 200) dataSpec.position else 0L).coerceAtLeast(0L)
            if (dataSpec.length != C.LENGTH_UNSET.toLong()) {
                bytesRemaining = if (bytesRemaining == C.LENGTH_UNSET.toLong()) dataSpec.length else minOf(bytesRemaining, dataSpec.length)
            }
            currentUri = uri
            transferStarted(dataSpec)
            transferIsStarted = true
            return bytesRemaining
        } catch (error: Exception) {
            runCatching { close() }
            throw if (error is IOException) error else IOException("Не удалось открыть WebDAV-файл", error)
        }
    }

    override fun read(buffer: ByteArray, offset: Int, length: Int): Int {
        if (length == 0) return 0
        if (bytesRemaining == 0L) return C.RESULT_END_OF_INPUT
        val count = input?.read(buffer, offset, if (bytesRemaining > 0L) minOf(length.toLong(), bytesRemaining).toInt() else length)
            ?: throw IOException("WebDAV-поток не открыт")
        if (count == -1) return C.RESULT_END_OF_INPUT
        if (bytesRemaining > 0L) bytesRemaining -= count
        bytesTransferred(count)
        return count
    }

    override fun getUri(): Uri? = currentUri
    override fun getResponseHeaders(): Map<String, List<String>> = response?.headers?.toMultimap() ?: emptyMap()

    override fun close() {
        try {
            input?.close()
        } finally {
            input = null
            response?.close()
            response = null
            currentUri = null
            bytesRemaining = C.LENGTH_UNSET.toLong()
            if (transferIsStarted) transferEnded()
            transferIsStarted = false
        }
    }

    private fun skipFully(stream: InputStream, position: Long) {
        var skipped = 0L
        while (skipped < position) {
            val count = stream.skip(position - skipped)
            if (count > 0L) skipped += count else {
                if (stream.read() == -1) throw IOException("Позиция WebDAV-файла находится за концом файла")
                skipped++
            }
        }
    }

    class Factory(private val context: Context) : DataSource.Factory {
        override fun createDataSource(): DataSource = WebDavDataSource(context)
    }
}
''', encoding="utf-8")

# Route the private WebDAV scheme to its authenticated DataSource.
p = PKG / "SmbDataSource.kt"
replace_once(
    p,
    '''            val source = if (dataSpec.uri.scheme.equals("smb", true)) {
                SmbDataSource(context)
            } else defaultFactory.createDataSource()''',
    '''            val source = when (dataSpec.uri.scheme?.lowercase()) {
                "smb" -> SmbDataSource(context)
                "webdav" -> WebDavDataSource(context)
                else -> defaultFactory.createDataSource()
            }''',
    "SMB/WebDAV data source routing"
)

(PKG / "WebDavLibraryScreen.kt").write_text('''package com.chiyuri.player

import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
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
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.MusicNote
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.core.net.toUri
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.Player
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.net.URI

@Composable
internal fun WebDavLibraryScreen(player: Player, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var baseUrl by remember { mutableStateOf("") }
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var currentPath by remember { mutableStateOf("") }
    var activeServer by remember { mutableStateOf<WebDavServerConfig?>(null) }
    var entries by remember { mutableStateOf<List<WebDavEntry>>(emptyList()) }
    var savedServers by remember { mutableStateOf(WebDavServerStore.loadAll(context)) }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var pendingServer by remember { mutableStateOf<WebDavServerConfig?>(null) }

    fun loadDirectory(server: WebDavServerConfig, path: String) {
        loading = true
        error = null
        scope.launch {
            val result = withContext(Dispatchers.IO) {
                runCatching { WebDavNetworkClient.list(server, path) }
            }
            result.onSuccess {
                activeServer = server
                currentPath = path
                entries = it
                runCatching { WebDavServerStore.save(context, server) }
                    .onFailure { error = "Подключение работает, но не удалось сохранить учётные данные: ${it.message}" }
                savedServers = WebDavServerStore.loadAll(context)
            }.onFailure { error = it.message ?: "Не удалось подключиться к WebDAV" }
            loading = false
        }
    }

    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        val pending = pendingServer
        pendingServer = null
        if (granted && pending != null) loadDirectory(pending, "")
        else if (pending != null) error = "Разреши доступ к локальной сети в настройках Android."
    }

    fun requestConnection(server: WebDavServerConfig) {
        val host = runCatching { URI(server.baseUrl).host }.getOrNull().orEmpty()
        if (Build.VERSION.SDK_INT >= 37 && requiresLocalNetworkPermission(host) &&
            ContextCompat.checkSelfPermission(context, "android.permission.ACCESS_LOCAL_NETWORK") != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            pendingServer = server
            permissionLauncher.launch("android.permission.ACCESS_LOCAL_NETWORK")
        } else loadDirectory(server, "")
    }

    fun connect() {
        val normalized = normalizeWebDavBaseUrl(baseUrl)
        if (normalized == null) {
            error = "Укажи корректный HTTPS-адрес WebDAV без логина и пароля в URL."
            return
        }
        val id = webDavServerId(normalized)
        requestConnection(WebDavServerConfig(id, normalized, username.trim(), password))
    }

    Column(modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Сетевые папки WebDAV", style = MaterialTheme.typography.titleMedium)
        Text("Защищённое HTTPS-подключение. Учётные данные сохраняются в зашифрованном виде через Android Keystore.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        if (savedServers.isNotEmpty()) {
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                savedServers.forEach { saved ->
                    TextButton(onClick = {
                        baseUrl = saved.baseUrl
                        username = saved.username
                        password = saved.password
                        requestConnection(saved)
                    }) { Text(URI(saved.baseUrl).host ?: saved.baseUrl) }
                }
            }
        }
        OutlinedTextField(baseUrl, { baseUrl = it }, Modifier.fillMaxWidth(), singleLine = true, label = { Text("HTTPS URL WebDAV") }, placeholder = { Text("https://nas.example/dav/") })
        OutlinedTextField(username, { username = it }, Modifier.fillMaxWidth(), singleLine = true, label = { Text("Пользователь") })
        OutlinedTextField(password, { password = it }, Modifier.fillMaxWidth(), singleLine = true, label = { Text("Пароль") }, visualTransformation = PasswordVisualTransformation())
        Button(onClick = ::connect, enabled = !loading, modifier = Modifier.fillMaxWidth()) { Text("Подключиться") }
        activeServer?.let { server ->
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(server.baseUrl + currentPath, style = MaterialTheme.typography.bodySmall, maxLines = 1)
                if (currentPath.isNotBlank()) TextButton(onClick = {
                    loadDirectory(server, currentPath.substringBeforeLast('/', ""))
                }) { Text("Назад") }
            }
        }
        error?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
        if (loading) CircularProgressIndicator()
        LazyColumn(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            items(entries, key = { it.uri }) { entry ->
                Surface(
                    color = MaterialTheme.colorScheme.surface,
                    shape = MaterialTheme.shapes.medium,
                    modifier = Modifier.fillMaxWidth().clickable {
                        val server = activeServer ?: return@clickable
                        if (entry.isDirectory) loadDirectory(server, entry.relativePath) else {
                            val item = MediaItem.Builder()
                                .setUri(entry.uri.toUri())
                                .setMimeType(entry.mimeType)
                                .setMediaMetadata(MediaMetadata.Builder().setTitle(entry.name).build())
                                .build()
                            player.setMediaItem(item)
                            player.prepare()
                            player.play()
                        }
                    }
                ) {
                    Row(Modifier.padding(horizontal = 12.dp, vertical = 10.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        androidx.compose.material3.Icon(
                            if (entry.isDirectory) Icons.Default.Folder else Icons.Default.MusicNote,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary
                        )
                        Column(Modifier.weight(1f)) {
                            Text(entry.name, color = MaterialTheme.colorScheme.onSurface, maxLines = 1)
                            if (!entry.isDirectory) Text("${entry.mimeType ?: "Файл"} • ${entry.sizeBytes / 1024} КБ", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
        }
    }
}
''', encoding="utf-8")

# Integrate the WebDAV browser into the Android "More" tab.
p = PKG / "MainActivity.kt"
replace_once(
    p,
    '''                        "SMB" -> SmbLibraryScreen(player, Modifier.weight(1f))''',
    '''                        "SMB" -> SmbLibraryScreen(player, Modifier.weight(1f))
                        "WebDAV" -> WebDavLibraryScreen(player, Modifier.weight(1f))''',
    "WebDAV navigation route"
)
replace_once(
    p,
    '''                                ActionCard("Сетевые папки SMB", "Подключение к NAS и общим папкам по SMB 2/3", Icons.Default.FolderShared) { morePage = "SMB" }''',
    '''                                ActionCard("Сетевые папки SMB", "Подключение к NAS и общим папкам по SMB 2/3", Icons.Default.FolderShared) { morePage = "SMB" }
                                ActionCard("Сетевые папки WebDAV", "Защищённое подключение к NAS и облачным хранилищам", Icons.Default.Cloud) { morePage = "WebDAV" }''',
    "WebDAV action card"
)

(TEST / "WebDavAddressTest.kt").write_text('''package com.chiyuri.player

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class WebDavAddressTest {
    @Test fun acceptsOnlyCredentialFreeHttpsEndpoints() {
        assertEquals("https://nas.example/dav/", normalizeWebDavBaseUrl("https://NAS.example/dav"))
        assertNull(normalizeWebDavBaseUrl("http://nas.example/dav"))
        assertNull(normalizeWebDavBaseUrl("https://user:pass@nas.example/dav"))
        assertNull(normalizeWebDavBaseUrl("https://nas.example/dav?token=secret"))
        assertNull(normalizeWebDavBaseUrl("https://nas.example/dav#fragment"))
    }

    @Test fun encodesPathsAndRejectsTraversal() {
        val id = "0123456789abcdef"
        assertEquals("webdav://0123456789abcdef/Music/A%20Song.mp3", buildWebDavItemUri(id, "Music/A Song.mp3"))
        assertNull(buildWebDavItemUri(id, "../private"))
        assertNull(buildWebDavItemUri(id, "Music/../private"))
        assertEquals("https://nas.example/dav/Music/A%20Song.mp3", resolveWebDavRequestUrl("https://nas.example/dav/", "Music/A Song.mp3"))
        assertNull(resolveWebDavRequestUrl("https://nas.example/dav/", "../private"))
    }
}
''', encoding="utf-8")

print("patch_0453: secure WebDAV browser, encrypted credentials and authenticated Media3 streaming added")
