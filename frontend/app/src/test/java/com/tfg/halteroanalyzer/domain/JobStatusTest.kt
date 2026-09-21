package com.tfg.halteroanalyzer.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class JobStatusTest {

    @Test
    fun `traduce los estados conocidos del backend`() {
        assertEquals(JobStatus.PENDING, JobStatus.fromApi("pending"))
        assertEquals(JobStatus.PROCESSING, JobStatus.fromApi("processing"))
        assertEquals(JobStatus.COMPLETED, JobStatus.fromApi("completed"))
        assertEquals(JobStatus.FAILED, JobStatus.fromApi("failed"))
    }

    @Test
    fun `un estado desconocido se considera pendiente`() {
        assertEquals(JobStatus.PENDING, JobStatus.fromApi("estado_inventado"))
    }

    @Test
    fun `identifica los estados finales`() {
        assertTrue(JobStatus.COMPLETED.isTerminal)
        assertTrue(JobStatus.FAILED.isTerminal)
        assertFalse(JobStatus.PENDING.isTerminal)
        assertFalse(JobStatus.PROCESSING.isTerminal)
    }
}