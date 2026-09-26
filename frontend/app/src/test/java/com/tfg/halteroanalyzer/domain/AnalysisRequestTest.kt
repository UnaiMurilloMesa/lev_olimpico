package com.tfg.halteroanalyzer.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AnalysisRequestTest {

    @Test
    fun `convierte los centimetros a metros`() {
        assertEquals(1.78, AnalysisRequest(heightCm = 178).heightMeters, 0.001)
    }

    @Test
    fun `una peticion con valores por defecto es valida`() {
        assertTrue(AnalysisRequest().isValid)
    }

    @Test
    fun `rechaza una estatura por debajo del minimo`() {
        assertFalse(AnalysisRequest(heightCm = MIN_HEIGHT_CM - 1).isValid)
    }

    @Test
    fun `rechaza una estatura por encima del maximo`() {
        assertFalse(AnalysisRequest(heightCm = MAX_HEIGHT_CM + 1).isValid)
    }

    @Test
    fun `acepta las estaturas en los limites`() {
        assertTrue(AnalysisRequest(heightCm = MIN_HEIGHT_CM).isValid)
        assertTrue(AnalysisRequest(heightCm = MAX_HEIGHT_CM).isValid)
    }

    @Test
    fun `rechaza un instante de inicio negativo`() {
        assertFalse(AnalysisRequest(startSeconds = -1.0).isValid)
    }
}