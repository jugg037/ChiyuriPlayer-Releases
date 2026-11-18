from pathlib import Path
root=Path("app/src/main/java/com/chiyuri/player")
main=root/"MainActivity.kt"
s=main.read_text(encoding="utf-8")
print("=== MAIN STATE AND RESET CONTEXT ===")
lines=s.splitlines()
for start,end in [(270,315),(450,480),(630,665)]:
    print(f"--- MainActivity.kt {start}-{end} ---")
    for n in range(start,min(end,len(lines))):
        print(f"{n+1}: {lines[n]}")
print("=== AUDIO EFFECTS SCREEN FULL FUNCTION ===")
start=s.index("private fun AudioEffectsScreen(")
end=s.find("\\n@Composable",start+20)
if end<0: end=len(s)
for n,line in enumerate(s[start:end].splitlines(),1):
    print(f"AudioEffectsScreen+{n}: {line}")
print("=== EXPANSION STATE CANDIDATES ===")
for i,line in enumerate(s.splitlines(),1):
    if any(k in line.lower() for k in ("expanded", "miniplayer", "audioeffectsscreen")):
        print(f"{i}: {line}")
print("=== EXPANSION CALL CONTEXT ===")
lines=s.splitlines()
for i,line in enumerate(lines):
    if "MiniPlayerBar(" in line and not line.strip().startswith("private fun"):
        print("\n".join(f"{j+1}: {lines[j]}" for j in range(max(0,i-12),min(len(lines),i+38))))
print("=== EQUALIZER FILE DISCOVERY ===")
for p in sorted(root.glob("*.kt")):
    t=p.read_text(encoding="utf-8")
    if "Equalizer(" in t or "AudioEffectsScreen" in t or "equalizer" in t.lower():
        print(f"\n--- {p.name} ({len(t.splitlines())} lines) ---")
        ls=t.splitlines()
        hits=[i for i,x in enumerate(ls) if "Equalizer(" in x or "AudioEffectsScreen" in x or "equalizer" in x.lower()]
        shown=set()
        for i in hits:
            for j in range(max(0,i-8),min(len(ls),i+28)):
                if j not in shown:
                    print(f"{j+1}: {ls[j]}")
                    shown.add(j)
print("=== DIAGNOSTIC COMPLETE; STOP BEFORE BUILD/RELEASE ===")
raise SystemExit("INTENTIONAL_DIAGNOSTIC_STOP")
