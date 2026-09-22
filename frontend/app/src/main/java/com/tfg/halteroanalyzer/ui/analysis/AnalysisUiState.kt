package com.tfg.halteroanalyzer.ui.analysis

import com.tfg.halteroanalyzer.domain.AnalysisSummary
import java.io.File

/** Estado de la pantalla de análisis. */
sealed interface AnalysisUiState {

    /** Nada seleccionado todavía: se muestra el botón de analizar. */
    data object Idle : AnalysisUiState

    /** Vídeo elegido, pendiente de confirmar el inicio del análisis. */
    data class VideoSelected(val videoUri: String) : AnalysisUiState

    /** El vídeo se está enviando al servidor. */
    data object Uploading : AnalysisUiState

    /** El servidor está procesando el vídeo. */
    data class Processing(val jobId: String, val queued: Boolean) : AnalysisUiState

    /** Análisis terminado: vídeo descargado y listo para reproducir. */
    data class Completed(
        val jobId: String,
        val video: File,
        val summary: AnalysisSummary?,
    ) : AnalysisUiState

    /** Algo falló; se ofrece reintentar. */
    data class Failed(val message: String) : AnalysisUiState
}