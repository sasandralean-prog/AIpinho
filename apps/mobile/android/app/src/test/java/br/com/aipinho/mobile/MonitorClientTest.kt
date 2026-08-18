package br.com.aipinho.mobile
import org.junit.Assert.*
import org.junit.Test
class MonitorClientTest { @Test fun supervisorRestartIsBlocked(){ assertTrue(9099 in AppConfig.restartBlockedPorts); assertFalse(9099 in AppConfig.restartAllowedPorts) } }
