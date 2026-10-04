package com.tfg.halteroanalyzer.data.local

import android.content.ContentValues
import android.content.Context
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import com.tfg.halteroanalyzer.domain.SaveResult
import com.tfg.halteroanalyzer.domain.VideoGallery
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.IOException

private const val ALBUM_NAME = "Haltero Analyzer"
private const val VIDEO_MIME = "video/mp4"

/** Galería del dispositivo, accedida mediante MediaStore. */
class MediaStoreVideoGallery(
    private val context: Context,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO,
) : VideoGallery {

    override suspend fun save(video: File, displayName: String): SaveResult =
        withContext(ioDispatcher) {
            runCatching { insert(video, displayName) }
                .getOrElse { error ->
                    SaveResult.Failed(error.message ?: "No se pudo guardar el vídeo.")
                }
        }

    private fun insert(video: File, displayName: String): SaveResult {
        val resolver = context.contentResolver
        val collection = MediaStore.Video.Media.getContentUri(
            MediaStore.VOLUME_EXTERNAL_PRIMARY,
        )

        val values = ContentValues().apply {
            put(MediaStore.Video.Media.DISPLAY_NAME, displayName)
            put(MediaStore.Video.Media.MIME_TYPE, VIDEO_MIME)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                put(
                    MediaStore.Video.Media.RELATIVE_PATH,
                    "${Environment.DIRECTORY_MOVIES}/$ALBUM_NAME",
                )
                // Oculta la entrada hasta terminar de escribir, para que las
                // apps de galería no muestren un vídeo incompleto.
                put(MediaStore.Video.Media.IS_PENDING, 1)
            }
        }

        val uri = resolver.insert(collection, values)
            ?: return SaveResult.Failed("La galería rechazó la inserción.")

        try {
            resolver.openOutputStream(uri)?.use { output ->
                video.inputStream().use { input -> input.copyTo(output) }
            } ?: throw IOException("No se pudo abrir el destino en la galería.")
        } catch (error: IOException) {
            resolver.delete(uri, null, null)
            return SaveResult.Failed(error.message ?: "Error al escribir el vídeo.")
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            resolver.update(
                uri,
                ContentValues().apply { put(MediaStore.Video.Media.IS_PENDING, 0) },
                null,
                null,
            )
        }

        return SaveResult.Saved
    }
}