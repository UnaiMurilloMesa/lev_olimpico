package com.tfg.halteroanalyzer.ui.analysis

import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.net.toUri
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView

private const val PREVIEW_ASPECT_RATIO = 9f / 16f
private const val MILLIS_PER_SECOND = 1000.0

/** Previsualización del vídeo local, sincronizada con el instante seleccionado. */
@Composable
fun VideoScrubber(
    videoUri: String,
    positionSeconds: Double,
    onDurationKnown: (Double) -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current

    val player = remember(videoUri) {
        ExoPlayer.Builder(context).build().apply {
            setMediaItem(MediaItem.fromUri(videoUri.toUri()))
            prepare()
            playWhenReady = false
        }
    }

    // La duración solo se conoce cuando el reproductor termina de preparar el medio.
    DisposableEffect(player) {
        val listener = object : Player.Listener {
            override fun onPlaybackStateChanged(playbackState: Int) {
                if (playbackState == Player.STATE_READY && player.duration > 0) {
                    onDurationKnown(player.duration / MILLIS_PER_SECOND)
                }
            }
        }
        player.addListener(listener)
        onDispose {
            player.removeListener(listener)
            player.release()
        }
    }

    LaunchedEffect(positionSeconds) {
        player.seekTo((positionSeconds * MILLIS_PER_SECOND).toLong())
    }

    AndroidView(
        factory = { ctx ->
            PlayerView(ctx).apply {
                this.player = player
                useController = false
            }
        },
        modifier = modifier.aspectRatio(PREVIEW_ASPECT_RATIO),
    )
}