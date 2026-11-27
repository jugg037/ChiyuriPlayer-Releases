from pathlib import Path
ROOT = Path.cwd()
PKG = ROOT / "app/src/main/java/com/chiyuri/player"
TEST = ROOT / "app/src/test/java/com/chiyuri/player"

p = ROOT / "app/build.gradle.kts"
s = p.read_text(encoding="utf-8")
anchor = '    implementation("androidx.media3:media3-session:1.11.1")\n'
replacement = anchor + '    implementation("eu.agno3.jcifs:jcifs-ng:2.1.10")\n    implementation("org.slf4j:slf4j-nop:1.7.36")\n'
if anchor not in s: raise SystemExit("patch_0444: dependency insertion anchor missing")
p.write_text(s.replace(anchor, replacement, 1), encoding="utf-8")

(PKG / "SmbServerStore.kt").write_text('''package com.chiyuri.player

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import androidx.core.content.edit
import org.json.JSONArray
import org.json.JSONObject
import java.net.URI
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

data class SmbServerConfig(
    val host: String,
    val share: String,
    val username: String,
    val domain: String,
    val password: String
)

data class SmbEntry(
    val name: String,
    val relativePath: String,
    val uri: String,
    val isDirectory: Boolean,
    val sizeBytes: Long,
    val mimeType: String?
)

internal fun normalizeSmbHost(raw: String): String? {
    val host = raw.trim().lowercase()
    if (host.isBlank() || host.contains("://") || host.any { it.isWhitespace() || it == '/' || it == '\\\\' }) return null
    if (!host.matches(Regex("[a-z0-9.-]+(:[0-9]{1,5})?"))) return null
    return host
}

internal fun normalizeSmbShare(raw: String): String? {
    val share = raw.trim().trim('/')
    if (share.isBlank() || share.contains('/') || share == "." || share == "..") return null
    return share
}

internal fun buildSmbUri(hostValue: String, shareValue: String, relativePath: String = ""): String? {
    val host = normalizeSmbHost(hostValue) ?: return null
    val share = normalizeSmbShare(shareValue) ?: return null
    val segments = listOf(share) + relativePath.split('/').filter { it.isNotBlank() }
    if (segments.any { it == "." || it == ".." }) return null
    val encoded = segments.joinToString("/") { segment ->
        java.net.URLEncoder.encode(segment, "UTF-8").replace("+", "%20")
    }
    return runCatching { URI("smb://$host/$encoded").toASCIIString() }.getOrNull()
}

/** Credentials are encrypted with an AES-GCM key held by Android Keystore. */
object SmbServerStore {
    private const val PREFS = "smb_servers"
    private const val KEY_SERVERS = "servers"
    private const val KEY_ALIAS = "ChiyuriPlayer.SMB.Credentials"

    fun loadAll(context: Context): List<SmbServerConfig> {
        val raw = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_SERVERS, "[]") ?: "[]"
        return runCatching {
            val array = JSONArray(raw)
            buildList {
                for (index in 0 until array.length()) {
                    val item = array.optJSONObject(index) ?: continue
                    val host = normalizeSmbHost(item.optString("host")) ?: continue
                    val share = normalizeSmbShare(item.optString("share")) ?: continue
                    val encrypted = item.optString("password")
                    add(SmbServerConfig(host, share, item.optString("username"), item.optString("domain"), decrypt(encrypted)))
                }
            }.distinctBy { "\u0024{it.host}|\u0024{it.share}" }.take(20)
        }.getOrDefault(emptyList())
    }

    fun find(context: Context, host: String, share: String): SmbServerConfig? =
        loadAll(context).firstOrNull { it.host.equals(host, true) && it.share.equals(share, true) }

    fun save(context: Context, config: SmbServerConfig) {
        val host = normalizeSmbHost(config.host) ?: return
        val share = normalizeSmbShare(config.share) ?: return
        val normalized = config.copy(host = host, share = share)
        val updated = (listOf(normalized) + loadAll(context).filterNot { it.host == host && it.share == share }).take(20)
        val array = JSONArray()
        updated.forEach { server ->
            array.put(JSONObject()
                .put("host", server.host)
                .put("share", server.share)
                .put("username", server.username)
                .put("domain", server.domain)
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
        val encrypted = cipher.doFinal(value.toByteArray(Charsets.UTF_8))
        return Base64.encodeToString(cipher.iv + encrypted, Base64.NO_WRAP)
    }

    private fun decrypt(value: String): String {
        if (value.isBlank()) return ""
        return runCatching {
            val bytes = Base64.decode(value, Base64.NO_WRAP)
            val iv = bytes.copyOfRange(0, 12)
            val encrypted = bytes.copyOfRange(12, bytes.size)
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, secretKey(), GCMParameterSpec(128, iv))
            String(cipher.doFinal(encrypted), Charsets.UTF_8)
        }.getOrDefault("")
    }
}
''', encoding="utf-8")

