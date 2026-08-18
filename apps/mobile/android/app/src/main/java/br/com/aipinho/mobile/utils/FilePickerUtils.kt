package br.com.aipinho.mobile.utils
import android.content.Intent
object FilePickerUtils { fun createIntent()=Intent(Intent.ACTION_OPEN_DOCUMENT).apply { type="*/*"; addCategory(Intent.CATEGORY_OPENABLE) } }
