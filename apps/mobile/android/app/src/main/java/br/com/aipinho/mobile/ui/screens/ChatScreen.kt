package br.com.aipinho.mobile.ui.screens

import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.provider.OpenableColumns
import android.view.View
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import br.com.aipinho.mobile.data.ChatAttachmentBridge
import br.com.aipinho.mobile.data.ChatSessionRepository
import br.com.aipinho.mobile.data.SettingsRepository
import br.com.aipinho.mobile.data.TokenRepository
import br.com.aipinho.mobile.network.ApiResponse
import br.com.aipinho.mobile.network.ArtifactClient
import br.com.aipinho.mobile.network.ChatClient
import br.com.aipinho.mobile.network.MobileViewModelClient
import br.com.aipinho.mobile.network.PipelineClient
import br.com.aipinho.mobile.network.TaskRuntimeClient
import br.com.aipinho.mobile.ui.cards.ChatDecisionCard
import br.com.aipinho.mobile.ui.cards.ChatPresentationRenderer
import br.com.aipinho.mobile.ui.cards.ArtifactLinkRenderer
import br.com.aipinho.mobile.ui.cards.HumanizedViewModelTerminal
import br.com.aipinho.mobile.ui.components.NeonButton
import br.com.aipinho.mobile.ui.components.NeonActionGroup
import br.com.aipinho.mobile.ui.components.NeonCyberCard
import br.com.aipinho.mobile.ui.components.NeonRawCopyButton
import br.com.aipinho.mobile.ui.components.NeonSearchField
import br.com.aipinho.mobile.ui.components.NeonSectionHeader
import br.com.aipinho.mobile.ui.components.NeonTerminalCard
import br.com.aipinho.mobile.ui.components.NeonUploadCard
import br.com.aipinho.mobile.ui.components.MobileScreenScaffold
import br.com.aipinho.mobile.ui.policies.ChatAutoRefreshPolicy
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme
import br.com.aipinho.mobile.ui.theme.NeonColors
import br.com.aipinho.mobile.ui.theme.NeonTypography
import br.com.aipinho.mobile.utils.ChatSessionIdExtractor
import br.com.aipinho.mobile.utils.MobileUiAsync
import org.json.JSONObject

private data class ChatSessionSummary(
    val sessionId: String,
    val title: String,
    val messageCount: Int,
    val updatedAt: String,
)

class ChatScreen {
    companion object {
        private var activeSessionId: String? = null
        private var draft: String = ""
        private var lastConversation: String = ""
        private var lastOperationalResult: String = ""
        private var lastViewModelPayload: String = ""
        private var displayMode: String = "normal"
        private var activeTaskRunId: String? = null
        private var latestArtifactId: String? = null
        private var latestArtifactFilename: String? = null
        private var latestArtifactContentType: String? = null
        private var operationFeedbackUntilMs: Long = 0L
        private var speakerTaskRunId: String? = null
        private var speakerEventCursor: String? = null
        private val speakerEventIds = mutableSetOf<String>()
        private val attachedArtifactIds = mutableListOf<String>()
    }

