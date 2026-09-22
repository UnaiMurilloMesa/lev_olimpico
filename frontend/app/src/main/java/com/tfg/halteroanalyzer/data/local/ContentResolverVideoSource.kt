package com.tfg.halteroanalyzer.data.local

import android.content.ContentResolver
import android.net.Uri
import android.provider.OpenableColumns
import com.tfg.halteroanalyzer.domain.VideoSource
import java.io.FileNotFoundException
import java.io.InputStream

/** Vídeo de la galería del dispositivo, accedido mediante su `Uri`. */
class ContentResolverVideoSource private constructor(
    private val resolver: ContentResolver,
    private val uri: Uri,
    override val fileName: String,
    override val mimeType: String,
    override val sizeBytes: Long,
) : VideoSource {

    override fun openStream(): InputStream =
        resolver.openInputStream(uri) ?: throw FileNotFoundException("No se pudo abrir $uri")

    companion object {
        private const val DEFAULT_MIME = "video/mp4"
        private const val UNKNOWN_SIZE = -1L

        /** Construye el origen consultando nombre, tipo y tamaño del contenido. */
        fun from(resolver: ContentResolver, uri: Uri): ContentResolverVideoSource {
            val mimeType = resolver.getType(uri) ?: DEFAULT_MIME
            var displayName: String? = null
            var size = UNKNOWN_SIZE

            resolver.query(uri, null, null, null, null)?.use { cursor ->
                if (cursor.moveToFirst()) {
                    val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                    val sizeIndex = cursor.getColumnIndex(OpenableColumns.SIZE)
                    if (nameIndex >= 0) displayName = cursor.getString(nameIndex)
                    if (sizeIndex >= 0 && !cursor.isNull(sizeIndex)) size = cursor.getLong(sizeIndex)
                }
            }

            return ContentResolverVideoSource(
                resolver = resolver,
                uri = uri,
                fileName = ensureVideoExtension(displayName, mimeType),
                mimeType = mimeType,
                sizeBytes = size,
            )
        }
    }
}