package com.tfg.halteroanalyzer.domain

import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.io.IOException
import kotlin.time.Duration.Companion.seconds
import kotlinx.coroutines.ExperimentalCoroutinesApi

@OptIn(ExperimentalCoroutinesApi::class)
class AnalysisStatusPollerTest {

    private val jobId = "abc"

    @Test
    fun `emite los estados hasta que el analisis se completa`() = runTest {
        val repository = FakeRepository(
            listOf(state(JobStatus.PENDING), state(JobStatus.PROCESSING), state(JobStatus.COMPLETED)),
        )
        val poller = AnalysisStatusPoller(repository, pollInterval = 2.seconds)

        val emitted = poller.poll(jobId).toList()

        assertEquals(
            listOf(JobStatus.PENDING, JobStatus.PROCESSING, JobStatus.COMPLETED),
            emitted.map { it.status },
        )
    }

    @Test
    fun `deja de consultar cuando el analisis falla`() = runTest {
        val repository = FakeRepository(listOf(state(JobStatus.PROCESSING), state(JobStatus.FAILED)))
        val poller = AnalysisStatusPoller(repository, pollInterval = 2.seconds)

        val emitted = poller.poll(jobId).toList()

        assertEquals(2, emitted.size)
        assertEquals(2, repository.calls)
    }

    @Test
    fun `la primera consulta no espera al intervalo`() = runTest {
        val repository = FakeRepository(listOf(state(JobStatus.COMPLETED)))
        val poller = AnalysisStatusPoller(repository, pollInterval = 30.seconds)

        poller.poll(jobId).toList()

        assertEquals(0, testScheduler.currentTime)
    }

    @Test
    fun `espera el intervalo entre consultas sucesivas`() = runTest {
        val repository =
            FakeRepository(listOf(state(JobStatus.PROCESSING), state(JobStatus.COMPLETED)))
        val poller = AnalysisStatusPoller(repository, pollInterval = 5.seconds)

        poller.poll(jobId).toList()

        assertEquals(5_000, testScheduler.currentTime)
    }

    @Test
    fun `agota los intentos si el analisis nunca termina`() = runTest {
        val repository = FakeRepository(listOf(state(JobStatus.PROCESSING)))
        val poller = AnalysisStatusPoller(repository, pollInterval = 1.seconds, maxAttempts = 4)

        val error = runCatching { poller.poll(jobId).toList() }.exceptionOrNull()

        assertTrue(error is AnalysisException.Timeout)
        assertEquals(4, repository.calls)
    }

    @Test
    fun `propaga los errores de red`() = runTest {
        val repository =
            FakeRepository(listOf(Result.failure(AnalysisException.Network(IOException()))))
        val poller = AnalysisStatusPoller(repository, pollInterval = 1.seconds)

        val error = runCatching { poller.poll(jobId).toList() }.exceptionOrNull()

        assertTrue(error is AnalysisException.Network)
    }

    private fun state(status: JobStatus) =
        Result.success(AnalysisState(jobId = jobId, status = status))

    /** Repositorio que devuelve respuestas predefinidas; repite la última al agotarlas. */
    private class FakeRepository(
        private val responses: List<Result<AnalysisState>>,
    ) : AnalysisRepository {

        var calls = 0
            private set

        override suspend fun getState(jobId: String): Result<AnalysisState> {
            val response = responses[calls.coerceAtMost(responses.lastIndex)]
            calls++
            return response
        }

        override suspend fun submit(video: VideoSource, request: AnalysisRequest): Result<String> =
            throw NotImplementedError()

        override suspend fun downloadVideo(jobId: String, destination: File): Result<File> =
            throw NotImplementedError()

        override suspend fun downloadChart(jobId: String, destination: File): Result<File> =
            throw NotImplementedError()

        override suspend fun delete(jobId: String): Result<Unit> = throw NotImplementedError()

        override suspend fun downloadSnapshot(
            jobId: String,
            name: String,
            destination: File,
        ): Result<File> = throw NotImplementedError()
    }
}