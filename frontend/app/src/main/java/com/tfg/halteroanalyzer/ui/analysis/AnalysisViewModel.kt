package com.tfg.halteroanalyzer.ui.analysis

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.tfg.halteroanalyzer.domain.AnalysisRepository
import com.tfg.halteroanalyzer.domain.AnalysisState
import com.tfg.halteroanalyzer.domain.AnalysisStatusPoller
import com.tfg.halteroanalyzer.domain.JobStatus
import com.tfg.halteroanalyzer.domain.LiftType
import com.tfg.halteroanalyzer.domain.VideoSource
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.File

/** Crea el fichero local donde se guarda el vídeo analizado de un trabajo. */
fun interface ResultFileProvider {
    fun fileFor(jobId: String): File
}

/** Coordina la selección, envío y seguimiento de un análisis. */
class AnalysisViewModel(
    private val repository: AnalysisRepository,
    private val poller: AnalysisStatusPoller,
    private val videoSourceProvider: (String) -> VideoSource,
    private val resultFileProvider: ResultFileProvider,
) : ViewModel() {

    private val _uiState = MutableStateFlow<AnalysisUiState>(AnalysisUiState.Idle)
    val uiState: StateFlow<AnalysisUiState> = _uiState.asStateFlow()

    private var activeJob: Job? = null

    /** Registra el vídeo elegido por el usuario en la galería. */
    fun onVideoSelected(videoUri: String) {
        _uiState.value = AnalysisUiState.VideoSelected(videoUri)
    }

    /** Envía el vídeo seleccionado y sigue el análisis hasta su finalización. */
    fun startAnalysis(liftType: LiftType = LiftType.SNATCH) {
        val selected = _uiState.value as? AnalysisUiState.VideoSelected ?: return

        activeJob?.cancel()
        activeJob = viewModelScope.launch {
            _uiState.value = AnalysisUiState.Uploading

            val jobId = repository
                .submit(videoSourceProvider(selected.videoUri), liftType)
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

            JobStatus.COMPLETED -> downloadResult(jobId, state)

            JobStatus.FAILED ->
                _uiState.value = AnalysisUiState.Failed(
                    state.detail ?: "El análisis no pudo completarse.",
                )
        }
    }

    private suspend fun downloadResult(jobId: String, state: AnalysisState) {
        repository.downloadVideo(jobId, resultFileProvider.fileFor(jobId))
            .onSuccess { file ->
                _uiState.value = AnalysisUiState.Completed(jobId, file, state.summary)
            }
            .onFailure { error -> fail(error) }
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