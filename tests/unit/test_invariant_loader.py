from aipinho.services.maintenance.invariant_loader import InvariantLoader

def test_loader_parses_config_driven_conditions():
    values = InvariantLoader().load()
    assert values["speaker_no_false_progress"].violation_if["completion_event_present"] is False
