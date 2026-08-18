from aipinho.services.replay.collectors.collectors import SnapshotCollector

class MemorySnapshotCollector(SnapshotCollector):
    collector_type = 'memory'
