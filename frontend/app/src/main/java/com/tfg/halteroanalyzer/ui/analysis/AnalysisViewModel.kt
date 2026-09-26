package com.tfg.halteroanalyzer.ui.analysis

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.tfg.halteroanalyzer.domain.AnalysisRepository
import com.tfg.halteroanalyzer.domain.AnalysisRequest
import com.tfg.halteroanalyzer.domain.AnalysisState
import com.tfg.halteroanalyzer.domain.AnalysisStatusPoller
import com.tfg.halteroanalyzer.domain.JobStatus
import com.tfg.halteroanalyzer.domain.VideoSource
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.File

/** Crea los ficheros locales donde se guardan los artefactos de un trabajo. */
interface ResultFileProvider {
    fun videoFor(jobId: String): File
    fun chartFor(jobId: String): File
}

/** Coordina la selección, preparación, envío y seguimiento de un análisis. */
class AnalysisViewModel(
    private val repository: AnalysisRepository,
    private val poller: AnalysisStatusPoller,
    private val videoSourceProvider: (String) -> VideoSource,
    private val resultFileProvider: ResultFileProvider,
) : ViewModel() {

    private val _uiState = MutableStateFlow<AnalysisUiState>(AnalysisUiState.Idle)
    val uiState: StateFlow<AnalysisUiState> = _uiState.asStateFlow()

    private var activeJob: Job? = null

    /** Registra el vídeo elegido y pasa a la pantalla de preparación. */
    fun onVideoSelected(videoUri: String) {
        _uiState.value = AnalysisUiState.Preparing(videoUri = videoUri)
    }

    /** Guarda la duración del vídeo, conocida al prepararse el reproductor. */
    fun onVideoDurationKnown(durationSeconds: Double) {
        updatePreparing { it.copy(videoDurationSeconds = durationSeconds) }
    }

    /** Actualiza el instante en que la barra despega del suelo. */
    fun onStartSecondsChanged(seconds: Double) {
        updateRequest { it.copy(startSeconds = seconds) }
    }

    /** Actualiza la estatura del levantador, en centímetros. */
    fun onHeightChanged(heightCm: Int) {
        updateRequest { it.copy(heightCm = heightCm) }
    }

    /** Envía el vídeo preparado y sigue el análisis hasta su finalización. */
    fun startAnalysis() {
        val preparing = _uiState.value as? AnalysisUiState.Preparing ?: return
        if (!preparing.canStart) return

        activeJob?.cancel()
        activeJob = viewModelScope.launch {
            _uiState.value = AnalysisUiState.Uploading

            val jobId = repository
                .submit(videoSourceProvider(preparing.videoUri), preparing.request)
                .getOrElse { error -> return@launch fail(error) }

            trackProgress(jobId)
        }
    }

    /** Descarta el resultado actual y libera los datos en el servidor. */
    fun reset() {
        activeJob?.cancel()
        val current = _uiState.value
        if (current is AnalysisUiState.Completed) {
            current.video.delete()
            current.chart?.delete()
            viewModelScope.launch { repository.delete(current.jobId) }
        }
        _uiState.value = AnalysisUiState.Idle
    }

    private suspend fun trackProgress(jobId: String) {
        runCatching {
            poller.poll(jobId).collect { state -> onStateReceived(jobId, state) }
        }.onFailure { error -> fail(error) }
    }

    private suspend fun onStateReceived(jobId: String, state: AnalysisState) {
        when (state.status) {
            JobStatus.PENDING ->
                _uiState.value = AnalysisUiState.Processing(jobId, queued = true)

            JobStatus.PROCESSING ->
                _uiState.value = AnalysisUiState.Processing(jobId, queued = false)

            JobStatus.COMPLETED -> downloadResults(jobId, state)

            JobStatus.FAILED ->
                _uiState.value = AnalysisUiState.Failed(
                    state.detail ?: "El análisis no pudo completarse.",
                )
        }
    }

    private suspend fun downloadResults(jobId: String, state: AnalysisState) {
        val video = repository
            .downloadVideo(jobId, resultFileProvider.videoFor(jobId))
            .getOrElse { error -> return fail(error) }

        // La gráfica es prescindible: si falla su descarga, el resto del
        // análisis sigue siendo útil para el usuario.
        val chart = if (state.summary?.hasVelocityChart == true) {
            repository.downloadChart(jobId, resultFileProvider.chartFor(jobId)).getOrNull()
        } else {
            null
        }

        _uiState.value = AnalysisUiState.Completed(jobId, video, chart, state.summary)
    }

    private fun updatePreparing(
        transform: (AnalysisUiState.Preparing) -> AnalysisUiState.Preparing,
    ) {
        val current = _uiState.value as? AnalysisUiState.Preparing ?: return
        _uiState.value = transform(current)
    }

    private fun updateRequest(transform: (AnalysisRequest) -> AnalysisRequest) {
        updatePreparing { it.copy(request = transform(it.request)) }
    }

    private fun fail(error: Throwable) {
        _uiState.value = AnalysisUiState.Failed(error.message ?: "Error desconocido.")
    }

    /** Factoría que inyecta las dependencias del ViewModel. */
    class Factory(
        private val repository: AnalysisRepository,
        private val videoSourceProvider: (String) -> VideoSource,
        private val resultFileProvider: ResultFileProvider,
    ) : ViewModelProvider.Factory {

        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = AnalysisViewModel(
            repository = repository,
            poller = AnalysisStatusPoller(repository),
            videoSourceProvider = videoSourceProvider,
            resultFileProvider = resultFileProvider,
        ) as T
    }
}