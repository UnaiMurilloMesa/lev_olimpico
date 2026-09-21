package com.tfg.halteroanalyzer.data.repository

import com.tfg.halteroanalyzer.data.remote.NetworkFactory
import com.tfg.halteroanalyzer.domain.AnalysisException
import com.tfg.halteroanalyzer.domain.JobStatus
import com.tfg.halteroanalyzer.domain.LiftType
import com.tfg.halteroanalyzer.domain.VideoSource
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.runTest
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.SocketPolicy
import org.junit.After
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.InputStream

class RemoteAnalysisRepositoryTest {

    @get:Rule
    val tempFolder = TemporaryFolder()

    private lateinit var server: MockWebServer
    private lateinit var repository: RemoteAnalysisRepository

    @Before
    fun setUp() {
        server = MockWebServer().apply { start() }
        val api = NetworkFactory.createAnalysisApi(server.url("/").toString(), OkHttpClient())
        repository = RemoteAnalysisRepository(api, Dispatchers.Unconfined)
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    @Test
    fun `al subir un video envia un multipart y devuelve el identificador`() = runTest {
        server.enqueue(json(202, """{"job_id":"abc","status":"pending","lift_type":"snatch"}"""))

        val result = repository.submit(FakeVideo(), LiftType.SNATCH)

        assertEquals("abc", result.getOrThrow())
        val request = server.takeRequest()
        assertEquals("POST", request.method)
        assertEquals("/api/v1/analyses", request.path)
        assertTrue(request.getHeader("Content-Type")!!.startsWith("multipart/form-data"))
        assertTrue(request.body.readUtf8().contains("name=\"lift_type\""))
    }

    @Test
    fun `un rechazo del servidor expone el mensaje de detalle`() = runTest {
        server.enqueue(json(422, """{"detail":"Extensión no admitida: '.pdf'."}"""))

        val error = repository.submit(FakeVideo(), LiftType.SNATCH).exceptionOrNull()

        assertTrue(error is AnalysisException.Server)
        assertEquals(422, (error as AnalysisException.Server).code)
        assertEquals("Extensión no admitida: '.pdf'.", error.message)
    }

    @Test
    fun `interpreta un analisis completado con su resumen`() = runTest {
        server.enqueue(
            json(
                200,
                """
                {"job_id":"abc","status":"completed","result":{
                  "video_name":"analysis.mp4","processed_frames":120,
                  "detected_frames":118,"detection_ratio":0.98,"duration_seconds":4.0}}
                """.trimIndent(),
            ),
        )

        val state = repository.getState("abc").getOrThrow()

        assertEquals(JobStatus.COMPLETED, state.status)
        assertEquals(120, state.summary!!.processedFrames)
    }

    @Test
    fun `ignora los campos que todavia no conoce`() = runTest {
        server.enqueue(json(200, """{"job_id":"abc","status":"processing","campo_nuevo":42}"""))

        val state = repository.getState("abc").getOrThrow()

        assertEquals(JobStatus.PROCESSING, state.status)
        assertNull(state.summary)
    }

    @Test
    fun `descarga el video en el fichero indicado`() = runTest {
        val contenido = byteArrayOf(1, 2, 3, 4, 5)
        server.enqueue(MockResponse().setBody(okio.Buffer().write(contenido)))
        val destino = tempFolder.newFile("resultado.mp4")

        repository.downloadVideo("abc", destino).getOrThrow()

        assertArrayEquals(contenido, destino.readBytes())
    }

    @Test
    fun `eliminar un analisis envia un DELETE`() = runTest {
        server.enqueue(MockResponse().setResponseCode(204))

        repository.delete("abc").getOrThrow()

        val request = server.takeRequest()
        assertEquals("DELETE", request.method)
        assertEquals("/api/v1/analyses/abc", request.path)
    }

    @Test
    fun `un fallo de conexion se traduce en error de red`() = runTest {
        server.enqueue(MockResponse().setSocketPolicy(SocketPolicy.DISCONNECT_AT_START))

        val error = repository.getState("abc").exceptionOrNull()

        assertTrue(error is AnalysisException.Network)
    }

    private fun json(code: Int, body: String) =
        MockResponse()
            .setResponseCode(code)
            .setHeader("Content-Type", "application/json")
            .setBody(body)

    private class FakeVideo : VideoSource {
        private val bytes = ByteArray(64)
        override val fileName = "snatch.mp4"
        override val mimeType = "video/mp4"
        override val sizeBytes = bytes.size.toLong()
        override fun openStream(): InputStream = bytes.inputStream()
    }
}