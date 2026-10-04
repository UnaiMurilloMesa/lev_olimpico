package com.tfg.halteroanalyzer.data.remote.dto

import com.tfg.halteroanalyzer.domain.AnalysisState
import com.tfg.halteroanalyzer.domain.AnalysisSummary
import com.tfg.halteroanalyzer.domain.Criterion
import com.tfg.halteroanalyzer.domain.JobStatus
import com.tfg.halteroanalyzer.domain.LiftPhase
import com.tfg.halteroanalyzer.domain.PathQuality
import com.tfg.halteroanalyzer.domain.ScoreLevel

/** Convierte el resumen recibido del backend al modelo de dominio. */
fun AnalysisSummaryDto.toDomain(): AnalysisSummary = AnalysisSummary(
    videoName = videoName,
    processedFrames = processedFrames,
    detectedFrames = detectedFrames,
    detectionRatio = detectionRatio,
    durationSeconds = durationSeconds,
    barPathDeviation = barPathDeviation,
    barPathQuality = PathQuality.fromApi(barPathQuality),
    liftStartSeconds = liftStartSeconds,
    liftEndSeconds = liftEndSeconds,
    liftDurationSeconds = liftDurationSeconds,
    peakVelocityMs = peakVelocityMs,
    peakVelocityTime = peakVelocityTime,
    hasVelocityChart = hasVelocityChart,
    interpolatedFrames = interpolatedFrames,
    overallScore = overallScore,
    phases = phases.map { it.toDomain() },
)

/** Convierte el estado recibido del backend al modelo de dominio. */
fun AnalysisStatusDto.toDomain(): AnalysisState = AnalysisState(
    jobId = jobId,
    status = JobStatus.fromApi(status),
    detail = detail,
    summary = result?.toDomain(),
)

/** Convierte un criterio recibido del backend al modelo de dominio. */
fun CriterionDto.toDomain(): Criterion = Criterion(
    criterion = criterion,
    score = score,
    level = ScoreLevel.fromApi(level),
    measuredValue = measuredValue,
    explanation = explanation,
)

/** Convierte una fase recibida del backend al modelo de dominio. */
fun PhaseDto.toDomain(): LiftPhase = LiftPhase(
    id = phase,
    label = label,
    startSeconds = startSeconds,
    endSeconds = endSeconds,
    durationSeconds = durationSeconds,
    snapshot = snapshot,
    score = score,
    level = ScoreLevel.fromApi(level),
    criteria = criteria.map { it.toDomain() },
)