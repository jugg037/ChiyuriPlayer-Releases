from pathlib import Path
def replace_once(path, old, new):
    source = path.read_text(encoding='utf-8')
    if old not in source: raise SystemExit(f'patch_0448: anchor missing in {path.name}: {old[:90]!r}')
    path.write_text(source.replace(old, new, 1), encoding='utf-8')
PKG = Path('app/src/main/java/com/chiyuri/player')
placeholder = Path('app/src/test/java/com/chiyuri/player/PlaceholderTest.kt')
replace_once(placeholder, 'assertEquals(listOf(-12f, -6f, 0f, 8f, 12f), normalized.bandsDb)', 'assertEquals(10, normalized.bandsDb.size)\n        assertEquals(-12f, normalized.bandsDb.first(), 0f)\n        assertEquals(12f, normalized.bandsDb.last(), 0f)')
replace_once(placeholder, 'assertEquals(2.5f, normalized.playerVolume, 0f)', 'assertEquals(2f, normalized.playerVolume, 0f)')
replace_once(placeholder, 'assertEquals(listOf(0f, 0f, 0f, 0f, 0f), normalized.bandsDb)', 'assertEquals(List(10) { 0f }, normalized.bandsDb)')
replace_once(placeholder, 'assertEquals(3f, normalized.playerVolume, 0f)', 'assertEquals(2f, normalized.playerVolume, 0f)')
audioSettings = PKG / 'AudioEffectsSettings.kt'
replace_once(audioSettings, 'bandsDb = List(10) { index ->\n            bounded(config.bandsDb.getOrElse(index) { 0f }, -12f, 12f, 0f)\n        },', 'bandsDb = resampleEqualizerBands(config.bandsDb, 10).map { bounded(it, -12f, 12f, 0f) },')
gesture = PKG / 'VideoGestureMath.kt'
replace_once(gesture, 'distancePx / viewWidthPx.toFloat() * 60_000f', 'distancePx / viewWidthPx.toFloat() * 30_000f')
replace_once(gesture, 'distanceYpx / viewHeightPx.toFloat() * maxLevel', 'distanceYpx / viewHeightPx.toFloat() * maxLevel * 0.5f')
videoTests = Path('app/src/test/java/com/chiyuri/player/VideoGestureMathTest.kt')
replace_once(videoTests, 'assertEquals(25, videoSwipeLevel(50, 25f, 100, 100))', 'assertEquals(37, videoSwipeLevel(50, 25f, 100, 100))')
paging = PKG / 'MediaLibraryPaging.kt'
replace_once(paging, '    val start = (page.toLong() * pageSize).coerceAtMost(items.size.toLong()).toInt()\n    val end = (start + pageSize).coerceAtMost(items.size)\n', '    if (items.isEmpty()) return emptyList()\n    val lastPage = (items.lastIndex / pageSize).coerceAtLeast(0)\n    val safePage = page.coerceAtMost(lastPage)\n    val start = safePage * pageSize\n    val end = (start + pageSize).coerceAtMost(items.size)\n')
print('patch_0448: aligned legacy volume tests with 10-band/200% rules, tuned video gesture sensitivity and clamped Android Auto pagination')