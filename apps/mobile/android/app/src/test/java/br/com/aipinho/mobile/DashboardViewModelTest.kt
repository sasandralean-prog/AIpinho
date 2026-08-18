package br.com.aipinho.mobile
import org.junit.Assert.*
import org.junit.Test
import br.com.aipinho.mobile.viewmodel.DashboardViewModel
class DashboardViewModelTest { @Test fun supportsDegradedState(){ val vm=DashboardViewModel(); vm.markDegraded("partial"); assertEquals("degraded",vm.status) } }
