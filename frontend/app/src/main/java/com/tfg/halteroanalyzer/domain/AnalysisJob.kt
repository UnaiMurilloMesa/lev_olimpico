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
)

/** Estado de un análisis en curso o terminado. */
data class AnalysisState(
    val jobId: String,
    val status: JobStatus,
    val detail: String? = null,
    val summary: AnalysisSummary? = null,
)