package br.com.aipinho.mobile.utils
object DownloadUtils { private val blocked=setOf("exe","dll","bat","cmd","ps1","sh","msi"); fun safeFilename(name:String)=name.substringAfterLast('/').substringAfterLast('\\').replace(Regex("[^A-Za-z0-9._-]"),"_"); fun canAutoOpen(name:String)=false; fun isBlocked(name:String)=name.substringAfterLast('.',"").lowercase() in blocked }