(PKG / "SmbNetworkClient.kt").write_text('''package com.chiyuri.player

import android.content.Context
import android.webkit.MimeTypeMap
import jcifs.CIFSContext
import jcifs.context.BaseContext
import jcifs.config.PropertyConfiguration
import jcifs.smb.NtlmPasswordAuthenticator
import jcifs.smb.SmbFile
import java.io.IOException
import java.util.Properties

internal fun createSmbContext(config: SmbServerConfig): CIFSContext {
    val properties = Properties().apply {
        setProperty("jcifs.smb.client.minVersion", "SMB202")
        setProperty("jcifs.smb.client.maxVersion", "SMB311")
        setProperty("jcifs.smb.client.connTimeout", "10000")
        setProperty("jcifs.smb.client.responseTimeout", "15000")
        setProperty("jcifs.smb.client.soTimeout", "15000")
    }
    val base = BaseContext(PropertyConfiguration(properties))
    return base.withCredentials(NtlmPasswordAuthenticator(config.domain, config.username, config.password))
}

object SmbNetworkClient {
    fun list(context: Context, config: SmbServerConfig, relativePath: String): List<SmbEntry> {
        val url = buildSmbUri(config.host, config.share, relativePath)
            ?: throw IOException("Некорректный SMB-путь")
        val cifs = createSmbContext(config)
        try {
            val directory = SmbFile(url.trimEnd('/') + "/", cifs)
            return directory.listFiles().mapNotNull { child ->
                runCatching {
                    val name = child.name.trimEnd('/').ifBlank { return@runCatching null }
                    val isDirectory = child.isDirectory
                    val childRelative = listOf(relativePath.trim('/'), name).filter { it.isNotBlank() }.joinToString("/")
                    val extension = name.substringAfterLast('.', "").lowercase()
                    SmbEntry(
                        name = name,
                        relativePath = childRelative,
                        uri = child.canonicalPath,
                        isDirectory = isDirectory,
                        sizeBytes = if (isDirectory) 0L else child.length().coerceAtLeast(0L),
                        mimeType = if (isDirectory) null else MimeTypeMap.getSingleton().getMimeTypeFromExtension(extension)
                    )
                }.getOrNull()
            }.sortedWith(compareByDescending<SmbEntry> { it.isDirectory }.thenBy { it.name.lowercase() })
        } finally {
            runCatching { cifs.close() }
        }
    }
}
''', encoding="utf-8")

