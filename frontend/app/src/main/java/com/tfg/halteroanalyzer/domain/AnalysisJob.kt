package com.tfg.halteroanalyzer.domain

/** Estados posibles de un análisis, equivalentes a los del backend. */
enum class JobStatus {
    PENDING,
    PROCESSING,
    COMPLETED,
    FAILED;

    val isTerminal: Boolean
        get() = this == COMPLETED || this == FAILED

    companion object {
        /** Traduce el valor recibido del backend, sin fallar ante valores desconocidos. */
        fun fromApi(value: String): JobStatus =
            entries.firstOrNull { it.name.equals(value, ignoreCase = true) } ?: PENDING
    }
}

enum class PathQuality {
    EXCELLENT,
    ACCEPTABLE,
    POOR,
    UNKNOWN;

    companion object {
        /** Traduce el valor recibido del backend sin fallar ante valores nuevos. */
        fun fromApi(value: String): PathQuality =
            entries.firstOrNull { it.name.equals(value, ignoreCase = true) } ?: UNKNOWN
    }
}

/** Valoración cualitativa de una puntuación. */
enum class ScoreLevel {
    GOOD,
    FAIR,
    POOR,
    UNKNOWN;

    companion object {
        private const val GOOD_THRESHOLD = 7.0
        private const val FAIR_THRESHOLD = 5.0

        /** Traduce el valor recibido del backend sin fallar ante valores nuevos. */
        fun fromApi(value: String): ScoreLevel =
            entries.firstOrNull { it.name.equals(value, ignoreCase = true) } ?: UNKNOWN

        /** Clasifica una puntuación numérica, con los mismos umbrales del backend. */
        fun fromScore(score: Double): ScoreLevel = when {
            score >= GOOD_THRESHOLD -> GOOD
            score >= FAIR_THRESHOLD -> FAIR
            else -> POOR
        }
    }
}

/** Resumen de un análisis completado. */
data class AnalysisSummary(
    val videoName: String,
    val processedFrames: Int,
    val detectedFrames: Int,
    val detectionRatio: Double,
    val durationSeconds: Double,
    val barPathDeviation: Double,
    val barPathQuality: PathQuality,
    val liftStartSeconds: Double,
    val liftEndSeconds: Double,
    val liftDurationSeconds: Double,
    val peakVelocityMs: Double,
    val peakVelocityTime: Double,
    val hasVelocityChart: Boolean,
    val interpolatedFrames: Int,
    val overallScore: Double,
    val phases: List<LiftPhase>,
)

/** Estado de un análisis en curso o terminado. */
data class AnalysisState(
    val jobId: String,
    val status: JobStatus,
    val detail: String? = null,
    val summary: AnalysisSummary? = null,
)

/** Criterio evaluado dentro de una fase. */
data class Criterion(
    val criterion: String,
    val score: Double,
    val level: ScoreLevel,
    val measuredValue: Double,
    val explanation: String,
)

/** Fase del levantamiento con su valoración. */
data class LiftPhase(
    val id: String,
    val label: String,
    val startSeconds: Double,
    val endSeconds: Double,
    val durationSeconds: Double,
    val snapshot: String?,
    val score: Double,
    val level: ScoreLevel,
    val criteria: List<Criterion>,
) {
    /** Indica si la fase llegó a evaluarse. */
    val isScored: Boolean
        get() = criteria.isNotEmpty()
}