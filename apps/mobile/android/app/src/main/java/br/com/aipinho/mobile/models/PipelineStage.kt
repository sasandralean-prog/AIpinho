package br.com.aipinho.mobile.models
data class PipelineStage(val stageId:String,val label:String,val status:String,val permissions:List<String> = emptyList(),val blockedReasons:List<String> = emptyList())
