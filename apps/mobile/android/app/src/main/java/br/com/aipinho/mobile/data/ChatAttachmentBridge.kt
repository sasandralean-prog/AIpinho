package br.com.aipinho.mobile.data

object ChatAttachmentBridge {
    const val REQUEST_CODE = 4101
    var onSelected: ((String) -> Unit)? = null

    fun dispatch(uriText: String) {
        onSelected?.invoke(uriText)
    }
}
