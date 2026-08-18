from apps.launcher.ui.state.notification_state_store import NotificationStateStore
def test_notification_store_snapshots():
    s=NotificationStateStore(); s.set("unread",1); assert s.get("unread")==1
