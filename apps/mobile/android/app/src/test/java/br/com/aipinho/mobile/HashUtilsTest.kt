package br.com.aipinho.mobile
import org.junit.Assert.*
import org.junit.Test
import br.com.aipinho.mobile.utils.HashUtils
class HashUtilsTest { @Test fun hashesDeterministically(){ assertEquals(HashUtils.sha256(byteArrayOf(1)),HashUtils.sha256(byteArrayOf(1))) } }
