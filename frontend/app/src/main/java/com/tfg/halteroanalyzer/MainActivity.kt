package com.tfg.halteroanalyzer

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.tfg.halteroanalyzer.ui.analysis.AnalysisScreen
import com.tfg.halteroanalyzer.ui.analysis.AnalysisViewModel
import com.tfg.halteroanalyzer.ui.theme.HalteroAnalyzerTheme
import java.io.File

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val container = (application as HalteroAnalyzerApp).container
        val factory = AnalysisViewModel.Factory(
            repository = container.analysisRepository,
            videoSourceProvider = container::videoSourceFor,
            resultFileProvider = { jobId -> File(cacheDir, "$jobId.mp4") },
        )

        setContent {
            HalteroAnalyzerTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
                    AnalysisScreen(
                        viewModel = viewModel(factory = factory),
                        modifier = Modifier.padding(innerPadding),
                    )
                }
            }
        }
    }
}