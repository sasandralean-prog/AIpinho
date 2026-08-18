from aipinho.services.ux.ux_progress_service import UXProgressService
def test_progress_reaches_completed():
    p=UXProgressService().progress("x","Download",10,10); assert p.state=="completed" and p.percent==100