    fun build(context: Context): View {
        val profile = SettingsRepository(context).loadProfile()
        val tokens = TokenRepository(context)
        val chatSessions = ChatSessionRepository(context)
        activeSessionId = activeSessionId ?: chatSessions.loadActiveSessionId()
        if (draft.isBlank()) draft = chatSessions.loadDraft()
        if (lastConversation.isBlank()) lastConversation = chatSessions.loadLastConversation()
        if (lastOperationalResult.isBlank()) lastOperationalResult = chatSessions.loadLastOperationalResult()
        activeTaskRunId = activeTaskRunId ?: chatSessions.loadActiveTaskRunId()
        latestArtifactId = latestArtifactId ?: chatSessions.loadLatestArtifactId()
        latestArtifactFilename = latestArtifactFilename ?: chatSessions.loadLatestArtifactFilename()
        latestArtifactContentType = latestArtifactContentType ?: chatSessions.loadLatestArtifactContentType()
        val chat = ChatClient(profile) { tokens.load() }
        val artifacts = ArtifactClient(profile) { tokens.load() }
        val mobileViewModels = MobileViewModelClient(profile) { tokens.load() }
        val taskRuntime = TaskRuntimeClient(profile) { tokens.load() }
        val pipeline = PipelineClient(profile) { tokens.load() }
        val presentationRenderer = ChatPresentationRenderer()
        val artifactLinkRenderer = ArtifactLinkRenderer()
        val refreshHandler = Handler(Looper.getMainLooper())
        val root = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            AipinhoNeonTheme.applyScreen(this)
        }
        val input = NeonSearchField(context, "Mensagem para AIpinho").apply { setText(draft) }
        val decisionCard = ChatDecisionCard(context)
        decisionCard.visibility = if (displayMode == "normal") View.GONE else View.VISIBLE
        val viewModelTerminal = HumanizedViewModelTerminal(context, "Chat cockpit", minHeightDp = 320)
        viewModelTerminal.visibility = View.VISIBLE
        val stateCard = NeonCyberCard(context, "Estado", "Speaker Truth").apply {
            addBody("Respostas humanas, artifacts por artifact_id, feedback e retry sem duplicar.")
        }
        val artifactPanel = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
        }
        renderArtifactPanel(context, artifactPanel, artifacts, artifactLinkRenderer) { tokens.load() }
        val timeline = NeonTerminalCard(
            context,
            "Timeline",
            lastConversation.takeIf { it.isNotBlank() }?.lines() ?: listOf("Sessao: ${activeSessionId ?: "nao criada"}", "Raw oculto por padrao."),
            minHeightDp = 280,
        )
        val operationalResult = NeonTerminalCard(
            context,
            "Resultado operacional",
            lastOperationalResult.takeIf { it.isNotBlank() }?.lines()
                ?: listOf("Nenhuma analise operacional concluida nesta conversa."),
            minHeightDp = 220,
        )

        ChatAttachmentBridge.onSelected = { uriText ->
            timeline.terminal.addLine("Anexo selecionado; preparando upload governado...")
            MobileUiAsync.run(context, { body ->
                lastConversation = body
                chatSessions.saveLastConversation(body)
                timeline.terminal.setLines(body.lines())
            }) {
                val uri = Uri.parse(uriText)
                val filename = attachmentName(context, uri)
                val contentType = context.contentResolver.getType(uri) ?: "text/plain"
                val content = readTextAttachment(context, uri)
                val response = artifacts.upload(filename, content, contentType)
                Regex("artifact_[a-zA-Z0-9-]+").find(response.body)?.value?.let { artifactId ->
                    if (!attachedArtifactIds.contains(artifactId)) attachedArtifactIds.add(artifactId)
                }
                response.visibleText("upload_attachment")
            }
        }

        val refreshRunnable = object : Runnable {
            override fun run() {
                if (!activeSessionId.isNullOrBlank() && System.currentTimeMillis() >= operationFeedbackUntilMs) {
                    reloadChatViewModel(context, mobileViewModels, viewModelTerminal, timeline, artifactPanel, artifacts, artifactLinkRenderer) { tokens.load() }
                    pollSpeakerUpdates(context, taskRuntime, timeline)
                }
                refreshHandler.postDelayed(this, ChatAutoRefreshPolicy.pollIntervalMs)
            }
        }
        root.addOnAttachStateChangeListener(object : View.OnAttachStateChangeListener {
            override fun onViewAttachedToWindow(view: View) {
                refreshHandler.removeCallbacks(refreshRunnable)
                refreshHandler.postDelayed(refreshRunnable, ChatAutoRefreshPolicy.pollIntervalMs)
            }

            override fun onViewDetachedFromWindow(view: View) {
                refreshHandler.removeCallbacks(refreshRunnable)
            }
        })

        root.addView(NeonSectionHeader(context, "Chat"))
        root.addView(stateCard)
        root.addView(decisionCard)
        root.addView(viewModelTerminal)
        root.addView(input)

        root.addView(NeonActionGroup(context, listOf(
            NeonButton(context, "Sessoes") {
                    showSessionsDialog(
                        context = context,
                        chat = chat,
                        chatSessions = chatSessions,
                        mobileViewModels = mobileViewModels,
                        viewModelTerminal = viewModelTerminal,
                        timeline = timeline,
                        artifactPanel = artifactPanel,
                        artifacts = artifacts,
                        artifactLinkRenderer = artifactLinkRenderer,
                        tokenProvider = { tokens.load() },
                    )
                },
            NeonButton(context, "Criar") {
                    timeline.terminal.setLines(listOf("Criando sessao..."))
                    MobileUiAsync.run(context, { text ->
                        lastConversation = text
                        chatSessions.saveLastConversation(text)
                        timeline.terminal.setLines(text.lines())
                    }) {
                        val response = chat.createSession()
                        activeSessionId = extractSessionId(response.body) ?: activeSessionId
                        chatSessions.saveActiveSessionId(activeSessionId)
                        chatSessions.clearDraft()
                        draft = ""
                        input.setText("")
                        response.visibleText("create_session")
                    }
                },
            NeonButton(context, "Enviar") {
                    val text = input.text.toString()
                    if (text.isBlank()) {
                        timeline.terminal.setLines(listOf("Digite uma mensagem antes de enviar."))
                        return@NeonButton
                    }
                    val expectedMessagesAfterSend = (countPresentationMessages(lastViewModelPayload).takeIf { it > 0 } ?: 0) + 2
                    draft = text
                    chatSessions.saveDraft(text)
                    timeline.terminal.setLines(listOf("Enviando mensagem...", "Aguardando backend..."))
                    MobileUiAsync.run(context, { responsePayload ->
                        val visibleText = chatSendVisibleTextFromPayload(responsePayload, activeSessionId ?: "")
                        lastConversation = visibleText
                        chatSessions.saveLastConversation(visibleText)
                        timeline.terminal.setLines(visibleText.lines())
                        syncLatestArtifactFromChatResponse(responsePayload, chatSessions)
                        syncActiveTaskFromChatResponse(responsePayload, chatSessions)
                        lastViewModelPayload = ""
                        renderArtifactPanel(context, artifactPanel, artifacts, artifactLinkRenderer) { tokens.load() }
                        chatSessions.clearDraft()
                        draft = ""
                        input.setText("")
                        reloadChatViewModelStabilized(
                            context,
                            mobileViewModels,
                            viewModelTerminal,
                            timeline,
                            artifactPanel,
                            artifacts,
                            artifactLinkRenderer,
                            { tokens.load() },
                            expectedMessagesAfterSend,
                        )
                    }) {
                        if (activeSessionId.isNullOrBlank()) {
                            val created = chat.createSession()
                            activeSessionId = extractSessionId(created.body)
                            chatSessions.saveActiveSessionId(activeSessionId)
                            if (activeSessionId.isNullOrBlank()) {
                                return@run created.visibleText("create_session")
                            }
                        }
                        val pendingArtifacts = attachedArtifactIds.toList()
                        val response = chat.send(activeSessionId ?: "", text, pendingArtifacts)
                        if (response.ok) attachedArtifactIds.clear()
                        if (response.ok && response.body.isNotBlank()) response.body else response.visibleText("send_message")
                    }
                },
            NeonButton(context, "Anexar") {
                    val picker = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                        addCategory(Intent.CATEGORY_OPENABLE)
                        type = "*/*"
                    }
                    (context as? Activity)?.startActivityForResult(
                        Intent.createChooser(picker, "Selecionar arquivo"),
                        ChatAttachmentBridge.REQUEST_CODE,
                    ) ?: timeline.terminal.addLine("Anexo indisponivel: tela atual nao e Activity.", error = true)
                },
        )))

        root.addView(NeonActionGroup(context, listOf(
            NeonButton(context, "Aprovar approval") {
                    val approvalId = approvalIdFromPayload(lastViewModelPayload)
                    if (approvalId.isNullOrBlank()) {
                        timeline.terminal.setLines(listOf("Nenhum approval pendente encontrado no chat atual."))
                        return@NeonButton
                    }
                    timeline.terminal.setLines(listOf("Aprovando $approvalId...", "Aguardando backend confirmar."))
                    MobileUiAsync.run(context, { payload ->
                        timeline.terminal.setLines(payload.lines())
                        reloadChatViewModel(context, mobileViewModels, viewModelTerminal, timeline, artifactPanel, artifacts, artifactLinkRenderer) { tokens.load() }
                    }) {
                        val response = pipeline.approve(approvalId)
                        response.body.ifBlank { response.visibleText("approve_approval") }
                    }
                },
            NeonButton(context, "Negar approval") {
                    val approvalId = approvalIdFromPayload(lastViewModelPayload)
                    if (approvalId.isNullOrBlank()) {
                        timeline.terminal.setLines(listOf("Nenhum approval pendente encontrado no chat atual."))
                        return@NeonButton
                    }
                    timeline.terminal.setLines(listOf("Negando $approvalId...", "Nenhuma acao sera executada sem confirmacao do backend."))
                    MobileUiAsync.run(context, { payload ->
                        timeline.terminal.setLines(payload.lines())
                        reloadChatViewModel(context, mobileViewModels, viewModelTerminal, timeline, artifactPanel, artifacts, artifactLinkRenderer) { tokens.load() }
                    }) {
                        val response = pipeline.deny(approvalId)
                        response.body.ifBlank { response.visibleText("deny_approval") }
                    }
                },
            NeonButton(context, "Aprovar seguras") {
                    val taskId = activeTaskRunId ?: taskIdFromPayload(lastViewModelPayload)
                    if (taskId.isNullOrBlank()) {
                        timeline.terminal.setLines(listOf("Nenhuma task com approval pendente encontrada."))
                        return@NeonButton
                    }
                    timeline.terminal.setLines(listOf("Aprovando acoes seguras de $taskId..."))
                    MobileUiAsync.run(context, { payload ->
                        timeline.terminal.setLines(payload.lines())
                        reloadChatViewModel(context, mobileViewModels, viewModelTerminal, timeline, artifactPanel, artifacts, artifactLinkRenderer) { tokens.load() }
                    }) {
                        val response = pipeline.approveSafeBatch(taskId)
                        response.body.ifBlank { response.visibleText("approve_safe_batch") }
                    }
                },
        )))

        root.addView(NeonActionGroup(context, listOf(
            NeonButton(context, "Normal", selected = displayMode == "normal") {
                    displayMode = "normal"
                    decisionCard.visibility = View.GONE
                    viewModelTerminal.visibility = View.VISIBLE
                    timeline.terminal.setLines(presentationRenderer.normalLines(lastViewModelPayload.ifBlank { lastConversation }))
                },
            NeonButton(context, "Detalhes", selected = displayMode == "details") {
                    displayMode = "details"
                    decisionCard.visibility = View.VISIBLE
                    viewModelTerminal.visibility = View.VISIBLE
                    timeline.terminal.setLines(presentationRenderer.detailsLines(lastViewModelPayload.ifBlank { lastConversation }))
                },
            NeonButton(context, "Raw", selected = displayMode == "raw") {
                    displayMode = "raw"
                    decisionCard.visibility = View.VISIBLE
                    viewModelTerminal.visibility = View.VISIBLE
                    timeline.terminal.setLines(presentationRenderer.rawLines(lastViewModelPayload.ifBlank { lastConversation }))
                },
            NeonRawCopyButton(context) { lastConversation },
            NeonButton(context, "Limpar cockpit") {
                    viewModelTerminal.clear()
                    timeline.terminal.setLines(listOf("Cockpit limpo. Historico persistido preservado."))
                },
            NeonButton(context, "Like") { timeline.terminal.addLine("feedback=like pendente de message_id real") },
            NeonButton(context, "Dislike") { timeline.terminal.addLine("feedback=dislike pendente de message_id real", error = true) },
        )))

        root.addView(artifactPanel)
        root.addView(timeline)
        root.addView(operationalResult)
        root.addView(NeonUploadCard(context, "Upload governado; executavel bloqueado por policy."))
        MobileUiAsync.run(context, { decisionCard.updateFromJson(it) }) {
            val response = mobileViewModels.chat(activeSessionId ?: "latest")
            response.body.ifBlank { "chat_view_model_unavailable status=${response.statusCode}" }
        }
        MobileUiAsync.run(context, { payload ->
            lastViewModelPayload = payload
            viewModelTerminal.setPayload(payload)
            renderArtifactPanel(context, artifactPanel, artifacts, artifactLinkRenderer) { tokens.load() }
            timeline.terminal.setLines(presentationRenderer.render(payload, displayMode))
        }) {
            val response = mobileViewModels.chat(activeSessionId ?: "latest")
            response.body.ifBlank { "chat_view_model_unavailable status=${response.statusCode}" }
        }
        return MobileScreenScaffold(context, root)
    }

    private fun syncActiveTaskFromChatResponse(payload: String, repository: ChatSessionRepository) {
        val taskId = runCatching { JSONObject(payload).optString("task_id").takeIf { it.isNotBlank() } }.getOrNull() ?: return
        if (taskId != activeTaskRunId) {
            activeTaskRunId = taskId
            speakerTaskRunId = taskId
            speakerEventCursor = null
            speakerEventIds.clear()
            repository.saveActiveTaskRunId(taskId)
        }
    }

    private fun pollSpeakerUpdates(context: Context, runtime: TaskRuntimeClient, timeline: NeonTerminalCard) {
        val taskId = activeTaskRunId?.takeIf { it.isNotBlank() } ?: return
        if (speakerTaskRunId != taskId) {
            speakerTaskRunId = taskId
            speakerEventCursor = null
            speakerEventIds.clear()
        }
        MobileUiAsync.run(context, { payload ->
            runCatching {
                val body = JSONObject(payload)
                val messages = body.optJSONArray("messages") ?: return@runCatching
                for (index in 0 until messages.length()) {
                    val message = messages.optJSONObject(index) ?: continue
                    val sourceIds = message.optJSONArray("source_event_ids")
                    val ids = mutableListOf<String>()
                    if (sourceIds != null) for (item in 0 until sourceIds.length()) ids.add(sourceIds.optString(item))
                    if (ids.isNotEmpty() && ids.all { speakerEventIds.contains(it) }) continue
                    message.optString("text").takeIf { it.isNotBlank() }?.let { timeline.terminal.addLine("AIpinho: $it") }
                    speakerEventIds.addAll(ids)
                }
                speakerEventCursor = body.optString("latest_event_id").takeIf { it.isNotBlank() } ?: speakerEventCursor
            }
        }) {
            val response = runtime.speakerUpdates(taskId, speakerEventCursor)
            response.body.ifBlank { "{}" }
        }
    }

    private fun reloadChatViewModel(
        context: Context,
        mobileViewModels: MobileViewModelClient,
        viewModelTerminal: HumanizedViewModelTerminal,
        timeline: NeonTerminalCard,
        artifactPanel: LinearLayout,
        artifacts: ArtifactClient,
        artifactLinkRenderer: ArtifactLinkRenderer,
        tokenProvider: () -> String?,
    ) {
        MobileUiAsync.run(context, { payload ->
            lastViewModelPayload = payload
            viewModelTerminal.setPayload(payload)
            renderArtifactPanel(context, artifactPanel, artifacts, artifactLinkRenderer, tokenProvider)
            if (payload.isBlank()) timeline.terminal.addLine("Historico humanizado indisponivel.", error = true)
            else timeline.terminal.setLines(ChatPresentationRenderer().render(payload, displayMode))
        }) {
            val response = mobileViewModels.chat(activeSessionId ?: "latest")
            response.body.ifBlank { "chat_view_model_unavailable status=${response.statusCode}" }
        }
    }

    private fun showSessionsDialog(
        context: Context,
        chat: ChatClient,
        chatSessions: ChatSessionRepository,
        mobileViewModels: MobileViewModelClient,
        viewModelTerminal: HumanizedViewModelTerminal,
        timeline: NeonTerminalCard,
        artifactPanel: LinearLayout,
        artifacts: ArtifactClient,
        artifactLinkRenderer: ArtifactLinkRenderer,
        tokenProvider: () -> String?,
    ) {
        timeline.terminal.setLines(listOf("Consultando sessoes..."))
        MobileUiAsync.run(context, { payload ->
            val sessions = parseChatSessions(payload)
            if (sessions.isEmpty()) {
                AlertDialog.Builder(context)
                    .setTitle("Sessoes de chat")
                    .setMessage("Nenhuma sessao encontrada. Crie uma nova conversa para comecar.")
                    .setPositiveButton("OK", null)
                    .show()
                timeline.terminal.setLines(listOf("Nenhuma sessao encontrada."))
                return@run
            }
            openSessionsDialog(
                context = context,
                sessions = sessions,
                chat = chat,
                chatSessions = chatSessions,
                mobileViewModels = mobileViewModels,
                viewModelTerminal = viewModelTerminal,
                timeline = timeline,
                artifactPanel = artifactPanel,
                artifacts = artifacts,
                artifactLinkRenderer = artifactLinkRenderer,
                tokenProvider = tokenProvider,
            )
        }) {
            val response = chat.sessions()
            response.body.ifBlank { response.visibleText("sessions") }
        }
    }

    private fun openSessionsDialog(
        context: Context,
        sessions: List<ChatSessionSummary>,
        chat: ChatClient,
        chatSessions: ChatSessionRepository,
        mobileViewModels: MobileViewModelClient,
        viewModelTerminal: HumanizedViewModelTerminal,
        timeline: NeonTerminalCard,
        artifactPanel: LinearLayout,
        artifacts: ArtifactClient,
        artifactLinkRenderer: ArtifactLinkRenderer,
        tokenProvider: () -> String?,
    ) {
        val shell = neonDialogShell(context, "Sessoes de chat")
        val content = ScrollView(context).apply {
            setBackgroundColor(NeonColors.matrixBlack)
        }
        val list = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(
                AipinhoNeonTheme.dp(context, 8),
                AipinhoNeonTheme.dp(context, 8),
                AipinhoNeonTheme.dp(context, 8),
                AipinhoNeonTheme.dp(context, 8),
            )
        }
        content.addView(list)
        shell.addView(content, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            AipinhoNeonTheme.dp(context, 420),
        ))
        var dialog: AlertDialog? = null
        sessions.forEach { session ->
            val row = LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                background = AipinhoNeonTheme.rounded(context, fill = NeonColors.cardBlueGray, stroke = NeonColors.neonCyan, radiusDp = 14)
                setPadding(
                    AipinhoNeonTheme.dp(context, 10),
                    AipinhoNeonTheme.dp(context, 8),
                    AipinhoNeonTheme.dp(context, 10),
                    AipinhoNeonTheme.dp(context, 8),
                )
                layoutParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                ).apply { setMargins(0, 0, 0, AipinhoNeonTheme.dp(context, 8)) }
            }
            row.addView(TextView(context).apply {
                text = sessionDialogLabel(session)
                setTextColor(NeonColors.neonGreen)
                textSize = 13f
                typeface = NeonTypography.terminalTypeface
                setTextIsSelectable(true)
            })
            row.addView(LinearLayout(context).apply {
                orientation = LinearLayout.VERTICAL
                addView(LinearLayout(context).apply {
                    orientation = LinearLayout.HORIZONTAL
                    addView(NeonButton(context, "Abrir") {
                        activeSessionId = session.sessionId
                        chatSessions.saveActiveSessionId(activeSessionId)
                        lastConversation = ""
                        lastViewModelPayload = ""
                        chatSessions.saveLastConversation("")
                        timeline.terminal.setLines(listOf("Abrindo sessao ${session.title}...", "Historico mais recente primeiro."))
                        dialog?.dismiss()
                        reloadChatViewModel(context, mobileViewModels, viewModelTerminal, timeline, artifactPanel, artifacts, artifactLinkRenderer, tokenProvider)
                    })
                    addView(NeonButton(context, "Renomear") {
                        dialog?.dismiss()
                        showRenameSessionDialog(context, session, chat, timeline) {
                            showSessionsDialog(context, chat, chatSessions, mobileViewModels, viewModelTerminal, timeline, artifactPanel, artifacts, artifactLinkRenderer, tokenProvider)
                        }
                    })
                })
                addView(NeonButton(context, "Deletar") {
                    showNeonConfirmDialog(
                        context = context,
                        title = "Deletar chat",
                        message = "Deletar '${session.title}' e suas mensagens?",
                        confirmLabel = "Deletar",
                        cancelLabel = "Cancelar",
                    ) {
                            dialog?.dismiss()
                            MobileUiAsync.run(context, { resultText ->
                                if (session.sessionId == activeSessionId) {
                                    activeSessionId = null
                                    chatSessions.saveActiveSessionId(null)
                                    lastConversation = ""
                                    lastViewModelPayload = ""
                                    chatSessions.saveLastConversation("")
                                    viewModelTerminal.clear()
                                }
                                timeline.terminal.setLines(resultText.lines())
                                showSessionsDialog(context, chat, chatSessions, mobileViewModels, viewModelTerminal, timeline, artifactPanel, artifacts, artifactLinkRenderer, tokenProvider)
                            }) {
                                val response = chat.deleteSession(session.sessionId)
                                if (response.ok) "Sessao deletada: ${session.title}" else response.visibleText("delete_session")
                            }
                    }
                })
            })
            list.addView(row)
        }
        shell.addView(NeonButton(context, "Fechar") { dialog?.dismiss() }, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.WRAP_CONTENT,
            LinearLayout.LayoutParams.WRAP_CONTENT,
        ))
        dialog = AlertDialog.Builder(context)
            .setView(shell)
            .create()
        dialog.show()
        dialog.window?.setBackgroundDrawable(AipinhoNeonTheme.rounded(context, fill = NeonColors.matrixBlack, stroke = NeonColors.neonCyan, radiusDp = 20))
    }

    private fun showRenameSessionDialog(
        context: Context,
        session: ChatSessionSummary,
        chat: ChatClient,
        timeline: NeonTerminalCard,
        onDone: () -> Unit,
    ) {
        val shell = neonDialogShell(context, "Renomear chat")
        val input = EditText(context).apply {
            setText(session.title)
            setSingleLine(true)
            setTextColor(NeonColors.neonGreen)
            setHintTextColor(NeonColors.neonCyan)
            background = AipinhoNeonTheme.rounded(context, fill = NeonColors.matrixBlack, stroke = NeonColors.neonCyan, radiusDp = 12)
            setPadding(
                AipinhoNeonTheme.dp(context, 12),
                AipinhoNeonTheme.dp(context, 10),
                AipinhoNeonTheme.dp(context, 12),
                AipinhoNeonTheme.dp(context, 10),
            )
            setTextIsSelectable(true)
        }
        shell.addView(input, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT,
        ))
        var dialog: AlertDialog? = null
        shell.addView(LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            addView(NeonButton(context, "Cancelar") { dialog?.dismiss() })
            addView(NeonButton(context, "Salvar") {
                val newTitle = input.text.toString().trim()
                if (newTitle.isBlank()) {
                    timeline.terminal.setLines(listOf("Nome vazio: renomeacao cancelada."))
                    dialog?.dismiss()
                    return@NeonButton
                }
                dialog?.dismiss()
                MobileUiAsync.run(context, { resultText ->
                    timeline.terminal.setLines(resultText.lines())
                    onDone()
                }) {
                    val response = chat.renameSession(session.sessionId, newTitle)
                    if (response.ok) "Sessao renomeada para: $newTitle" else response.visibleText("rename_session")
                }
            })
        })
        dialog = AlertDialog.Builder(context)
            .setView(shell)
            .create()
        dialog.show()
        dialog.window?.setBackgroundDrawable(AipinhoNeonTheme.rounded(context, fill = NeonColors.matrixBlack, stroke = NeonColors.neonCyan, radiusDp = 20))
    }

    private fun neonDialogShell(context: Context, title: String): LinearLayout {
        return LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            background = AipinhoNeonTheme.rounded(context, fill = NeonColors.matrixBlack, stroke = NeonColors.neonCyan, radiusDp = 20)
            setPadding(
                AipinhoNeonTheme.dp(context, 16),
                AipinhoNeonTheme.dp(context, 14),
                AipinhoNeonTheme.dp(context, 16),
                AipinhoNeonTheme.dp(context, 14),
            )
            addView(TextView(context).apply {
                text = title
                setTextColor(NeonColors.neonCyan)
                textSize = 20f
                typeface = NeonTypography.terminalTypeface
                setTextIsSelectable(true)
            })
        }
    }

    private fun showNeonConfirmDialog(
        context: Context,
        title: String,
        message: String,
        confirmLabel: String,
        cancelLabel: String,
        onConfirm: () -> Unit,
    ) {
        val shell = neonDialogShell(context, title)
        shell.addView(TextView(context).apply {
            text = message
            setTextColor(NeonColors.neonGreen)
            textSize = 14f
            typeface = NeonTypography.terminalTypeface
            setTextIsSelectable(true)
        })
        var dialog: AlertDialog? = null
        shell.addView(LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            addView(NeonButton(context, cancelLabel) { dialog?.dismiss() })
            addView(NeonButton(context, confirmLabel) {
                dialog?.dismiss()
                onConfirm()
            })
        })
        dialog = AlertDialog.Builder(context)
            .setView(shell)
            .create()
        dialog.show()
        dialog.window?.setBackgroundDrawable(AipinhoNeonTheme.rounded(context, fill = NeonColors.matrixBlack, stroke = NeonColors.neonPink, radiusDp = 20))
    }

    private fun parseChatSessions(payload: String): List<ChatSessionSummary> {
        return runCatching {
            val root = JSONObject(payload)
            val sessions = root.optJSONArray("sessions") ?: return@runCatching emptyList()
            val items = mutableListOf<ChatSessionSummary>()
            for (index in 0 until sessions.length()) {
                val item = sessions.optJSONObject(index) ?: continue
                val sessionId = item.optString("session_id").takeIf { it.isNotBlank() } ?: continue
                items.add(
                    ChatSessionSummary(
                        sessionId = sessionId,
                        title = item.optString("title").takeIf { it.isNotBlank() } ?: "Nova conversa",
                        messageCount = item.optInt("message_count", 0),
                        updatedAt = item.optString("updated_at"),
                    )
                )
            }
            items.sortedByDescending { it.updatedAt }
        }.getOrDefault(emptyList())
    }

    private fun sessionDialogLabel(session: ChatSessionSummary): String {
        val active = if (session.sessionId == activeSessionId) " [ativa]" else ""
        return "${session.title}$active\nMensagens: ${session.messageCount}\nAtualizada: ${session.updatedAt}\n${session.sessionId}"
    }

    private fun reloadChatViewModelStabilized(
        context: Context,
        mobileViewModels: MobileViewModelClient,
        viewModelTerminal: HumanizedViewModelTerminal,
        timeline: NeonTerminalCard,
        artifactPanel: LinearLayout,
        artifacts: ArtifactClient,
        artifactLinkRenderer: ArtifactLinkRenderer,
        tokenProvider: () -> String?,
        expectedMinimumMessages: Int,
    ) {
        MobileUiAsync.run(context, { payload ->
            lastViewModelPayload = payload
            viewModelTerminal.setPayload(payload)
            renderArtifactPanel(context, artifactPanel, artifacts, artifactLinkRenderer, tokenProvider)
            if (payload.isBlank()) timeline.terminal.addLine("Historico humanizado indisponivel.", error = true)
            else timeline.terminal.setLines(ChatPresentationRenderer().render(payload, displayMode))
        }) {
            var latest = ""
            repeat(ChatAutoRefreshPolicy.stabilizationAttempts) { attempt ->
                val response = mobileViewModels.chat(activeSessionId ?: "latest")
                latest = response.body.ifBlank { "chat_view_model_unavailable status=${response.statusCode}" }
                if (countPresentationMessages(latest) >= expectedMinimumMessages) return@run latest
                if (attempt < ChatAutoRefreshPolicy.stabilizationAttempts - 1) {
                    Thread.sleep(ChatAutoRefreshPolicy.stabilizationDelayMs)
                }
            }
            latest
        }
    }

    private fun ApiResponse.visibleText(operation: String): String {
        if (ok && body.isNotBlank()) return body
        val lines = mutableListOf("operation=$operation", "status=$statusCode")
        if (body.isNotBlank()) lines.add(body)
        error?.takeIf { it.isNotBlank() }?.let { lines.add("error=$it") }
        if (lines.size == 2) lines.add("Resposta vazia do backend.")
        return lines.joinToString("\n")
    }

    private fun ApiResponse.chatSendVisibleText(sessionId: String): String {
        if (!ok || body.isBlank()) return visibleText("send_message")
        return chatSendVisibleTextFromPayload(body, sessionId)
    }

    private fun chatSendVisibleTextFromPayload(payload: String, sessionId: String): String {
        if (payload.isBlank()) return "Resposta vazia do backend."
        return runCatching {
            val root = JSONObject(payload)
            val assistant = root.optJSONObject("assistant_message")
            val chatResponse = root.optJSONObject("chat_response")
            val status = chatResponse?.optString("status")?.takeIf { it.isNotBlank() } ?: root.optString("status", "unknown")
            val text = assistant?.optString("content")?.takeIf { it.isNotBlank() } ?: "Resposta do assistente ainda nao disponivel."
            listOf(
                "Mensagem enviada.",
                "Sessao persistente: $sessionId",
                "Status: $status",
                "Assistente:",
                text,
                "Raw oculto por padrao. Historico humanizado atualizado no Chat cockpit.",
            ).joinToString("\n")
        }.getOrElse { payload }
    }

    private fun extractSessionId(value: String): String? {
        return ChatSessionIdExtractor.extract(value)
    }

    private fun approvalIdFromPayload(payload: String): String? {
        return metadataValue(payload, "approval_id")
            ?: Regex("approval_[A-Za-z0-9_-]+").find(payload)?.value
    }

    private fun taskIdFromPayload(payload: String): String? {
        return metadataValue(payload, "task_id")
            ?: Regex("task_run_[A-Za-z0-9_-]+|task_[A-Za-z0-9_-]+").find(payload)?.value
    }

    private fun metadataValue(payload: String, key: String): String? {
        return runCatching {
            fun valid(value: String): String? = value.trim()
                .takeUnless { it.isBlank() || it.equals("null", ignoreCase = true) || it.equals("none", ignoreCase = true) }
            val root = JSONObject(payload)
            valid(root.optString(key))?.let { return@runCatching it }
            val cards = root.optJSONArray("cards")
            if (cards != null) {
                for (index in cards.length() - 1 downTo 0) {
                    val card = cards.optJSONObject(index) ?: continue
                    valid(card.optString(key))?.let { return@runCatching it }
                    val metadata = card.optJSONObject("metadata")
                    if (metadata != null) valid(metadata.optString(key))?.let { return@runCatching it }
                }
            }
            null
        }.getOrNull()
    }

    private fun countPresentationMessages(payload: String): Int {
        return runCatching {
            JSONObject(payload)
                .optJSONObject("presentation")
                ?.optJSONArray("messages")
                ?.length() ?: 0
        }.getOrDefault(0)
    }

    private fun holdOperationalFeedback() {
        operationFeedbackUntilMs = System.currentTimeMillis() + ChatAutoRefreshPolicy.operationFeedbackHoldMs
    }

    private fun extractArtifactLink(payload: String): Triple<String?, String?, String?> {
        return runCatching {
            val root = JSONObject(payload)
            val chatResponse = root.optJSONObject("chat_response") ?: root
            val links = chatResponse.optJSONArray("artifact_links")
            val link = links?.optJSONObject(0)
            val artifactId = link?.optString("artifact_id")?.takeIf { it.isNotBlank() }
                ?: chatResponse.optString("artifact_id").takeIf { it.isNotBlank() }
            val filename = link?.optString("filename")?.takeIf { it.isNotBlank() }
                ?: chatResponse.optString("artifact_filename").takeIf { it.isNotBlank() }
                ?: "artifact"
            val contentType = link?.optString("content_type")?.takeIf { it.isNotBlank() }
                ?: chatResponse.optString("artifact_content_type").takeIf { it.isNotBlank() }
                ?: "application/octet-stream"
            Triple(artifactId, filename, contentType)
        }.getOrDefault(Triple(null, null, null))
    }

    private fun syncLatestArtifactFromChatResponse(payload: String, repository: ChatSessionRepository) {
        val (artifactId, filename, contentType) = extractArtifactLink(payload)
        if (artifactId.isNullOrBlank()) return
        latestArtifactId = artifactId
        latestArtifactFilename = filename ?: "artifact"
        latestArtifactContentType = contentType ?: "application/octet-stream"
        repository.saveLatestArtifact(latestArtifactId, latestArtifactFilename, latestArtifactContentType)
    }

    private fun renderArtifactPanel(
        context: Context,
        container: LinearLayout,
        artifactClient: ArtifactClient,
        renderer: ArtifactLinkRenderer,
        tokenProvider: () -> String?,
    ) {
        renderer.renderInto(
            context = context,
            container = container,
            payload = artifactPanelPayload(),
            artifactClient = artifactClient,
            tokenProvider = tokenProvider,
            fallbackArtifactId = latestArtifactId,
            fallbackFilename = latestArtifactFilename,
            fallbackContentType = latestArtifactContentType,
        )
    }

    private fun artifactPanelPayload(): String {
        val latest = latestArtifactId
        val payload = lastViewModelPayload.ifBlank { lastConversation }
        if (!latest.isNullOrBlank() && payload.isNotBlank() && !payload.contains(latest)) {
            return lastConversation
        }
        return payload
    }

    private fun attachmentName(context: Context, uri: Uri): String {
        context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
            val index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (index >= 0 && cursor.moveToFirst()) return cursor.getString(index)
        }
        return uri.lastPathSegment?.substringAfterLast('/')?.takeIf { it.isNotBlank() } ?: "mobile_attachment.txt"
    }

    private fun readTextAttachment(context: Context, uri: Uri): String {
        return context.contentResolver.openInputStream(uri)?.use { stream ->
            stream.bufferedReader(Charsets.UTF_8).use { it.readText() }
        } ?: throw IllegalArgumentException("attachment_stream_unavailable")
    }
}
