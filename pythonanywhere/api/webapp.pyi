from pathlib import Path
from typing import Dict, List, Any

class Webapp:
    domain: str = ...
    def __init__(self, domain: str) -> None: ...
    def __eq__(self, other: Webapp) -> bool: ...
    def sanity_checks(self, nuke: bool) -> None: ...
    def create(self, python_version: str, virtualenv_path: Path, project_path: Path, nuke: bool) -> None: ...
    def add_default_static_files_mappings(self, project_path: Path) -> None: ...
    def reload(self) -> None: ...
    def set_ssl(self, certificate: str, private_key: str) -> None: ...
    def get_ssl_info(self) -> Dict[str, Any]: ...
    def delete_log(self, log_type: str, index: int = 0) -> None: ...
    def get_log_info(self) -> Dict[str, List[int]]: ...