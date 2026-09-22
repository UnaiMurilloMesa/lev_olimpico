package com.tfg.halteroanalyzer.domain

/** Errores que puede producir la comunicación con el servicio de análisis. */
sealed class AnalysisException(message: String, cause: Throwable? = null) :
    Exception(message, cause) {

    class Network(cause: Throwable) :
        AnalysisException("No se pudo conectar con el servidor.", cause)

    class Server(val code: Int, message: String) : AnalysisException(message)

    class Unexpected(cause: Throwable) :
        AnalysisException("Respuesta inesperada del servidor.", cause)

    class Timeout(val jobId: String) :
        AnalysisException("El análisis está tardando más de lo previsto.")
}