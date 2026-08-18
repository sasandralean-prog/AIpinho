package br.com.aipinho.mobile.data.aggregators

import br.com.aipinho.mobile.network.MobileViewModelClient

class MobileChatAggregator(private val client: MobileViewModelClient) {
    fun load(sessionId: String) = client.chat(sessionId)
}

