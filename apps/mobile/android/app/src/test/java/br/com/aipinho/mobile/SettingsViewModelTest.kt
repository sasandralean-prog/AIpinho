package br.com.aipinho.mobile
import org.junit.Assert.*
import org.junit.Test
import br.com.aipinho.mobile.viewmodel.SettingsViewModel
class SettingsViewModelTest { @Test fun supportsDegradedState(){ val vm=SettingsViewModel(); vm.markDegraded("partial"); assertEquals("degraded",vm.status) } }
