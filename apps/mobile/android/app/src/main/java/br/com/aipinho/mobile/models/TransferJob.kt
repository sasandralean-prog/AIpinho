package br.com.aipinho.mobile.models
data class TransferJob(val jobId:String,val transferType:String,val status:String,val progressPercent:Double=0.0,val artifactId:String?=null,val filename:String?=null)
