package br.com.aipinho.mobile.network
import br.com.aipinho.mobile.AppConfig
import br.com.aipinho.mobile.models.ConnectionProfile
class MonitorClient(profile:ConnectionProfile,token:()->String?):BaseApiClient(profile,profile.monitorPort,token) {
    fun status()=get("/api/v1/monitor/status")
    fun ports()=get("/api/v1/monitor/ports")
    fun services()=get("/api/v1/monitor/services")
    fun resources()=get("/api/v1/monitor/resources")
    fun restart(serviceId:String,port:Int)=if(port in AppConfig.restartAllowedPorts) post("/api/v1/monitor/services/$serviceId/restart") else ApiResponse(false,409,"", "restart_not_allowed")
    fun backendControlStatus()=get("/api/v1/backend-control/status")
    fun restartBackend()=post("/api/v1/backend-control/restart")
}

class BootstrapControlClient(profile:ConnectionProfile,token:()->String?):BaseApiClient(profile,profile.bootstrapPort,token) {
    fun status()=get("/api/v1/bootstrap-control/status")
    fun restartMonitor()=post("/api/v1/bootstrap-control/monitor/restart")
}
