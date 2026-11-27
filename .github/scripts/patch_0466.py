from pathlib import Path
p=Path("app/src/main/java/com/chiyuri/player")
def add_import(file, line):
 f=p/file; s=f.read_text(encoding="utf-8")
 if line not in s:
  marker="package com.chiyuri.player\n"
  if s.count(marker)!=1: raise SystemExit(f"patch_0466: package marker mismatch in {file}")
  s=s.replace(marker,marker+"\n"+line,1)
  f.write_text(s,encoding="utf-8")
add_import("SmbLibraryScreen.kt","import androidx.compose.material.icons.Icons")
add_import("SmbLibraryScreen.kt","import androidx.compose.material.icons.filled.PlaylistAdd")
add_import("WebDavLibraryScreen.kt","import androidx.compose.material.icons.filled.PlaylistAdd")
print("patch_0466: added explicit Compose icon imports for SMB and WebDAV queue-add controls")
