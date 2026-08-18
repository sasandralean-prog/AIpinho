package br.com.aipinho.mobile.data

import android.content.Context

class ThemePreferenceRepository(context: Context) {
    private val prefs = context.getSharedPreferences("aipinho_theme", Context.MODE_PRIVATE)
    fun neonReduced(): Boolean = prefs.getBoolean("neon_reduced", false)
    fun setNeonReduced(enabled: Boolean) = prefs.edit().putBoolean("neon_reduced", enabled).apply()
}
