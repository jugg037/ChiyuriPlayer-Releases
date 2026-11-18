from pathlib import Path
BASE=Path("app/src/main/java/com/chiyuri/player")
def r(p): return p.read_text(encoding="utf-8")
def w(p,s): p.write_text(s,encoding="utf-8")
def once(s,a,b,label):
    if s.count(a)!=1: raise SystemExit(f"{label}: anchor count={s.count(a)}")
    return s.replace(a,b,1)
def imp(s,x):
    if x not in s: s=s.replace("package com.chiyuri.player\n","package com.chiyuri.player\n\n"+x+"\n",1)
    return s

p=BASE/"MainActivity.kt"; m=r(p)
for x in [
 "import androidx.compose.runtime.saveable.rememberSaveable",
 "import androidx.activity.compose.rememberLauncherForActivityResult",
 "import androidx.activity.result.IntentSenderRequest",
 "import androidx.activity.result.contract.ActivityResultContracts",
 "import android.app.Activity","import android.app.RecoverableSecurityException",
 "import android.os.Build","import android.provider.MediaStore",
 "import androidx.compose.foundation.layout.aspectRatio",
 "import androidx.compose.foundation.layout.heightIn",
 "import androidx.compose.material3.OutlinedTextField"
]: m=imp(m,x)
m=once(m,"var expandedMiniPlayer by remember { mutableStateOf(false) }",
       "var expandedMiniPlayer by rememberSaveable { mutableStateOf(false) }","save mini-player state")
if m.count("expandedMiniPlayer = false")!=2: raise SystemExit("Expected two auto-collapse assignments")
m=m.replace("expandedMiniPlayer = false","",2)
m=once(m,"modifier = Modifier.fillMaxWidth().height(230.dp)",
       "modifier = Modifier.fillMaxWidth().heightIn(max = 480.dp).aspectRatio(16f / 9f)","responsive video")
anchor="""    val context = LocalContext.current
    var queueVersion by remember { mutableIntStateOf(0) }"""
logic=r'''    val context = LocalContext.current
    var pendingDeleteUri by remember { mutableStateOf<Uri?>(null) }
    var retryDeleteAfterConsent by remember { mutableStateOf(false) }
    val deleteMediaLauncher = rememberLauncherForActivityResult(ActivityResultContracts.StartIntentSenderForResult()) { result ->
        val uri = pendingDeleteUri
        pendingDeleteUri = null
        if (result.resultCode == Activity.RESULT_OK && uri != null) {
            val deleted = if (retryDeleteAfterConsent) runCatching { context.contentResolver.delete(uri, null, null) > 0 }.getOrDefault(false) else true
            retryDeleteAfterConsent = false
            if (deleted) {
                val index = player.currentMediaItemIndex
                if (index >= 0) player.removeMediaItem(index)
                android.widget.Toast.makeText(context, "Файл удалён с устройства", android.widget.Toast.LENGTH_SHORT).show()
            } else android.widget.Toast.makeText(context, "Android не подтвердил удаление файла", android.widget.Toast.LENGTH_LONG).show()
        } else retryDeleteAfterConsent = false
    }
    fun requestDeleteCurrentTrack() {
        val uri = player.currentMediaItem?.localConfiguration?.uri
        if (uri == null || uri.scheme != "content") {
            android.widget.Toast.makeText(context, "Этот источник нельзя удалить как локальный файл", android.widget.Toast.LENGTH_LONG).show()
            return
        }
        pendingDeleteUri = uri
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            retryDeleteAfterConsent = false
            val request = MediaStore.createDeleteRequest(context.contentResolver, listOf(uri))
            deleteMediaLauncher.launch(IntentSenderRequest.Builder(request.intentSender).build())
        } else {
            try {
                val deleted = context.contentResolver.delete(uri, null, null) > 0
                pendingDeleteUri = null
                if (deleted) {
                    val index = player.currentMediaItemIndex
                    if (index >= 0) player.removeMediaItem(index)
                    android.widget.Toast.makeText(context, "Файл удалён с устройства", android.widget.Toast.LENGTH_SHORT).show()
                } else android.widget.Toast.makeText(context, "Файл не найден или уже удалён", android.widget.Toast.LENGTH_LONG).show()
            } catch (security: RecoverableSecurityException) {
                retryDeleteAfterConsent = true
                deleteMediaLauncher.launch(IntentSenderRequest.Builder(security.userAction.actionIntent.intentSender).build())
            } catch (security: SecurityException) {
                pendingDeleteUri = null
                android.widget.Toast.makeText(context, "Нет разрешения на удаление: " + (security.localizedMessage ?: ""), android.widget.Toast.LENGTH_LONG).show()
            }
        }
    }
    var queueVersion by remember { mutableIntStateOf(0) }'''
