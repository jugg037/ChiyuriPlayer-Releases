from pathlib import Path
p=Path("app/src/main/java/com/chiyuri/player")
def add_import(file,line):
 f=p/file; s=f.read_text(encoding="utf-8")
 if line not in s:
  marker="package com.chiyuri.player\n"
  if s.count(marker)!=1: raise SystemExit(f"patch_0470: package marker mismatch in {file}")
  s=s.replace(marker,marker+"\n"+line,1)
  f.write_text(s,encoding="utf-8")
f=p/"MainActivity.kt"; s=f.read_text(encoding="utf-8")
for old,new in [
 ("Icons.Default.QueueMusic","Icons.AutoMirrored.Filled.QueueMusic"),
 ("Icons.Default.ArrowBack","Icons.AutoMirrored.Filled.ArrowBack"),
 ("Icons.Default.PlaylistAdd","Icons.AutoMirrored.Filled.PlaylistAdd")
]:
 if old not in s: raise SystemExit(f"patch_0470: deprecated icon reference missing: {old}")
 s=s.replace(old,new)
f.write_text(s,encoding="utf-8")
for line in [
 "import androidx.compose.material.icons.automirrored.filled.QueueMusic",
 "import androidx.compose.material.icons.automirrored.filled.ArrowBack",
 "import androidx.compose.material.icons.automirrored.filled.PlaylistAdd"
]: add_import("MainActivity.kt",line)
for file in ("SmbLibraryScreen.kt","WebDavLibraryScreen.kt"):
 add_import(file,"import androidx.compose.material.icons.automirrored.filled.PlaylistAdd")
f=p/"AudioEffectsController.kt"; s=f.read_text(encoding="utf-8")
anchor="    private fun applySettings() {"
if s.count(anchor)!=1: raise SystemExit("patch_0470: Virtualizer applySettings anchor mismatch")
s=s.replace(anchor,'    @Suppress("DEPRECATION") // The platform Virtualizer remains an optional compatibility effect.\n'+anchor,1)
f.write_text(s,encoding="utf-8")
print("patch_0470: migrated deprecated directional Compose icons to AutoMirrored variants and isolated Virtualizer strength deprecations")
