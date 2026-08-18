package br.com.aipinho.mobile
import org.junit.Assert.*
import org.junit.Test
import br.com.aipinho.mobile.viewmodel.ChatViewModel
class ChatViewModelTest { @Test fun supportsDegradedState(){ val vm=ChatViewModel(); vm.markDegraded("partial"); assertEquals("degraded",vm.status) } }
