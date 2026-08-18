package br.com.aipinho.mobile

import org.junit.Assert.assertTrue
import org.junit.Test

class TaskSpeakerPollingContractTest {
    @Test
    fun chatPollsIncrementalSpeakerUpdatesWithoutRaw() {
        val client = NeonSourceContract.source("network/TaskRuntimeClient.kt")
        val chat = NeonSourceContract.source("ui/screens/ChatScreen.kt")

        assertTrue(client.contains("/speaker/updates"))
        assertTrue(client.contains("after_event_id"))
        assertTrue(chat.contains("pollSpeakerUpdates"))
        assertTrue(chat.contains("speakerEventCursor"))
        assertTrue(chat.contains("ChatAutoRefreshPolicy.pollIntervalMs"))
        assertTrue(!client.contains("/raw"))
    }
}
