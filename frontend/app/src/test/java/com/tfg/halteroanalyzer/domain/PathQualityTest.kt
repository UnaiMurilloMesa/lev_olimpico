package com.tfg.halteroanalyzer.domain

import org.junit.Assert.assertEquals
import org.junit.Test

class PathQualityTest {

    @Test
    fun `traduce las valoraciones conocidas`() {
        assertEquals(PathQuality.EXCELLENT, PathQuality.fromApi("excellent"))
        assertEquals(PathQuality.ACCEPTABLE, PathQuality.fromApi("acceptable"))
        assertEquals(PathQuality.POOR, PathQuality.fromApi("poor"))
    }

    @Test
    fun `una valoracion desconocida no rompe la app`() {
        assertEquals(PathQuality.UNKNOWN, PathQuality.fromApi("valoracion_futura"))
    }
}