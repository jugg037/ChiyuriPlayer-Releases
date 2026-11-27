from pathlib import Path

ROOT = Path.cwd()
PKG = ROOT / "app/src/main/java/com/chiyuri/player"
TEST = ROOT / "app/src/test/java/com/chiyuri/player"

# Ten-band logical EQ model, with backward-compatible five-band migration.
p = PKG / "AudioEffectsSettings.kt"
s = p.read_text(encoding="utf-8")
s = s.replace('val bandsDb: List<Float> = List(5) { 0f }', 'val bandsDb: List<Float> = List(10) { 0f }', 1)
s = s.replace('bandsDb = List(5) { index ->\n            bounded(config.bandsDb.getOrElse(index) { 0f }, -12f, 12f, 0f)\n        },', 'bandsDb = List(10) { index ->\n            bounded(config.bandsDb.getOrElse(index) { 0f }, -12f, 12f, 0f)\n        },', 1)
s = s.replace('playerVolume = bounded(config.playerVolume, 1f, 3f, 1f)', 'playerVolume = bounded(config.playerVolume, 1f, 2f, 1f)', 1)
old = '''        val bands = (0 until 5).map { index ->
            preferences.getFloat(KEY_BAND_PREFIX + index, 0f)
        }
        return normalizeAudioEffectsConfig(
            AudioEffectsConfig(
                equalizerEnabled = preferences.getBoolean(KEY_EQUALIZER_ENABLED, false),
                bandsDb = bands,
                playerVolume = preferences.getFloat(KEY_PLAYER_VOLUME, 1f)
            )
        )'''
new = '''        val hasTenBandValues = (5 until 10).any { preferences.contains(KEY_BAND_PREFIX + it) }
        val storedCount = if (hasTenBandValues) 10 else 5
        val storedBands = (0 until storedCount).map { index ->
            preferences.getFloat(KEY_BAND_PREFIX + index, 0f)
        }
        val bands = resampleEqualizerBands(storedBands, 10)
        if (!hasTenBandValues) {
            preferences.edit {
                bands.forEachIndexed { index, value -> putFloat(KEY_BAND_PREFIX + index, value) }
            }
        }
        return normalizeAudioEffectsConfig(
            AudioEffectsConfig(
                equalizerEnabled = preferences.getBoolean(KEY_EQUALIZER_ENABLED, false),
                bandsDb = bands,
                playerVolume = preferences.getFloat(KEY_PLAYER_VOLUME, 1f)
            )
        )'''
if old not in s:
    raise SystemExit("patch_0435: AudioEffectsSettings.load anchor missing")
s = s.replace(old, new, 1)
s = s.replace('playerVolume.coerceIn(1f, 3f)', 'playerVolume.coerceIn(1f, 2f)', 1)
s = s.replace('coerceIn(0, 954)', 'coerceIn(0, 602)', 1)
s += '''

/** Resamples old and new EQ profiles without losing their overall tonal curve. */
internal fun resampleEqualizerBands(values: List<Float>, targetCount: Int): List<Float> {
    if (targetCount <= 0) return emptyList()
    if (values.isEmpty()) return List(targetCount) { 0f }
    if (values.size == 1) return List(targetCount) { (values.first().takeIf { it.isFinite() } ?: 0f).coerceIn(-12f, 12f) }
    if (values.size == targetCount) return values.map { if (it.isFinite()) it.coerceIn(-12f, 12f) else 0f }
    return List(targetCount) { targetIndex ->
        val position = if (targetCount == 1) 0f else targetIndex.toFloat() * values.lastIndex / (targetCount - 1)
        val lower = kotlin.math.floor(position).toInt().coerceIn(0, values.lastIndex)
        val upper = (lower + 1).coerceAtMost(values.lastIndex)
        val fraction = position - lower
        val a = values[lower].takeIf { it.isFinite() } ?: 0f
        val b = values[upper].takeIf { it.isFinite() } ?: 0f
        (a + (b - a) * fraction).coerceIn(-12f, 12f)
    }
}

/** Interpolates EQ gain over logarithmic frequency, matching human pitch perception. */
internal fun interpolateEqualizerGain(frequencyHz: Float, gainsDb: List<Float>): Float {
    val centers = floatArrayOf(31f, 62f, 125f, 250f, 500f, 1000f, 2000f, 4000f, 8000f, 16000f)
    if (gainsDb.isEmpty()) return 0f
    val frequency = frequencyHz.takeIf { it.isFinite() && it > 0f } ?: centers.first()
    if (frequency <= centers.first()) return (gainsDb.first().takeIf { it.isFinite() } ?: 0f).coerceIn(-12f, 12f)
    if (frequency >= centers.last()) return (gainsDb.getOrElse(centers.lastIndex) { 0f }.takeIf { it.isFinite() } ?: 0f).coerceIn(-12f, 12f)
    val upper = centers.indexOfFirst { it >= frequency }.coerceAtLeast(1)
    val lower = upper - 1
    val fraction = (kotlin.math.ln(frequency) - kotlin.math.ln(centers[lower])) /
        (kotlin.math.ln(centers[upper]) - kotlin.math.ln(centers[lower]))
    val a = gainsDb.getOrElse(lower) { 0f }.takeIf { it.isFinite() } ?: 0f
    val b = gainsDb.getOrElse(upper) { 0f }.takeIf { it.isFinite() } ?: 0f
    return (a + (b - a) * fraction).coerceIn(-12f, 12f)
}
'''
p.write_text(s, encoding="utf-8")

