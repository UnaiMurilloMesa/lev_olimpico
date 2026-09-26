package com.tfg.halteroanalyzer.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** Respuesta del backend al encolar un análisis. */
@Serializable
data class AnalysisCreatedDto(
    @SerialName("job_id") val jobId: String,
    @SerialName("status") val status: String,
    @SerialName("lift_type") val liftType: String,
)

/** Resumen del análisis, disponible solo cuando el trabajo ha terminado. */
@Serializable
data class AnalysisSummaryDto(
    @SerialName("video_name") val videoName: String,
    @SerialName("processed_frames") val processedFrames: Int,
    @SerialName("detected_frames") val detectedFrames: Int,
    @SerialName("detection_ratio") val detectionRatio: Double,
    @SerialName("duration_seconds") val durationSeconds: Double,
    @SerialName("bar_path_deviation") val barPathDeviation: Double,
    @SerialName("bar_path_quality") val barPathQuality: String,
    @SerialName("lift_start_seconds") val liftStartSeconds: Double,
    @SerialName("lift_end_seconds") val liftEndSeconds: Double,
    @SerialName("lift_duration_seconds") val liftDurationSeconds: Double,
    @SerialName("peak_velocity_ms") val peakVelocityMs: Double,
    @SerialName("peak_velocity_time") val peakVelocityTime: Double,
    @SerialName("has_velocity_chart") val hasVelocityChart: Boolean,
)

/** Estado actual de un trabajo de análisis. */
@Serializable
data class AnalysisStatusDto(
    @SerialName("job_id") val jobId: String,
    @SerialName("status") val status: String,
    @SerialName("detail") val detail: String? = null,
    @SerialName("result") val result: AnalysisSummaryDto? = null,
)