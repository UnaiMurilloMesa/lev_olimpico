package com.tfg.halteroanalyzer.data.local

import org.junit.Assert.assertEquals
import org.junit.Test

class VideoFileNamesTest {

    @Test
    fun `conserva un nombre que ya tiene extension admitida`() {
        assertEquals("snatch.mp4", ensureVideoExtension("snatch.mp4", "video/mp4"))
    }

    @Test
    fun `respeta la extension aunque venga en mayusculas`() {
        assertEquals("SNATCH.MOV", ensureVideoExtension("SNATCH.MOV", "video/quicktime"))
    }

    @Test
    fun `anade la extension segun el tipo mime si falta`() {
        assertEquals("1000012345.mov", ensureVideoExtension("1000012345", "video/quicktime"))
    }

    @Test
    fun `usa mp4 si el tipo mime es desconocido`() {
        assertEquals("clip.mp4", ensureVideoExtension("clip", "video/desconocido"))
    }

    @Test
    fun `genera un nombre si no hay ninguno`() {
        assertEquals("video.mp4", ensureVideoExtension(null, null))
    }
}