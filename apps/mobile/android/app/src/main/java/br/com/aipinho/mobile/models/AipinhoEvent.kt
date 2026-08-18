package br.com.aipinho.mobile.models
data class AipinhoEvent(val eventId:String,val eventType:String,val sourceService:String,val humanSummary:String,val severity:String="info",val status:String="created",val visibility:String="public",val rawRef:String?=null)
