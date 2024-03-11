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
        self.access_token = self.options.get("access_token", self.org_config.access_token)
        self.instance_url = self.options.get("instance_url", self.org_config.instance_url)

    def _run_task(self):
        self._prep_runtime()
        self._extend_context_definition()

    def _extend_context_definition(self):
        url, headers = self._build_url_and_headers("connect/context-definitions")
        payload = {
            "name": "RLM_SalesTransactionContext",
            "description": "Extension of Standard Sales Transaction Context",
            "developerName": "RLM_SalesTransactionContext",
            "baseReference": "SalesTransactionContext__stdctx",
            "startDate": "2024-01-01T00:00:00.000Z"
        }
        response = self._make_request("post", url, headers=headers, json=payload)
        if response:
            self.context_id = response.get('contextDefinitionId')
            if self.context_id:
                self.logger.info(f"Context ID: {self.context_id}")
                self._process_context_id()

    def _process_context_id(self):
        url, headers = self._build_url_and_headers(f"connect/context-definitions/{self.context_id}")
        response = self._make_request("get", url, headers=headers)
        if response:
            version_list = response.get('contextDefinitionVersionList', [])
            if version_list:
                self._process_version_list(version_list)

    def _process_version_list(self, version_list):
        context_mappings = version_list[0].get('contextMappings', [])
        for mapping in context_mappings:
            if mapping.get("name") == "SalesTransaction":
                self.sales_transaction_mapping_id = mapping['contextMappingId']
                self.logger.info(f"Sales Transaction Context Mapping ID: {self.sales_transaction_mapping_id}")
                self._update_context_mappings()
                break

    def _update_context_mappings(self):
        url, headers = self._build_url_and_headers(f"connect/context-definitions/{self.context_id}/context-mappings")
        payload = {
            "contextMappings": [{"contextMappingId": self.sales_transaction_mapping_id, "isDefault": "true", "name": "SalesTransaction"}]
        }
        self._make_request("patch", url, headers=headers, json=payload)
        self._activate_context_id()

    def _activate_context_id(self):
        url, headers = self._build_url_and_headers(f"connect/context-definitions/{self.context_id}")
        payload = {"isActive": "true"}
        self._make_request("patch", url, headers=headers, json=payload)

    def _build_url_and_headers(self, endpoint):
        url = f"{self.instance_url}/services/data/v{self.project_config.project__package__api_version}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        return url, headers

    def _make_request(self, method, url, **kwargs):
        response = requests.request(method, url, **kwargs)
        if response.ok:
            return response.json()
        else:
            self.logger.error(f"Failed {method.upper()} request to {url}: {response.text}")
            return None

    @abstractmethod
    def get_keychain_class(self):
        pass

    @abstractmethod
    def get_keychain_key(self):
        pass
