from pathlib import Path

ROOT = Path("app/src/main/java/com/chiyuri/player")
RES = Path("app/src/main/res/drawable")
RES.mkdir(parents=True, exist_ok=True)

VECTOR_XML = r'''<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="256dp" android:height="256dp" android:viewportWidth="256" android:viewportHeight="256">
<path android:fillColor="#FFFDFB" android:fillType="evenOdd" android:pathData="M154,240 L146,243 L141,243 L145,240Z"/>
<path android:fillColor="#FFFDFB" android:fillType="evenOdd" android:pathData="M215,215 L216,219 L214,222 L212,218Z"/>
<path android:fillColor="#FFFDFB" android:fillType="evenOdd" android:pathData="M213,214 L214,213 L215,215 L214,216Z"/>
<path android:fillColor="#FFFDFB" android:fillType="evenOdd" android:pathData="M89,211 L79,215 L78,220 L69,237 L69,239 L72,238 L85,220Z"/>
<path android:fillColor="#FFFDFB" android:fillType="evenOdd" android:pathData="M215,215 L208,205 L201,200 L185,194 L170,192 L163,196 L179,200 L192,206 L202,216 L202,222 L194,228 L179,231 L163,233 L157,236 L155,235 L158,223 L156,223 L152,225 L130,246 L128,245 L128,248 L142,251 L176,250 L176,248 L164,245 L163,243 L192,238 L202,234 L208,231 L214,224 L216,220Z"/>
<path android:fillColor="#FFFDFB" android:fillType="evenOdd" android:pathData="M203,118 L204,123 L203,136 L201,142 L195,152 L192,154 L176,170 L149,189 L146,188 L104,198 L88,204 L87,203 L90,201 L91,193 L91,185 L88,174 L78,160 L62,150 L62,140 L67,132 L70,130 L73,126 L78,124 L80,120 L91,115 L104,114 L109,115 L113,117 L118,124 L118,130 L116,134 L119,132 L121,129 L123,132 L121,137 L127,131 L128,131 L131,126 L140,118 L156,109 L165,107 L180,106 L187,108 L197,112Z"/>
<path android:fillColor="#FFFDFB" android:fillType="evenOdd" android:pathData="M184,101 L188,100 L191,102 L188,103Z"/>
<path android:fillColor="#FFFDFB" android:fillType="evenOdd" android:pathData="M169,101 L174,99 L182,99 L185,101Z"/>
<path android:fillColor="#FFFDFB" android:fillType="evenOdd" android:pathData="M216,106 L206,96 L193,90 L174,89 L167,91 L152,98 L139,107 L130,118 L119,132 L118,117 L114,109 L108,106 L98,104 L88,105 L76,109 L71,112 L58,124 L52,133 L49,142 L50,157 L52,158 L59,158 L67,161 L75,168 L81,174 L85,185 L85,196 L83,201 L84,204 L81,207 L47,222 L36,224 L34,223 L32,221 L34,211 L40,200 L54,185 L64,176 L72,171 L68,171 L53,180 L33,200 L26,211 L24,218 L24,226 L26,229 L31,232 L39,231 L85,210 L116,200 L136,196 L138,193 L144,193 L71,240 L63,244 L60,244 L61,246 L65,246 L95,232 L124,214 L126,215 L153,200 L188,173 L208,151 L214,141 L218,124 L216,112Z"/>
<path android:fillColor="#FFFDFB" android:fillType="evenOdd" android:pathData="M10,75 L8,77 L10,91 L21,118 L29,131 L41,142 L44,143 L46,142 L46,138 L44,136 L44,134 L46,132 L42,129 L50,129 L49,125 L55,123 L55,121 L50,121 L41,117 L26,104 L19,95 L13,82 L11,80 L12,76Z"/>
<path android:fillColor="#FFFDFB" android:fillType="evenOdd" android:pathData="M248,2 L245,2 L239,6 L243,7 L246,12 L245,28 L240,45 L235,54 L223,71 L208,83 L200,87 L200,89 L203,89 L211,85 L212,87 L210,89 L212,90 L210,92 L212,92 L216,88 L218,89 L215,94 L217,94 L218,97 L220,95 L221,96 L219,99 L221,106 L220,109 L224,108 L237,92 L243,81 L249,67 L252,48 L253,22 L251,8Z"/>
<path android:fillColor="#777777" android:fillType="evenOdd" android:pathData="M164,236 L157,238 L159,239Z M196,232 L187,234 L193,233Z M192,231 L187,233 L174,235 L184,234Z M26,222 L29,226 L37,227 L30,226Z M204,220 L204,224 L202,226 L203,225 L205,226 L199,231 L207,225 L207,223 L205,226 L203,224Z M199,207 L205,213 L203,210 L202,211 L201,210 L202,208Z M138,205 L136,207 L135,206 L124,214Z M187,198 L191,201 L195,201 L199,205 L198,204 L199,203 L196,201Z M175,196 L185,200 L187,199Z M130,193 L134,193 L133,192Z M180,167 L155,185 L177,171Z M58,134 L54,142 L54,146 L53,147 L54,153 L56,155 L54,151 L54,143Z M126,125 L122,130 L124,128Z M42,123 L42,124 L49,128 L48,127 L49,126 L47,127Z M31,119 L32,118 L33,119 L32,120Z M30,118 L31,117 L32,118 L31,119Z M28,115 L29,114 L32,117 L30,118Z M205,114 L206,113 L207,114 L206,115Z M207,113 L208,112 L209,113 L208,114Z M206,112 L207,111 L208,112 L207,113Z M205,111 L206,110 L207,111 L206,112Z M25,111 L38,129 L45,135 L39,130 L33,121 L34,120 L43,131 L44,130 L31,115 L29,114 L28,115Z M204,110 L205,109 L206,110 L205,111Z M202,108 L205,111 L204,113 L205,114 L206,113 L207,114 L204,109Z M80,113 L83,111 L90,110 L100,110 L88,110Z M181,102 L189,104 L188,103Z M192,104 L195,105 L197,104 L192,101 L196,104 L195,105 L192,104Z M164,103 L163,102 L158,104 L147,111 L159,104Z M17,101 L22,114 L29,124 L20,110Z M221,100 L219,101 L220,102 L219,103Z M194,100 L202,105 L209,112 L211,117 L207,110 L202,106Z M219,95 L220,94 L221,95 L220,96Z M220,93 L221,92 L222,93 L221,94Z M217,92 L218,91 L219,92 L218,93Z M225,84 L221,89 L220,88 L221,89 L219,91 L218,90 L219,92 L218,93 L217,92 L216,94 L217,95Z M230,77 L226,83 L228,85 L219,97 L221,96 L223,91 L228,85 L227,82Z M223,77 L222,78 L221,77 L222,79 L219,82 L218,80 L211,89 L218,81 L219,84 L217,86 L218,87 L217,88 L218,89 L220,88 L218,86Z M246,72 L240,87 L234,95 L239,88 L244,78Z M248,55 L247,55 L246,60 L243,68 L245,66 L247,59Z M248,44 L247,44 L247,48 L242,63 L243,63 L243,60 L246,53Z M251,38 L250,50 L249,51 L250,52 L246,65 L247,67 L250,52Z M251,25 L251,31 L250,32 L249,31 L250,33 L251,33Z M243,3 L242,4 L245,5 L248,10 L249,15 L249,10 L246,5 L244,5Z"/>
</vector>'''

