package com.tfg.halteroanalyzer.domain

import java.io.File

/** Resultado de intentar guardar un vídeo en la galería. */
sealed interface SaveResult {
    data object Saved : SaveResult
    data class Failed(val reason: String) : SaveResult
    data object PermissionRequired : SaveResult
}

/** Almacén de vídeos del dispositivo. */
interface VideoGallery {
    /** Guarda un vídeo en la galería con el nombre indicado. */
    suspend fun save(video: File, displayName: String): SaveResult
}