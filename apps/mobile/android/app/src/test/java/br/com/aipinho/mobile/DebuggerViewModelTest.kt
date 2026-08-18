package br.com.aipinho.mobile
import org.junit.Assert.*
import org.junit.Test
import br.com.aipinho.mobile.viewmodel.DebuggerViewModel
class DebuggerViewModelTest { @Test fun supportsDegradedState(){ val vm=DebuggerViewModel(); vm.markDegraded("partial"); assertEquals("degraded",vm.status) } }