(PKG / "SmbDataSource.kt").write_text('''package com.chiyuri.player

import android.content.Context
import android.net.Uri
import androidx.media3.common.C
import androidx.media3.datasource.BaseDataSource
import androidx.media3.datasource.DataSource
import androidx.media3.datasource.DataSpec
import androidx.media3.datasource.DefaultDataSource
import androidx.media3.datasource.TransferListener
import java.io.IOException
import java.io.InputStream

@OptIn(androidx.media3.common.util.UnstableApi::class)
class SmbDataSource(context: Context) : BaseDataSource(true) {
    private val appContext = context.applicationContext
    private var input: InputStream? = null
    private var cifs: jcifs.CIFSContext? = null
    private var currentUri: Uri? = null
    private var bytesRemaining = C.LENGTH_UNSET.toLong()
    private var transferIsStarted = false

    override fun open(dataSpec: DataSpec): Long {
        transferInitializing(dataSpec)
        try {
            val uri = dataSpec.uri
            val host = uri.authority ?: uri.host ?: throw IOException("В SMB-ссылке отсутствует сервер")
            val share = uri.pathSegments.firstOrNull() ?: throw IOException("В SMB-ссылке отсутствует общая папка")
            val server = SmbServerStore.find(appContext, host, share)
                ?: throw IOException("Сначала сохраните подключение SMB-сервера в приложении")
            val smbContext = createSmbContext(server)
            cifs = smbContext
            val smbFile = jcifs.smb.SmbFile(uri.toString(), smbContext)
            val stream = smbFile.inputStream
            input = stream
            val fileLength = smbFile.length().coerceAtLeast(0L)
            if (dataSpec.position > 0L) skipFully(stream, dataSpec.position)
            bytesRemaining = (fileLength - dataSpec.position).coerceAtLeast(0L)
            if (dataSpec.length != C.LENGTH_UNSET.toLong()) bytesRemaining = minOf(bytesRemaining, dataSpec.length)
            currentUri = uri
            transferStarted(dataSpec)
            transferIsStarted = true
            return bytesRemaining
        } catch (error: Exception) {
            runCatching { close() }
            throw if (error is IOException) error else IOException("Не удалось открыть SMB-файл", error)
        }
    }

    override fun read(buffer: ByteArray, offset: Int, length: Int): Int {
        if (length == 0) return 0
        if (bytesRemaining == 0L) return C.RESULT_END_OF_INPUT
        val count = input?.read(buffer, offset, if (bytesRemaining > 0L) minOf(length.toLong(), bytesRemaining).toInt() else length)
            ?: throw IOException("SMB-поток не открыт")
        if (count == -1) return C.RESULT_END_OF_INPUT
        if (bytesRemaining > 0L) bytesRemaining -= count
        bytesTransferred(count)
        return count
    }

    override fun getUri(): Uri? = currentUri
    override fun getResponseHeaders(): Map<String, List<String>> = emptyMap()

    override fun close() {
        try {
            input?.close()
        } finally {
            input = null
            runCatching { cifs?.close() }
            cifs = null
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
                if (stream.read() == -1) throw IOException("Позиция SMB-файла находится за концом файла")
                skipped++
            }
        }
    }

    @OptIn(androidx.media3.common.util.UnstableApi::class)
    class Factory(private val context: Context) : DataSource.Factory {
        override fun createDataSource(): DataSource = SmbDataSource(context)
    }
}

@OptIn(androidx.media3.common.util.UnstableApi::class)
class SmbRoutingDataSourceFactory(private val context: Context) : DataSource.Factory {
    override fun createDataSource(): DataSource = RoutingDataSource(context)

    @OptIn(androidx.media3.common.util.UnstableApi::class)
    private class RoutingDataSource(private val context: Context) : DataSource {
        private val defaultFactory = DefaultDataSource.Factory(context)
        private val listeners = mutableListOf<TransferListener>()
        private var active: DataSource? = null

        override fun addTransferListener(transferListener: TransferListener) {
            listeners += transferListener
            active?.addTransferListener(transferListener)
        }

        override fun open(dataSpec: DataSpec): Long {
            close()
            val source = if (dataSpec.uri.scheme.equals("smb", true)) {
                SmbDataSource(context)
            } else defaultFactory.createDataSource()
            listeners.forEach(source::addTransferListener)
            active = source
            return source.open(dataSpec)
        }

        override fun read(buffer: ByteArray, offset: Int, length: Int): Int =
            active?.read(buffer, offset, length) ?: throw IOException("Источник данных не открыт")

        override fun getUri(): Uri? = active?.uri
        override fun getResponseHeaders(): Map<String, List<String>> = active?.responseHeaders ?: emptyMap()

        override fun close() {
            val source = active
            active = null
            source?.close()
        }
    }
}
''', encoding="utf-8")

p = PKG / "PlaybackService.kt"
s = p.read_text(encoding="utf-8")
if 'import androidx.media3.exoplayer.source.DefaultMediaSourceFactory' not in s:
    s = s.replace('import androidx.media3.exoplayer.ExoPlayer\n', 'import androidx.media3.exoplayer.ExoPlayer\nimport androidx.media3.exoplayer.source.DefaultMediaSourceFactory\n', 1)
