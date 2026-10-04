package com.tfg.halteroanalyzer.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ScoreLevelTest {

    @Test
    fun `traduce los niveles conocidos`() {
        assertEquals(ScoreLevel.GOOD, ScoreLevel.fromApi("good"))
        assertEquals(ScoreLevel.FAIR, ScoreLevel.fromApi("fair"))
        assertEquals(ScoreLevel.POOR, ScoreLevel.fromApi("poor"))
    }

    @Test
    fun `un nivel desconocido no rompe la app`() {
        assertEquals(ScoreLevel.UNKNOWN, ScoreLevel.fromApi("nivel_futuro"))
    }

    @Test
    fun `una fase sin criterios no esta evaluada`() {
        val fase = LiftPhase(
            id = "turnover", label = "Recepción", startSeconds = 1.0, endSeconds = 1.3,
            durationSeconds = 0.3, snapshot = null, score = 0.0,
            level = ScoreLevel.UNKNOWN, criteria = emptyList(),
        )

        assertFalse(fase.isScored)
    }

    @Test
    fun `clasifica las puntuaciones con los umbrales del backend`() {
        assertEquals(ScoreLevel.GOOD, ScoreLevel.fromScore(7.0))
        assertEquals(ScoreLevel.FAIR, ScoreLevel.fromScore(6.9))
        assertEquals(ScoreLevel.FAIR, ScoreLevel.fromScore(5.0))
        assertEquals(ScoreLevel.POOR, ScoreLevel.fromScore(4.9))
    }
}