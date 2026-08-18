package br.com.aipinho.mobile.ui.navigation

enum class MainTab(val label: String, val icon: String) {
    DASHBOARD("Dashboard", "D"),
    AGENTS("Agentes", "A"),
    CHAT("Chat", "C"),
    GEMINI("Gemini", "G"),
    CODEX("Codex", "X"),
    PIPELINE("Pipeline", "P"),
    APPROVERS("Approvers", "V"),
    DEBUGGER("Debugger 2.0", "*"),
    SETTINGS("Config", "S");
}

class MainNavigationState(initial: MainTab = MainTab.DASHBOARD) {
    var selected: MainTab = initial
        private set

    fun select(tab: MainTab) {
        selected = tab
    }
}
