package br.com.aipinho.mobile.data.aggregators

import br.com.aipinho.mobile.network.MobileViewModelClient

class MobilePipelineAggregator(private val client: MobileViewModelClient) {
    fun load() = client.pipeline()
}

