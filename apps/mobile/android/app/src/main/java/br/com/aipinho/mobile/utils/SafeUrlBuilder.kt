package br.com.aipinho.mobile.utils
object SafeUrlBuilder { fun build(host:String,port:Int,path:String):String { require(host.isNotBlank()) { "host_required" }; require(port in 1..65535) { "invalid_port" }; require(!host.contains("/") && !host.contains("?")) { "invalid_host" }; val safePath=if(path.startsWith('/')) path else "/$path"; return "http://$host:$port$safePath" } }