s = s.replace('val player = ExoPlayer.Builder(this).build()', 'val player = ExoPlayer.Builder(this).setMediaSourceFactory(DefaultMediaSourceFactory(SmbRoutingDataSourceFactory(this))).build()', 1)
p.write_text(s, encoding="utf-8")

p = PKG / "NetworkStreamCard.kt"
s = p.read_text(encoding="utf-8").replace('private fun requiresLocalNetworkPermission(hostValue: String): Boolean', 'internal fun requiresLocalNetworkPermission(hostValue: String): Boolean', 1)
p.write_text(s, encoding="utf-8")

(PKG / "SmbLibraryScreen.kt").write_text('''package com.chiyuri.player

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

@Composable
internal fun SmbLibraryScreen(player: Player, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var host by remember { mutableStateOf("") }
    var share by remember { mutableStateOf("") }
    var domain by remember { mutableStateOf("") }
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var currentPath by remember { mutableStateOf("") }
    var activeServer by remember { mutableStateOf<SmbServerConfig?>(null) }
    var entries by remember { mutableStateOf<List<SmbEntry>>(emptyList()) }
    var savedServers by remember { mutableStateOf(SmbServerStore.loadAll(context)) }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var pendingServer by remember { mutableStateOf<SmbServerConfig?>(null) }

    fun loadDirectory(server: SmbServerConfig, path: String) {
        loading = true
        error = null
        scope.launch {
            val result = withContext(Dispatchers.IO) { runCatching { SmbNetworkClient.list(context, server, path) } }
            result.onSuccess {
                activeServer = server
                currentPath = path
                entries = it
                runCatching { SmbServerStore.save(context, server) }
                    .onFailure { error = "Подключение работает, но не удалось безопасно сохранить пароль: \u0024{it.message}" }
                savedServers = SmbServerStore.loadAll(context)
            }.onFailure { error = it.message ?: "Не удалось подключиться к SMB-серверу" }
            loading = false
        }
    }

    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        val pending = pendingServer
        pendingServer = null
        if (granted && pending != null) loadDirectory(pending, "")
        else if (pending != null) error = "Разреши доступ к локальной сети в настройках Android."
    }

    fun requestConnection(server: SmbServerConfig) {
        if (Build.VERSION.SDK_INT >= 37 && requiresLocalNetworkPermission(server.host.substringBefore(':')) &&
            ContextCompat.checkSelfPermission(context, "android.permission.ACCESS_LOCAL_NETWORK") != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            pendingServer = server
            permissionLauncher.launch("android.permission.ACCESS_LOCAL_NETWORK")
        } else loadDirectory(server, "")
    }

    fun connect() {
        val normalizedHost = normalizeSmbHost(host)
        val normalizedShare = normalizeSmbShare(share)
        if (normalizedHost == null || normalizedShare == null) {
            error = "Укажи адрес сервера и имя общей папки (share)."
            return
        }
        requestConnection(SmbServerConfig(normalizedHost, normalizedShare, username.trim(), domain.trim(), password))
    }

    Column(modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Сетевые папки SMB", style = MaterialTheme.typography.titleMedium)
        Text("Поддерживается SMB 2/3. Пароль сохраняется только в зашифрованном виде через Android Keystore.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        if (savedServers.isNotEmpty()) {
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                savedServers.forEach { saved ->
                    TextButton(onClick = {
                        host = saved.host; share = saved.share; domain = saved.domain
                        username = saved.username; password = saved.password
                        requestConnection(saved)
                    }) { Text("\u0024{saved.host}/\u0024{saved.share}") }
                }
            }
        }
        OutlinedTextField(host, { host = it }, Modifier.fillMaxWidth(), singleLine = true, label = { Text("Сервер / IP") }, placeholder = { Text("192.168.1.10 или nas.local") })
        OutlinedTextField(share, { share = it }, Modifier.fillMaxWidth(), singleLine = true, label = { Text("Общая папка (share)") })
        OutlinedTextField(domain, { domain = it }, Modifier.fillMaxWidth(), singleLine = true, label = { Text("Домен (необязательно)") })
        OutlinedTextField(username, { username = it }, Modifier.fillMaxWidth(), singleLine = true, label = { Text("Пользователь") })
        OutlinedTextField(password, { password = it }, Modifier.fillMaxWidth(), singleLine = true, label = { Text("Пароль") }, visualTransformation = PasswordVisualTransformation())
        Button(onClick = { connect() }, enabled = !loading, modifier = Modifier.fillMaxWidth()) { Text("Подключиться") }
        activeServer?.let { server ->
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("\u0024{server.host}/\u0024{server.share}/\u0024{currentPath}", style = MaterialTheme.typography.bodySmall, maxLines = 1)
                if (currentPath.isNotBlank()) TextButton(onClick = {
                    val parent = currentPath.substringBeforeLast('/', "")
                    loadDirectory(server, parent)
                }) { Text("Назад") }
            }
        }
        error?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
        if (loading) CircularProgressIndicator()
        LazyColumn(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            items(entries, key = { it.uri }) { entry ->
                Surface(color = MaterialTheme.colorScheme.surface, shape = MaterialTheme.shapes.medium,
                    modifier = Modifier.fillMaxWidth().clickable {
                        val server = activeServer ?: return@clickable
                        if (entry.isDirectory) loadDirectory(server, entry.relativePath) else {
                            val metadata = MediaMetadata.Builder().setTitle(entry.name).build()
                            val item = MediaItem.Builder().setUri(entry.uri.toUri()).setMimeType(entry.mimeType).setMediaMetadata(metadata).build()
                            player.setMediaItem(item)
                            player.prepare()
                            player.play()
                        }
                    }) {
                    Column(Modifier.padding(horizontal = 12.dp, vertical = 10.dp)) {
                        Text(if (entry.isDirectory) "📁 \u0024{entry.name}" else entry.name, color = MaterialTheme.colorScheme.onSurface, maxLines = 1)
                        if (!entry.isDirectory) Text("\u0024{entry.mimeType ?: "Файл"} • \u0024{entry.sizeBytes / 1024} КБ", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }
    }
}
''', encoding="utf-8")

