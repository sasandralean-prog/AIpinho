from aipinho.services.ux.ux_error_message_service import UXErrorMessageService
def test_error_message_is_human():
    msg=UXErrorMessageService().message("backend_down","error"); assert "Backend" in msg.human_message
