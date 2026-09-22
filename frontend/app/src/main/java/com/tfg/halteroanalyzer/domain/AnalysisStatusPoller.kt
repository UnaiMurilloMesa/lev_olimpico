package com.tfg.halteroanalyzer.domain

import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlin.time.Duration
import kotlin.time.Duration.Companion.seconds

/** Consulta periódicamente el estado de un análisis hasta que termina. */
class AnalysisStatusPoller(
    private val repository: AnalysisRepository,
    private val pollInterval: Duration = DEFAULT_INTERVAL,
    private val maxAttempts: Int = DEFAULT_MAX_ATTEMPTS,
) {

    /**
     * Emite el estado del trabajo hasta alcanzar uno final.
     *
     * El flujo termina al completarse o fallar el análisis, y lanza
     * [AnalysisException.Timeout] si se agotan los intentos.
     */
    fun poll(jobId: String): Flow<AnalysisState> = flow {
        repeat(maxAttempts) { attempt ->
            if (attempt > 0) delay(pollInterval)

            val state = repository.getState(jobId).getOrElse { error -> throw error }
            emit(state)
            if (state.status.isTerminal) return@flow
        }
        throw AnalysisException.Timeout(jobId)
    }

    companion object {
        val DEFAULT_INTERVAL: Duration = 2.seconds

        /** Con el intervalo por defecto, equivale a unos diez minutos de espera. */
        const val DEFAULT_MAX_ATTEMPTS = 300
    }
}