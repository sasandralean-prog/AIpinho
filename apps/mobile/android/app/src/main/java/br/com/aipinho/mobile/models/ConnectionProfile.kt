package br.com.aipinho.mobile.models

enum class ConnectionProfileType { ADB_REVERSE, WIFI_LAN, TAILSCALE, MANUAL }
data class ConnectionProfile(val type:ConnectionProfileType,val host:String,val corePort:Int=9088,val realtimePort:Int=9089,val artifactPort:Int=9098,val monitorPort:Int=9099,val bootstrapPort:Int=9080) {
    companion object {
        fun adbReverse()=ConnectionProfile(ConnectionProfileType.ADB_REVERSE,"127.0.0.1")
        fun wifi(host:String)=ConnectionProfile(ConnectionProfileType.WIFI_LAN,host)
        fun tailscale(host:String)=ConnectionProfile(ConnectionProfileType.TAILSCALE,host)
        fun manual(host:String,core:Int,realtime:Int,artifact:Int,monitor:Int,bootstrap:Int=9080)=ConnectionProfile(ConnectionProfileType.MANUAL,host,core,realtime,artifact,monitor,bootstrap)
    }
}
