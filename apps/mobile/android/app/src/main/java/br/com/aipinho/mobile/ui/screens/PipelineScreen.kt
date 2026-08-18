package br.com.aipinho.mobile.ui.screens

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.CheckBox
import android.widget.LinearLayout
import br.com.aipinho.mobile.data.SettingsRepository
import br.com.aipinho.mobile.data.TokenRepository
import br.com.aipinho.mobile.network.MobileViewModelClient
import br.com.aipinho.mobile.network.PipelineClient
import br.com.aipinho.mobile.network.TaskRuntimeClient
import br.com.aipinho.mobile.ui.cards.HumanizedViewModelTerminal
import br.com.aipinho.mobile.ui.components.NeonButton
import br.com.aipinho.mobile.ui.components.NeonActionGroup
import br.com.aipinho.mobile.ui.components.NeonCyberCard
import br.com.aipinho.mobile.ui.components.MobileScreenScaffold
import br.com.aipinho.mobile.ui.components.NeonSearchField
import br.com.aipinho.mobile.ui.components.NeonSectionHeader
import br.com.aipinho.mobile.ui.theme.AipinhoNeonTheme
import br.com.aipinho.mobile.ui.theme.NeonColors
import br.com.aipinho.mobile.utils.MobileUiAsync
import org.json.JSONObject

class PipelineScreen {
    companion object {
        private const val REFRESH_INTERVAL_MS = 5_000L
        private var lastPipelinePayload: String = ""
    }

    fun build(context: Context): View {
        val profile = SettingsRepository(context).loadProfile()
        val tokens = TokenRepository(context)
        val mobileViewModels = MobileViewModelClient(profile) { tokens.load() }
        val pipeline = PipelineClient(profile) { tokens.load() }
        val runtime = TaskRuntimeClient(profile) { tokens.load() }
        val root = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            AipinhoNeonTheme.applyScreen(this)
        }
        val taskInput = NeonSearchField(context, "").apply {
            isFocusable = false
            isCursorVisible = false
            setTextIsSelectable(true)
        }
        val queueCard = NeonCyberCard(context, "Fila de tasks")
        val queueCount = queueCard.addBody("Na fila: 0")
        val decisionCount = queueCard.addBody("Precisam de permissao: 0")
        val selectedApprovalLine = queueCard.addBody("Approval selecionado: nenhum")
        val universalTaskLine = queueCard.addBody("Sessao universal: nenhuma task selecionada")
        val planningLine = queueCard.addBody("Execution Plan: nenhum")
        val executionGraphLine = queueCard.addBody("Execution Graph: nenhum")
        val cockpit = HumanizedViewModelTerminal(
            context,
            "Pipeline cockpit",
            minHeightDp = 440,
        )
        val handler = Handler(Looper.getMainLooper())
        var refreshInFlight = false
        var activeOnly = false

