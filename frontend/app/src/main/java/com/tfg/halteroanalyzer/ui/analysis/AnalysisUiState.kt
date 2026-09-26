package com.tfg.halteroanalyzer.ui.analysis

import com.tfg.halteroanalyzer.domain.AnalysisRequest
import com.tfg.halteroanalyzer.domain.AnalysisSummary
import java.io.File

/** Estado de la pantalla de análisis. */
sealed interface AnalysisUiState {

    /** Nada seleccionado todavía: se muestra el botón de analizar. */
    data object Idle : AnalysisUiState

    /**
     * Vídeo elegido: el usuario ajusta el instante de despegue y su estatura
     * antes de lanzar el análisis.
     */
    data class Preparing(
        val videoUri: String,
        val request: AnalysisRequest = AnalysisRequest(),
        val videoDurationSeconds: Double = 0.0,
    ) : AnalysisUiState {

        /** Indica si los datos introducidos permiten lanzar el análisis. */
        val canStart: Boolean
            get() = videoDurationSeconds > 0 &&
                    request.isValid &&
                    request.startSeconds <= videoDurationSeconds
    }

    /** El vídeo se está enviando al servidor. */
    data object Uploading : AnalysisUiState

    /** El servidor está procesando el vídeo. */
    data class Processing(val jobId: String, val queued: Boolean) : AnalysisUiState

    /** Análisis terminado: vídeo descargado y listo para reproducir. */
    data class Completed(
        val jobId: String,
        val video: File,
        val chart: File?,
        val summary: AnalysisSummary?,
    ) : AnalysisUiState

    /** Algo falló; se ofrece reintentar. */
    data class Failed(val message: String) : AnalysisUiState
}