KOTLIN = r'''package com.chiyuri.player

import android.graphics.Bitmap
import android.graphics.BlurMaskFilter
import android.graphics.LinearGradient
import android.graphics.Paint as NativePaint
import android.graphics.Path
import android.graphics.Path as NativePath
import android.graphics.PorterDuff
import android.graphics.PorterDuffXfermode
import android.graphics.RectF
import android.graphics.Shader
import android.graphics.Canvas as NativeCanvas
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.platform.LocalContext
import kotlin.math.cos
import kotlin.math.sin
import kotlin.random.Random

@Composable
fun BloodLoader(progress: Float? = null, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    val emblem = remember(context) {
        context.getDrawable(R.drawable.chiyuri_emblem)?.let {
            Bitmap.createBitmap(512, 512, Bitmap.Config.ARGB_8888).also { bitmap ->
                val target = NativeCanvas(bitmap)
                it.setBounds(0, 0, 512, 512)
                it.draw(target)
            }
        }
    }
    val blood = remember { createChiyuriBloodTexture() }
    val transition = rememberInfiniteTransition(label = "chiyuri-blood-loader")
    val rotation by transition.animateFloat(
        initialValue = 0f, targetValue = 360f,
        animationSpec = infiniteRepeatable(tween(1900, easing = LinearEasing), RepeatMode.Restart),
        label = "chiyuri-blood-rotation"
    )
    Canvas(modifier = modifier) {
        if (emblem == null || size.minDimension <= 0f) return@Canvas
        val dst = RectF(0f, 0f, size.width, size.height)
        val cx = size.width / 2f
        val cy = size.height / 2f
        val radius = kotlin.math.hypot(size.width, size.height) * 0.72f
        val indeterminate = progress == null
        val start = if (indeterminate) rotation - 90f else -90f
        val sweep = if (indeterminate) 82f else ((progress?.coerceIn(0f, 1f) ?: 0f) * 360f)
        val canvas = drawContext.canvas.nativeCanvas
        val base = NativePaint(NativePaint.ANTI_ALIAS_FLAG or NativePaint.FILTER_BITMAP_FLAG).apply { alpha = 235 }
        canvas.drawBitmap(emblem, null, dst, base)
        if (sweep > 0.1f) {
            val wedge = Path().apply {
                if (sweep >= 359.9f) addOval(dst, Path.Direction.CW)
                else {
                    moveTo(cx, cy)
                    val a = Math.toRadians(start.toDouble())
                    lineTo(cx + radius * cos(a).toFloat(), cy + radius * sin(a).toFloat())
                    arcTo(RectF(cx-radius, cy-radius, cx+radius, cy+radius), start, sweep, false)
                    close()
                }
            }
            canvas.save()
            canvas.clipPath(wedge)
            val layer = canvas.saveLayer(dst, null)
            canvas.drawBitmap(blood, null, dst, NativePaint(NativePaint.ANTI_ALIAS_FLAG or NativePaint.FILTER_BITMAP_FLAG).apply { alpha = 226 })
            val mask = NativePaint(NativePaint.ANTI_ALIAS_FLAG or NativePaint.FILTER_BITMAP_FLAG).apply {
                xfermode = PorterDuffXfermode(PorterDuff.Mode.DST_IN)
            }
            canvas.drawBitmap(emblem, null, dst, mask)
            mask.xfermode = null
            canvas.restoreToCount(layer)
            canvas.restore()
            canvas.save()
            canvas.clipPath(wedge)
            canvas.drawBitmap(emblem, null, dst, NativePaint(NativePaint.ANTI_ALIAS_FLAG or NativePaint.FILTER_BITMAP_FLAG).apply { alpha = 62 })
            canvas.restore()
            val a = Math.toRadians((start + sweep).toDouble())
            val x = cx + radius * cos(a).toFloat()
            val y = cy + radius * sin(a).toFloat()
            val frontLayer = canvas.saveLayer(dst, null)
            val front = NativePaint(NativePaint.ANTI_ALIAS_FLAG).apply {
                color = android.graphics.Color.argb(220, 255, 75, 105)
                strokeWidth = (size.minDimension * 0.018f).coerceAtLeast(2f)
                strokeCap = NativePaint.Cap.ROUND
                style = NativePaint.Style.STROKE
                maskFilter = BlurMaskFilter((size.minDimension * 0.025f).coerceAtLeast(2f), BlurMaskFilter.Blur.NORMAL)
            }
            canvas.drawLine(cx, cy, x, y, front)
            front.maskFilter = null
            front.color = android.graphics.Color.rgb(255, 154, 170)
            front.strokeWidth = (size.minDimension * 0.006f).coerceAtLeast(1.2f)
            canvas.drawLine(cx, cy, x, y, front)
            val frontMask = NativePaint(NativePaint.ANTI_ALIAS_FLAG or NativePaint.FILTER_BITMAP_FLAG).apply {
                xfermode = PorterDuffXfermode(PorterDuff.Mode.DST_IN)
            }
            canvas.drawBitmap(emblem, null, dst, frontMask)
            frontMask.xfermode = null
            canvas.restoreToCount(frontLayer)
        }
    }
}

private fun createChiyuriBloodTexture(): Bitmap {
    val bitmap = Bitmap.createBitmap(384, 384, Bitmap.Config.ARGB_8888)
    val canvas = NativeCanvas(bitmap)
    val base = NativePaint(NativePaint.ANTI_ALIAS_FLAG).apply {
        shader = LinearGradient(0f, 0f, 384f, 384f,
            intArrayOf(0xFF390009.toInt(), 0xFFB20D2A.toInt(), 0xFF5B0012.toInt(), 0xFF8D061D.toInt()),
            floatArrayOf(0f, 0.38f, 0.72f, 1f), Shader.TileMode.MIRROR)
    }
    canvas.drawRect(0f, 0f, 384f, 384f, base)
    val random = Random(0xC41A)
    repeat(34) { index ->
        val x = random.nextFloat() * 384f
        val y = random.nextFloat() * 384f
        val length = 18f + random.nextFloat() * 105f
        val drift = -24f + random.nextFloat() * 48f
        val path = NativePath().apply {
            moveTo(x, y)
            cubicTo(x + length * 0.28f, y + drift, x + length * 0.7f, y - drift * 0.4f, x + length, y + drift * 0.25f)
        }
        val vein = NativePaint(NativePaint.ANTI_ALIAS_FLAG).apply {
            color = if (index % 3 == 0) 0x66FF7588 else 0x66700018
            style = NativePaint.Style.STROKE
            strokeWidth = 1.2f + random.nextFloat() * 5f
            strokeCap = NativePaint.Cap.ROUND
            maskFilter = BlurMaskFilter(1.5f + random.nextFloat() * 3f, BlurMaskFilter.Blur.NORMAL)
        }
        canvas.drawPath(path, vein)
        vein.maskFilter = null
        vein.color = 0x44FFC0C9
        vein.strokeWidth = 0.8f
        canvas.drawPath(path, vein)
    }
    repeat(48) {
        val shine = NativePaint(NativePaint.ANTI_ALIAS_FLAG).apply { color = 0x55FF9BAA }
        canvas.drawCircle(random.nextFloat() * 384f, random.nextFloat() * 384f, 0.7f + random.nextFloat() * 2.8f, shine)
    }
    return bitmap
}'''

