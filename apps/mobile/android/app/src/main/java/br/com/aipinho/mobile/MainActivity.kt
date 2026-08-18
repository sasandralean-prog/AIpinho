package br.com.aipinho.mobile

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.View
import android.widget.FrameLayout
import android.widget.LinearLayout
import br.com.aipinho.mobile.data.ChatAttachmentBridge
import br.com.aipinho.mobile.data.SettingsRepository
import br.com.aipinho.mobile.data.TokenRepository
import br.com.aipinho.mobile.ui.components.AipinhoLogo
import br.com.aipinho.mobile.ui.components.AipinhoScrollableTabBar
import br.com.aipinho.mobile.ui.screens.AgentMarketplaceScreen
import br.com.aipinho.mobile.ui.screens.ChatScreen
import br.com.aipinho.mobile.ui.screens.CodexAgentScreen
import br.com.aipinho.mobile.ui.screens.DashboardScreen
import br.com.aipinho.mobile.ui.screens.DebuggerScreen
import br.com.aipinho.mobile.ui.screens.GeminiExecutorScreen
import br.com.aipinho.mobile.ui.screens.PairingScreen
import br.com.aipinho.mobile.ui.screens.PipelineScreen
import br.com.aipinho.mobile.ui.screens.SettingsScreen
import br.com.aipinho.mobile.ui.screens.UniversalApproversScreen
import br.com.aipinho.mobile.ui.navigation.MainNavigationState
import br.com.aipinho.mobile.ui.navigation.MainTab
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme
import br.com.aipinho.mobile.ui.theme.NeonColors
import br.com.aipinho.mobile.network.ArtifactDownloadNotifier

class MainActivity : Activity() {
    private lateinit var content: FrameLayout
    private lateinit var navHost: LinearLayout
    private lateinit var settings: SettingsRepository
    private lateinit var tokens: TokenRepository
    private val navigation = MainNavigationState()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = NeonColors.matrixBlack
        window.navigationBarColor = NeonColors.matrixBlack
        settings = SettingsRepository(this)
        tokens = TokenRepository(this)
        requestNotificationPermissionIfNeeded()
        ArtifactDownloadNotifier(applicationContext).resumePersistedDownloads()
        setContentView(buildRoot())
        if (tokens.hasToken()) showTab(MainTab.DASHBOARD) else showPairing()
    }

    private fun buildRoot(): View {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(12, statusBarPaddingPx() + 12, 12, 12)
            AipinhoNeonTheme.applyScreen(this)
        }
        root.addView(AipinhoLogo(this))
        navHost = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        root.addView(navHost)
        content = FrameLayout(this)
        root.addView(content, LinearLayout.LayoutParams(-1, 0, 1f))
        return root
    }

    private fun show(view: View) {
        content.removeAllViews()
        content.addView(
            view,
            FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT,
            ),
        )
    }
    private fun renderTabs() {
        navHost.removeAllViews()
        navHost.addView(AipinhoScrollableTabBar(this, navigation.selected, mapOf(MainTab.DASHBOARD to "9088", MainTab.DEBUGGER to "RO")) { showTab(it) })
    }

    private fun showTab(tab: MainTab) {
        navigation.select(tab)
        renderTabs()
        show(
            when (tab) {
                MainTab.DASHBOARD -> DashboardScreen().build(this)
                MainTab.AGENTS -> AgentMarketplaceScreen().build(this)
                MainTab.CHAT -> ChatScreen().build(this)
                MainTab.CODEX -> CodexAgentScreen().build(this)
                MainTab.GEMINI -> GeminiExecutorScreen().build(this)
                MainTab.PIPELINE -> PipelineScreen().build(this)
                MainTab.APPROVERS -> UniversalApproversScreen().build(this)
                MainTab.DEBUGGER -> DebuggerScreen().build(this)
                MainTab.SETTINGS -> SettingsScreen(settings, tokens).build(this)
            }
        )
    }

    private fun showPairing() = show(PairingScreen(settings, tokens) { showTab(MainTab.DASHBOARD) }.build(this))

    private fun statusBarPaddingPx(): Int {
        val resourceId = resources.getIdentifier("status_bar_height", "dimen", "android")
        return if (resourceId > 0) resources.getDimensionPixelSize(resourceId) else 0
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
        if (checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) return
        requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 42)
    }

    @Deprecated("Android framework callback kept for this no-AndroidX Activity.")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == ChatAttachmentBridge.REQUEST_CODE && resultCode == RESULT_OK) {
            data?.data?.toString()?.let { ChatAttachmentBridge.dispatch(it) }
        }
    }
}
