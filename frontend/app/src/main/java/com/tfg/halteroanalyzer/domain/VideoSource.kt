package com.tfg.halteroanalyzer.domain

import java.io.InputStream

/** Origen de un vídeo a subir, independiente de dónde esté almacenado. */
interface VideoSource {
    val fileName: String
    val mimeType: String

    /** Tamaño en bytes, o -1 si no se conoce. */
    val sizeBytes: Long

    fun openStream(): InputStream
}