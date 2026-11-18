from pathlib import Path

main = Path("app/src/main/java/com/chiyuri/player/MainActivity.kt")
s = main.read_text(encoding="utf-8")

# The three-dot action menu replaces the dedicated edit button and gathers every
# secondary mini-player action in one vertical, accessible list.
old_button = """                GothicIconButton(
                    onClick = onEditMetadata,
                    enabled = player.currentMediaItem != null
                ) {
                    GothicIcon(Icons.Default.Edit, contentDescription = "Редактировать информацию о треке", tint = MaterialTheme.colorScheme.onSurface)
                }"""
new_button = """                var moreActionsExpanded by remember { mutableStateOf(false) }
                var speedMenuExpanded by remember { mutableStateOf(false) }
                Box {
                    GothicIconButton(
                        onClick = { moreActionsExpanded = true },
                        enabled = player.currentMediaItem != null
                    ) {
                        GothicIcon(Icons.Default.MoreVert, contentDescription = "Дополнительные действия", tint = MaterialTheme.colorScheme.onSurface)
                    }
                    DropdownMenu(
                        expanded = moreActionsExpanded,
                        onDismissRequest = { moreActionsExpanded = false }
                    ) {
                        DropdownMenuItem(
                            text = { Text("Редактировать информацию") },
                            leadingIcon = { GothicIcon(Icons.Default.Edit, contentDescription = null) },
                            onClick = { moreActionsExpanded = false; onEditMetadata() }
                        )
                        DropdownMenuItem(
                            text = { Text("Удалить файл с устройства") },
                            leadingIcon = { GothicIcon(Icons.Default.Delete, contentDescription = null) },
                            onClick = { moreActionsExpanded = false; onDeleteTrack() }
                        )
                        DropdownMenuItem(
                            text = { Text(if (shuffleEnabled) "Выключить перемешивание" else "Перемешать очередь") },
                            leadingIcon = { GothicIcon(Icons.Default.Shuffle, contentDescription = null) },
                            onClick = { moreActionsExpanded = false; onToggleShuffle() }
                        )
                        DropdownMenuItem(
                            text = { Text(when (repeatMode) {
                                Player.REPEAT_MODE_ALL -> "Повтор: все"
                                Player.REPEAT_MODE_ONE -> "Повтор: одного"
                                else -> "Повтор: выключен"
                            }) },
                            leadingIcon = { GothicIcon(if (repeatMode == Player.REPEAT_MODE_ONE) Icons.Default.RepeatOne else Icons.Default.Repeat, contentDescription = null) },
                            onClick = { moreActionsExpanded = false; onCycleRepeat() }
                        )
                        DropdownMenuItem(
                            text = { Text("Скорость: " + String.format(Locale.getDefault(), "%.2fx", playbackSpeed) + "  ›") },
                            leadingIcon = { GothicIcon(Icons.Default.Speed, contentDescription = null) },
                            onClick = { speedMenuExpanded = true }
                        )
                        DropdownMenuItem(
                            text = { Text(
                                when {
                                    sleepAfterCurrentTrack -> "Таймер: после текущего трека"
                                    sleepRemainingSeconds > 0 -> "Таймер сна: " + (sleepRemainingSeconds / 60) + ":" + (sleepRemainingSeconds % 60).toString().padStart(2, '0')
                                    else -> "Таймер сна…"
                                }
                            ) },
                            leadingIcon = { GothicIcon(Icons.Default.Bedtime, contentDescription = null) },
                            onClick = { moreActionsExpanded = false; onSleepTimerClick() }
                        )
                    }
                    DropdownMenu(
                        expanded = speedMenuExpanded,
                        onDismissRequest = { speedMenuExpanded = false }
                    ) {
                        listOf(0.5f, 0.75f, 1f, 1.25f, 1.5f, 1.75f, 2f).forEach { speed ->
                            DropdownMenuItem(
                                text = { Text(String.format(Locale.getDefault(), "%.2fx", speed)) },
                                onClick = {
                                    onPlaybackSpeedChange(speed)
                                    speedMenuExpanded = false
                                    moreActionsExpanded = false
                                }
                            )
                        }
                    }
                }"""
if s.count(old_button) != 1:
    raise SystemExit(f"Three-dot menu anchor mismatch: {s.count(old_button)}")
s = s.replace(old_button, new_button, 1)

# Remove the old expanded-only shuffle/repeat and speed/timer rows; these actions
# now live in the three-dot menu.
start_marker = """            if (expanded) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                TextButton(onClick = onToggleShuffle)"""
end_marker = """            }
            }
            if (expanded) {
                TextButton(onClick = onDeleteTrack, modifier = Modifier.align(Alignment.End)) {
                    GothicIcon(Icons.Default.Delete, contentDescription = null)
                    Spacer(Modifier.width(6.dp))
                    Text("Удалить файл")
                }
            }
            if (expanded) VolumeIndicator()"""
if s.count(start_marker) != 1 or s.count(end_marker) != 1:
    raise SystemExit("Expanded secondary action block anchor mismatch")
a = s.index(start_marker)
b = s.index(end_marker, a)
s = s[:a] + """            if (expanded) VolumeIndicator()""" + s[b + len(end_marker):]

# Move the visualizer to the bottom of the expanded mini-player and double its
# previous expanded height (54dp -> 108dp). Keep the compact collapsed strip.
old_visualizer = """                    AudioVisualizerMiniDisplay(player, Modifier.height(54.dp))
"""
if s.count(old_visualizer) != 1:
    raise SystemExit(f"Expanded visualizer anchor mismatch: {s.count(old_visualizer)}")
s = s.replace(old_visualizer, "", 1)
insert_anchor = """                GothicIconButton(onClick = onQueueClick) {
                    GothicIcon(Icons.Default.QueueMusic, contentDescription = "Очередь воспроизведения", tint = MaterialTheme.colorScheme.onSurface)
                }
            }
            if (expanded) VolumeIndicator()"""
replacement = """                GothicIconButton(onClick = onQueueClick) {
                    GothicIcon(Icons.Default.QueueMusic, contentDescription = "Очередь воспроизведения", tint = MaterialTheme.colorScheme.onSurface)
                }
            }
            if (expanded) {
                AudioVisualizerMiniDisplay(
                    player,
                    Modifier.fillMaxWidth().height(108.dp).padding(top = 8.dp)
                )
            }
            if (expanded) VolumeIndicator()"""
if s.count(insert_anchor) != 1:
    raise SystemExit("Bottom visualizer insertion anchor mismatch")
s = s.replace(insert_anchor, replacement, 1)
main.write_text(s, encoding="utf-8")

# Version bump for the next release.
gradle = Path("app/build.gradle.kts")
g = gradle.read_text(encoding="utf-8")
if 'versionName = "0.5.3"' not in g:
    raise SystemExit("Expected current versionName 0.5.3 in app Gradle config")
g = g.replace('versionName = "0.5.3"', 'versionName = "0.5.4"', 1)
if 'orElse("339")' not in g:
    raise SystemExit("Expected current fallback versionCode 339")
g = g.replace('orElse("339")', 'orElse("340")', 1)
gradle.write_text(g, encoding="utf-8")

print("PATCH_0430_OK: vertical three-dot mini-player actions; visualizer moved to bottom and expanded to 108dp; app version 0.5.4 (340).")
