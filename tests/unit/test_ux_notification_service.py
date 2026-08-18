from aipinho.services.ux.ux_notification_service import UXNotificationService
def test_notification_dedupes_and_acks(tmp_path):
    svc=UXNotificationService(tmp_path/"n.json"); n1=svc.notify("service_down","Servico caiu",dedupe_key="x"); n2=svc.notify("service_down","Servico caiu",dedupe_key="x"); assert n1.notification_id==n2.notification_id; assert svc.ack([n1.notification_id])[0].acknowledged
