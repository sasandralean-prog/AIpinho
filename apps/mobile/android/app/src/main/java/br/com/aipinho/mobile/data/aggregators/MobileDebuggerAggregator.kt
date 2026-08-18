package br.com.aipinho.mobile.data.aggregators

import br.com.aipinho.mobile.network.MobileViewModelClient

class MobileDebuggerAggregator(private val client: MobileViewModelClient) {
    fun load() = client.debugger()
}