        fun renderPipeline(payload: String) {
            lastPipelinePayload = payload
            cockpit.setPayload(payload)
            val parsed = runCatching { JSONObject(payload) }.getOrNull()
            val queue = parsed?.optJSONObject("queue")
            val taskId = cleanJsonValue(parsed?.optString("selected_task_id"))
                ?: cleanJsonValue(parsed?.optString("task_id"))
                ?: cleanJsonValue(queue?.optString("selected_task_id"))
            val selectedApprovalId = cleanJsonValue(parsed?.optString("selected_approval_id"))
                ?: cleanJsonValue(queue?.optString("selected_approval_id"))
            val approvalKind = cleanJsonValue(parsed?.optString("approval_kind"))
                ?: cleanJsonValue(queue?.optString("approval_kind"))
            val linkedTaskRunId = cleanJsonValue(parsed?.optString("linked_task_run_id"))
                ?: cleanJsonValue(queue?.optString("linked_task_run_id"))
            taskInput.setText(taskId.orEmpty())
            taskInput.hint = if (taskId == null) "" else "Task selecionada"
            val taskApprovals = parsed?.optInt("task_approvals_pending", -1)?.takeIf { it >= 0 }
                ?: queue?.optInt("task_approvals_pending", 0)
                ?: 0
            val standaloneApprovals = parsed?.optInt("standalone_approvals_pending", -1)?.takeIf { it >= 0 }
                ?: queue?.optInt("standalone_approvals_pending", 0)
                ?: 0
            queueCount.text = "Na fila: ${queue?.optInt("pending", 0) ?: 0} | approvals de task: $taskApprovals"
            decisionCount.text =
                "Permissoes: ${queue?.optInt("requires_decision", 0) ?: 0} | avulsas: $standaloneApprovals"
            selectedApprovalLine.text = "Approval selecionado: ${selectedApprovalId ?: "nenhum"} | tipo: ${approvalKind ?: "-"} | task vinculada: ${linkedTaskRunId ?: "-"}"
            val universal = latestMetadataObject(payload, "universal_task_session")
            val progress = universal?.optJSONObject("progress")
            val percent = progress?.optInt("percent", -1) ?: -1
            val progressLabel = if (percent >= 0) "$percent%" else "sem progresso"
            val phase = cleanJsonValue(universal?.optString("phase")) ?: "-"
            val status = cleanJsonValue(universal?.optString("status")) ?: "-"
            val approvalState = universal?.optJSONObject("approval_state")?.optString("status") ?: "-"
            val artifacts = universal?.optJSONObject("artifact_state")?.optInt("count", 0) ?: 0
            val ccr = latestMetadataObject(payload, "external_collaboration")
            val ccrLabel = ccr?.let {
                "CCR ${it.optString("status", "none")} (${it.optInt("active_count", 0)}/${it.optInt("count", 0)})"
            } ?: "CCR none"
            universalTaskLine.text = "Sessao: $status | fase: $phase | progresso: $progressLabel | approval: $approvalState | artifacts: $artifacts | $ccrLabel"
            val plan = latestMetadataObject(payload, "planning_report")
            val planNodes = plan?.optJSONArray("nodes")
            val planRisk = cleanJsonValue(plan?.optString("risk_level")) ?: "-"
            val planType = cleanJsonValue(plan?.optString("task_type")) ?: "-"
            planningLine.text = if (plan == null || plan.optString("status", "none") == "none") {
                "Execution Plan: nenhum"
            } else {
                "Execution Plan: ${plan.optString("status", "-")} | tipo: $planType | risco: $planRisk | nodes: ${planNodes?.length() ?: 0}"
            }
            val graph = latestMetadataObject(payload, "execution_graph")
            val nodes = graph?.optJSONArray("nodes")
            val ready = graph?.optJSONArray("ready_nodes")?.length() ?: 0
            val running = graph?.optJSONArray("running_nodes")?.length() ?: 0
            val completed = graph?.optJSONArray("completed_nodes")?.length() ?: 0
            val blocked = graph?.optJSONArray("blocked_nodes")?.length() ?: 0
            executionGraphLine.text = if (graph == null || graph.optString("status", "none") == "none") {
                "Execution Graph: nenhum"
            } else {
                "Execution Graph: ${graph.optString("status", "-")} | nodes: ${nodes?.length() ?: 0} | ready: $ready | running: $running | done: $completed | blocked: $blocked"
            }
        }

        fun refreshPipeline() {
            if (refreshInFlight) return
            refreshInFlight = true
            MobileUiAsync.run(context, {
                refreshInFlight = false
                renderPipeline(it)
            }) {
                val response = if (activeOnly) {
                    mobileViewModels.pipeline("active")
                } else {
                    mobileViewModels.pipeline()
                }
                response.body.ifBlank {
                    """{"status":"failed","human_summary":"Pipeline indisponivel (${response.statusCode}).","queue":{"total":0,"requires_decision":0},"task_id":null}"""
                }
            }
        }

        val refreshRunnable = object : Runnable {
            override fun run() {
                if (root.isAttachedToWindow) {
                    refreshPipeline()
                    handler.postDelayed(this, REFRESH_INTERVAL_MS)
                }
            }
        }

