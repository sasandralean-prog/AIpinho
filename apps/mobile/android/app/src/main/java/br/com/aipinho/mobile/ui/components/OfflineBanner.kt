package br.com.aipinho.mobile.ui.components
import android.content.Context
import android.widget.TextView
class OfflineBanner(private val text:String="") { fun view(context:Context)=TextView(context).apply { this.text=this@OfflineBanner.text } }
