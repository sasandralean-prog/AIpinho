package br.com.aipinho.mobile

import br.com.aipinho.mobile.models.ConnectionProfile

data class AppState(
    var profile: ConnectionProfile = ConnectionProfile.adbReverse(),
    var paired: Boolean = false,
    var online: Boolean = false,
    var degraded: Boolean = true,
    var cursor: String = "0",
    var activeSessionId: String? = null,
    var selectedTaskId: String? = null,
)
