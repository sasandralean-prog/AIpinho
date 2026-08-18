package br.com.aipinho.mobile
import org.junit.Assert.*
import org.junit.Test
import br.com.aipinho.mobile.viewmodel.TransferViewModel
class TransferViewModelTest { @Test fun supportsDegradedState(){ val vm=TransferViewModel(); vm.markDegraded("partial"); assertEquals("degraded",vm.status) } }
