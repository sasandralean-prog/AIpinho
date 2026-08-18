package br.com.aipinho.mobile.models
data class ServiceStatus(val serviceId:String,val status:String,val humanMessage:String="",val latencyMs:Long?=null)