(RES / "chiyuri_emblem.xml").write_text(VECTOR_XML, encoding="utf-8")
(ROOT / "BloodLoadingIndicator.kt").write_text(KOTLIN, encoding="utf-8")

def replace_once(path, old, new, label):
    source = path.read_text(encoding="utf-8")
    if source.count(old) != 1:
        raise SystemExit(f"{label}: expected one match, found {source.count(old)}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

main = ROOT / "MainActivity.kt"
replace_once(main,
    "        super.onCreate(savedInstanceState)\n        window.setBackgroundDrawableResource(R.drawable.chiyuri_background)",
    """        super.onCreate(savedInstanceState)
        setContent {
            ChiyuriTheme {
                Surface(color = Color(0xFF080000), modifier = Modifier.fillMaxSize()) {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(14.dp)) {
                            BloodLoader(progress = null, modifier = Modifier.size(156.dp))
                            Text("Chiyuri", color = Color.White, style = MaterialTheme.typography.titleLarge)
                        }
                    }
                }
            }
        }
        window.setBackgroundDrawableResource(R.drawable.chiyuri_background)""",
    "startup loading screen")
replace_once(main,
    "        if (permissionDenied) {\n            Text(",
    """        if (isLoading) {
            Row(Modifier.fillMaxWidth().padding(vertical = 10.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.Center) {
                BloodLoader(progress = null, modifier = Modifier.size(42.dp))
                Spacer(Modifier.width(10.dp))
                Text(if (isVideo) "Сканирование видео…" else "Сканирование медиатеки…", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        if (permissionDenied) {
            Text(""",
    "media library scanning")

lyrics = ROOT / "LyricsScreen.kt"
s = lyrics.read_text(encoding="utf-8")
s = s.replace("""CircularProgressIndicator(
                    modifier = Modifier.height(18.dp),
                    strokeWidth = 2.dp,
                    color = MaterialTheme.colorScheme.onPrimary
                )""", """BloodLoader(progress = null, modifier = Modifier.size(22.dp))""")
if "CircularProgressIndicator(" in s:
    raise SystemExit("Unconverted lyrics progress indicator")
lyrics.write_text(s.replace("import androidx.compose.material3.CircularProgressIndicator\n", ""), encoding="utf-8")

track = ROOT / "TrackDetailsComponents.kt"
s = track.read_text(encoding="utf-8")
s = s.replace("CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)", "BloodLoader(progress = null, modifier = Modifier.size(20.dp))")
s = s.replace("import androidx.compose.material3.CircularProgressIndicator\n", "")
if "CircularProgressIndicator(" in s:
    raise SystemExit("Unconverted metadata progress indicator")
track.write_text(s, encoding="utf-8")

mini = ROOT / "LyricsMiniPanel.kt"
replace_once(mini,
    'lyrics == null && loading -> Text("Ищу текст и загружаю сохранённую версию…", color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 12.sp)',
    """lyrics == null && loading -> Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                BloodLoader(progress = null, modifier = Modifier.size(30.dp))
                Text("Ищу текст и загружаю сохранённую версию…", color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 12.sp)
            }""",
    "mini-player lyrics search")

updates = ROOT / "AppUpdates.kt"
replace_once(updates,
    "if (checking) androidx.compose.material3.LinearProgressIndicator(Modifier.fillMaxWidth())",
    """if (checking) Row(Modifier.fillMaxWidth().padding(vertical = 8.dp), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    BloodLoader(progress = null, modifier = Modifier.size(42.dp))
                    androidx.compose.material3.Text("Проверяем обновления…", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }""",
    "update checking")
replace_once(updates,
    """androidx.compose.material3.LinearProgressIndicator(
                        progress = { progress / 100f },
                        modifier = Modifier.fillMaxWidth(),
                        color = MaterialTheme.colorScheme.primary,
                        trackColor = MaterialTheme.colorScheme.surfaceVariant
                    )
                    androidx.compose.material3.Text("Загрузка " + progress + "%")""",
    """Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        BloodLoader(progress = progress / 100f, modifier = Modifier.size(76.dp))
                        Column {
                            androidx.compose.material3.Text("Загрузка " + progress + "%", style = MaterialTheme.typography.titleMedium)
                            androidx.compose.material3.Text("Кровавая заливка отражает фактический прогресс APK", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                        }
                    }""",
    "update download progress")

replace_once(Path("app/build.gradle.kts"), 'orElse("333")', 'orElse("334")', "versionCode fallback")
print("Chiyuri Blood Loader installed: vector emblem, procedural blood texture, radial clockwise reveal and loading UI integrations.")
