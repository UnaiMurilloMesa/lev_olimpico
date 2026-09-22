package com.tfg.halteroanalyzer.ui.analysis

import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.common.MediaItem
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import java.io.File

private const val VIDEO_ASPECT_RATIO = 9f / 16f

/** Reproductor del vídeo analizado. */
@Composable
fun VideoPlayer(video: File, modifier: Modifier = Modifier) {
    val context = LocalContext.current

    val player = remember(video) {
        ExoPlayer.Builder(context).build().apply {
            setMediaItem(MediaItem.fromUri(video.toURI().toString()))
            prepare()
            playWhenReady = false
        }
    }

    DisposableEffect(player) {
        onDispose { player.release() }
    }

    AndroidView(
        factory = { ctx -> PlayerView(ctx).apply { this.player = player } },
        modifier = modifier.aspectRatio(VIDEO_ASPECT_RATIO),
    )
}