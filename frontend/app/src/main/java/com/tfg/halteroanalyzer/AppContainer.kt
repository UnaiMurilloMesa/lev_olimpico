package com.tfg.halteroanalyzer

import android.content.Context
import android.net.Uri
import com.tfg.halteroanalyzer.data.local.ContentResolverVideoSource
import com.tfg.halteroanalyzer.data.local.MediaStoreVideoGallery
import com.tfg.halteroanalyzer.data.remote.NetworkFactory
import com.tfg.halteroanalyzer.data.repository.RemoteAnalysisRepository
import com.tfg.halteroanalyzer.domain.AnalysisRepository
import com.tfg.halteroanalyzer.domain.VideoGallery
import com.tfg.halteroanalyzer.domain.VideoSource

/** Punto único donde se construyen y conectan las dependencias de la aplicación. */
class AppContainer(private val context: Context) {

    val analysisRepository: AnalysisRepository by lazy {
        val client = NetworkFactory.createOkHttpClient(enableLogging = BuildConfig.DEBUG)
        RemoteAnalysisRepository(NetworkFactory.createAnalysisApi(BuildConfig.BASE_URL, client))
    }

    val videoGallery: VideoGallery by lazy { MediaStoreVideoGallery(context) }

    fun videoSourceFor(uri: String): VideoSource =
        ContentResolverVideoSource.from(context.contentResolver, Uri.parse(uri))
}