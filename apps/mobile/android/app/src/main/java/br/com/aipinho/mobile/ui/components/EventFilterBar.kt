package br.com.aipinho.mobile.ui.components
import android.content.Context
import android.widget.TextView
class EventFilterBar(private val text:String="") { fun view(context:Context)=TextView(context).apply { this.text=this@EventFilterBar.text } }
