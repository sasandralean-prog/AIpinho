package br.com.aipinho.mobile.models
data class ArtifactLink(val artifactId:String,val filename:String,val sizeBytes:Long=0,val sha256:String?=null,val zipAvailable:Boolean=false)
