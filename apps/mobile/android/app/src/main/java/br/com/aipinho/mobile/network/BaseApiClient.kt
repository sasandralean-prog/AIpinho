package br.com.aipinho.mobile.network

import br.com.aipinho.mobile.models.ConnectionProfile
import br.com.aipinho.mobile.utils.Redaction
import br.com.aipinho.mobile.utils.SafeUrlBuilder
import java.net.HttpURLConnection
import java.net.URL

data class ApiResponse(val ok:Boolean,val statusCode:Int,val body:String,val error:String?=null)

open class BaseApiClient(private val profile:ConnectionProfile, private val port:Int, private val tokenProvider:()->String?, private val timeoutMs:Int=5000) {
    fun request(method:String,path:String,body:String?=null):ApiResponse {
        val urlText=SafeUrlBuilder.build(profile.host,port,path)
        return try {
            val connection=(URL(urlText).openConnection() as HttpURLConnection).apply {
                requestMethod=method; connectTimeout=timeoutMs; readTimeout=timeoutMs
                setRequestProperty("Accept","application/json; charset=utf-8"); setRequestProperty("Content-Type","application/json; charset=utf-8")
                tokenProvider()?.takeIf { it.isNotBlank() }?.let { setRequestProperty("Authorization","Bearer $it") }
                if (body!=null) { doOutput=true; outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) } }
            }
            val code=connection.responseCode
            val stream=if(code in 200..299) connection.inputStream else connection.errorStream
            val text=stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            ApiResponse(code in 200..299,code,Redaction.redact(text),if(code in 200..299) null else Redaction.redact(text))
        } catch (error:Exception) { ApiResponse(false,0,"",Redaction.redact(error.message.orEmpty())) }
    }
    fun get(path:String)=request("GET",path)
    fun post(path:String,body:String="{}")=request("POST",path,body)
    fun patch(path:String,body:String="{}")=request("PATCH",path,body)
    fun delete(path:String)=request("DELETE",path)
}
