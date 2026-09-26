package com.tfg.halteroanalyzer.ui.analysis

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.text.KeyboardOptions
import com.tfg.halteroanalyzer.domain.MAX_HEIGHT_CM
import com.tfg.halteroanalyzer.domain.MIN_HEIGHT_CM

/** Pantalla donde el usuario marca el despegue de la barra e indica su estatura. */
@Composable
fun PreparationContent(
    state: AnalysisUiState.Preparing,
    onDurationKnown: (Double) -> Unit,
    onStartSecondsChanged: (Double) -> Unit,
    onHeightChanged: (Int) -> Unit,
    onAnalyze: () -> Unit,
    onPickAnother: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text("Prepara el análisis", style = MaterialTheme.typography.titleLarge)

        VideoScrubber(
            videoUri = state.videoUri,
            positionSeconds = state.request.startSeconds,
            onDurationKnown = onDurationKnown,
            modifier = Modifier.fillMaxWidth(),
        )

        StartTimeSelector(
            startSeconds = state.request.startSeconds,
            durationSeconds = state.videoDurationSeconds,
            onChange = onStartSecondsChanged,
        )

        HeightSelector(heightCm = state.request.heightCm, onChange = onHeightChanged)

        Text(
            text = "Modalidad: snatch",
            style = MaterialTheme.typography.bodyMedium,
        )

        Button(
            onClick = onAnalyze,
            enabled = state.canStart,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text("Iniciar análisis")
        }
        OutlinedButton(onClick = onPickAnother, modifier = Modifier.fillMaxWidth()) {
            Text("Elegir otro vídeo")
        }
    }
}

@Composable
private fun StartTimeSelector(
    startSeconds: Double,
    durationSeconds: Double,
    onChange: (Double) -> Unit,
) {
    Column {
        Text(
            text = "Momento en que la barra despega del suelo",
            style = MaterialTheme.typography.bodyMedium,
        )
        Slider(
            value = startSeconds.toFloat(),
            onValueChange = { onChange(it.toDouble()) },
            valueRange = 0f..durationSeconds.toFloat().coerceAtLeast(0.1f),
            enabled = durationSeconds > 0,
        )
        Text(
            text = "%.2f s de %.2f s".format(startSeconds, durationSeconds),
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.fillMaxWidth(),
            textAlign = TextAlign.End,
        )
    }
}

@Composable
private fun HeightSelector(heightCm: Int, onChange: (Int) -> Unit) {
    var text by remember(heightCm) { mutableStateOf(heightCm.toString()) }
    val isValid = text.toIntOrNull() in MIN_HEIGHT_CM..MAX_HEIGHT_CM

    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        OutlinedTextField(
            value = text,
            onValueChange = { nuevo ->
                text = nuevo.filter(Char::isDigit).take(3)
                text.toIntOrNull()?.let(onChange)
            },
            label = { Text("Estatura (cm)") },
            isError = !isValid,
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            supportingText = {
                if (!isValid) Text("Entre $MIN_HEIGHT_CM y $MAX_HEIGHT_CM cm")
            },
            modifier = Modifier.fillMaxWidth(),
        )
    }
}

private operator fun IntRange.contains(value: Int?): Boolean = value != null && value in this