package br.com.aipinho.mobile.models
data class TaskCard(val taskId:String,val status:String,val phase:String="",val approvalRequired:Boolean=false,val blockedReasons:List<String> = emptyList())
