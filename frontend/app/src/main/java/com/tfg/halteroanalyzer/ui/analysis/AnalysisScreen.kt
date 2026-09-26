package com.tfg.halteroanalyzer.ui.analysis

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import android.graphics.BitmapFactory
import com.tfg.halteroanalyzer.domain.AnalysisSummary
import com.tfg.halteroanalyzer.domain.PathQuality
import java.io.File

/** Pantalla principal: selección, preparación, progreso y resultado del análisis. */
@Composable
fun AnalysisScreen(viewModel: AnalysisViewModel, modifier: Modifier = Modifier) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    val picker = rememberLauncherForActivityResult(
        ActivityResultContracts.PickVisualMedia(),
    ) { uri -> uri?.let { viewModel.onVideoSelected(it.toString()) } }

    val onPickVideo: () -> Unit = {
        picker.launch(
            PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.VideoOnly),
        )
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        when (val state = uiState) {
            is AnalysisUiState.Idle -> IdleContent(onPickVideo)

            is AnalysisUiState.Preparing -> PreparationContent(
                state = state,
                onDurationKnown = viewModel::onVideoDurationKnown,
                onStartSecondsChanged = viewModel::onStartSecondsChanged,
                onHeightChanged = viewModel::onHeightChanged,
                onAnalyze = viewModel::startAnalysis,
                onPickAnother = onPickVideo,
            )

            is AnalysisUiState.Uploading -> ProgressContent("Subiendo el vídeo…")

            is AnalysisUiState.Processing -> ProgressContent(
                if (state.queued) "En cola…" else "Analizando el levantamiento…",
            )

            is AnalysisUiState.Completed -> CompletedContent(
                video = state.video,
                chart = state.chart,
                summary = state.summary,
                onRestart = viewModel::reset,
            )

            is AnalysisUiState.Failed -> FailedContent(state.message, viewModel::reset)
        }
    }
}

@Composable
private fun IdleContent(onPickVideo: () -> Unit) {
    Text(
        text = "Analiza tu levantamiento",
        style = MaterialTheme.typography.headlineMedium,
        textAlign = TextAlign.Center,
    )
    Text(
        text = "Graba el levantamiento desde un ángulo de 45º y elige el vídeo de tu galería.",
        style = MaterialTheme.typography.bodyMedium,
        textAlign = TextAlign.Center,
    )
    Button(onClick = onPickVideo, modifier = Modifier.fillMaxWidth()) {
        Text("Analizar levantamiento")
    }
}

@Composable
private fun ProgressContent(message: String) {
    CircularProgressIndicator()
    Text(message, style = MaterialTheme.typography.bodyLarge, textAlign = TextAlign.Center)
    Text(
        text = "El análisis puede tardar varios minutos.",
        style = MaterialTheme.typography.bodySmall,
        textAlign = TextAlign.Center,
    )
}

@Composable
private fun CompletedContent(
    video: File,
    chart: File?,
    summary: AnalysisSummary?,
    onRestart: () -> Unit,
) {
    Text("Análisis completado", style = MaterialTheme.typography.titleLarge)
    VideoPlayer(video = video, modifier = Modifier.fillMaxWidth())

    summary?.let { SummaryContent(it) }

    chart?.let {
        HorizontalDivider()
        Text("Velocidad de la barra", style = MaterialTheme.typography.titleMedium)
        ChartImage(it)
    }

    OutlinedButton(onClick = onRestart, modifier = Modifier.fillMaxWidth()) {
        Text("Analizar otro levantamiento")
    }
}

@Composable
private fun SummaryContent(summary: AnalysisSummary) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        MetricRow("Duración del levantamiento", "%.2f s".format(summary.liftDurationSeconds))
        MetricRow("Velocidad máxima", "%.2f m/s".format(summary.peakVelocityMs))
        MetricRow("Instante de velocidad máxima", "%.2f s".format(summary.peakVelocityTime))
        MetricRow("Trayectoria de la barra", summary.barPathQuality.label())
        MetricRow("Desviación horizontal", "%.1f %%".format(summary.barPathDeviation * 100))
        MetricRow("Detección corporal", "%.0f %%".format(summary.detectionRatio * 100))
    }
}

@Composable
private fun MetricRow(label: String, value: String) {
    Text(
        text = "$label: $value",
        style = MaterialTheme.typography.bodyMedium,
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun ChartImage(chart: File) {
    val bitmap = remember(chart.path) { BitmapFactory.decodeFile(chart.path) }
    if (bitmap == null) {
        Text("No se pudo cargar la gráfica.", style = MaterialTheme.typography.bodySmall)
        return
    }
    Image(
        bitmap = bitmap.asImageBitmap(),
        contentDescription = "Gráfica de velocidad de la barra",
        contentScale = ContentScale.FillWidth,
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun FailedContent(message: String, onRetry: () -> Unit) {
    Text(
        text = "No se pudo analizar el vídeo",
        style = MaterialTheme.typography.titleLarge,
        color = MaterialTheme.colorScheme.error,
    )
    Text(message, style = MaterialTheme.typography.bodyMedium, textAlign = TextAlign.Center)
    Button(onClick = onRetry, modifier = Modifier.fillMaxWidth()) {
        Text("Volver a empezar")
    }
}

/** Texto legible para la valoración de la trayectoria. */
private fun PathQuality.label(): String = when (this) {
    PathQuality.EXCELLENT -> "Excelente"
    PathQuality.ACCEPTABLE -> "Aceptable"
    PathQuality.POOR -> "Mejorable"
    PathQuality.UNKNOWN -> "Sin valorar"
}