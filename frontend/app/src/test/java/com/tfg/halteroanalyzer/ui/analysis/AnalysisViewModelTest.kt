package com.tfg.halteroanalyzer.ui.analysis

import com.tfg.halteroanalyzer.domain.AnalysisException
import com.tfg.halteroanalyzer.domain.AnalysisRepository
import com.tfg.halteroanalyzer.domain.AnalysisRequest
import com.tfg.halteroanalyzer.domain.AnalysisState
import com.tfg.halteroanalyzer.domain.AnalysisStatusPoller
import com.tfg.halteroanalyzer.domain.AnalysisSummary
import com.tfg.halteroanalyzer.domain.JobStatus
import com.tfg.halteroanalyzer.domain.PathQuality
import com.tfg.halteroanalyzer.domain.VideoSource
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.ByteArrayInputStream
import java.io.File
import java.io.InputStream
import kotlin.time.Duration.Companion.milliseconds

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

    // --- Estado inicial y preparación ---

    @Test
    fun `al inicio la pantalla esta en reposo`() = runTest(dispatcher) {
        assertTrue(viewModel(FakeRepository()).uiState.value is AnalysisUiState.Idle)
    }

    @Test
    fun `seleccionar un video pasa a la pantalla de preparacion`() = runTest(dispatcher) {
        val vm = viewModel(FakeRepository())

        vm.onVideoSelected(uri)

        val state = vm.uiState.value
        assertTrue(state is AnalysisUiState.Preparing)
        assertEquals(uri, (state as AnalysisUiState.Preparing).videoUri)
    }

    @Test
    fun `registra la duracion del video`() = runTest(dispatcher) {
        val vm = viewModel(FakeRepository())
        vm.onVideoSelected(uri)

        vm.onVideoDurationKnown(7.5)

        val state = vm.uiState.value as AnalysisUiState.Preparing
        assertEquals(7.5, state.videoDurationSeconds, 0.001)
    }

    @Test
    fun `un video sin duracion conocida no permite analizar`() = runTest(dispatcher) {
        val vm = viewModel(FakeRepository())

        vm.onVideoSelected(uri)

        assertFalse((vm.uiState.value as AnalysisUiState.Preparing).canStart)
    }

    // --- Validación previa al envío ---

    @Test
    fun `sin video seleccionado no se envia nada`() = runTest(dispatcher) {
        val repository = FakeRepository()
        val vm = viewModel(repository)

        vm.startAnalysis()
        advanceUntilIdle()

        assertEquals(0, repository.submitCalls)
    }

    @Test
    fun `no permite analizar con una estatura invalida`() = runTest(dispatcher) {
        val repository = FakeRepository()
        val vm = viewModel(repository)
        prepare(vm)
        vm.onHeightChanged(300)

        vm.startAnalysis()
        advanceUntilIdle()

        assertEquals(0, repository.submitCalls)
    }

    @Test
    fun `no permite analizar si el inicio supera la duracion`() = runTest(dispatcher) {
        val repository = FakeRepository()
        val vm = viewModel(repository)
        prepare(vm, duration = 3.0)
        vm.onStartSecondsChanged(10.0)

        vm.startAnalysis()
        advanceUntilIdle()

        assertEquals(0, repository.submitCalls)
    }

    // --- Envío y seguimiento ---

    @Test
    fun `envia el instante y la estatura elegidos`() = runTest(dispatcher) {
        val repository = FakeRepository()
        val vm = viewModel(repository)
        prepare(vm)
        vm.onStartSecondsChanged(1.5)
        vm.onHeightChanged(182)

        vm.startAnalysis()
        advanceUntilIdle()

        assertEquals(1.5, repository.lastRequest!!.startSeconds, 0.001)
        assertEquals(182, repository.lastRequest!!.heightCm)
    }

    @Test
    fun `un analisis correcto termina con el video descargado`() = runTest(dispatcher) {
        val repository = FakeRepository(
            states = listOf(JobStatus.PROCESSING, JobStatus.COMPLETED),
        )
        val vm = viewModel(repository)
        prepare(vm)

        vm.startAnalysis()
        advanceUntilIdle()

        val state = vm.uiState.value
        assertTrue(state is AnalysisUiState.Completed)
        assertTrue((state as AnalysisUiState.Completed).video.exists())
        assertEquals("trabajo-1", state.jobId)
    }

    @Test
    fun `expone el resumen del analisis`() = runTest(dispatcher) {
        val vm = viewModel(FakeRepository())
        prepare(vm)

        vm.startAnalysis()
        advanceUntilIdle()

        val summary = (vm.uiState.value as AnalysisUiState.Completed).summary
        assertEquals(1.8, summary!!.peakVelocityMs, 0.001)
        assertEquals(PathQuality.ACCEPTABLE, summary.barPathQuality)
    }

    @Test
    fun `descarga la grafica cuando el analisis la incluye`() = runTest(dispatcher) {
        val vm = viewModel(FakeRepository(hasChart = true))
        prepare(vm)

        vm.startAnalysis()
        advanceUntilIdle()

        val state = vm.uiState.value as AnalysisUiState.Completed
        assertTrue(state.chart!!.exists())
    }

    @Test
    fun `no descarga grafica si el analisis no la genero`() = runTest(dispatcher) {
        val vm = viewModel(FakeRepository(hasChart = false))
        prepare(vm)

        vm.startAnalysis()
        advanceUntilIdle()

        assertNull((vm.uiState.value as AnalysisUiState.Completed).chart)
    }

    // --- Errores ---

    @Test
    fun `un fallo al subir muestra el mensaje del servidor`() = runTest(dispatcher) {
        val repository = FakeRepository(
            submitResult = Result.failure(AnalysisException.Server(422, "Extensión no admitida.")),
        )
        val vm = viewModel(repository)
        prepare(vm)

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
        prepare(vm)

        vm.startAnalysis()
        advanceUntilIdle()

        assertEquals("Vídeo corrupto", (vm.uiState.value as AnalysisUiState.Failed).message)
    }

    // --- Reinicio ---

    @Test
    fun `reiniciar borra los ficheros locales y avisa al servidor`() = runTest(dispatcher) {
        val repository = FakeRepository()
        val vm = viewModel(repository)
        prepare(vm)
        vm.startAnalysis()
        advanceUntilIdle()
        val completado = vm.uiState.value as AnalysisUiState.Completed

        vm.reset()
        advanceUntilIdle()

        assertTrue(vm.uiState.value is AnalysisUiState.Idle)
        assertFalse(completado.video.exists())
        assertFalse(completado.chart!!.exists())
        assertEquals(listOf("trabajo-1"), repository.deleted)
    }

    // --- Utilidades ---

    /** Deja el ViewModel listo para lanzar un análisis. */
    private fun prepare(vm: AnalysisViewModel, duration: Double = 10.0) {
        vm.onVideoSelected(uri)
        vm.onVideoDurationKnown(duration)
    }

    private fun viewModel(repository: FakeRepository) = AnalysisViewModel(
        repository = repository,
        poller = AnalysisStatusPoller(repository, pollInterval = 10.milliseconds),
        videoSourceProvider = { FakeVideoSource() },
        resultFileProvider = object : ResultFileProvider {
            override fun videoFor(jobId: String): File = tempFolder.newFile("$jobId.mp4")
            override fun chartFor(jobId: String): File = tempFolder.newFile("$jobId.png")
        },
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
        private val hasChart: Boolean = true,
    ) : AnalysisRepository {

        var submitCalls = 0
            private set
        var lastRequest: AnalysisRequest? = null
            private set
        val deleted = mutableListOf<String>()
        private var stateIndex = 0

        override suspend fun submit(
            video: VideoSource,
            request: AnalysisRequest,
        ): Result<String> {
            submitCalls++
            lastRequest = request
            return submitResult
        }

        override suspend fun getState(jobId: String): Result<AnalysisState> {
            val status = states[stateIndex.coerceAtMost(states.lastIndex)]
            stateIndex++
            return Result.success(
                AnalysisState(
                    jobId = jobId,
                    status = status,
                    detail = failureDetail,
                    summary = if (status == JobStatus.COMPLETED) summary() else null,
                ),
            )
        }

        override suspend fun downloadVideo(jobId: String, destination: File): Result<File> {
            destination.writeBytes(byteArrayOf(1, 2, 3))
            return Result.success(destination)
        }

        override suspend fun downloadChart(jobId: String, destination: File): Result<File> {
            destination.writeBytes(byteArrayOf(4, 5))
            return Result.success(destination)
        }

        override suspend fun delete(jobId: String): Result<Unit> {
            deleted.add(jobId)
            return Result.success(Unit)
        }

        private fun summary() = AnalysisSummary(
            videoName = "analysis.mp4",
            processedFrames = 120,
            detectedFrames = 118,
            detectionRatio = 0.98,
            durationSeconds = 4.0,
            barPathDeviation = 0.12,
            barPathQuality = PathQuality.ACCEPTABLE,
            liftStartSeconds = 1.0,
            liftEndSeconds = 3.5,
            liftDurationSeconds = 2.5,
            peakVelocityMs = 1.8,
            peakVelocityTime = 0.6,
            hasVelocityChart = hasChart,
        )
    }
}