m=once(m,anchor,logic,"delete permission flow")
m=once(m,"                    onEditMetadata = { showMetadataEditor = true },",
       "                    onEditMetadata = { showMetadataEditor = true },\n                    onDeleteTrack = { requestDeleteCurrentTrack() },","delete callback")
a=m.index("private fun MiniPlayerBar("); b=m.index("\n@Composable",a+20); mini=m[a:b]
mini=once(mini,"    onEditMetadata: () -> Unit,","    onEditMetadata: () -> Unit,\n    onDeleteTrack: () -> Unit,","delete parameter")
mini=once(mini,") {\n    Surface(",") {\n    var showDeleteConfirmation by remember { mutableStateOf(false) }\n    Surface(","delete confirmation state")
ui=r'''            if (expanded) {
                TextButton(onClick = { showDeleteConfirmation = true }, modifier = Modifier.align(Alignment.End)) {
                    GothicIcon(Icons.Default.Delete, contentDescription = null)
                    Spacer(Modifier.width(6.dp))
                    Text("Удалить файл")
                }
                if (showDeleteConfirmation) {
                    AlertDialog(
                        onDismissRequest = { showDeleteConfirmation = false },
                        title = { Text("Удалить файл с устройства?") },
                        text = { Text("Файл будет удалён после системного подтверждения Android. Это не просто удаление из очереди или плейлиста.") },
                        confirmButton = { TextButton(onClick = { showDeleteConfirmation = false; onDeleteTrack() }) { Text("Продолжить") } },
                        dismissButton = { TextButton(onClick = { showDeleteConfirmation = false }) { Text("Отмена") } }
                    )
                }
            }
'''
mini=once(mini,"            if (expanded) VolumeIndicator()",ui+"            if (expanded) VolumeIndicator()","delete button and confirmation")
m=m[:a]+mini+m[b:]; w(p,m)

# Persist custom user EQ presets in app-private preferences.
store=BASE/"CustomEqualizerPresets.kt"
w(store,r'''package com.chiyuri.player

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

internal data class CustomEqualizerPreset(val name: String, val bandsDb: List<Float>)
internal object CustomEqualizerPresetStore {
    private const val PREFS="chiyuri_custom_equalizer_presets"
    private const val KEY="presets"
    fun normalizeName(value:String)=value.trim().replace(Regex("\\s+")," ").take(32)
    fun isInvalidName(value:String)=normalizeName(value).isBlank()
    fun load(context:Context):List<CustomEqualizerPreset> {
        val raw=context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).getString(KEY,"[]") ?: "[]"
        return runCatching {
            val array=JSONArray(raw)
            buildList {
                for (i in 0 until array.length()) {
                    val item=array.optJSONObject(i) ?: continue
                    val name=normalizeName(item.optString("name"))
                    val bands=item.optJSONArray("bands") ?: continue
                    if(name.isBlank() || bands.length()!=5) continue
                    add(CustomEqualizerPreset(name,(0 until 5).map { bands.optDouble(it,0.0).toFloat().coerceIn(-12f,12f) }))
                }
            }
        }.getOrDefault(emptyList())
    }
    fun save(context:Context,nameValue:String,bandsDb:List<Float>):List<CustomEqualizerPreset> {
        val name=normalizeName(nameValue)
        require(name.isNotBlank()) { "Укажи название пресета" }
        require(bandsDb.size==5) { "Нужно пять полос эквалайзера" }
        val values=bandsDb.map { if(it.isFinite()) it.coerceIn(-12f,12f) else 0f }
        val updated=load(context).filterNot { it.name.equals(name,true) }.plus(CustomEqualizerPreset(name,values)).takeLast(30)
        persist(context,updated); return updated
    }
    fun delete(context:Context,name:String):List<CustomEqualizerPreset> {
        val updated=load(context).filterNot { it.name==name }; persist(context,updated); return updated
    }
    private fun persist(context:Context,presets:List<CustomEqualizerPreset>) {
        val array=JSONArray()
        presets.forEach { array.put(JSONObject().put("name",it.name).put("bands",JSONArray(it.bandsDb))) }
        context.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().putString(KEY,array.toString()).apply()
    }
}
''')
test=Path("app/src/test/java/com/chiyuri/player/CustomEqualizerPresetNameTest.kt")
test.parent.mkdir(parents=True,exist_ok=True)
w(test,r'''package com.chiyuri.player
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
class CustomEqualizerPresetNameTest {
    @Test fun normalizesNames() { assertEquals("My dark sound",CustomEqualizerPresetStore.normalizeName("  My   dark sound  ")) }
    @Test fun rejectsBlankNames() { assertTrue(CustomEqualizerPresetStore.isInvalidName("   ")) }
}
''')

