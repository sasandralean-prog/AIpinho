package br.com.aipinho.mobile
import org.junit.Assert.*
import org.junit.Test
import br.com.aipinho.mobile.viewmodel.ConnectionViewModel
class ConnectionViewModelTest { @Test fun supportsDegradedState(){ val vm=ConnectionViewModel(); vm.markDegraded("partial"); assertEquals("degraded",vm.status) } }
