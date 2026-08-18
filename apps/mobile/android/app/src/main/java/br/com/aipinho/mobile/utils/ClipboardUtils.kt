package br.com.aipinho.mobile.utils
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
object ClipboardUtils { fun copy(context:Context,label:String,text:String) { (context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager).setPrimaryClip(ClipData.newPlainText(label,Redaction.redact(text))) } }