m=r(p); eqstart=m.index("private fun AudioEffectsScreen("); eqend=m.find("\n@Composable",eqstart+20)
if eqend<0: eqend=len(m)
eq=m[eqstart:eqend]
eq=once(eq,'    val bandLabels = listOf("Низкие", "Ниже средних", "Средние", "Выше средних", "Высокие")',
'''    val bandLabels = listOf("Низкие", "Ниже средних", "Средние", "Выше средних", "Высокие")
    var customPresets by remember(context) { mutableStateOf(CustomEqualizerPresetStore.load(context)) }
    var showSavePresetDialog by remember { mutableStateOf(false) }
    var customPresetName by remember { mutableStateOf("") }''',"custom preset state")
old='''                    EqualizerPresets.all.forEach { preset ->
                        FilterChip(
                            selected = EqualizerPresets.selectedPreset(config) == preset.id,
                            onClick = { updateConfig(EqualizerPresets.apply(config, preset)) },
                            label = { Text(preset.title) }
                        )
                    }'''
new='''                    EqualizerPresets.all.forEach { preset ->
                        FilterChip(
                            selected = EqualizerPresets.selectedPreset(config) == preset.id,
                            onClick = { updateConfig(EqualizerPresets.apply(config, preset)) },
                            label = { Text(preset.title) }
                        )
                    }
                    customPresets.forEach { preset ->
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            FilterChip(selected = config.bandsDb == preset.bandsDb,
                                onClick = { updateConfig(config.copy(bandsDb = preset.bandsDb)) },
                                label = { Text(preset.name) })
                            IconButton(onClick = { customPresets = CustomEqualizerPresetStore.delete(context, preset.name) }) {
                                GothicIcon(Icons.Default.Delete, contentDescription = "Удалить пресет " + preset.name)
                            }
                        }
                    }
                    FilterChip(selected = false, onClick = { customPresetName = ""; showSavePresetDialog = true },
                        label = { Text("Свой +") })'''
eq=once(eq,old,new,"custom preset controls")
dialog=r'''
    if (showSavePresetDialog) {
        AlertDialog(
            onDismissRequest = { showSavePresetDialog = false },
            title = { Text("Сохранить свой пресет") },
            text = {
                OutlinedTextField(value = customPresetName, onValueChange = { customPresetName = it.take(32) },
                    label = { Text("Название пресета") }, singleLine = true)
            },
            confirmButton = {
                TextButton(enabled = !CustomEqualizerPresetStore.isInvalidName(customPresetName), onClick = {
                    customPresets = CustomEqualizerPresetStore.save(context, customPresetName, config.bandsDb)
                    showSavePresetDialog = false
                }) { Text("Сохранить") }
            },
            dismissButton = { TextButton(onClick = { showSavePresetDialog = false }) { Text("Отмена") } }
        )
    }
'''
eq=eq[:eq.rfind("}")]+dialog+eq[eq.rfind("}"):]
m=m[:eqstart]+eq+m[eqend:]; w(p,m)

# Explicit user-controlled rotation and tablet/landscape video sizing.
manifest=Path("app/src/main/AndroidManifest.xml"); s=r(manifest)
if 'android:screenOrientation="fullUser"' not in s:
    s=once(s,'            android:name=".MainActivity"\n            android:exported="true"',
           '            android:name=".MainActivity"\n            android:exported="true"\n            android:screenOrientation="fullUser"',"rotation policy")
w(manifest,s)

m=r(p)
for marker in ["rememberSaveable { mutableStateOf(false) }","onDeleteTrack = { requestDeleteCurrentTrack() }",
               "MediaStore.createDeleteRequest","CustomEqualizerPresetStore.save(context, customPresetName, config.bandsDb)",
               "heightIn(max = 480.dp).aspectRatio(16f / 9f)"]:
    if marker not in m: raise SystemExit("Missing final feature marker: "+marker)
if "expandedMiniPlayer = false" in m: raise SystemExit("Track transition still resets expanded state")
if 'android:screenOrientation="fullUser"' not in r(manifest): raise SystemExit("fullUser orientation missing")
print("PATCH_0428_OK: expanded mini-player persists; Android system-confirmed file deletion; custom EQ presets save/apply/delete; landscape/tablet video layout.")
