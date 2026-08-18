package br.com.aipinho.mobile
import org.junit.Assert.*
import org.junit.Test
import br.com.aipinho.mobile.viewmodel.PipelineViewModel
class PipelineViewModelTest { @Test fun supportsDegradedState(){ val vm=PipelineViewModel(); vm.markDegraded("partial"); assertEquals("degraded",vm.status) } }
