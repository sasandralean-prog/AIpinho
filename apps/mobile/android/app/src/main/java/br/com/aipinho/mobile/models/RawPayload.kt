package br.com.aipinho.mobile.models
data class RawPayload(val rawRef:String,val sanitizedText:String,val hiddenByDefault:Boolean=true,val copyAllowed:Boolean=false)
