package br.com.aipinho.mobile

import java.io.File

object NeonSourceContract {
    private val projectRoot: File = generateSequence(File(".").canonicalFile) { it.parentFile }
        .firstOrNull {
            File(it, "src/main/java/br/com/aipinho/mobile").exists() ||
                File(it, "app/src/main/java/br/com/aipinho/mobile").exists()
        }
        ?: File(".").canonicalFile
    private val mainRoot: File =
        if (File(projectRoot, "src/main/java/br/com/aipinho/mobile").exists()) {
            File(projectRoot, "src/main/java/br/com/aipinho/mobile")
        } else {
            File(projectRoot, "app/src/main/java/br/com/aipinho/mobile")
        }

    fun source(path: String): String =
        File(mainRoot, path).readText()

    fun config(path: String): String {
        val mobileRoot = generateSequence(projectRoot) { it.parentFile }
            .firstOrNull { File(it, "config/mobile").exists() }
            ?: projectRoot
        return File(mobileRoot, "config/mobile/$path").readText()
    }
}
