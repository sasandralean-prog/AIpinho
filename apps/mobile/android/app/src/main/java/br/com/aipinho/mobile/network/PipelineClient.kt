package br.com.aipinho.mobile.network
import br.com.aipinho.mobile.models.ConnectionProfile
import org.json.JSONObject
class PipelineClient(profile:ConnectionProfile,token:()->String?):BaseApiClient(profile,profile.corePort,token) {
    fun tasks()=get("/api/v1/tasks/cards")
    fun task(taskId:String)=get("/api/v1/tasks/cards/$taskId")
    fun pipeline(taskId:String)=get("/api/v1/pipeline/cards/$taskId")
    fun approve(approvalId:String)=post("/api/v1/approvals/${identifier(approvalId)}/approve")
    fun reject(approvalId:String)=post("/api/v1/approvals/${identifier(approvalId)}/reject")
    fun deny(approvalId:String)=post("/api/v1/approvals/${identifier(approvalId)}/deny")
    fun cancel(approvalId:String)=post("/api/v1/approvals/${identifier(approvalId)}/cancel")
    fun pendingApprovals()=get("/api/v1/approvals/pending")
    fun taskApprovals(taskId:String)=get("/api/v1/tasks/${identifier(taskId)}/approvals")
    fun approveSafeBatch(taskId:String)=post(
        "/api/v1/tasks/${identifier(taskId)}/approvals/approve-safe-batch",
        decisionBody("mobile_safe_batch_approved"),
    )
    fun denySafeBatch(taskId:String)=post(
        "/api/v1/tasks/${identifier(taskId)}/approvals/deny-safe-batch",
        decisionBody("mobile_safe_batch_denied"),
    )
    private fun identifier(value:String):String {
        require(value.matches(Regex("[A-Za-z0-9_-]+"))) { "invalid_approval_identifier" }
        return value
    }
    private fun decisionBody(reason:String):String = JSONObject()
        .put("actor", JSONObject().put("type", "human").put("id", "mobile_operator"))
        .put("reason", reason)
        .toString()
}
