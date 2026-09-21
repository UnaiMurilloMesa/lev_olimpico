package com.tfg.halteroanalyzer.data.remote.dto

import com.tfg.halteroanalyzer.domain.AnalysisState
import com.tfg.halteroanalyzer.domain.AnalysisSummary
import com.tfg.halteroanalyzer.domain.JobStatus

/** Convierte el resumen recibido del backend al modelo de dominio. */
fun AnalysisSummaryDto.toDomain(): AnalysisSummary = AnalysisSummary(
    videoName = videoName,
    processedFrames = processedFrames,
    detectedFrames = detectedFrames,
    detectionRatio = detectionRatio,
    durationSeconds = durationSeconds,
)

/** Convierte el estado recibido del backend al modelo de dominio. */
fun AnalysisStatusDto.toDomain(): AnalysisState = AnalysisState(
    jobId = jobId,
    status = JobStatus.fromApi(status),
    detail = detail,
    summary = result?.toDomain(),
)