from pathlib import Path
ROOT = Path.cwd()
PKG = ROOT / "app/src/main/java/com/chiyuri/player"
TEST = ROOT / "app/src/test/java/com/chiyuri/player"

(PKG / "AudioOutputProfiles.kt").write_text('''package com.chiyuri.player

import android.content.Context
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.os.Build
import androidx.core.content.edit
import org.json.JSONArray
import org.json.JSONObject

/** Stable, non-secret profile key derived from the routed output's type and product label. */
internal fun audioOutputProfileKey(type: Int, productName: String): String {
    val safeName = productName.trim().lowercase().replace(Regex("[^a-z0-9а-я_-]+"), "_").trim('_').take(48)
    return "${type}_${safeName.ifBlank { "device" }}"
}

object AudioOutputProfiles {
    internal const val PREFERENCES_NAME = "audio_output_profiles"
    private const val PREFS = PREFERENCES_NAME
    private const val KEY_PROFILES = "profiles"

    fun activeDevice(context: Context): AudioDeviceInfo? {
        val manager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        return runCatching {
            val outputs = if (Build.VERSION.SDK_INT >= 31) {
                manager.getDevicesForAttributes(
                    android.media.AudioAttributes.Builder()
                        .setUsage(android.media.AudioAttributes.USAGE_MEDIA)
                        .build()
                ).filter { it.isSink }
            } else {
                manager.getDevices(AudioManager.GET_DEVICES_OUTPUTS).filter { it.isSink }
            }
            outputs.firstOrNull { it.type != AudioDeviceInfo.TYPE_BUILTIN_SPEAKER } ?: outputs.firstOrNull()
        }.getOrNull()
    }

    fun activeProfileKey(context: Context): String? = activeDevice(context)?.let { device ->
        audioOutputProfileKey(device.type, device.productName?.toString().orEmpty())
    }

    fun activeLabel(context: Context): String {
        val device = activeDevice(context) ?: return "Аудиовыход Android"
        val product = device.productName?.toString()?.trim().orEmpty()
        return when (device.type) {
            AudioDeviceInfo.TYPE_BUILTIN_SPEAKER -> "Динамик телефона"
            AudioDeviceInfo.TYPE_WIRED_HEADSET, AudioDeviceInfo.TYPE_WIRED_HEADPHONES -> product.ifBlank { "Проводные наушники" }
            AudioDeviceInfo.TYPE_BLUETOOTH_A2DP, AudioDeviceInfo.TYPE_BLUETOOTH_SCO, AudioDeviceInfo.TYPE_BLE_HEADSET -> product.ifBlank { "Bluetooth" }
            AudioDeviceInfo.TYPE_USB_HEADSET -> product.ifBlank { "USB-аудио" }
            else -> product.ifBlank { "Аудиоустройство ${device.type}" }
        }
    }

    internal fun load(context: Context, profileKey: String): AudioEffectsConfig? {
        val raw = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_PROFILES, "{}") ?: "{}"
        return runCatching {
            val profile = JSONObject(raw).optJSONObject(profileKey) ?: return null
            val bands = profile.optJSONArray("bands") ?: JSONArray()
            normalizeAudioEffectsConfig(AudioEffectsConfig(
                equalizerEnabled = profile.optBoolean("equalizer_enabled", false),
                bandsDb = (0 until bands.length()).map { bands.optDouble(it, 0.0).toFloat() },
                playerVolume = profile.optDouble("player_volume", 1.0).toFloat()
            ))
        }.getOrNull()
    }

    internal fun save(context: Context, profileKey: String, config: AudioEffectsConfig) {
        val preferences = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val profiles = runCatching { JSONObject(preferences.getString(KEY_PROFILES, "{}") ?: "{}") }
            .getOrDefault(JSONObject())
        val normalized = normalizeAudioEffectsConfig(config)
        profiles.put(profileKey, JSONObject()
            .put("equalizer_enabled", normalized.equalizerEnabled)
            .put("player_volume", normalized.playerVolume)
            .put("bands", JSONArray(normalized.bandsDb)))
        preferences.edit { putString(KEY_PROFILES, profiles.toString()) }
    }
}
''', encoding="utf-8")

