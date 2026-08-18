package br.com.aipinho.mobile.utils
import java.security.MessageDigest
object HashUtils { fun sha256(bytes:ByteArray)=MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }; fun verify(bytes:ByteArray,expected:String?)=!expected.isNullOrBlank() && sha256(bytes).equals(expected,true) }
