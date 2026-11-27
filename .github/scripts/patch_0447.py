from pathlib import Path
def write(path, source):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists(): raise SystemExit(f'patch_0447: {path} already exists')
    path.write_text(source, encoding='utf-8')
def replace_once(path, old, new):
    source = path.read_text(encoding='utf-8')
    if old not in source: raise SystemExit(f'patch_0447: anchor missing in {path.name}: {old[:80]!r}')
    path.write_text(source.replace(old, new, 1), encoding='utf-8')
PKG = Path('app/src/main/java/com/chiyuri/player')
TEST = Path('app/src/test/java/com/chiyuri/player')
actions = r'''package com.chiyuri.player

internal object PlaybackWidgetActions {
    const val PREVIOUS = "com.chiyuri.player.widget.PREVIOUS"
    const val PLAY_PAUSE = "com.chiyuri.player.widget.PLAY_PAUSE"
    const val NEXT = "com.chiyuri.player.widget.NEXT"

    fun isKnown(action: String?): Boolean = action == PREVIOUS || action == PLAY_PAUSE || action == NEXT
}
'''
provider = r'''package com.chiyuri.player

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews
import androidx.media3.common.Player
import androidx.media3.session.MediaController
import androidx.media3.session.SessionToken
import com.google.common.util.concurrent.MoreExecutors

class PlaybackWidgetProvider : AppWidgetProvider() {
    override fun onUpdate(context: Context, manager: AppWidgetManager, appWidgetIds: IntArray) {
        appWidgetIds.forEach { manager.updateAppWidget(it, placeholder(context, it)) }
        refreshFromSession(context)
    }

    companion object {
        internal fun updateAll(context: Context, player: Player) {
            val manager = AppWidgetManager.getInstance(context)
            val ids = manager.getAppWidgetIds(ComponentName(context, PlaybackWidgetProvider::class.java))
            ids.forEach { manager.updateAppWidget(it, buildViews(context, it, player)) }
        }

        private fun refreshFromSession(context: Context) {
            val token = SessionToken(context, ComponentName(context, PlaybackService::class.java))
            val future = MediaController.Builder(context, token).buildAsync()
            future.addListener({
                runCatching {
                    val controller = future.get()
                    updateAll(context, controller)
                }
                MediaController.releaseFuture(future)
            }, MoreExecutors.directExecutor())
        }

        private fun placeholder(context: Context, widgetId: Int): RemoteViews {
            val views = RemoteViews(context.packageName, R.layout.widget_player)
            views.setTextViewText(R.id.widget_title, "ChiyuriPlayer")
            views.setTextViewText(R.id.widget_artist, "Откройте плеер для воспроизведения")
            views.setImageViewResource(R.id.widget_play_pause, android.R.drawable.ic_media_play)
            attachActions(context, views, widgetId)
            return views
        }

        private fun buildViews(context: Context, widgetId: Int, player: Player): RemoteViews {
            val views = RemoteViews(context.packageName, R.layout.widget_player)
            val title = player.mediaMetadata.title?.toString()?.take(100).orEmpty()
            val artist = player.mediaMetadata.artist?.toString()?.take(100).orEmpty()
            views.setTextViewText(R.id.widget_title, title.ifBlank { "ChiyuriPlayer" })
            views.setTextViewText(R.id.widget_artist, artist.ifBlank { if (player.mediaItemCount > 0) " " else "Ничего не воспроизводится" })
            views.setImageViewResource(
                R.id.widget_play_pause,
                if (player.isPlaying) android.R.drawable.ic_media_pause else android.R.drawable.ic_media_play
            )
            attachActions(context, views, widgetId)
            return views
        }

        private fun attachActions(context: Context, views: RemoteViews, widgetId: Int) {
            fun actionIntent(action: String, requestCode: Int): PendingIntent {
                val intent = Intent(context, PlaybackWidgetActionReceiver::class.java).setAction(action)
                return PendingIntent.getBroadcast(
                    context,
                    widgetId * 10 + requestCode,
                    intent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )
            }
            views.setOnClickPendingIntent(R.id.widget_previous, actionIntent(PlaybackWidgetActions.PREVIOUS, 1))
            views.setOnClickPendingIntent(R.id.widget_play_pause, actionIntent(PlaybackWidgetActions.PLAY_PAUSE, 2))
            views.setOnClickPendingIntent(R.id.widget_next, actionIntent(PlaybackWidgetActions.NEXT, 3))
            val openIntent = Intent(context, MainActivity::class.java)
            val open = PendingIntent.getActivity(
                context, widgetId * 10 + 4, openIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            views.setOnClickPendingIntent(R.id.widget_title, open)
        }
    }
}

class PlaybackWidgetActionReceiver : android.content.BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.action ?: return
        if (!PlaybackWidgetActions.isKnown(action)) return
        val pending = goAsync()
        val token = SessionToken(context, ComponentName(context, PlaybackService::class.java))
        val future = MediaController.Builder(context, token).buildAsync()
        future.addListener({
            runCatching {
                val controller = future.get()
                when (action) {
                    PlaybackWidgetActions.PREVIOUS -> controller.seekToPreviousMediaItem()
                    PlaybackWidgetActions.PLAY_PAUSE -> if (controller.isPlaying) controller.pause() else controller.play()
                    PlaybackWidgetActions.NEXT -> controller.seekToNextMediaItem()
                }
                PlaybackWidgetProvider.updateAll(context, controller)
            }
            MediaController.releaseFuture(future)
            pending.finish()
        }, MoreExecutors.directExecutor())
    }
}
'''
test = r'''package com.chiyuri.player

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PlaybackWidgetActionsTest {
    @Test fun acceptsOnlySupportedMediaActions() {
        assertTrue(PlaybackWidgetActions.isKnown(PlaybackWidgetActions.PREVIOUS))
        assertTrue(PlaybackWidgetActions.isKnown(PlaybackWidgetActions.PLAY_PAUSE))
        assertTrue(PlaybackWidgetActions.isKnown(PlaybackWidgetActions.NEXT))
        assertFalse(PlaybackWidgetActions.isKnown("android.intent.action.DELETE"))
        assertFalse(PlaybackWidgetActions.isKnown(null))
    }
}
'''
layout = r'''<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="horizontal"
    android:gravity="center_vertical"
    android:padding="12dp"
    android:background="#171014">

    <LinearLayout
        android:layout_width="0dp"
        android:layout_height="wrap_content"
        android:layout_weight="1"
        android:orientation="vertical"
        android:gravity="center_vertical">

        <TextView
            android:id="@+id/widget_title"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:maxLines="1"
            android:ellipsize="end"
            android:text="ChiyuriPlayer"
            android:textColor="#FFFFFF"
            android:textStyle="bold"
            android:textSize="14sp" />

        <TextView
            android:id="@+id/widget_artist"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:maxLines="1"
            android:ellipsize="end"
            android:text="Ничего не воспроизводится"
            android:textColor="#D0C6CB"
            android:textSize="12sp" />
    </LinearLayout>

    <ImageButton
        android:id="@+id/widget_previous"
        android:layout_width="44dp"
        android:layout_height="44dp"
        android:background="@android:color/transparent"
        android:src="@android:drawable/ic_media_previous"
        android:contentDescription="Предыдущий трек" />

    <ImageButton
        android:id="@+id/widget_play_pause"
        android:layout_width="48dp"
        android:layout_height="48dp"
        android:background="@android:color/transparent"
        android:src="@android:drawable/ic_media_play"
        android:contentDescription="Воспроизведение или пауза" />

    <ImageButton
        android:id="@+id/widget_next"
        android:layout_width="44dp"
        android:layout_height="44dp"
        android:background="@android:color/transparent"
        android:src="@android:drawable/ic_media_next"
        android:contentDescription="Следующий трек" />
</LinearLayout>
'''
info = r'''<?xml version="1.0" encoding="utf-8"?>
<appwidget-provider xmlns:android="http://schemas.android.com/apk/res/android"
    android:minWidth="250dp"
    android:minHeight="72dp"
    android:minResizeWidth="220dp"
    android:minResizeHeight="72dp"
    android:updatePeriodMillis="0"
    android:initialLayout="@layout/widget_player"
    android:resizeMode="horizontal|vertical"
    android:widgetCategory="home_screen" />
'''
write(PKG / 'PlaybackWidgetActions.kt', actions)
write(PKG / 'PlaybackWidgetProvider.kt', provider)
write(TEST / 'PlaybackWidgetActionsTest.kt', test)
write(Path('app/src/main/res/layout/widget_player.xml'), layout)
write(Path('app/src/main/res/xml/player_widget_info.xml'), info)
manifest = Path('app/src/main/AndroidManifest.xml')
receiver = '''\n        <receiver android:name=".PlaybackWidgetProvider" android:exported="true">\n            <intent-filter>\n                <action android:name="android.appwidget.action.APPWIDGET_UPDATE" />\n            </intent-filter>\n            <meta-data android:name="android.appwidget.provider" android:resource="@xml/player_widget_info" />\n        </receiver>\n        <receiver android:name=".PlaybackWidgetActionReceiver" android:exported="false" />\n'''
replace_once(manifest, '</application>', receiver + '    </application>')
service = PKG / 'PlaybackService.kt'
replace_once(service, '                PlaybackHistoryStore.record(this@PlaybackService, mediaItem, player.duration)\n', '                PlaybackHistoryStore.record(this@PlaybackService, mediaItem, player.duration)\n                PlaybackWidgetProvider.updateAll(this@PlaybackService, player)\n')
replace_once(service, '            override fun onIsPlayingChanged(isPlaying: Boolean) {\n                PlaybackQueueStore.save(this@PlaybackService, player)\n', '            override fun onIsPlayingChanged(isPlaying: Boolean) {\n                PlaybackQueueStore.save(this@PlaybackService, player)\n                PlaybackWidgetProvider.updateAll(this@PlaybackService, player)\n')
print('patch_0447: Android home-screen media widget with previous/play-pause/next actions and live metadata applied')