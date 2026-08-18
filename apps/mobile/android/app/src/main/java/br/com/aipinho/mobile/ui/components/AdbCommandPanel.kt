package br.com.aipinho.mobile.ui.components
import android.content.Context
import android.widget.TextView
class AdbCommandPanel(private val text:String="") { fun view(context:Context)=TextView(context).apply { this.text=this@AdbCommandPanel.text } }
