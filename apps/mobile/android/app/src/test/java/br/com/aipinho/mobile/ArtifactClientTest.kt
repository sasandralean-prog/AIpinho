package br.com.aipinho.mobile
import org.junit.Assert.*
import org.junit.Test
import br.com.aipinho.mobile.utils.HashUtils
class ArtifactClientTest { @Test fun verifiesSha256(){ assertTrue(HashUtils.verify("abc".toByteArray(),"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")) } }
