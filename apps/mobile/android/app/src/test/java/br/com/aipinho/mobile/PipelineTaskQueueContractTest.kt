package br.com.aipinho.mobile

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PipelineTaskQueueContractTest {
    @Test
    fun pipelineShowsQueueCountsAndAutomaticallySelectedTask() {
        val screen = NeonSourceContract.source("ui/screens/PipelineScreen.kt")
        val runtime = NeonSourceContract.source("network/TaskRuntimeClient.kt")

        assertTrue(screen.contains("\"Na fila: 0\""))
        assertTrue(screen.contains("\"Precisam de permissao: 0\""))
        assertTrue(screen.contains("optJSONObject(\"queue\")"))
        assertTrue(screen.contains("optString(\"task_id\")"))
        assertTrue(screen.contains("taskInput.setText(taskId.orEmpty())"))
        assertTrue(screen.contains("REFRESH_INTERVAL_MS = 5_000L"))
        assertTrue(screen.contains("\"Somente task ativa\""))
        assertFalse(screen.contains("\"Nenhuma task na fila\""))
        assertTrue(screen.contains("mobileViewModels.pipeline(\"active\")"))
        assertTrue(runtime.contains("/api/v1/task-runtime/queue"))
    }
}
