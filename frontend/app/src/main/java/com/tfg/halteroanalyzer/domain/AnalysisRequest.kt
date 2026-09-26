package com.tfg.halteroanalyzer.domain

/** Límites admitidos para la estatura del levantador, en centímetros. */
const val MIN_HEIGHT_CM = 120
const val MAX_HEIGHT_CM = 230
const val DEFAULT_HEIGHT_CM = 175

/** Datos que el usuario aporta antes de lanzar un análisis. */
data class AnalysisRequest(
    val liftType: LiftType = LiftType.SNATCH,
    val startSeconds: Double = 0.0,
    val heightCm: Int = DEFAULT_HEIGHT_CM,
) {
    /** Estatura en metros, que es la unidad que espera el backend. */
    val heightMeters: Double
        get() = heightCm / 100.0

    /** Indica si los datos son válidos para enviarse al servidor. */
    val isValid: Boolean
        get() = startSeconds >= 0 && heightCm in MIN_HEIGHT_CM..MAX_HEIGHT_CM
}