# Ten-band presets.
p = PKG / "EqualizerPresets.kt"
p.write_text('''package com.chiyuri.player

data class EqualizerPreset(
    val id: String,
    val title: String,
    val bandsDb: List<Float>
) {
    init { require(bandsDb.size == 10) }
}

object EqualizerPresets {
    val all = listOf(
        EqualizerPreset("flat", "Ровный", listOf(0f,0f,0f,0f,0f,0f,0f,0f,0f,0f)),
        EqualizerPreset("bass", "Басы", listOf(6f,5f,4f,2f,0f,-1f,-2f,-2f,-1f,0f)),
        EqualizerPreset("pop", "Поп", listOf(-1f,0f,2f,4f,5f,3f,0f,-1f,-1f,0f)),
        EqualizerPreset("rock", "Рок", listOf(5f,4f,2f,0f,-2f,1f,3f,4f,5f,5f)),
        EqualizerPreset("classical", "Классика", listOf(4f,3f,2f,1f,-1f,1f,2f,3f,4f,5f)),
        EqualizerPreset("jazz", "Джаз", listOf(4f,3f,1f,0f,-2f,0f,1f,2f,3f,4f)),
        EqualizerPreset("vocal", "Вокал", listOf(-3f,-2f,0f,3f,5f,4f,2f,1f,0f,0f))
    )

    fun apply(config: AudioEffectsConfig, preset: EqualizerPreset): AudioEffectsConfig =
        normalizeAudioEffectsConfig(config.copy(equalizerEnabled = true, bandsDb = preset.bandsDb))

    fun selectedPreset(config: AudioEffectsConfig): String? =
        all.firstOrNull { preset -> preset.bandsDb.indices.all { index ->
            kotlin.math.abs(config.bandsDb.getOrElse(index) { 0f } - preset.bandsDb[index]) < 0.05f
        } }?.id
}
''', encoding="utf-8")

# Preserve saved custom presets when upgrading from five to ten bands.
p = PKG / "CustomEqualizerPresets.kt"
s = p.read_text(encoding="utf-8")
old = 'if(name.isBlank() || bands.length()!=5) continue\n                    add(CustomEqualizerPreset(name,(0 until 5).map { bands.optDouble(it,0.0).toFloat().coerceIn(-12f,12f) }))'
new = 'if(name.isBlank() || bands.length() !in 5..10) continue\n                    val stored = (0 until bands.length()).map { bands.optDouble(it,0.0).toFloat() }\n                    add(CustomEqualizerPreset(name, resampleEqualizerBands(stored, 10)))'
if old not in s:
    raise SystemExit("patch_0435: custom preset migration anchor missing")
s = s.replace(old, new, 1)
s = s.replace('require(bandsDb.size==5) { "Нужно пять полос эквалайзера" }', 'require(bandsDb.size==10) { "Нужно десять полос эквалайзера" }', 1)
p.write_text(s, encoding="utf-8")

# Map the ten virtual bands onto each device's real hardware EQ bands.
p = PKG / "AudioEffectsController.kt"
s = p.read_text(encoding="utf-8")
old = '''                        val centerHz = effect.getCenterFreq(band.toShort())
                            .toFloat()
                            .div(1000f)
                            .coerceAtLeast(1f)
                        val controlIndex = CONTROL_CENTERS_HZ.indices.minByOrNull { index ->
                            abs(ln(centerHz / CONTROL_CENTERS_HZ[index]))
                        } ?: 2
                        val level = (config.bandsDb[controlIndex] * 100f)
                            .roundToInt()
                            .coerceIn(range[0].toInt(), range[1].toInt())
                            .toShort()'''
new = '''                        val centerHz = effect.getCenterFreq(band.toShort())
                            .toFloat()
                            .div(1000f)
                            .coerceAtLeast(1f)
                        val level = (interpolateEqualizerGain(centerHz, config.bandsDb) * 100f)
                            .roundToInt()
                            .coerceIn(range[0].toInt(), range[1].toInt())
                            .toShort()'''
if old not in s:
    raise SystemExit("patch_0435: hardware EQ interpolation anchor missing")
s = s.replace(old, new, 1)
s = s.replace('import kotlin.math.abs\n', '').replace('import kotlin.math.ln\n', '')
s = s.replace('        val CONTROL_CENTERS_HZ = floatArrayOf(60f, 230f, 910f, 3600f, 14000f)\n', '')
p.write_text(s, encoding="utf-8")

