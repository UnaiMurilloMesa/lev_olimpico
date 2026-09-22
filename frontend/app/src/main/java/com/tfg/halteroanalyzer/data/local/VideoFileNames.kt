package com.tfg.halteroanalyzer.data.local

/** Extensiones de vídeo admitidas por el backend, indexadas por tipo MIME. */
private val EXTENSION_BY_MIME = mapOf(
    "video/mp4" to "mp4",
    "video/quicktime" to "mov",
    "video/x-matroska" to "mkv",
    "video/x-msvideo" to "avi",
    "video/avi" to "avi",
)

private const val DEFAULT_EXTENSION = "mp4"

/**
 * Garantiza que el nombre del fichero lleve una extensión reconocible.
 *
 * El selector de fotos no siempre devuelve nombres con extensión, y el backend
 * valida el vídeo por ella.
 */
fun ensureVideoExtension(displayName: String?, mimeType: String?): String {
    val base = displayName?.takeIf { it.isNotBlank() } ?: "video"
    if (base.substringAfterLast('.', "").lowercase() in EXTENSION_BY_MIME.values) return base
    val extension = EXTENSION_BY_MIME[mimeType?.lowercase()] ?: DEFAULT_EXTENSION
    return "$base.$extension"
}