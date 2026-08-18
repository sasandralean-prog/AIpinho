package br.com.aipinho.mobile.utils
object Redaction {
    private val bearer=Regex("""Bearer\s+[A-Za-z0-9._~+/-]+""",RegexOption.IGNORE_CASE)
    private val apiKey=Regex("""(?:sk-|ghp_)[A-Za-z0-9_-]{10,}""")
    fun redact(value:String)=value.replace(bearer,"Bearer [REDACTED]").replace(apiKey,"[REDACTED_SECRET]")
}
