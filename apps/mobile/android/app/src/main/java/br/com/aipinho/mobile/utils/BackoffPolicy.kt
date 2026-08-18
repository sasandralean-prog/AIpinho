package br.com.aipinho.mobile.utils
object BackoffPolicy { private val schedule=listOf(1,2,5,10,30); fun seconds(attempt:Int)=schedule[attempt.coerceIn(0,schedule.lastIndex)] }
