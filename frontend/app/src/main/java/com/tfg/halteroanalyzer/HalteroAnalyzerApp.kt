package com.tfg.halteroanalyzer

import android.app.Application

/** Aplicación: mantiene el contenedor de dependencias durante todo su ciclo de vida. */
class HalteroAnalyzerApp : Application() {

    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
    }
}