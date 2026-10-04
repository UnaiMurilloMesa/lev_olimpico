package com.tfg.halteroanalyzer.data.remote

import com.tfg.halteroanalyzer.data.remote.dto.AnalysisCreatedDto
import com.tfg.halteroanalyzer.data.remote.dto.AnalysisStatusDto
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Streaming

/** Definición de los endpoints del backend de análisis. */
interface AnalysisApi {

    @Multipart
    @POST("api/v1/analyses")
    suspend fun createAnalysis(
        @Part video: MultipartBody.Part,
        @Part("lift_type") liftType: RequestBody,
        @Part("start_seconds") startSeconds: RequestBody,
        @Part("athlete_height_m") athleteHeightM: RequestBody,
    ): AnalysisCreatedDto

    @Streaming
    @GET("api/v1/analyses/{jobId}/velocity-chart")
    suspend fun downloadChart(@Path("jobId") jobId: String): ResponseBody

    @GET("api/v1/analyses/{jobId}")
    suspend fun getStatus(@Path("jobId") jobId: String): AnalysisStatusDto

    @Streaming
    @GET("api/v1/analyses/{jobId}/video")
    suspend fun downloadVideo(@Path("jobId") jobId: String): ResponseBody

    @DELETE("api/v1/analyses/{jobId}")
    suspend fun deleteAnalysis(@Path("jobId") jobId: String): Response<Unit>

    @Streaming
    @GET("api/v1/analyses/{jobId}/phases/{name}")
    suspend fun downloadSnapshot(
        @Path("jobId") jobId: String,
        @Path("name") name: String,
    ): ResponseBody
}