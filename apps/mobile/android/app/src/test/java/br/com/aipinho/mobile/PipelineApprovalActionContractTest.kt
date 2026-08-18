package br.com.aipinho.mobile

import org.junit.Assert.assertTrue
import org.junit.Test

class PipelineApprovalActionContractTest {
    @Test
    fun pipelineApprovalAndCancellationUseRealIdentifiers() {
        val screen = NeonSourceContract.source("ui/screens/PipelineScreen.kt")
        val client = NeonSourceContract.source("network/PipelineClient.kt")
        val runtime = NeonSourceContract.source("network/TaskRuntimeClient.kt")

        assertTrue(screen.contains("\"Aprovar\""))
        assertTrue(screen.contains("\"Cancelar task\""))
        assertTrue(screen.contains("Execution Graph"))
        assertTrue(screen.contains("Execution Plan"))
        assertTrue(screen.contains("latestMetadataObject(payload, \"planning_report\")"))
        assertTrue(screen.contains("latestMetadataObject(payload, \"execution_graph\")"))
        assertTrue(screen.contains("\"Retry node\""))
        assertTrue(screen.contains("\"Cancel node\""))
        assertTrue(screen.contains("selectedExecutionNode"))
        assertTrue(screen.contains("latestMetadataValue(lastPipelinePayload, \"approval_id\")"))
        assertTrue(screen.contains("pipeline.approve(approvalId)"))
        assertTrue(screen.contains("runtime.cancel(taskId)"))
        assertTrue(client.contains("/api/v1/approvals/"))
        assertTrue(client.contains("/approve"))
        assertTrue(client.contains("invalid_approval_identifier"))
        assertTrue(runtime.contains("/api/v1/task-runs/"))
        assertTrue(runtime.contains("/cancel"))
        assertTrue(runtime.contains("retryNode"))
        assertTrue(runtime.contains("cancelNode"))
        assertTrue(runtime.contains("planningReport"))
        assertTrue(runtime.contains("replanNode"))
        assertTrue(runtime.contains("/execution-graph/nodes/"))
        assertTrue(runtime.contains("/planning/report"))
        assertTrue(runtime.contains("/planning/nodes/"))
    }
}
