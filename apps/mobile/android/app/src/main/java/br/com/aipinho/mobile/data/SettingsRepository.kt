package br.com.aipinho.mobile.data
import android.content.Context
import br.com.aipinho.mobile.models.ConnectionProfile
import br.com.aipinho.mobile.models.ConnectionProfileType
class SettingsRepository(context:Context) {
    private val prefs=context.getSharedPreferences("aipinho_settings",Context.MODE_PRIVATE)
    fun saveProfile(profile:ConnectionProfile) { prefs.edit().putString("type",profile.type.name).putString("host",profile.host).putInt("core",profile.corePort).putInt("realtime",profile.realtimePort).putInt("artifact",profile.artifactPort).putInt("monitor",profile.monitorPort).putInt("bootstrap",profile.bootstrapPort).apply() }
    fun loadProfile():ConnectionProfile {
        val type=runCatching { ConnectionProfileType.valueOf(prefs.getString("type",ConnectionProfileType.ADB_REVERSE.name)!!) }.getOrDefault(ConnectionProfileType.ADB_REVERSE)
        return ConnectionProfile(type,prefs.getString("host","127.0.0.1")!!,prefs.getInt("core",9088),prefs.getInt("realtime",9089),prefs.getInt("artifact",9098),prefs.getInt("monitor",9099),prefs.getInt("bootstrap",9080))
    }
    fun saveCursor(cursor:String)=prefs.edit().putString("cursor",cursor).apply()
    fun loadCursor():String=prefs.getString("cursor","0")!!
}
