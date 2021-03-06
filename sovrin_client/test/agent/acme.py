from plenum.common.signer_simple import SimpleSigner
from sovrin_client.agent.helper import bootstrap_schema
from sovrin_client.client.wallet.wallet import Wallet
from stp_core.common.log import getlogger
from sovrin_client.agent.runnable_agent import RunnableAgent
from sovrin_client.agent.agent import create_client
from sovrin_client.test.agent.mock_backend_system import MockBackendSystem

from sovrin_client.agent.walleted_agent import WalletedAgent
from sovrin_client.test.constants import primes
from sovrin_client.test.agent.helper import buildAcmeWallet
from sovrin_client.test.client.TestClient import TestClient

from anoncreds.protocol.types import AttribType, AttribDef, ID

logger = getlogger()

schema_id = None

ACME_SEED = b'Acme0000000000000000000000000000'

class AcmeAgent(WalletedAgent):
    async def postProofVerif(self, claimName, link, frm):
        if claimName == "Job-Application":

            for schema in await self.issuer.wallet.getAllSchemas():

                if schema.name == 'Job-Certificate':
                    await self._set_available_claim_by_internal_id(link.internalId,
                                                   ID(schemaKey=schema.getKey(),
                                                      schemaId=schema.seqId))

                    claims = self.get_available_claim_list(link)
                    self.sendNewAvailableClaimsData(claims, frm, link)

def create_acme(name=None, wallet=None, base_dir_path=None, port=6666, client=None):
    if client is None:
        client = create_client(base_dir_path=None, client_class=TestClient)

    endpoint_args = {'onlyListener': True}
    if wallet:
        endpoint_args['seed'] = wallet._signerById(wallet.defaultId).seed
    else:
        wallet = Wallet(name)
        wallet.addIdentifier(signer=SimpleSigner(seed=ACME_SEED))
        endpoint_args['seed'] = ACME_SEED

    agent = AcmeAgent(name=name or "Acme Corp",
                      basedirpath=base_dir_path,
                      client=client,
                      wallet=wallet,
                      port=port,
                      endpointArgs=endpoint_args)

    # maps invitation nonces to internal ids
    agent._invites = {
        "57fbf9dc8c8e6acde33de98c6d747b28c": (1, "Alice"),
        "3a2eb72eca8b404e8d412c5bf79f2640": (2, "Carol"),
        "8513d1397e87cada4214e2a650f603eb": (3, "Frank"),
        "810b78be79f29fc81335abaa4ee1c5e8": (4, "Bob")
    }

    job_cert_def = AttribDef('Job-Certificate',
                             [AttribType('first_name', encode=True),
                              AttribType('last_name', encode=True),
                              AttribType('employee_status', encode=True),
                              AttribType('experience', encode=True),
                              AttribType('salary_bracket', encode=True)])

    job_appl_def = AttribDef('Job-Application',
                             [AttribType('first_name', encode=True),
                              AttribType('last_name', encode=True),
                              AttribType('phone_number', encode=True),
                              AttribType('degree', encode=True),
                              AttribType('status', encode=True),
                              AttribType('ssn', encode=True)])

    agent.add_attribute_definition(job_cert_def)
    agent.add_attribute_definition(job_appl_def)

    backend = MockBackendSystem(job_cert_def)
    backend.add_record(1,
                       first_name="Alice",
                       last_name="Garcia",
                       employee_status="Permanent",
                       experience="3 years",
                       salary_bracket="between $50,000 to $100,000")

    backend.add_record(2,
                       first_name="Carol",
                       last_name="Atkinson",
                       employee_status="Permanent",
                       experience="2 years",
                       salary_bracket="between $60,000 to $90,000")

    backend.add_record(3,
                       first_name="Frank",
                       last_name="Jeffrey",
                       employee_status="Temporary",
                       experience="4 years",
                       salary_bracket="between $40,000 to $80,000")

    backend.add_record(4,
                       first_name="Bob",
                       last_name="Richards",
                       employee_status="On Contract",
                       experience="3 years",
                       salary_bracket="between $50,000 to $70,000")

    agent.set_issuer_backend(backend)

    agent._proofRequestsSchema = {
        "Job-Application-v0.2": {
            "name": "Job-Application",
            "version": "0.2",
            "attributes": {
                "first_name": "string",
                "last_name": "string",
                "phone_number": "string",
                "degree": "string",
                "status": "string",
                "ssn": "string"
            },
            "verifiableAttributes": ["degree", "status", "ssn"]
        },
        "Job-Application-v0.3": {
            "name": "Job-Application-2",
            "version": "0.3",
            "attributes": {
                "first_name": "string",
                "last_name": "string",
                "phone_number": "string",
                "degree": "string",
                "status": "string",
                "ssn": "string"
            },
            "verifiableAttributes": ["degree", "status"]
        }
    }

    return agent


async def bootstrap_acme(agent):
    await bootstrap_schema(agent,
                           'Job-Certificate',
                           'Job-Certificate',
                           '0.2',
                           primes["prime1"][0],
                           primes["prime1"][1])

    await bootstrap_schema(agent,
                           'Job-Application',
                           'Job-Application',
                           '0.2',
                           primes["prime2"][0],
                           primes["prime2"][1])


if __name__ == "__main__":
    args = RunnableAgent.parser_cmd_args()
    name = 'Acme Corp'
    port = args.port
    if port is None:
        port = 6666
    with_cli = args.withcli
    agent = create_acme(name=name, wallet=buildAcmeWallet(),
                        base_dir_path=None, port=port)
    RunnableAgent.run_agent(agent, bootstrap=bootstrap_acme(agent),
                            with_cli=with_cli)
