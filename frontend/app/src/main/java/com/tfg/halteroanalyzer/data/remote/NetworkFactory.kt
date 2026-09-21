package com.tfg.halteroanalyzer.data.remote

import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import java.util.concurrent.TimeUnit

/** Construcción de los clientes HTTP de la aplicación. */
object NetworkFactory {

    private const val UPLOAD_TIMEOUT_SECONDS = 180L
    private const val READ_TIMEOUT_SECONDS = 60L

    val json: Json = Json {
        ignoreUnknownKeys = true
        explicitNulls = false
    }

    fun createOkHttpClient(enableLogging: Boolean): OkHttpClient =
        OkHttpClient.Builder()
            .writeTimeout(UPLOAD_TIMEOUT_SECONDS, TimeUnit.SECONDS)
            .readTimeout(READ_TIMEOUT_SECONDS, TimeUnit.SECONDS)
            .apply {
                if (enableLogging) {
                    // BASIC y no BODY: con BODY se volcarían al log los bytes del vídeo.
                    addInterceptor(
                        HttpLoggingInterceptor().setLevel(HttpLoggingInterceptor.Level.BASIC)
                    )
                }
            }
            .build()

    fun createAnalysisApi(baseUrl: String, client: OkHttpClient): AnalysisApi =
        Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(AnalysisApi::class.java)
}