from anoncreds.protocol.issuer import Issuer
from anoncreds.protocol.repo.attributes_repo import AttributeRepo
from anoncreds.protocol.repo.public_repo import PublicRepo
from anoncreds.protocol.wallet.issuer_wallet import IssuerWalletInMemory
from sovrin_client.anon_creds.sovrin_public_repo import SovrinPublicRepo
from sovrin_client.client.wallet.wallet import Wallet


class SovrinIssuer(Issuer):
    def __init__(self, client, wallet: Wallet, attrRepo: AttributeRepo,
                 publicRepo: PublicRepo = None):
        publicRepo = publicRepo or SovrinPublicRepo(client=client,
                                                    wallet=wallet)
        issuerWallet = IssuerWalletInMemory(wallet.name, publicRepo)
        super().__init__(issuerWallet, attrRepo)

    def resetIssuerWallet(self, issuerWallet):
        curRepo = self.wallet._repo
        self.wallet = issuerWallet
        self._primaryIssuer._wallet = issuerWallet
        self._nonRevocationIssuer._wallet = issuerWallet
        self.wallet._repo = curRepo
