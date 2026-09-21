package com.tfg.halteroanalyzer.data.remote

import com.tfg.halteroanalyzer.domain.VideoSource
import okhttp3.MediaType
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.RequestBody
import okio.BufferedSink
import okio.source

/** Cuerpo de petición que transmite el vídeo sin cargarlo entero en memoria. */
class VideoRequestBody(private val video: VideoSource) : RequestBody() {

    override fun contentType(): MediaType? = video.mimeType.toMediaTypeOrNull()

    override fun contentLength(): Long = video.sizeBytes

    override fun writeTo(sink: BufferedSink) {
        video.openStream().source().use { source -> sink.writeAll(source) }
    }
}