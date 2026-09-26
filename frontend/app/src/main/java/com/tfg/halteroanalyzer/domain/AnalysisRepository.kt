package com.tfg.halteroanalyzer.domain

import java.io.File

/** Operaciones disponibles sobre el servicio de análisis. */
interface AnalysisRepository {
    suspend fun submit(video: VideoSource, request: AnalysisRequest): Result<String>
    suspend fun getState(jobId: String): Result<AnalysisState>
    suspend fun downloadVideo(jobId: String, destination: File): Result<File>
    suspend fun downloadChart(jobId: String, destination: File): Result<File>
    suspend fun delete(jobId: String): Result<Unit>
}