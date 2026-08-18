package br.com.aipinho.mobile.utils
object HumanFormatting { fun connection(ok:Int,total:Int)=when { ok==total->"Online"; ok==0->"Offline"; else->"Degradado: $ok/$total servicos" }; fun bytes(value:Long)=when { value>=1_048_576->"%.1f MB".format(value/1_048_576.0); value>=1024->"%.1f KB".format(value/1024.0); else->"$value B" } }
