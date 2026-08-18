package br.com.aipinho.mobile.viewmodel
class ChatViewModel {
    var status:String="idle"; private set
    var message:String=""; private set
    fun update(newStatus:String,humanMessage:String="") { status=newStatus; message=humanMessage }
    fun markOffline()=update("offline","Backend indisponivel. Estado local preservado.")
    fun markDegraded(reason:String)=update("degraded",reason)
}