        root.addView(NeonSectionHeader(context, "Pipeline"))
        root.addView(queueCard)
        root.addView(CheckBox(context).apply {
            text = "Somente task ativa"
            setTextColor(NeonColors.neonCyan)
            setOnCheckedChangeListener { _, checked ->
                activeOnly = checked
                refreshPipeline()
            }
        })
        root.addView(taskInput)
        root.addView(NeonActionGroup(context, listOf(
            NeonButton(context, "Atualizar fila") { refreshPipeline() },
            NeonButton(context, "Aprovar") {
                decideApproval(
                    context = context,
                    cockpit = cockpit,
                    pipeline = pipeline,
                    decision = "approve",
                    onCompleted = { refreshPipeline() },
                )
            },
            NeonButton(context, "Negar") {
                decideApproval(
                    context = context,
                    cockpit = cockpit,
                    pipeline = pipeline,
                    decision = "deny",
                    onCompleted = { refreshPipeline() },
                )
            },
            NeonButton(context, "Cancelar task") {
                cancelTask(
                    context = context,
                    cockpit = cockpit,
                    runtime = runtime,
                    taskId = taskInput.text.toString(),
                    onCompleted = { refreshPipeline() },
                )
            },
            NeonButton(context, "Aprovar seguras") {
                decideSafeBatch(
                    context = context,
                    cockpit = cockpit,
                    pipeline = pipeline,
                    taskId = taskInput.text.toString(),
                    approve = true,
                    onCompleted = { refreshPipeline() },
                )
            },
            NeonButton(context, "Negar seguras") {
                decideSafeBatch(
                    context = context,
                    cockpit = cockpit,
                    pipeline = pipeline,
                    taskId = taskInput.text.toString(),
                    approve = false,
                    onCompleted = { refreshPipeline() },
                )
            },
            NeonButton(context, "Retry node") {
                decideNode(
                    context = context,
                    cockpit = cockpit,
                    runtime = runtime,
                    taskId = taskInput.text.toString(),
                    retry = true,
                    onCompleted = { refreshPipeline() },
                )
            },
            NeonButton(context, "Cancel node") {
                decideNode(
                    context = context,
                    cockpit = cockpit,
                    runtime = runtime,
                    taskId = taskInput.text.toString(),
                    retry = false,
                    onCompleted = { refreshPipeline() },
                )
            },
        )))
        root.addView(NeonCyberCard(context, "Fonte oficial", "/api/v1/mobile/view-model/pipeline").apply {
            addBody("A fila prioriza a task ativa e depois as pendencias mais recentes.")
        })
        root.addView(cockpit)
        root.addOnAttachStateChangeListener(object : View.OnAttachStateChangeListener {
            override fun onViewAttachedToWindow(view: View) {
                handler.removeCallbacks(refreshRunnable)
                handler.post(refreshRunnable)
            }

            override fun onViewDetachedFromWindow(view: View) {
                handler.removeCallbacks(refreshRunnable)
            }
        })
        refreshPipeline()
        return MobileScreenScaffold(context, root)
    }

    private fun decideApproval(
        context: Context,
        cockpit: HumanizedViewModelTerminal,
        pipeline: PipelineClient,
        decision: String,
        onCompleted: () -> Unit,
    ) {
        val approvalId = selectedValue(lastPipelinePayload, "selected_approval_id")
            ?: latestMetadataValue(lastPipelinePayload, "approval_id")
        if (approvalId.isNullOrBlank()) {
            cockpit.setPayload(
                """{"status":"pending","human_summary":"A primeira task da fila nao possui permissao pendente."}""",
            )
            return
        }
        cockpit.setPayload(
            """{"status":"running","human_summary":"Registrando decisao de approval..."}""",
        )
        MobileUiAsync.run(context, {
            cockpit.setPayload(it)
            onCompleted()
        }) {
            val response = if (decision == "deny") pipeline.deny(approvalId) else pipeline.approve(approvalId)
            response.body.ifBlank {
                """{"status":"failed","human_summary":"Decisao falhou com status ${response.statusCode}."}"""
            }
        }
    }

    private fun decideSafeBatch(
        context: Context,
        cockpit: HumanizedViewModelTerminal,
        pipeline: PipelineClient,
        taskId: String,
        approve: Boolean,
        onCompleted: () -> Unit,
    ) {
        if (taskId.isBlank()) {
            cockpit.setPayload(
                """{"status":"pending","human_summary":"Nao ha task selecionada para batch seguro."}""",
            )
            return
        }
        cockpit.setPayload(
            """{"status":"running","human_summary":"Processando batch seguro de approvals..."}""",
        )
        MobileUiAsync.run(context, {
            cockpit.setPayload(it)
            onCompleted()
        }) {
            val response = if (approve) pipeline.approveSafeBatch(taskId) else pipeline.denySafeBatch(taskId)
            response.body.ifBlank {
                """{"status":"failed","human_summary":"Batch seguro falhou com status ${response.statusCode}."}"""
            }
        }
    }

    private fun cancelTask(
        context: Context,
        cockpit: HumanizedViewModelTerminal,
        runtime: TaskRuntimeClient,
        taskId: String,
        onCompleted: () -> Unit,
    ) {
        if (taskId.isBlank()) {
            cockpit.setPayload(
                """{"status":"pending","human_summary":"Nao ha task selecionada para cancelar."}""",
            )
            return
        }
        cockpit.setPayload(
            """{"status":"running","human_summary":"Cancelando a task selecionada..."}""",
        )
        MobileUiAsync.run(context, {
            cockpit.setPayload(it)
            onCompleted()
        }) {
            val response = runtime.cancel(taskId)
            response.body.ifBlank {
                """{"status":"failed","human_summary":"Cancelamento falhou com status ${response.statusCode}."}"""
            }
        }
    }

    private fun decideNode(
        context: Context,
        cockpit: HumanizedViewModelTerminal,
        runtime: TaskRuntimeClient,
        taskId: String,
        retry: Boolean,
        onCompleted: () -> Unit,
    ) {
        val nodeId = selectedExecutionNode(lastPipelinePayload)
        if (taskId.isBlank() || nodeId.isNullOrBlank()) {
            cockpit.setPayload(
                """{"status":"pending","human_summary":"Nao ha task/node selecionado para a acao do Execution Graph."}""",
            )
            return
        }
        cockpit.setPayload(
            """{"status":"running","human_summary":"Enviando acao governada para o node $nodeId..."}""",
        )
        MobileUiAsync.run(context, {
            cockpit.setPayload(it)
            onCompleted()
        }) {
            val response = if (retry) runtime.retryNode(taskId, nodeId) else runtime.cancelNode(taskId, nodeId)
            response.body.ifBlank {
                """{"status":"failed","human_summary":"Acao de node falhou com status ${response.statusCode}."}"""
            }
        }
    }

    private fun cleanJsonValue(value: String?): String? {
        val text = value?.trim().orEmpty()
        return text.takeUnless { it.isBlank() || it.lowercase() in setOf("null", "none", "unknown") }
    }

    private fun selectedValue(payload: String, key: String): String? {
        return runCatching {
            val root = JSONObject(payload)
            cleanJsonValue(root.optString(key)) ?: cleanJsonValue(root.optJSONObject("queue")?.optString(key))
        }.getOrNull()
    }

    private fun latestMetadataValue(payload: String, key: String): String? {
        return runCatching {
            val cards = JSONObject(payload).optJSONArray("cards") ?: return@runCatching null
            for (index in cards.length() - 1 downTo 0) {
                val metadata = cards.optJSONObject(index)?.optJSONObject("metadata") ?: continue
                val value = metadata.optString(key).trim()
                if (value.isNotBlank() && value.lowercase() !in setOf("null", "none", "unknown")) {
                    return@runCatching value
                }
            }
            null
        }.getOrNull()
    }

    private fun latestMetadataObject(payload: String, key: String): JSONObject? {
        return runCatching {
            val cards = JSONObject(payload).optJSONArray("cards") ?: return@runCatching null
            for (index in cards.length() - 1 downTo 0) {
                val metadata = cards.optJSONObject(index)?.optJSONObject("metadata") ?: continue
                metadata.optJSONObject(key)?.let { return@runCatching it }
                val text = metadata.optString(key).trim()
                if (text.startsWith("{") && text.endsWith("}")) {
                    runCatching { JSONObject(text) }.getOrNull()?.let { return@runCatching it }
                }
            }
            null
        }.getOrNull()
    }

    private fun selectedExecutionNode(payload: String): String? {
        return runCatching {
            val graph = latestMetadataObject(payload, "execution_graph") ?: return@runCatching null
            val nodes = graph.optJSONArray("nodes") ?: return@runCatching null
            for (index in 0 until nodes.length()) {
                val node = nodes.optJSONObject(index) ?: continue
                val status = node.optString("status")
                if (status in setOf("failed", "blocked", "cancelled", "completed")) {
                    return@runCatching cleanJsonValue(node.optString("node_id"))
                }
            }
            for (index in 0 until nodes.length()) {
                cleanJsonValue(nodes.optJSONObject(index)?.optString("node_id"))?.let { return@runCatching it }
            }
            null
        }.getOrNull()
    }
}
