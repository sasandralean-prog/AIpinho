package br.com.aipinho.mobile.models
data class ContextStatus(val status:String="degraded",val enabled:Boolean=false,val warnings:List<String> = emptyList())
