package br.com.aipinho.mobile.models
data class UxHealth(val state:String="degraded",val offline:Boolean=false,val warnings:List<String> = emptyList())