# Correct total volume limit to 200% (1x Android volume + 1x player boost).
p = PKG / "MainActivity.kt"
s = p.read_text(encoding="utf-8")
replacements = [
    ('val bandLabels = listOf("Низкие", "Ниже средних", "Средние", "Выше средних", "Высокие")',
     'val bandLabels = listOf("31 Гц", "62 Гц", "125 Гц", "250 Гц", "500 Гц", "1 кГц", "2 кГц", "4 кГц", "8 кГц", "16 кГц")'),
    ('Text("Пять полос настройки частот"', 'Text("Десять полос настройки частот"'),
    ('(config.playerVolume + 0.1f).coerceAtMost(3f)', '(config.playerVolume + 0.05f).coerceAtMost(2f)'),
    ('(config.playerVolume - 0.1f).coerceAtLeast(1f)', '(config.playerVolume - 0.05f).coerceAtLeast(1f)'),
    ('(config.playerVolume - 1f).coerceIn(0f, 2f)', '(config.playerVolume - 1f).coerceIn(0f, 1f)'),
    ('valueRange = 0f..2f,\n                    steps = 39', 'valueRange = 0f..1f,\n                    steps = 19'),
    ('дополнительное усиление плеера — до +200% (до 300% общей громкости, 3x).',
     'дополнительное усиление плеера — до +100% (до 200% общей громкости, 2x).')
]
for old, new in replacements:
    if old not in s:
        raise SystemExit("patch_0435: MainActivity anchor missing: " + old[:70])
    s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

# Version and regression tests.
p = ROOT / "app/build.gradle.kts"
s = p.read_text(encoding="utf-8")
if 'versionName = "0.5.6"' not in s or 'orElse("342")' not in s:
    raise SystemExit("patch_0435: app version 0.5.6 (342) anchor missing")
s = s.replace('versionName = "0.5.6"', 'versionName = "0.5.8"', 1)
s = s.replace('orElse("342")', 'orElse("344")', 1)
p.write_text(s, encoding="utf-8")

p = TEST / "EqualizerPresetsTest.kt"
s = p.read_text(encoding="utf-8").replace('List(5) { 0f }', 'List(10) { 0f }')
s = s.replace('applyingPresetEnablesEqualizerAndSetsFiveBands', 'applyingPresetEnablesEqualizerAndSetsTenBands')
s = s.replace('assertEquals(5, preset.bandsDb.size)', 'assertEquals(10, preset.bandsDb.size)')
p.write_text(s, encoding="utf-8")

p = TEST / "CustomEqualizerPresetNameTest.kt"
s = p.read_text(encoding="utf-8").replace('List(5) { 0f }', 'List(10) { 0f }')
p.write_text(s, encoding="utf-8")


# Keep the original gain regression test aligned with the strict 200% ceiling.
p = TEST / "PlaceholderTest.kt"
s = p.read_text(encoding="utf-8")
old = "assertEquals(954, volumeBoostToMillibels(3f))"
new = "assertEquals(602, volumeBoostToMillibels(2f))"
if old not in s:
    raise SystemExit("patch_0435: legacy volume boost test anchor missing")
p.write_text(s.replace(old, new, 1), encoding="utf-8")

p = TEST / "AudioEffectsSettingsTest.kt"
p.write_text('''package com.chiyuri.player

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AudioEffectsSettingsTest {
    @Test fun legacyFiveBandProfilesExpandToTenBands() {
        val expanded = resampleEqualizerBands(listOf(-10f, -5f, 0f, 5f, 10f), 10)
        assertEquals(10, expanded.size)
        assertEquals(-10f, expanded.first(), 0.001f)
        assertEquals(10f, expanded.last(), 0.001f)
        assertTrue(expanded.zipWithNext().all { (a, b) -> b >= a })
    }

    @Test fun resamplingHandlesEmptySingleAndInvalidValues() {
        assertEquals(List(10) { 0f }, resampleEqualizerBands(emptyList(), 10))
        assertEquals(List(4) { 3f }, resampleEqualizerBands(listOf(3f), 4))
        assertEquals(0f, resampleEqualizerBands(listOf(Float.NaN), 1).single(), 0.001f)
    }

    @Test fun hardwareBandGainIsInterpolatedOnLogFrequency() {
        val flat = List(10) { 0f }
        assertEquals(0f, interpolateEqualizerGain(1000f, flat), 0.001f)
        val ramp = (0 until 10).map { it.toFloat() }
        assertEquals(4f, interpolateEqualizerGain(500f, ramp), 0.001f)
    }

    @Test fun playerBoostIsCappedAtTwoTimesTotalOutput() {
        val normalized = normalizeAudioEffectsConfig(AudioEffectsConfig(playerVolume = 3f))
        assertEquals(2f, normalized.playerVolume, 0.001f)
        assertEquals(602, volumeBoostToMillibels(2f))
        assertEquals(0, volumeBoostToMillibels(1f))
    }
}
''', encoding="utf-8")

print("patch_0435: ten-band EQ, legacy migration, 200% total volume cap, and unit tests applied")
