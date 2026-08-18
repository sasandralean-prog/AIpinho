package br.com.aipinho.mobile

object AppConfig {
    const val CORE_PORT = 9088
    const val REALTIME_PORT = 9089
    const val ARTIFACT_PORT = 9098
    const val MONITOR_PORT = 9099
    const val BOOTSTRAP_PORT = 9080
    const val BACKEND_CONTROL_PORT = MONITOR_PORT
    val restartAllowedPorts = setOf(CORE_PORT, REALTIME_PORT, ARTIFACT_PORT)
    val restartBlockedPorts = setOf(MONITOR_PORT)
    val adbCommands = listOf(
        "adb reverse tcp:9080 tcp:9080",
        "adb reverse tcp:9088 tcp:9088",
        "adb reverse tcp:9089 tcp:9089",
        "adb reverse tcp:9098 tcp:9098",
        "adb reverse tcp:9099 tcp:9099",
    )
}
