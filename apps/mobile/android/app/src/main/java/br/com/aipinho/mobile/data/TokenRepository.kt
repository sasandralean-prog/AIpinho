package br.com.aipinho.mobile.data
import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
class TokenRepository(context:Context) {
    private val prefs=context.getSharedPreferences("aipinho_secure",Context.MODE_PRIVATE)
    private val alias="aipinho_mobile_token"
    private fun key():SecretKey {
        val store=KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(alias,null) as? SecretKey)?.let { return it }
        val generator=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore")
        generator.init(KeyGenParameterSpec.Builder(alias,KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT).setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
        return generator.generateKey()
    }
    fun save(token:String) {
        require(token.isNotBlank()) { "empty_token_blocked" }
        val cipher=Cipher.getInstance("AES/GCM/NoPadding"); cipher.init(Cipher.ENCRYPT_MODE,key())
        prefs.edit().putString("cipher",Base64.encodeToString(cipher.doFinal(token.toByteArray()),Base64.NO_WRAP)).putString("iv",Base64.encodeToString(cipher.iv,Base64.NO_WRAP)).apply()
    }
    fun load():String? {
        val encrypted=prefs.getString("cipher",null) ?: return null; val iv=prefs.getString("iv",null) ?: return null
        return runCatching { val cipher=Cipher.getInstance("AES/GCM/NoPadding"); cipher.init(Cipher.DECRYPT_MODE,key(),GCMParameterSpec(128,Base64.decode(iv,Base64.NO_WRAP))); String(cipher.doFinal(Base64.decode(encrypted,Base64.NO_WRAP))) }.getOrNull()
    }
    fun hasToken()=!load().isNullOrBlank()
    fun clear()=prefs.edit().remove("cipher").remove("iv").apply()
    fun preview():String=load()?.take(4)?.plus("...") ?: "nao pareado"
}