p = PKG / "AudioEffectsSettings.kt"
s = p.read_text(encoding="utf-8")
old_load = '''    fun load(context: Context): AudioEffectsConfig {
        val preferences = context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)
        return load(preferences)
    }'''
new_load = '''    fun load(context: Context): AudioEffectsConfig {
        val preferences = context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)
        val global = load(preferences)
        val profileKey = AudioOutputProfiles.activeProfileKey(context)
        return profileKey?.let { AudioOutputProfiles.load(context, it) } ?: global
    }'''
if old_load not in s: raise SystemExit("patch_0441: AudioEffectsSettings.load anchor missing")
s = s.replace(old_load, new_load, 1)
old_save = '''        context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE).edit {
            putBoolean(KEY_EQUALIZER_ENABLED, normalized.equalizerEnabled)
            putFloat(KEY_PLAYER_VOLUME, normalized.playerVolume)
            normalized.bandsDb.forEachIndexed { index, value ->
                putFloat(KEY_BAND_PREFIX + index, value)
            }
        }'''
new_save = '''        val profileKey = AudioOutputProfiles.activeProfileKey(context)
        if (profileKey != null) {
            AudioOutputProfiles.save(context, profileKey, normalized)
        } else {
            context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE).edit {
                putBoolean(KEY_EQUALIZER_ENABLED, normalized.equalizerEnabled)
                putFloat(KEY_PLAYER_VOLUME, normalized.playerVolume)
                normalized.bandsDb.forEachIndexed { index, value ->
                    putFloat(KEY_BAND_PREFIX + index, value)
                }
            }
        }'''
if old_save not in s: raise SystemExit("patch_0441: AudioEffectsSettings.save anchor missing")
s = s.replace(old_save, new_save, 1)
p.write_text(s, encoding="utf-8")

p = PKG / "AudioEffectsController.kt"
s = p.read_text(encoding="utf-8")
for import_line in ["import android.media.AudioDeviceCallback", "import android.media.AudioManager", "import android.os.Handler", "import android.os.Looper"]:
    if import_line not in s:
        s = s.replace("import android.content.Context\n", "import android.content.Context\n" + import_line + "\n", 1)
s = s.replace('''    private val preferences = context.getSharedPreferences(
        AudioEffectsSettings.PREFERENCES_NAME,
        Context.MODE_PRIVATE
    )''', '''    private val appContext = context.applicationContext
    private val preferences = context.getSharedPreferences(
        AudioEffectsSettings.PREFERENCES_NAME,
        Context.MODE_PRIVATE
    )
    private val profilePreferences = context.getSharedPreferences(AudioOutputProfiles.PREFERENCES_NAME, Context.MODE_PRIVATE)
    private val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
    private val deviceCallback = object : AudioDeviceCallback() {
        override fun onAudioDevicesAdded(addedDevices: Array<out android.media.AudioDeviceInfo>) = applySettings()
        override fun onAudioDevicesRemoved(removedDevices: Array<out android.media.AudioDeviceInfo>) = applySettings()
    }''', 1)
s = s.replace('''        preferences.registerOnSharedPreferenceChangeListener(this)
        player.addListener(audioListener)''', '''        preferences.registerOnSharedPreferenceChangeListener(this)
        profilePreferences.registerOnSharedPreferenceChangeListener(this)
        audioManager.registerAudioDeviceCallback(deviceCallback, Handler(Looper.getMainLooper()))
        player.addListener(audioListener)''', 1)
s = s.replace('val config = AudioEffectsSettings.load(preferences)', 'val config = AudioEffectsSettings.load(appContext)', 1)
s = s.replace('''        preferences.unregisterOnSharedPreferenceChangeListener(this)
        player.removeListener(audioListener)''', '''        preferences.unregisterOnSharedPreferenceChangeListener(this)
        profilePreferences.unregisterOnSharedPreferenceChangeListener(this)
        audioManager.unregisterAudioDeviceCallback(deviceCallback)
        player.removeListener(audioListener)''', 1)
