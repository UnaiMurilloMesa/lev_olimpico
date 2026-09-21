package com.tfg.halteroanalyzer.data.repository

import com.tfg.halteroanalyzer.data.remote.AnalysisApi
import com.tfg.halteroanalyzer.data.remote.NetworkFactory
import com.tfg.halteroanalyzer.data.remote.VideoRequestBody
import com.tfg.halteroanalyzer.data.remote.dto.toDomain
import com.tfg.halteroanalyzer.domain.AnalysisException
import com.tfg.halteroanalyzer.domain.AnalysisRepository
import com.tfg.halteroanalyzer.domain.AnalysisState
import com.tfg.halteroanalyzer.domain.LiftType
import com.tfg.halteroanalyzer.domain.VideoSource
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.HttpException
import java.io.File
import java.io.IOException

/** Repositorio de análisis respaldado por el backend remoto. */
class RemoteAnalysisRepository(
    private val api: AnalysisApi,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO,
) : AnalysisRepository {

    override suspend fun submit(video: VideoSource, liftType: LiftType): Result<String> =
        safeCall {
            val videoPart = MultipartBody.Part.createFormData(
                VIDEO_FIELD, video.fileName, VideoRequestBody(video),
            )
            val liftPart = liftType.apiValue.toRequestBody(TEXT_PLAIN)
            api.createAnalysis(videoPart, liftPart).jobId
        }

    override suspend fun getState(jobId: String): Result<AnalysisState> =
        safeCall { api.getStatus(jobId).toDomain() }

    override suspend fun downloadVideo(jobId: String, destination: File): Result<File> =
        safeCall {
            api.downloadVideo(jobId).use { body ->
                destination.outputStream().use { output -> body.byteStream().copyTo(output) }
            }
            destination
        }

    override suspend fun delete(jobId: String): Result<Unit> =
        safeCall {
            val response = api.deleteAnalysis(jobId)
            if (!response.isSuccessful) throw HttpException(response)
        }

    private suspend fun <T> safeCall(block: suspend () -> T): Result<T> =
        withContext(ioDispatcher) {
            try {
                Result.success(block())
            } catch (error: CancellationException) {
                throw error
            } catch (error: HttpException) {
                Result.failure(error.toAnalysisException())
            } catch (error: IOException) {
                Result.failure(AnalysisException.Network(error))
            } catch (error: SerializationException) {
                Result.failure(AnalysisException.Unexpected(error))
            }
        }

    private fun HttpException.toAnalysisException(): AnalysisException.Server {
        val detail = response()?.errorBody()?.string()?.let(::extractDetail)
        return AnalysisException.Server(
            code = code(),
            message = detail ?: "El servidor respondió con el código ${code()}.",
        )
    }

    private companion object {
        const val VIDEO_FIELD = "video"
        val TEXT_PLAIN = "text/plain".toMediaType()

        /** Extrae el campo `detail` de un error de FastAPI, si es un texto. */
        fun extractDetail(body: String): String? = runCatching {
            NetworkFactory.json.parseToJsonElement(body)
                .jsonObject["detail"]?.jsonPrimitive?.contentOrNull
        }.getOrNull()
    }
}