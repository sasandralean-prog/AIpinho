package br.com.aipinho.mobile.models
data class EventContract(val eventType:String,val defaultVisibility:String="public",val defaultSeverity:String="info",val speakerAllowed:Boolean=true)
