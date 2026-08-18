package br.com.aipinho.mobile

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class DashboardPolishTest {
    @Test fun dashboardUsesHumanizedViewModelInsteadOfDirectMonitorCards() {
        val source = NeonSourceContract.source("ui/screens/DashboardScreen.kt")
        assertTrue(source.contains("HumanizedViewModelTerminal"))
        assertTrue(source.contains("mobileViewModels.dashboard()"))
        assertTrue(source.contains("fetchOfficialBackendStatus"))
        assertTrue(source.contains("mobileViewModels.status()"))
        assertTrue(source.contains("MobileUiAsync.run(context, { cockpit.setPayload(it) })"))
        assertTrue(source.contains("dashboard_core_backend"))
        assertTrue(source.contains("dashboard_backend_control"))
        assertFalse(source.contains("NeonPortRestartCard"))
        assertTrue(source.contains("MonitorClient"))
        assertTrue(source.contains("restartBackend()"))
        assertFalse(source.contains("backendControlStatus()"))
        assertFalse(source.contains("/v2"))
    }
}
