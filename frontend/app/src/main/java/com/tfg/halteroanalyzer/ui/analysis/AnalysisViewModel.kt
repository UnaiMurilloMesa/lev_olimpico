package com.tfg.halteroanalyzer.ui.analysis

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.tfg.halteroanalyzer.domain.AnalysisRepository
import com.tfg.halteroanalyzer.domain.AnalysisRequest
import com.tfg.halteroanalyzer.domain.AnalysisState
import com.tfg.halteroanalyzer.domain.AnalysisStatusPoller
import com.tfg.halteroanalyzer.domain.JobStatus
import com.tfg.halteroanalyzer.domain.VideoGallery
import com.tfg.halteroanalyzer.domain.VideoSource
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.File
import com.tfg.halteroanalyzer.domain.SaveResult

/** Crea los ficheros locales donde se guardan los artefactos de un trabajo. */
interface ResultFileProvider {
    fun videoFor(jobId: String): File
    fun chartFor(jobId: String): File
    fun snapshotFor(jobId: String, name: String): File
}

/** Coordina la selección, preparación, envío y seguimiento de un análisis. */
class AnalysisViewModel(
    private val repository: AnalysisRepository,
    private val poller: AnalysisStatusPoller,
    private val videoSourceProvider: (String) -> VideoSource,
    private val resultFileProvider: ResultFileProvider,
    private val gallery: VideoGallery,
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
            current.snapshots.values.forEach { it.delete() }
            viewModelScope.launch { repository.delete(current.jobId) }
        }
        _uiState.value = AnalysisUiState.Idle
    }

    /** Guarda el vídeo analizado en la galería del dispositivo. */
    fun saveToGallery() {
        val current = _uiState.value as? AnalysisUiState.Completed ?: return
        if (current.saveState == SaveState.SAVING || current.saveState == SaveState.SAVED) return

        _uiState.value = current.copy(saveState = SaveState.SAVING, saveMessage = null)

        viewModelScope.launch {
            val name = "haltero_${current.jobId.take(8)}.mp4"
            when (val result = gallery.save(current.video, name)) {
                is SaveResult.Saved -> updateSave(SaveState.SAVED, "Guardado en la galería.")
                is SaveResult.Failed -> updateSave(SaveState.FAILED, result.reason)
                is SaveResult.PermissionRequired ->
                    updateSave(SaveState.FAILED, "Concede permiso de almacenamiento para guardar.")
            }
        }
    }

    private fun updateSave(state: SaveState, message: String) {
        val current = _uiState.value as? AnalysisUiState.Completed ?: return
        _uiState.value = current.copy(saveState = state, saveMessage = message)
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

        // La gráfica y las capturas son prescindibles: si falla su descarga, el
        // resto del análisis sigue siendo útil para el usuario.
        val chart = if (state.summary?.hasVelocityChart == true) {
            repository.downloadChart(jobId, resultFileProvider.chartFor(jobId)).getOrNull()
        } else {
            null
        }

        _uiState.value = AnalysisUiState.Completed(
            jobId = jobId,
            video = video,
            chart = chart,
            snapshots = downloadSnapshots(jobId, state),
            summary = state.summary,
        )
    }

    private suspend fun downloadSnapshots(
        jobId: String,
        state: AnalysisState,
    ): Map<String, File> {
        val phases = state.summary?.phases.orEmpty()
        val downloaded = mutableMapOf<String, File>()

        for (phase in phases) {
            val name = phase.snapshot ?: continue
            repository
                .downloadSnapshot(jobId, name, resultFileProvider.snapshotFor(jobId, name))
                .onSuccess { file -> downloaded[phase.id] = file }
        }

        return downloaded
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
        private val gallery: VideoGallery,
    ) : ViewModelProvider.Factory {

        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = AnalysisViewModel(
            repository = repository,
            poller = AnalysisStatusPoller(repository),
            videoSourceProvider = videoSourceProvider,
            resultFileProvider = resultFileProvider,
            gallery = gallery,
        ) as T
    }
}