from pathlib import Path

def replace_once(path: Path, old: str, new: str, label: str):
    source = path.read_text(encoding="utf-8")
    if old not in source:
        raise SystemExit(f"patch_0457: missing {label}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

PKG = Path("app/src/main/java/com/chiyuri/player")
TEST = Path("app/src/test/java/com/chiyuri/player")

p = PKG / "AudioEffectsSettings.kt"
s = p.read_text(encoding="utf-8")
s = s.replace(
    "    val replayGainEnabled: Boolean = true\n)",
    "    val replayGainEnabled: Boolean = true,\n    val spatialEnabled: Boolean = false\n)",
    1
)
s = s.replace('    private const val KEY_REPLAYGAIN_ENABLED = "replay_gain_enabled"',
              '    private const val KEY_REPLAYGAIN_ENABLED = "replay_gain_enabled"\n    private const val KEY_SPATIAL_ENABLED = "spatial_enabled"', 1)
s = s.replace(
    "                replayGainEnabled = preferences.getBoolean(KEY_REPLAYGAIN_ENABLED, true)\n",
    "                replayGainEnabled = preferences.getBoolean(KEY_REPLAYGAIN_ENABLED, true),\n                spatialEnabled = preferences.getBoolean(KEY_SPATIAL_ENABLED, false)\n",
    1
)
s = s.replace(
    "            putBoolean(KEY_REPLAYGAIN_ENABLED, normalized.replayGainEnabled)\n",
    "            putBoolean(KEY_REPLAYGAIN_ENABLED, normalized.replayGainEnabled)\n            putBoolean(KEY_SPATIAL_ENABLED, normalized.spatialEnabled)\n",
    1
)
# save(context, config) has a second occurrence of the same preference write.
s = s.replace(
    "                putBoolean(KEY_REPLAYGAIN_ENABLED, normalized.replayGainEnabled)\n",
    "                putBoolean(KEY_REPLAYGAIN_ENABLED, normalized.replayGainEnabled)\n                putBoolean(KEY_SPATIAL_ENABLED, normalized.spatialEnabled)\n",
    1
)
p.write_text(s, encoding="utf-8")

p = PKG / "AudioOutputProfiles.kt"
s = p.read_text(encoding="utf-8")
s = s.replace(
    "                replayGainEnabled = profile.optBoolean(\"replay_gain_enabled\", true)\n",
    "                replayGainEnabled = profile.optBoolean(\"replay_gain_enabled\", true),\n                spatialEnabled = profile.optBoolean(\"spatial_enabled\", false)\n",
    1
)
s = s.replace(
    '            .put("replay_gain_enabled", normalized.replayGainEnabled)\n',
    '            .put("replay_gain_enabled", normalized.replayGainEnabled)\n            .put("spatial_enabled", normalized.spatialEnabled)\n',
    1
)
p.write_text(s, encoding="utf-8")

p = PKG / "AudioEffectsController.kt"
s = p.read_text(encoding="utf-8")
s = s.replace("import android.media.audiofx.LoudnessEnhancer", "import android.media.audiofx.LoudnessEnhancer\nimport android.media.audiofx.Virtualizer", 1)
s = s.replace("    private var loudnessEnhancer: LoudnessEnhancer? = null", "    private var loudnessEnhancer: LoudnessEnhancer? = null\n    private var virtualizer: Virtualizer? = null", 1)
s = s.replace("        loudnessEnhancer = runCatching { LoudnessEnhancer(audioSessionId) }.getOrNull()", "        loudnessEnhancer = runCatching { LoudnessEnhancer(audioSessionId) }.getOrNull()\n        virtualizer = runCatching { Virtualizer(0, audioSessionId) }.getOrNull()", 1)
anchor = '''        equalizer?.let { effect ->
            runCatching {'''
if anchor not in s: raise SystemExit("patch_0457: equalizer application anchor missing")
s = s.replace(anchor, '''        virtualizer?.let { effect ->
            runCatching {
                if (effect.strengthSupported) effect.setStrength(500.toShort())
                effect.enabled = config.spatialEnabled
            }
        }

''' + anchor, 1)
s = s.replace("        runCatching { loudnessEnhancer?.release() }", "        runCatching { loudnessEnhancer?.release() }\n        runCatching { virtualizer?.release() }", 1)
s = s.replace("        loudnessEnhancer = null", "        loudnessEnhancer = null\n        virtualizer = null", 1)
s += '''

internal fun isSpatialAudioAvailable(): Boolean =
    runCatching { Virtualizer.isAvailable() }.getOrDefault(false)
'''
p.write_text(s, encoding="utf-8")

p = PKG / "LibraryBackupManager.kt"
s = p.read_text(encoding="utf-8")
s = s.replace(
    "                replayGainEnabled = configObject.optBoolean(\"replay_gain_enabled\", true)\n",
    "                replayGainEnabled = configObject.optBoolean(\"replay_gain_enabled\", true),\n                spatialEnabled = configObject.optBoolean(\"spatial_enabled\", false)\n",
    1
)
s = s.replace(
    '            .put("replay_gain_enabled", config.replayGainEnabled)\n',
    '            .put("replay_gain_enabled", config.replayGainEnabled)\n            .put("spatial_enabled", config.spatialEnabled)\n',
    1
)
s = s.replace(
    "                replayGainEnabled = item.optBoolean(\"replay_gain_enabled\", true)\n",
    "                replayGainEnabled = item.optBoolean(\"replay_gain_enabled\", true),\n                spatialEnabled = item.optBoolean(\"spatial_enabled\", false)\n",
    1
)
s = s.replace(
    '                .put("replay_gain_enabled", normalized.second.replayGainEnabled)\n',
    '                .put("replay_gain_enabled", normalized.second.replayGainEnabled)\n                .put("spatial_enabled", normalized.second.spatialEnabled)\n',
    1
)
p.write_text(s, encoding="utf-8")

# Expose the optional effect only when the device audio driver reports support.
p = PKG / "MainActivity.kt"
replace_once(
    p,
    '''                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text("ReplayGain", color = MaterialTheme.colorScheme.onSurface, style = MaterialTheme.typography.titleSmall)
                        Text("Выравнивание громкости по тегам MP3 и FLAC", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                    }
                    Switch(checked = config.replayGainEnabled, onCheckedChange = { updateConfig(config.copy(replayGainEnabled = it)) })
                }''',
    '''                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text("ReplayGain", color = MaterialTheme.colorScheme.onSurface, style = MaterialTheme.typography.titleSmall)
                        Text("Выравнивание громкости по тегам MP3 и FLAC", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                    }
                    Switch(checked = config.replayGainEnabled, onCheckedChange = { updateConfig(config.copy(replayGainEnabled = it)) })
                }
                val spatialAvailable = remember { isSpatialAudioAvailable() }
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text("Пространственное звучание", color = MaterialTheme.colorScheme.onSurface, style = MaterialTheme.typography.titleSmall)
                        Text(
                            if (spatialAvailable) "Виртуализатор Android для совместимых аудиовыходов"
                            else "Аудиодрайвер устройства не предоставляет виртуализатор",
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                    Switch(
                        checked = config.spatialEnabled && spatialAvailable,
                        enabled = spatialAvailable,
                        onCheckedChange = { updateConfig(config.copy(spatialEnabled = it)) }
                    )
                }''',
    "spatial audio settings row"
)

# Add a pure regression assertion for the optional effect flag.
p = TEST / "AudioEffectsSettingsTest.kt"
s = p.read_text(encoding="utf-8")
if "spatialEffectFlagSurvivesNormalization" not in s:
    anchor = "    @Test fun clampsVolumeBoostToTwoHundredPercent() {"
    test = '''    @Test fun spatialEffectFlagSurvivesNormalization() {
        assertTrue(normalizeAudioEffectsConfig(AudioEffectsConfig(spatialEnabled = true)).spatialEnabled)
        assertFalse(normalizeAudioEffectsConfig(AudioEffectsConfig(spatialEnabled = false)).spatialEnabled)
    }

'''
    if anchor not in s:
        raise SystemExit("patch_0457: audio settings test anchor missing")
    s = s.replace(anchor, test + anchor, 1)
    if "import org.junit.Assert.assertTrue" not in s:
        s = s.replace("import org.junit.Assert.assertFalse", "import org.junit.Assert.assertFalse\nimport org.junit.Assert.assertTrue", 1)
    p.write_text(s, encoding="utf-8")

print("patch_0457: optional Android Virtualizer spatial audio, per-device persistence and backup support added")
