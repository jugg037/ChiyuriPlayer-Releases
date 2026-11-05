from pathlib import Path
base = Path("app/src/main/java/com/chiyuri/player")

p = base / "MainActivity.kt"
s = p.read_text(encoding="utf-8")
replacements = [
    ('listOf("Музыка", "Видео", "Плейлисты", "Текст", "Ещё")', 'listOf("Музыка", "Видео", "Плейлисты", "Ещё")'),
    ('                                        "Текст" -> Icons.Default.MusicNote\n', ''),
    ('                "Текст" -> LyricsScreen(player = player, modifier = Modifier.weight(1f))\n', ''),
    ('color = MaterialTheme.colorScheme.surface.copy(alpha = if (expanded) 0.9f else 1f)', 'color = MaterialTheme.colorScheme.surface.copy(alpha = if (expanded) 1f else 0.25f)'),
    ('NavigationBar(containerColor = MaterialTheme.colorScheme.surface)', 'NavigationBar(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.90f))'),
    ('                      selectedIconColor = Color.White,\n                      selectedTextColor = Color(0xFFFFE8ED),\n                      indicatorColor = Color(0xFF8B001B),\n                      unselectedIconColor = Color(0xFFFF718B),\n                      unselectedTextColor = Color(0xFFD69AA5)', '                      selectedIconColor = MaterialTheme.colorScheme.onPrimary,\n                      selectedTextColor = MaterialTheme.colorScheme.primary,\n                      indicatorColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.22f),\n                      unselectedIconColor = MaterialTheme.colorScheme.secondary,\n                      unselectedTextColor = MaterialTheme.colorScheme.onSurfaceVariant'),
    ('color = MaterialTheme.colorScheme.surface, shape = RoundedCornerShape(16.dp)', 'color = MaterialTheme.colorScheme.surface.copy(alpha = 0.90f), shape = RoundedCornerShape(16.dp)'),
    ('Text("Chiyuri", color = Color(0xFF8B0000),', 'Text("Chiyuri", color = MaterialTheme.colorScheme.primary,'),
    ('HorizontalDivider(color = Color(0xFF343641))', 'HorizontalDivider(color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.45f))'),
]
for old, new in replacements:
    if old not in s:
        raise SystemExit(f"Missing expected MainActivity marker: {old!r}")
    s = s.replace(old, new)
duplicate = '                    Text(if (tab == "Ещё" && morePage != "Главное") morePage else tab, style = MaterialTheme.typography.headlineLarge, color = MaterialTheme.colorScheme.onSurface)\n                    Text(if (tab == "Ещё" && morePage != "Главное") morePage else tab, style = MaterialTheme.typography.headlineLarge, color = MaterialTheme.colorScheme.onSurface)'
if duplicate in s:
    s = s.replace(duplicate, duplicate.split("\n")[0], 1)
toggle = '''            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Цвета из обложки", color = MaterialTheme.colorScheme.onSurface)
                    Text(
                        "Акцент, фон и карточки подстраиваются под обложку текущего трека",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        style = MaterialTheme.typography.bodySmall
                    )
                }
                Switch(
                    checked = config.dynamicColors,
                    onCheckedChange = {
                        config = config.copy(dynamicColors = it)
                        AppearanceSettings.save(context, config)
                    }
                )
            }
'''
if toggle not in s:
    raise SystemExit("Dynamic palette toggle block not found")
s = s.replace(toggle, "", 1)
s = s.replace("    val useArtworkPalette = appearance.dynamicColors\n", "    val useArtworkPalette = true\n")
old = "colorScheme = colors.copy(primary = Color(0xFFB20D24), secondary = Color(0xFF7A1024))"
new = '''colorScheme = colors.copy(
        primary = adaptiveAccent,
        secondary = adaptiveSecondary,
        tertiary = adaptiveAccent,
        background = adaptiveBackground.copy(alpha = 0.90f),
        surface = adaptiveSurface.copy(alpha = 0.90f),
        surfaceVariant = adaptiveSurface.copy(alpha = 0.90f)
    )'''
if old not in s:
    raise SystemExit("Missing fixed-color MaterialTheme override")
s = s.replace(old, new, 1)
assert '"Текст" -> LyricsScreen' not in s
assert 'if (expanded) 1f else 0.25f' in s
assert 'Цвета из обложки' not in s
p.write_text(s, encoding="utf-8")

p = base / "GothicUi.kt"
s = p.read_text(encoding="utf-8")
if "import androidx.compose.material3.MaterialTheme\n" not in s:
    s = s.replace("import androidx.compose.material3.IconButton\n", "import androidx.compose.material3.IconButton\nimport androidx.compose.material3.MaterialTheme\n", 1)
s = s.replace(".background(Color(0xFF3A0712))", ".background(MaterialTheme.colorScheme.surface)")
s = s.replace(".border(1.dp, Color(0xFFFF2448), ChiyuriGothicShape)", ".border(1.dp, MaterialTheme.colorScheme.primary, ChiyuriGothicShape)")
s = s.replace("drawPath(p, Color(0xFFB31332), style = Stroke(width = 1.dp.toPx()))", "drawPath(p, ornamentColor, style = Stroke(width = 1.dp.toPx()))")
s = s.replace(".background(Color(0xFF500A1B))", ".background(MaterialTheme.colorScheme.surface)")
s = s.replace(".border(1.dp, Color(0xFFFF3659), ChiyuriGothicShape)", ".border(1.dp, MaterialTheme.colorScheme.primary, ChiyuriGothicShape)")
needle = '''fun GothicIcon(
    imageVector: ImageVector,
    contentDescription: String?,
    modifier: Modifier = Modifier,
    tint: Color = Color.Unspecified
) {
    Box('''
replacement = '''fun GothicIcon(
    imageVector: ImageVector,
    contentDescription: String?,
    modifier: Modifier = Modifier,
    tint: Color = Color.Unspecified
) {
    val ornamentColor = MaterialTheme.colorScheme.secondary
    Box('''
if needle not in s:
    raise SystemExit("GothicIcon insertion point not found")
s = s.replace(needle, replacement, 1)
if any(x in s for x in ("Color(0xFF3A0712)", "Color(0xFFFF2448)", "Color(0xFF500A1B)", "Color(0xFFFF3659)", "MaterialTheme.colorScheme.secondary, style = Stroke")):
    raise SystemExit("Hard-coded Gothic palette or non-composable Canvas palette lookup remains")
p.write_text(s, encoding="utf-8")

p = base / "TrackArtworkBackdrop.kt"
s = p.read_text(encoding="utf-8")
if ".blur(2.dp)" not in s:
    raise SystemExit("Artwork backdrop blur must remain exactly 2.dp")

main = (base / "MainActivity.kt").read_text(encoding="utf-8")
assert 'listOf("Музыка", "Видео", "Плейлисты", "Текст", "Ещё")' not in main
assert 'if (expanded) 1f else 0.25f' in main
assert 'surface.copy(alpha = 0.90f)' in main
assert 'adaptiveAccent' in main and 'adaptiveSecondary' in main
assert '.blur(2.dp)' in s
print("0.4.14 UI patch applied: lyrics tab removed; mini-player alpha 0.25/1.0; app surfaces 0.90; artwork palette automatic; Gothic controls themed; backdrop blur remains 2.dp.")