p.write_text(s, encoding="utf-8")

p = PKG / "MainActivity.kt"
s = p.read_text(encoding="utf-8")
anchor = '''    var config by remember(context) { mutableStateOf(AudioEffectsSettings.load(context)) }
    val bandLabels'''
replacement = '''    var config by remember(context) { mutableStateOf(AudioEffectsSettings.load(context)) }
    var outputProfileLabel by remember(context) { mutableStateOf(AudioOutputProfiles.activeLabel(context)) }
    val bandLabels'''
if anchor not in s: raise SystemExit("patch_0441: EQ config state anchor missing")
s = s.replace(anchor, replacement, 1)
anchor = '''        val preferences = context.getSharedPreferences(AudioEffectsSettings.PREFERENCES_NAME, Context.MODE_PRIVATE)
        val listener = android.content.SharedPreferences.OnSharedPreferenceChangeListener { _, _ ->
            config = AudioEffectsSettings.load(context)
        }
        preferences.registerOnSharedPreferenceChangeListener(listener)
        onDispose { preferences.unregisterOnSharedPreferenceChangeListener(listener) }'''
replacement = '''        val preferences = context.getSharedPreferences(AudioEffectsSettings.PREFERENCES_NAME, Context.MODE_PRIVATE)
        val profilePreferences = context.getSharedPreferences(AudioOutputProfiles.PREFERENCES_NAME, Context.MODE_PRIVATE)
        val listener = android.content.SharedPreferences.OnSharedPreferenceChangeListener { _, _ ->
            config = AudioEffectsSettings.load(context)
        }
        preferences.registerOnSharedPreferenceChangeListener(listener)
        profilePreferences.registerOnSharedPreferenceChangeListener(listener)
        onDispose {
            preferences.unregisterOnSharedPreferenceChangeListener(listener)
            profilePreferences.unregisterOnSharedPreferenceChangeListener(listener)
        }'''
if anchor not in s: raise SystemExit("patch_0441: EQ preferences listener anchor missing")
s = s.replace(anchor, replacement, 1)
anchor = '''    LaunchedEffect(audioManager) {
        while (true) {'''
replacement = '''    DisposableEffect(context) {
        val callback = object : android.media.AudioDeviceCallback() {
            override fun onAudioDevicesAdded(addedDevices: Array<out android.media.AudioDeviceInfo>) {
                config = AudioEffectsSettings.load(context)
                outputProfileLabel = AudioOutputProfiles.activeLabel(context)
            }
            override fun onAudioDevicesRemoved(removedDevices: Array<out android.media.AudioDeviceInfo>) {
                config = AudioEffectsSettings.load(context)
                outputProfileLabel = AudioOutputProfiles.activeLabel(context)
            }
        }
        audioManager.registerAudioDeviceCallback(callback, android.os.Handler(android.os.Looper.getMainLooper()))
        onDispose { audioManager.unregisterAudioDeviceCallback(callback) }
    }

    LaunchedEffect(audioManager) {
        while (true) {'''
if anchor not in s: raise SystemExit("patch_0441: EQ device callback anchor missing")
s = s.replace(anchor, replacement, 1)
anchor = '''                        Text("Десять полос настройки частот", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                    }'''
replacement = '''                        Text("Десять полос настройки частот", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                        Text("Профиль устройства: $outputProfileLabel", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                    }'''
if anchor not in s: raise SystemExit("patch_0441: output label anchor missing")
s = s.replace(anchor, replacement, 1)
p.write_text(s, encoding="utf-8")

(TEST / "AudioOutputProfileKeyTest.kt").write_text('''package com.chiyuri.player

import org.junit.Assert.assertEquals
import org.junit.Test

class AudioOutputProfileKeyTest {
    @Test fun profileKeyUsesDeviceTypeAndSanitizedProductName() {
        assertEquals("7_sony_wh-1000xm5", audioOutputProfileKey(7, "Sony WH-1000XM5"))
        assertEquals("3_device", audioOutputProfileKey(3, "   "))
    }
}
''', encoding="utf-8")

print("patch_0441: per-output audio profiles and automatic active-device application applied")
