package br.com.aipinho.mobile
import org.junit.Assert.*
import org.junit.Test
import br.com.aipinho.mobile.models.TaskCard
class PipelineClientTest { @Test fun approvalIsExplicit(){ assertTrue(TaskCard("t","blocked",approvalRequired=true).approvalRequired) } }