p = PKG / "MainActivity.kt"
s = p.read_text(encoding="utf-8")
s = s.replace('''                        "История" -> PlaybackHistoryScreen(player, Modifier.weight(1f))
                        else -> {''', '''                        "История" -> PlaybackHistoryScreen(player, Modifier.weight(1f))
                        "SMB" -> SmbLibraryScreen(player, Modifier.weight(1f))
                        else -> {''', 1)
s = s.replace('''                                ActionCard("История и подборки", "Недавно воспроизведённое, частые прослушивания и избранное", Icons.Default.History) { morePage = "История" }
                                ActionCard("Открыть аудиофайл",''', '''                                ActionCard("История и подборки", "Недавно воспроизведённое, частые прослушивания и избранное", Icons.Default.History) { morePage = "История" }
                                ActionCard("Сетевые папки SMB", "Подключение к NAS и общим папкам компьютера", Icons.Default.FolderShared) { morePage = "SMB" }
                                ActionCard("Открыть аудиофайл",''', 1)
p.write_text(s, encoding="utf-8")

(TEST / "SmbAddressTest.kt").write_text('''package com.chiyuri.player

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class SmbAddressTest {
    @Test fun normalizesServerAndShare() {
        assertEquals("nas.local", normalizeSmbHost(" NAS.LOCAL "))
        assertEquals("Music", normalizeSmbShare("/Music/"))
    }

    @Test fun rejectsMalformedHostsSharesAndTraversal() {
        assertNull(normalizeSmbHost("https://nas.local"))
        assertNull(normalizeSmbHost("nas.local/share"))
        assertNull(normalizeSmbShare("../share"))
        assertNull(buildSmbUri("nas.local", "Music", "../private"))
    }

    @Test fun buildsEncodedSmbUris() {
        assertEquals("smb://nas.local/Music/Live%20Shows", buildSmbUri("nas.local", "Music", "Live Shows"))
    }
}
''', encoding="utf-8")

print("patch_0444: SMB2/3 browsing, Android-Keystore credential encryption and direct streaming DataSource applied")
