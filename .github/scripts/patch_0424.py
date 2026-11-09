from pathlib import Path
import re
import shutil

ROOT = Path("app/src/main/java/com/chiyuri/player")
DRAWABLE = Path("app/src/main/res/drawable")
NODPI = Path("app/src/main/res/drawable-nodpi")
source_image = Path("chiyuri_emblem.png")
if not source_image.is_file() or source_image.stat().st_size < 100_000:
    raise SystemExit("Original chiyuri_emblem.png is missing or unexpectedly small")

NODPI.mkdir(parents=True, exist_ok=True)
shutil.copyfile(source_image, NODPI / "chiyuri_emblem.png")
old_vector = DRAWABLE / "chiyuri_emblem.xml"
if old_vector.exists():
    old_vector.unlink()

loader = ROOT / "BloodLoadingIndicator.kt"
s = loader.read_text(encoding="utf-8")
if "R.drawable.chiyuri_emblem" not in s:
    raise SystemExit("Loader no longer references the emblem drawable resource")
if "private fun createChiyuriBloodTexture()" not in s:
    raise SystemExit("Expected blood texture generator was not found")

new_texture = r'''private fun createChiyuriBloodTexture(): Bitmap {
    val width = 512
    val height = 512
    val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
    val random = Random(0xC41A)
    val pixels = IntArray(width * height)
    fun smoothNoise(x: Float, y: Float, scale: Float): Float {
        val ix = (x / scale).toInt()
        val iy = (y / scale).toInt()
        val fx = (x / scale) - ix
        val fy = (y / scale) - iy
        fun hash(a: Int, b: Int): Float {
            var n = a * 374761393 + b * 668265263
            n = (n xor (n shr 13)) * 1274126177
            return ((n xor (n shr 16)) and 0x7fffffff) / 1073741824f - 1f
        }
        val a = hash(ix, iy)
        val b = hash(ix + 1, iy)
        val c = hash(ix, iy + 1)
        val d = hash(ix + 1, iy + 1)
        val ux = fx * fx * (3f - 2f * fx)
        val uy = fy * fy * (3f - 2f * fy)
        val top = a + (b - a) * ux
        val bottom = c + (d - c) * ux
        return top + (bottom - top) * uy
    }
    for (y in 0 until height) {
        for (x in 0 until width) {
            val broad = smoothNoise(x.toFloat(), y.toFloat(), 118f)
            val medium = smoothNoise(x.toFloat(), y.toFloat(), 39f)
            val fine = smoothNoise(x.toFloat(), y.toFloat(), 11f)
            val vein = smoothNoise(x.toFloat() + medium * 17f, y.toFloat() - broad * 22f, 17f)
            val shine = ((0.72f - kotlin.math.abs(vein)) * 0.16f).coerceAtLeast(0f)
            val depth = (0.52f + broad * 0.17f + medium * 0.13f + fine * 0.07f + shine).coerceIn(0f, 1f)
            val r = (38f + depth * 170f).toInt().coerceIn(0, 255)
            val g = (1f + depth * 24f + shine * 70f).toInt().coerceIn(0, 90)
            val b = (9f + depth * 39f + shine * 32f).toInt().coerceIn(0, 100)
            pixels[y * width + x] = android.graphics.Color.argb(255, r, g, b)
        }
    }
    bitmap.setPixels(pixels, 0, width, 0, 0, width, height)
    val canvas = NativeCanvas(bitmap)
    repeat(76) {
        val x = random.nextFloat() * width
        val y = random.nextFloat() * height
        val radius = 2.5f + random.nextFloat() * 17f
        val drop = NativePaint(NativePaint.ANTI_ALIAS_FLAG).apply {
            shader = android.graphics.RadialGradient(
                x - radius * 0.28f, y - radius * 0.34f, radius * 1.35f,
                intArrayOf(0xFFFFA0AD.toInt(), 0xFFB20B2C.toInt(), 0xFF43000D.toInt()),
                floatArrayOf(0f, 0.42f, 1f), Shader.TileMode.CLAMP
            )
        }
        canvas.drawOval(x - radius, y - radius * 0.62f, x + radius, y + radius * 0.82f, drop)
        val glint = NativePaint(NativePaint.ANTI_ALIAS_FLAG).apply {
            color = 0x99FFD1D8.toInt()
            strokeWidth = (radius * 0.12f).coerceAtLeast(0.8f)
            strokeCap = NativePaint.Cap.ROUND
        }
        canvas.drawLine(x - radius * 0.35f, y - radius * 0.28f, x + radius * 0.08f, y - radius * 0.43f, glint)
    }
    repeat(28) {
        val x = random.nextFloat() * width
        val y = random.nextFloat() * height
        val length = 24f + random.nextFloat() * 130f
        val path = Path().apply {
            moveTo(x, y)
            cubicTo(x + length * 0.25f, y - 18f, x + length * 0.65f, y + 16f, x + length, y - 4f)
        }
        val streak = NativePaint(NativePaint.ANTI_ALIAS_FLAG).apply {
            color = 0x88700018.toInt()
            style = NativePaint.Style.STROKE
            strokeWidth = 1.5f + random.nextFloat() * 6f
            strokeCap = NativePaint.Cap.ROUND
        }
        canvas.drawPath(path, streak)
        streak.color = 0x66FF899A
        streak.strokeWidth = 0.8f
        canvas.drawPath(path, streak)
    }
    return bitmap
}'''
start = s.index("private fun createChiyuriBloodTexture()")
s = s[:start] + new_texture + "\n"
loader.write_text(s, encoding="utf-8")

gradle = Path("app/build.gradle.kts")
g = gradle.read_text(encoding="utf-8")
if 'orElse("334")' in g:
    g = g.replace('orElse("334")', 'orElse("335")', 1)
elif 'orElse("335")' not in g:
    raise SystemExit("Unexpected versionCode fallback; refusing unsafe replacement")
gradle.write_text(g, encoding="utf-8")

print("Original PNG installed as drawable-nodpi; vector substitute removed; blood texture upgraded; versionCode fallback set to 335.")
