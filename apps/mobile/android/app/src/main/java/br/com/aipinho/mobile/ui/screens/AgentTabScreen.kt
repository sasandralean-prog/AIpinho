package br.com.aipinho.mobile.ui.screens

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.provider.OpenableColumns
import android.text.Selection
import android.text.SpannableString
import android.util.Base64
import android.view.MotionEvent
import android.view.View
import android.view.ViewParent
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import br.com.aipinho.mobile.data.AgentSessionRepository
import br.com.aipinho.mobile.data.ChatAttachmentBridge
import br.com.aipinho.mobile.data.SettingsRepository
import br.com.aipinho.mobile.data.TokenRepository
import br.com.aipinho.mobile.models.AgentMobileState
import br.com.aipinho.mobile.models.AgentTabConfig
import br.com.aipinho.mobile.network.AgentApiClient
import br.com.aipinho.mobile.network.ApiResponse
import br.com.aipinho.mobile.network.ArtifactClient
import br.com.aipinho.mobile.ui.components.AgentArtifactPanel
import br.com.aipinho.mobile.ui.components.MessageCopySupport
import br.com.aipinho.mobile.ui.components.NeonAgentDialogs
import br.com.aipinho.mobile.ui.components.NeonActionGroup
import br.com.aipinho.mobile.ui.components.NeonButton
import br.com.aipinho.mobile.ui.components.NeonCyberCard
import br.com.aipinho.mobile.ui.components.MobileScreenScaffold
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme
import br.com.aipinho.mobile.ui.theme.NeonColors
import br.com.aipinho.mobile.ui.theme.NeonTypography
import br.com.aipinho.mobile.utils.ClipboardUtils
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class AgentTabScreen(
    private val config: AgentTabConfig,
    private val sharedState: AgentMobileState = AgentMobileState(),
) {
    private val handler = Handler(Looper.getMainLooper())
    private var client: AgentApiClient? = null
    private var sessionRepository: AgentSessionRepository? = null
    private var sessionId: String? = null
    private var activeRunId: String? = null
    private var latestEventId: String? = null
    private var displayMode = "normal"
    private var latestCopyableMessage: String? = null
    private var attachedArtifactIds = mutableListOf<String>()
    private var attachedArtifactNames = mutableListOf<String>()
    private lateinit var root: LinearLayout
    private lateinit var status: TextView
    private lateinit var sessionState: TextView
    private lateinit var timeline: TextView
    private lateinit var timelineScroll: ScrollView
    private lateinit var searchInput: EditText
    private lateinit var newMessageNotice: TextView
    private lateinit var prompt: EditText
    private lateinit var workspace: EditText
    private lateinit var attachmentState: TextView
    private lateinit var artifactPanel: AgentArtifactPanel
    private lateinit var autorun: CheckBox
    private lateinit var autoreview: CheckBox
    private lateinit var autoapproval: CheckBox
    private var lastRenderedTimelineText = ""

    fun build(context: Context): View {
        val profile = SettingsRepository(context).loadProfile()
        val tokens = TokenRepository(context)
        client = AgentApiClient(profile, { tokens.load() }, config)
        sessionRepository = AgentSessionRepository(context)
        sessionId = sessionRepository?.loadSelectedSession(config.agentId)
        root = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            AipinhoNeonTheme.applyScreen(this)
        }
        buildHeader(context)
        buildSessionBar(context)
        buildTimeline(context)
        buildComposer(context)
        artifactPanel = AgentArtifactPanel(context, ArtifactClient(profile) { tokens.load() })
        artifactPanel.renderInputs(attachedArtifactNames)
        root.addView(artifactPanel)
        bindLifecycle()
        ChatAttachmentBridge.onSelected = { attachUri(context, it) }
        ensureSession()
        return MobileScreenScaffold(context, root)
    }

    private fun buildHeader(context: Context) {
        root.addView(NeonCyberCard(context, config.displayName, "${config.providerLabel} | Governed").apply {
            config.externalProviderNotice?.let(::addBody)
        })
        status = text(context, "Consultando backend...")
        root.addView(NeonCyberCard(context, "Estado").apply { addView(status) })
    }

    private fun buildSessionBar(context: Context) {
        val card = NeonCyberCard(context, "Sessao", "Historico persistente e separado por agente")
        sessionState = card.bodyView("Nenhuma sessao selecionada.")
        card.addView(NeonActionGroup(context, listOf(
            button(context, "Sessoes") { showSessions(context) },
            button(context, "Nova") { createSession() },
            button(context, "Atualizar") { refreshAll() },
        )))
        root.addView(card)
    }

    private fun buildTimeline(context: Context) {
        val card = NeonCyberCard(context, "Chat ${config.displayName}", "Normal | Detalhes | Raw sanitizado")
        card.addView(NeonActionGroup(context, listOf(
            button(context, "Normal") { setMode("normal") },
            button(context, "Detalhes") { setMode("details") },
            button(context, "Raw") {
                NeonAgentDialogs.confirm(
                    context,
                    "Raw sanitizado",
                    "Mostrar dados tecnicos sanitizados desta sessao?",
                ) { setMode("raw") }
            },
        )))
        card.addView(NeonActionGroup(context, listOf(
            button(context, "Copiar conversa") { copyConversation(context) },
            button(context, "Exportar") { exportConversation(context) },
            button(context, "Limpar tela") { clearConversationView() },
            button(context, "Expandir") { expandConversation(context) },
        )))
        searchInput = EditText(context).apply {
            hint = "Buscar na conversa"
            setTextColor(NeonColors.neonGreen)
            setHintTextColor(NeonColors.neonCyan)
            setSingleLine(true)
            background = AipinhoNeonTheme.rounded(context, fill = NeonColors.matrixBlack, stroke = NeonColors.neonCyan)
            setPadding(16, 10, 16, 10)
        }
        card.addView(searchInput)
        card.addView(NeonActionGroup(context, listOf(
            button(context, "Buscar") { searchConversation() },
            button(context, "Copiar mensagem") {
                MessageCopySupport.copySelectionOrLatest(
                    context,
                    timeline,
                    latestCopyableMessage,
                    "Mensagem ${config.displayName}",
                )
            },
        )))
        newMessageNotice = card.bodyView("")
        timeline = text(context, "").apply {
            setTextIsSelectable(true)
            setPadding(16, 14, 16, 14)
            background = AipinhoNeonTheme.rounded(
                context,
                fill = NeonColors.matrixBlack,
                stroke = NeonColors.neonCyan,
                radiusDp = 14,
            )
            setOnTouchListener { _, event ->
                keepTerminalGestureInsideScroll(event)
            }
        }
        timelineScroll = TerminalScrollView(context).apply {
            isFillViewport = true
            isVerticalScrollBarEnabled = true
            isSmoothScrollingEnabled = true
            overScrollMode = View.OVER_SCROLL_IF_CONTENT_SCROLLS
            addView(timeline)
            
        }
        card.addView(
            timelineScroll,

            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                AipinhoNeonTheme.dp(context, 360),
            ),
        )
        root.addView(card)
    }

    private fun buildComposer(context: Context) {
        val card = NeonCyberCard(context, "Nova mensagem")
        workspace = EditText(context).apply {
            hint = "Workspace opcional"
            setTextColor(NeonColors.neonGreen)
            setHintTextColor(NeonColors.neonCyan)
            background = AipinhoNeonTheme.rounded(context, fill = NeonColors.matrixBlack, stroke = NeonColors.neonCyan)
            visibility = if (config.supportsWorkspace) View.VISIBLE else View.GONE
        }
        prompt = EditText(context).apply {
            hint = "Mensagem para ${config.displayName}"
            setTextColor(NeonColors.neonGreen)
            setHintTextColor(NeonColors.neonCyan)
            minLines = 3
            setTextIsSelectable(true)
            background = AipinhoNeonTheme.rounded(context, fill = NeonColors.matrixBlack, stroke = NeonColors.neonCyan)
        }
        card.addView(workspace)
        card.addView(prompt)
        attachmentState = card.bodyView("Nenhum anexo.")
        val primaryActions = mutableListOf(
            button(context, "Enviar") { send("send") },
        )
        if (config.supportsPlan) primaryActions.add(button(context, "Plano") { send("plan") })
        if (config.supportsPreview) primaryActions.add(button(context, "Preview") { send("preview") })
        card.addView(NeonActionGroup(context, primaryActions))
        val secondaryActions = mutableListOf(
            button(context, "Anexar") { openAttachmentPicker(context) },
            button(context, "Cancelar run") { cancelRun() },
        )
        if (config.supportsRoutePreview) secondaryActions.add(button(context, "Ver rota") { send("route") })
        card.addView(NeonActionGroup(context, secondaryActions))
        autorun = toggle(context, "Autorun", true)
        autoreview = toggle(context, "Auto review", true)
        autoapproval = toggle(context, "Auto approval governado", true)
        card.addView(autorun)
        card.addView(autoreview)
        card.addView(autoapproval)
        root.addView(card)
    }

    private fun bindLifecycle() {
        val polling = object : Runnable {
            override fun run() {
                if (!sessionId.isNullOrBlank()) refreshViewModel()
                handler.postDelayed(this, 5000)
            }
        }
        root.addOnAttachStateChangeListener(object : View.OnAttachStateChangeListener {
            override fun onViewAttachedToWindow(view: View) {
                handler.removeCallbacksAndMessages(null)
                handler.post(polling)
            }

            override fun onViewDetachedFromWindow(view: View) {
                handler.removeCallbacksAndMessages(null)
            }
        })
    }

    private fun ensureSession() {
        val api = client ?: return
        Thread {
            val sessions = api.sessions()
            val items = parseSessions(sessions)
            val stored = sessionId
            sessionId = items.firstOrNull { it.first == stored }?.first
                ?: items.firstOrNull()?.first
            if (sessionId == null) {
                val created = api.createSession()
                sessionId = created.sessionId()
            }
            rememberSession()
            refreshAll()
        }.start()
    }

    private fun createSession() {
        val api = client ?: return
        Thread {
            val created = api.createSession()
            if (created.ok) {
                sessionId = created.sessionId()
                activeRunId = null
                latestEventId = null
                attachedArtifactIds.clear()
                attachedArtifactNames.clear()
                rememberSession()
            }
            refreshAll()
        }.start()
    }

    private fun showSessions(context: Context) {
        val api = client ?: return
        Thread {
            val sessions = parseSessions(api.sessions())
            timeline.post {
                NeonAgentDialogs.sessionList(
                    context = context,
                    title = "Sessoes ${config.displayName}",
                    sessions = sessions,
                    onOpen = { selected ->
                        sessionId = selected
                        activeRunId = null
                        latestEventId = null
                        rememberSession()
                        refreshAll()
                    },
                    onCreate = ::createSession,
                    onRename = { selected, title ->
                        Thread {
                            api.renameSession(selected, title)
                            if (sessionId == selected) refreshAll()
                        }.start()
                    },
                    onDelete = { selected ->
                        Thread {
                            api.deleteSession(selected)
                            if (sessionId == selected) {
                                sessionId = null
                                rememberSession()
                                ensureSession()
                            } else {
                                refreshAll()
                            }
                        }.start()
                    },
                )
            }
        }.start()
    }

    private fun send(mode: String) {
        val api = client ?: return
        val selected = sessionId ?: return
        val content = prompt.text.toString().trim()
        if (content.isBlank()) return
        val workspaceValue = workspace.text.toString().trim()
        prompt.setText("")
        status.text = "Enviando para ${config.displayName}..."
        Thread {
            val result = when (mode) {
                "plan" -> api.plan(selected, content, workspaceValue)
                "preview" -> api.preview(selected, content, workspaceValue)
                "route" -> api.routePreview(selected, content, workspaceValue, attachedArtifactIds)
                else -> api.send(
                    selected,
                    content,
                    workspaceValue,
                    attachedArtifactIds,
                    autorun.isChecked,
                    autoreview.isChecked,
                    autoapproval.isChecked,
                )
            }
            if (!result.ok) {
                timeline.post { status.text = "Falha controlada: ${result.humanError()}" }
            }
            attachedArtifactIds.clear()
            attachedArtifactNames.clear()
            artifactPanel.post { artifactPanel.renderInputs(attachedArtifactNames) }
            refreshAll()
        }.start()
    }

    private fun refreshAll() {
        refreshStatus()
        refreshViewModel()
        refreshArtifacts()
    }

    private fun refreshArtifacts() {
        val api = client ?: return
        val selected = sessionId ?: return
        Thread {
            val response = api.artifacts(selected)
            artifactPanel.post {
                artifactPanel.renderInputs(attachedArtifactNames)
                artifactPanel.renderPayload(response.body)
            }
        }.start()
    }

    private fun refreshStatus() {
        val api = client ?: return
        Thread {
            val health = api.health()
            val configStatus = api.configStatus()
            status.post {
                status.text = buildString {
                    append(if (health.ok) "Online" else "Indisponivel")
                    append("\nAgente: ${config.displayName}")
                    append("\nProvider: ${config.providerLabel}")
                    append("\nModo: $displayMode")
                    append("\nPolling: Universal Task Session / 5s")
                    if (!configStatus.ok) append("\nConfig: ${configStatus.humanError()}")
                }
            }
        }.start()
    }

    private fun refreshViewModel() {
        val api = client ?: return
        val selected = sessionId ?: return
        Thread {
            val response = api.viewModel(selected, latestEventId, displayMode)
            val messagesFallback = if (response.ok) null else api.messages(selected)
            timeline.post {
                sessionState.text = "Sessao ativa: $selected\nRun: ${activeRunId ?: "nenhum"}"
                if (response.ok) {
                    val root = JSONObject(response.body)
                    activeRunId = findString(root, "active_run", "run_id")
                        ?: root.optString("active_run_id").takeIf { it.isNotBlank() }
                    latestEventId = root.optString("latest_event_id").takeIf { it.isNotBlank() }
                        ?: latestEventId
                    sharedState.selectedSessionByAgent[config.agentId] = selected
                    activeRunId?.let { sharedState.activeRunBySession[selected] = it }
                    latestEventId?.let { sharedState.latestEventBySession[selected] = it }
                    updateTimelineText(renderViewModel(root))
                    latestCopyableMessage = latestAssistantMessage(root)
                } else if (messagesFallback?.ok == true) {
                    updateTimelineText(renderMessages(JSONObject(messagesFallback.body).optJSONArray("messages")))
                    latestCopyableMessage = latestAssistantMessage(
                        JSONObject().put("messages", JSONObject(messagesFallback.body).optJSONArray("messages"))
                    )
                } else {
                    updateTimelineText("Nao consegui carregar a sessao.\n${response.humanError()}")
                }
            }
        }.start()
    }

    private fun renderViewModel(root: JSONObject): String {
        if (displayMode == "raw") return root.toString(2)
        val messages = root.optJSONArray("messages")
            ?: root.optJSONObject("timeline")?.optJSONArray("messages")
            ?: JSONArray()
        val events = root.optJSONArray("events")
            ?: root.optJSONObject("timeline")?.optJSONArray("events")
            ?: JSONArray()
        return buildString {
            append(renderMessages(messages))
            if (displayMode == "normal") {
                val bridgeEvents = renderImportantEvents(events, details = false)
                if (bridgeEvents.isNotBlank()) {
                    append("\nEventos\n")
                    append(bridgeEvents)
                }
                append(renderDelegation(root))
            }
            if (displayMode == "details") {
                if (events.length() > 0) append("\nEventos sanitizados\n")
                append(renderImportantEvents(events, details = true, includeAll = true))
                val active = root.optJSONObject("active_run")
                if (active != null) {
                    append("Run\n")
                    append("id: ${active.optString("run_id")}\n")
                    append("status: ${active.optString("status")}\n")
                    append("delegation: ${active.optString("delegation_id", "nenhuma")}\n")
                }
                append(renderDelegation(root))
            }
        }.ifBlank { "Ainda nao ha mensagens nesta sessao." }
    }

    private fun renderDelegation(root: JSONObject): String {
        val delegation = root.optJSONObject("delegation")
            ?: root.optJSONObject("active_run")?.optJSONObject("delegation")
        val active = root.optJSONObject("active_run")
        val delegationId = firstNonBlank(
            delegation?.optString("delegation_id").orEmpty(),
            active?.optString("delegation_id").orEmpty(),
        )
        val isExternal = config.externalProviderNotice != null || config.providerLabel.contains("Cloud", ignoreCase = true)
        if (delegationId.isBlank()) {
            return if (isExternal) {
                "\nDelegation\nResposta direta do Provider\nSem delegacao\n"
            } else {
                ""
            }
        }
        return buildString {
            append("\nDelegation\n")
            append("Status: Delegado\n")
            append("Delegation ID: $delegationId\n")
            append("Executor: ${delegation?.optString("executor", "aipinho") ?: "aipinho"}\n")
            append("Child run: ${delegation?.optString("child_run_id", active?.optString("child_run_id", "nenhum") ?: "nenhum")}\n")
            append("Polling: ${delegation?.optInt("polling_count", 0) ?: 0}\n")
            append("Evidence: ${delegation?.optJSONArray("evidence_refs")?.length() ?: 0}\n")
            append("Review: ${delegation?.optString("review_status", "not_started") ?: "not_started"}\n")
        }
    }

    private fun renderImportantEvents(events: JSONArray, details: Boolean, includeAll: Boolean = false): String = buildString {
        for (index in 0 until events.length()) {
            val event = events.optJSONObject(index) ?: continue
            if (!includeAll && !isImportantTimelineEvent(event)) continue
            append("[${event.optString("severity", "info")}] ")
            append(event.optString("title", event.optString("event_type", "evento")))
            append('\n')
            append(eventText(event))
            if (details) {
                val status = event.optString("status").takeIf { it.isNotBlank() }
                val eventType = event.optString("event_type").takeIf { it.isNotBlank() }
                status?.let { append("\nstatus: $it") }
                eventType?.let { append("\ntipo: $it") }
            }
            append("\n\n")
        }
    }

    private fun isImportantTimelineEvent(event: JSONObject): Boolean {
        val eventType = event.optString("event_type")
        val severity = event.optString("severity")
        val status = event.optString("status")
        return severity in setOf("warning", "error") ||
            status in setOf("blocked", "failed", "pending_approval", "validation_failed", "completed") ||
            eventType.contains("delegation", ignoreCase = true) ||
            eventType.contains("artifact", ignoreCase = true) ||
            eventType.contains("approval", ignoreCase = true) ||
            eventType.contains("validation", ignoreCase = true)
    }

    private fun renderMessages(messages: JSONArray?): String = buildString {
        for (index in 0 until (messages?.length() ?: 0)) {
            val item = messages?.optJSONObject(index) ?: continue
            val role = item.optString("role")
            val label = when (role) {
                "user" -> "Voce"
                "error" -> "${config.displayName} | erro"
                "system" -> "${config.displayName} | sistema"
                else -> config.displayName
            }
            val content = messageText(item)
            append(label).append('\n')
            append(content.ifBlank { "Mensagem sem texto renderizavel." }).append("\n\n")
        }
    }

    private fun parseSessions(response: ApiResponse): List<Pair<String, String>> {
        if (!response.ok) return emptyList()
        val items = JSONObject(response.body).optJSONArray("sessions") ?: return emptyList()
        return buildList {
            for (index in 0 until items.length()) {
                val item = items.optJSONObject(index) ?: continue
                val id = item.optString("session_id").takeIf { it.isNotBlank() } ?: continue
                add(id to item.optString("title", config.displayName))
            }
        }
    }

    private fun latestAssistantMessage(root: JSONObject): String? {
        val messages = root.optJSONArray("messages")
            ?: root.optJSONObject("timeline")?.optJSONArray("messages")
            ?: return null
        for (index in messages.length() - 1 downTo 0) {
            val item = messages.optJSONObject(index) ?: continue
            if (item.optString("role") != "user") {
                return messageText(item).takeIf { it.isNotBlank() }
            }
        }
        return null
    }

    private fun setMode(mode: String) {
        displayMode = mode
        latestEventId = null
        refreshViewModel()
    }

    private fun cancelRun() {
        val api = client ?: return
        val runId = activeRunId
        if (runId.isNullOrBlank()) {
            status.text = "Nao ha run ativo para cancelar."
            return
        }
        Thread {
            val response = api.cancelRun(runId)
            status.post { status.text = if (response.ok) "Cancelamento solicitado." else response.humanError() }
            refreshViewModel()
        }.start()
    }

    private fun openAttachmentPicker(context: Context) {
        val activity = context as? Activity ?: return
        activity.startActivityForResult(
            Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                type = "*/*"
                addCategory(Intent.CATEGORY_OPENABLE)
                putExtra(
                    Intent.EXTRA_MIME_TYPES,
                    arrayOf(
                        "image/png",
                        "image/jpeg",
                        "image/webp",
                        "text/plain",
                        "text/markdown",
                        "application/json",
                        "application/pdf",
                    ),
                )
            },
            ChatAttachmentBridge.REQUEST_CODE,
        )
    }

    private fun attachUri(context: Context, uriText: String) {
        val api = client ?: return
        val selected = sessionId ?: return
        Thread {
            val uri = Uri.parse(uriText)
            val filename = attachmentName(context, uri)
            val contentType = context.contentResolver.getType(uri) ?: "text/plain"
            val bytes = context.contentResolver.openInputStream(uri)
                ?.use { it.readBytes() }
                ?: ByteArray(0)
            val textLike = contentType.startsWith("text/") || contentType == "application/json"
            val encoded = if (textLike) bytes.toString(Charsets.UTF_8) else Base64.encodeToString(bytes, Base64.NO_WRAP)
            val response = api.uploadTextArtifact(
                selected,
                filename,
                contentType,
                encoded,
                activeRunId,
                if (textLike) "text" else "base64",
            )
            val artifactId = if (response.ok) {
                JSONObject(response.body).optJSONObject("artifact")?.optString("artifact_id")
            } else null
            attachmentState.post {
                if (!artifactId.isNullOrBlank()) {
                    attachedArtifactIds.add(artifactId)
                    attachedArtifactNames.add(filename)
                    sharedState.attachedArtifactIdsBySession
                        .getOrPut(selected) { mutableListOf() }
                        .add(artifactId)
                    attachmentState.text = "Anexo pronto: $filename"
                    artifactPanel.renderInputs(attachedArtifactNames)
                } else {
                    attachmentState.text = "Falha ao anexar: ${response.humanError()}"
                }
            }
        }.start()
    }

    private fun attachmentName(context: Context, uri: Uri): String {
        context.contentResolver.query(uri, null, null, null, null)?.use {
            val index = it.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (index >= 0 && it.moveToFirst()) return it.getString(index)
        }
        return uri.lastPathSegment?.substringAfterLast('/') ?: "attachment.txt"
    }

    private fun rememberSession() {
        val selected = sessionId
        sessionRepository?.saveSelectedSession(config.agentId, selected)
        if (!selected.isNullOrBlank()) sharedState.selectedSessionByAgent[config.agentId] = selected
    }

    private fun keepTerminalGestureInsideScroll(event: MotionEvent): Boolean {
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN,
            MotionEvent.ACTION_MOVE,
            MotionEvent.ACTION_POINTER_DOWN -> {
                requestAncestorsDisallowIntercept(timelineScroll.parent, true)
            }
            MotionEvent.ACTION_UP,
            MotionEvent.ACTION_CANCEL,
            MotionEvent.ACTION_POINTER_UP -> {
                requestAncestorsDisallowIntercept(timelineScroll.parent, false)
            }
        }
        return false
    }

    private fun updateTimelineText(value: String) {
        val wasAtBottom = !timelineScroll.canScrollVertically(1)
        val changed = value != lastRenderedTimelineText
        timeline.text = value
        lastRenderedTimelineText = value
        if (wasAtBottom) {
            timelineScroll.post {
                timelineScroll.fullScroll(View.FOCUS_DOWN)
                newMessageNotice.text = ""
            }
        } else if (changed) {
            newMessageNotice.text = "Nova mensagem"
        }
    }

    private fun copyConversation(context: Context) {
        ClipboardUtils.copy(context, "Conversa ${config.displayName}", timeline.text.toString())
        newMessageNotice.text = "Conversa copiada"
    }

    private fun exportConversation(context: Context) {
        val exports = File(context.filesDir, "operator_exports").apply { mkdirs() }
        val filename = "${config.agentId}_${System.currentTimeMillis()}.txt"
        File(exports, filename).writeText(timeline.text.toString(), Charsets.UTF_8)
        newMessageNotice.text = "Exportado: $filename"
    }

    private fun clearConversationView() {
        timeline.text = ""
        lastRenderedTimelineText = ""
        newMessageNotice.text = ""
    }

    private fun expandConversation(context: Context) {
        val shell = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            background = AipinhoNeonTheme.rounded(
                context,
                fill = NeonColors.matrixBlack,
                stroke = NeonColors.neonCyan,
                radiusDp = 20,
            )
            setPadding(16, 14, 16, 14)
            addView(text(context, "Conversa ${config.displayName}").apply {
                setTextColor(NeonColors.neonCyan)
                textSize = 20f
            })
            addView(ScrollView(context).apply {
                addView(text(context, timeline.text.toString()).apply {
                    setPadding(16, 14, 16, 14)
                    background = AipinhoNeonTheme.rounded(
                        context,
                        fill = NeonColors.matrixBlack,
                        stroke = NeonColors.neonCyan,
                        radiusDp = 14,
                    )
                })
            }, LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                AipinhoNeonTheme.dp(context, 620),
            ))
        }
        android.app.AlertDialog.Builder(context)
            .setView(shell)
            .create()
            .also { dialog ->
                dialog.setOnShowListener {
                    dialog.window?.setBackgroundDrawable(
                        AipinhoNeonTheme.rounded(
                            context,
                            fill = NeonColors.matrixBlack,
                            stroke = NeonColors.neonCyan,
                            radiusDp = 20,
                        )
                    )
                }
                dialog.show()
            }
    }

    private fun searchConversation() {
        val query = searchInput.text.toString().trim()
        val content = lastRenderedTimelineText
        if (query.isBlank()) {
            newMessageNotice.text = ""
            return
        }
        val index = content.indexOf(query, ignoreCase = true)
        if (index < 0) {
            newMessageNotice.text = "Busca sem resultado"
            return
        }
        val span = SpannableString(content)
        Selection.setSelection(span, index, index + query.length)
        timeline.text = span
        newMessageNotice.text = "Busca: $query"
    }

    private fun requestAncestorsDisallowIntercept(parent: ViewParent?, disallow: Boolean) {
        var current = parent
        while (current != null) {
            current.requestDisallowInterceptTouchEvent(disallow)
            current = current.parent
        }
    }

    private fun messageText(item: JSONObject): String =
        firstNonBlank(
            item.optString("content"),
            item.optString("content_sanitized"),
            item.optString("text"),
            item.optString("message"),
            item.optString("human_message"),
            item.optString("body"),
            item.optString("summary"),
            item.optString("copy_text"),
        )

    private fun eventText(item: JSONObject): String =
        firstNonBlank(
            item.optString("human_message"),
            item.optString("human_summary"),
            item.optString("body"),
            item.optString("summary"),
            item.optString("technical_summary_sanitized"),
            item.optString("copy_text"),
        )

    private fun firstNonBlank(vararg values: String): String =
        values.firstOrNull { it.isNotBlank() }.orEmpty()

    private fun button(context: Context, label: String, action: () -> Unit) =
        NeonButton(context, label, onClick = action)

    private fun toggle(context: Context, label: String, checked: Boolean) = CheckBox(context).apply {
        text = label
        isChecked = checked
        setTextColor(NeonColors.neonGreen)
        buttonTintList = android.content.res.ColorStateList.valueOf(NeonColors.neonCyan)
    }

    private fun text(context: Context, value: String) = TextView(context).apply {
        text = value
        setTextColor(NeonColors.neonGreen)
        textSize = 15f
        typeface = NeonTypography.terminalTypeface
        setTextIsSelectable(true)
    }

    private fun ApiResponse.sessionId(): String? =
        runCatching { JSONObject(body).optJSONObject("session")?.optString("session_id") }
            .getOrNull()
            ?.takeIf { it.isNotBlank() }

    private fun ApiResponse.humanError(): String =
        error?.takeIf { it.isNotBlank() }
            ?: body.takeIf { it.isNotBlank() }
            ?: "HTTP $statusCode"

    private fun findString(root: JSONObject, objectName: String, field: String): String? =
        root.optJSONObject(objectName)?.optString(field)?.takeIf { it.isNotBlank() }

    private class TerminalScrollView(context: Context) : ScrollView(context) {
        override fun dispatchTouchEvent(event: MotionEvent): Boolean {
            val childHeight = getChildAt(0)?.height ?: 0
            val shouldOwnGesture = childHeight > height || canScrollVertically(-1) || canScrollVertically(1)
            when (event.actionMasked) {
                MotionEvent.ACTION_DOWN,
                MotionEvent.ACTION_MOVE,
                MotionEvent.ACTION_POINTER_DOWN -> {
                    requestAncestorsDisallowIntercept(parent, shouldOwnGesture)
                }
                MotionEvent.ACTION_UP,
                MotionEvent.ACTION_CANCEL,
                MotionEvent.ACTION_POINTER_UP -> {
                    requestAncestorsDisallowIntercept(parent, false)
                }
            }
            return super.dispatchTouchEvent(event)
        }

        private fun requestAncestorsDisallowIntercept(parent: ViewParent?, disallow: Boolean) {
            var current = parent
            while (current != null) {
                current.requestDisallowInterceptTouchEvent(disallow)
                current = current.parent
            }
        }
    }
}
