import json
import requests
from cumulusci.tasks.sfdx import SFDXBaseTask
from cumulusci.core.keychain import BaseProjectKeychain
from abc import abstractmethod

class ExtendStandardContext(SFDXBaseTask):
    keychain_class = BaseProjectKeychain
    task_options = {
        'access_token': {
            'description': 'The access token for the org.  Defaults to the project default',
        }
    }
    def _init_options(self, kwargs):
        super(ExtendStandardContext, self)._init_options(kwargs)
        self.env = self._get_env()
    
    def _prepruntime(self, a):
        self._load_keychain()
        # if not passed in - fall back to the key ring data
        if "accesstoken" not in self.options or not self.options["accesstoken"]:
            self.accesstoken = self.org_config.access_token
        else:
            self.accesstoken = self.options["accesstoken"]

        if "instanceurl" not in self.options or not self.options["instanceurl"]:
            self.instanceurl = self.org_config.instance_url
        else:
            self.instanceurl = self.options["instanceurl"]
    @property
    def keychain_cls(self):
        klass = self.get_keychain_class()
        return klass or self.keychain_class

    @abstractmethod
    def get_keychain_class(self):
        return None
    
    @property
    def keychain_key(self):
        return self.get_keychain_key()

    @abstractmethod
    def get_keychain_key(self):
        return None
    
    def _load_keychain(self):
        if hasattr(self, 'keychain') == True and not self.keychain is None:
            return

        keychain_key = self.keychain_key if self.keychain_cls.encrypted else None

        if self.project_config is None:
            self.keychain = self.keychain_cls(self.universal_config, keychain_key)
        else:
            self.keychain = self.keychain_cls(self.project_config, keychain_key)
            self.project_config.keychain = self.keychain
    def _run_task(self):
        self._prepruntime(self)
        self.__call__(self)
    
    def __call__(self):
        url = f"{self.org_config.instance_url}/services/data/v{self.project_config.project__package__api_version}/connect/context-definitions"
        self.logger.info(f"Request URL: {url}")
        headers = {
            "Authorization": f"Bearer {self.org_config.access_token}",
            "Content-Type": f"application/json",
        }

        # Prepare JSON payload
        payload = {
            "name": "RLM_SalesTransactionContext",
            "description": "Extension of Standard Sales Transaction Context",
            "developerName": "RLM_SalesTransactionContext",
            "baseReference": "SalesTransactionContext__stdctx",
            "startDate": "2024-01-01T00:00:00.000Z"
        }
        json_payload = json.dumps(payload)
        self.logger.info(f"Request body: {json_payload}")

        # Construct JSON request body
        body = (
            f"{json_payload}\r\n"
        ).encode("utf-8")

        response = requests.post(url, headers=headers, data=body)
        response_json = response.json()

        if response.status_code == 201:
            self.logger.info("Deployment request successful")
            self.logger.info(f"Response: {response_json}")
            self.logger.info(f"Context ID: {response_json['contextDefinitionId']}")
        else:
            self.logger.error(
                f"Create request failed with status code {response.status_code}"
            )