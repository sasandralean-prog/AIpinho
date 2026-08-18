from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file
def test_mobile_connection_profiles_and_ports():
    p=load_yaml_file(PATHS.config_root/"mobile"/"mobile_connection_policy.yaml",root=PATHS.project_root)["connection_profiles"]; assert set(p)=={"adb_reverse","wifi_lan","tailscale","manual"}; assert p["adb_reverse"]["ports"]["monitor"]==9099
