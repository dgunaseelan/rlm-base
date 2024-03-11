import requests
from cumulusci.tasks.sfdx import SFDXBaseTask
from cumulusci.core.keychain import BaseProjectKeychain
from abc import abstractmethod

class ExtendStandardContext(SFDXBaseTask):
    task_options = {
        'access_token': {
            'description': 'The access token for the org. Defaults to the project default',
        }
    }

    def __init__(self):
        self.keychain = None
        self.env = None
        self.access_token = None
        self.instance_url = None
        self.context_id = None
        self.sales_transaction_mapping_id = None
        super().__init__()

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.env = self._get_env()

    def _load_keychain(self):
        if not hasattr(self, 'keychain') or not self.keychain:
            keychain_class = self.get_keychain_class() or BaseProjectKeychain
            keychain_key = self.get_keychain_key() if keychain_class.encrypted else None
            self.keychain = keychain_class(self.project_config or self.universal_config, keychain_key)
            if self.project_config:
                self.project_config.keychain = self.keychain

    def _prep_runtime(self):
        self._load_keychain()
        self.access_token = self.options.get("access_token") or self.org_config.access_token
        self.instance_url = self.options.get("instance_url") or self.org_config.instance_url

    def _run_task(self):
        self._prep_runtime()
        self._extend_context_definition()

    def _extend_context_definition(self):
        url = f"{self.instance_url}/services/data/v{self.project_config.project__package__api_version}/connect/context-definitions"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "name": "RLM_SalesTransactionContext",
            "description": "Extension of Standard Sales Transaction Context",
            "developerName": "RLM_SalesTransactionContext",
            "baseReference": "SalesTransactionContext__stdctx",
            "startDate": "2024-01-01T00:00:00.000Z"
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.ok:
            response_json = response.json()
            context_id = response_json.get('contextDefinitionId')
            if context_id:
                self.logger.info(f"Context ID: {context_id}")
                self.context_id = context_id
                self._process_context_id()

    def _process_context_id(self):
        url = f"{self.instance_url}/services/data/v{self.project_config.project__package__api_version}/connect/context-definitions/{self.context_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        response = requests.get(url, headers=headers)
        if response.ok:
            response_json = response.json()
            version_list = response_json.get('contextDefinitionVersionList', [])
            if version_list:
                context_mappings = version_list[0].get('contextMappings', [])
                sales_transaction_mapping_id = next(
                    (m['contextMappingId'] for m in context_mappings if m.get("name") == "SalesTransaction"),
                    None
                )
                if sales_transaction_mapping_id:
                    self.sales_transaction_mapping_id = sales_transaction_mapping_id
                    self.logger.info(f"Sales Transaction Context Mapping ID: {sales_transaction_mapping_id}")
                    self._update_context_mappings()

    def _update_context_mappings(self):
        url = f"{self.instance_url}/services/data/v{self.project_config.project__package__api_version}/connect/context-definitions/{self.context_id}/context-mappings"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "contextMappings": [
                {
                    "contextMappingId": self.sales_transaction_mapping_id,
                    "isDefault": "true",
                    "name": "SalesTransaction"
                }
            ]
        }
        response = requests.patch(url, headers=headers, json=payload)
        if response.ok:
            self._activate_context_id()

    def _activate_context_id(self):
        url = f"{self.instance_url}/services/data/v{self.project_config.project__package__api_version}/connect/context-definitions/{self.context_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {"isActive": "true"}
        requests.patch(url, headers=headers, json=payload)

    @abstractmethod
    def get_keychain_class(self):
        return None

    @abstractmethod
    def get_keychain_key(self):
        return None
