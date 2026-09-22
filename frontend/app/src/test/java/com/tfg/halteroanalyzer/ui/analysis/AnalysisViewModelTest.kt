package com.tfg.halteroanalyzer.ui.analysis

import com.tfg.halteroanalyzer.domain.AnalysisException
import com.tfg.halteroanalyzer.domain.AnalysisRepository
import com.tfg.halteroanalyzer.domain.AnalysisState
import com.tfg.halteroanalyzer.domain.AnalysisStatusPoller
import com.tfg.halteroanalyzer.domain.JobStatus
import com.tfg.halteroanalyzer.domain.LiftType
import com.tfg.halteroanalyzer.domain.VideoSource
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.ByteArrayInputStream
import java.io.File
import java.io.InputStream
import kotlin.time.Duration.Companion.milliseconds
import kotlinx.coroutines.ExperimentalCoroutinesApi


@OptIn(ExperimentalCoroutinesApi::class)
class AnalysisViewModelTest {

    @get:Rule
    val tempFolder = TemporaryFolder()

    private val dispatcher = StandardTestDispatcher()
    private val uri = "content://media/external/video/media/42"

    @Before
    fun setUp() = Dispatchers.setMain(dispatcher)

    @After
    fun tearDown() = Dispatchers.resetMain()

    @Test
    fun `al inicio la pantalla esta en reposo`() = runTest(dispatcher) {
        assertTrue(viewModel(FakeRepository()).uiState.value is AnalysisUiState.Idle)
    }

    @Test
    fun `seleccionar un video actualiza el estado`() = runTest(dispatcher) {
        val vm = viewModel(FakeRepository())

        vm.onVideoSelected(uri)

        assertTrue(vm.uiState.value is AnalysisUiState.VideoSelected)
    }

    @Test
    fun `sin video seleccionado no se envia nada`() = runTest(dispatcher) {
        val repository = FakeRepository()
        val vm = viewModel(repository)

        vm.startAnalysis()
        advanceUntilIdle()

        assertEquals(0, repository.submitCalls)
    }

    @Test
    fun `un analisis correcto termina con el video descargado`() = runTest(dispatcher) {
        val repository = FakeRepository(
            states = listOf(JobStatus.PROCESSING, JobStatus.COMPLETED),
        )
        val vm = viewModel(repository)

        vm.onVideoSelected(uri)
        vm.startAnalysis()
        advanceUntilIdle()

        val state = vm.uiState.value
        assertTrue(state is AnalysisUiState.Completed)
        assertTrue((state as AnalysisUiState.Completed).video.exists())
        assertEquals("trabajo-1", state.jobId)
    }

    @Test
    fun `un fallo al subir muestra el mensaje del servidor`() = runTest(dispatcher) {
        val repository = FakeRepository(
            submitResult = Result.failure(AnalysisException.Server(422, "Extensión no admitida.")),
        )
        val vm = viewModel(repository)

        vm.onVideoSelected(uri)
        vm.startAnalysis()
        advanceUntilIdle()

        val state = vm.uiState.value
        assertTrue(state is AnalysisUiState.Failed)
        assertEquals("Extensión no admitida.", (state as AnalysisUiState.Failed).message)
    }

    @Test
    fun `un analisis fallido en el servidor se refleja en la pantalla`() = runTest(dispatcher) {
        val repository = FakeRepository(
            states = listOf(JobStatus.FAILED),
            failureDetail = "Vídeo corrupto",
        )
        val vm = viewModel(repository)

        vm.onVideoSelected(uri)
        vm.startAnalysis()
        advanceUntilIdle()

        assertEquals(
            "Vídeo corrupto",
            (vm.uiState.value as AnalysisUiState.Failed).message,
        )
    }

    @Test
    fun `reiniciar borra el video local y avisa al servidor`() = runTest(dispatcher) {
        val repository = FakeRepository(states = listOf(JobStatus.COMPLETED))
        val vm = viewModel(repository)
        vm.onVideoSelected(uri)
        vm.startAnalysis()
        advanceUntilIdle()
        val descargado = (vm.uiState.value as AnalysisUiState.Completed).video

        vm.reset()
        advanceUntilIdle()

        assertTrue(vm.uiState.value is AnalysisUiState.Idle)
        assertFalse(descargado.exists())
        assertEquals(listOf("trabajo-1"), repository.deleted)
    }

    private fun viewModel(repository: FakeRepository) = AnalysisViewModel(
        repository = repository,
        poller = AnalysisStatusPoller(repository, pollInterval = 10.milliseconds),
        videoSourceProvider = { FakeVideoSource() },
        resultFileProvider = { jobId -> tempFolder.newFile("$jobId.mp4") },
    )

    private class FakeVideoSource : VideoSource {
        override val fileName = "snatch.mp4"
        override val mimeType = "video/mp4"
        override val sizeBytes = 10L
        override fun openStream(): InputStream = ByteArrayInputStream(ByteArray(10))
    }

    private class FakeRepository(
        private val submitResult: Result<String> = Result.success("trabajo-1"),
        private val states: List<JobStatus> = listOf(JobStatus.COMPLETED),
        private val failureDetail: String? = null,
    ) : AnalysisRepository {

        var submitCalls = 0
            private set
        val deleted = mutableListOf<String>()
        private var stateIndex = 0

        override suspend fun submit(video: VideoSource, liftType: LiftType): Result<String> {
            submitCalls++
            return submitResult
        }

        override suspend fun getState(jobId: String): Result<AnalysisState> {
            val status = states[stateIndex.coerceAtMost(states.lastIndex)]
            stateIndex++
            return Result.success(
                AnalysisState(jobId = jobId, status = status, detail = failureDetail),
            )
        }

        override suspend fun downloadVideo(jobId: String, destination: File): Result<File> {
            destination.writeBytes(byteArrayOf(1, 2, 3))
            return Result.success(destination)
        }

        override suspend fun delete(jobId: String): Result<Unit> {
            deleted.add(jobId)
            return Result.success(Unit)
        }
    }
}