package br.com.aipinho.mobile
import org.junit.Assert.*
import org.junit.Test
import br.com.aipinho.mobile.models.ConnectionProfile
class ConnectionProfileTest { @Test fun adbUsesOfficialPorts(){ val p=ConnectionProfile.adbReverse(); assertEquals(9088,p.corePort); assertEquals(9099,p.monitorPort) } }
