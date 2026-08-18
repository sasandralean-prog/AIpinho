package br.com.aipinho.mobile.models.humanized

data class MobileConfigViewModel(val capabilities: Map<String, Boolean>, val cards: List<HumanizedCardViewModel>, val status: String)

