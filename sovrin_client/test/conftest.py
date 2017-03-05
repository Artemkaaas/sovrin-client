from plenum.common.eventually import eventually
from plenum.common.port_dispenser import genHa
from plenum.common.raet import initLocalKeep
from plenum.common.util import randomString
from plenum.test.helper import checkSufficientRepliesForRequests
from plenum.test.node_catchup.helper import \
    ensureClientConnectedToNodesAndPoolLedgerSame
from plenum.test.test_node import checkNodesConnected
from sovrin_client.client.wallet.node import Node

from sovrin_common import strict_types

# typecheck during tests
strict_types.defaultShouldCheck = True

import pytest

from ledger.compact_merkle_tree import CompactMerkleTree
from ledger.ledger import Ledger
from ledger.serializers.compact_serializer import CompactSerializer

from plenum.common.looper import Looper
from plenum.common.signer_simple import SimpleSigner
from plenum.common.txn import VERKEY, NODE_IP, NODE_PORT, CLIENT_IP, CLIENT_PORT, \
    ALIAS, SERVICES, VALIDATOR, TYPE
from plenum.test.plugin.helper import getPluginPath

from sovrin_client.client.wallet.wallet import Wallet
from sovrin_common.txn import STEWARD, NYM, SPONSOR, TRUSTEE
from sovrin_common.txn import TXN_TYPE, TARGET_NYM, TXN_ID, ROLE, \
    getTxnOrderedFields
from sovrin_common.config_util import getConfig
from sovrin_client.test.cli.helper import newCLI
from sovrin_node.test.helper import TestNode, \
    makePendingTxnsRequest, buildStewardClient
from sovrin_client.test.helper import addRole, getClientAddedWithRole, primes, \
    genTestClient, TestClient, createNym


@pytest.fixture(scope="module")
def primes1():
    P_PRIME1, Q_PRIME1 = primes.get("prime1")
    return dict(p_prime=P_PRIME1, q_prime=Q_PRIME1)


@pytest.fixture(scope="module")
def primes2():
    P_PRIME2, Q_PRIME2 = primes.get("prime2")
    return dict(p_prime=P_PRIME2, q_prime=Q_PRIME2)


# noinspection PyUnresolvedReferences
from plenum.test.conftest import tdir, counter, nodeReg, up, ready, \
    whitelist, concerningLogLevels, logcapture, keySharedNodes, \
    startedNodes, tdirWithDomainTxns, txnPoolNodeSet, poolTxnData, dirName, \
    poolTxnNodeNames, allPluginsPath, tdirWithNodeKeepInited, tdirWithPoolTxns, \
    poolTxnStewardData, poolTxnStewardNames, getValueFromModule, \
    txnPoolNodesLooper, nodeAndClientInfoFilePath, conf, patchPluginManager


@pytest.fixture(scope="module")
def tconf(conf, tdir):
    conf.baseDir = tdir
    conf.MinSepBetweenNodeUpgrades = 5
    return conf


@pytest.fixture(scope="module")
def updatedPoolTxnData(poolTxnData):
    data = poolTxnData
    trusteeSeed = 'thisistrusteeseednotsteward12345'
    signer = SimpleSigner(seed=trusteeSeed.encode())
    t = {
        TARGET_NYM: signer.verkey,
        ROLE: TRUSTEE,
        TYPE: NYM,
        ALIAS: "Trustee1",
        TXN_ID: "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4a"
    }
    data["seeds"]["Trustee1"] = trusteeSeed
    data["txns"].insert(0, t)
    return data


@pytest.fixture(scope="module")
def poolTxnTrusteeNames():
    return "Trustee1",


@pytest.fixture(scope="module")
def trusteeData(poolTxnTrusteeNames, updatedPoolTxnData):
    name = poolTxnTrusteeNames[0]
    seed = updatedPoolTxnData["seeds"][name]
    return name, seed.encode()


@pytest.fixture(scope="module")
def trusteeWallet(trusteeData):
    name, sigseed = trusteeData
    wallet = Wallet('trustee')
    signer = SimpleSigner(seed=sigseed)
    wallet.addIdentifier(signer=signer)
    return wallet


# TODO: This fixture is present in sovrin_node too, it should be
# sovrin_common's conftest.
@pytest.fixture(scope="module")
def trustee(nodeSet, looper, tdir, trusteeWallet):
    return buildStewardClient(looper, tdir, trusteeWallet)


@pytest.fixture(scope="module")
def allPluginsPath():
    return [getPluginPath('stats_consumer')]


@pytest.fixture(scope="module")
def stewardWallet(poolTxnStewardData):
    name, sigseed = poolTxnStewardData
    wallet = Wallet('steward')
    signer = SimpleSigner(seed=sigseed)
    wallet.addIdentifier(signer=signer)
    return wallet


@pytest.fixture(scope="module")
def looper():
    with Looper() as l:
        yield l


# TODO: This fixture is present in sovrin_node too, it should be
# sovrin_common's conftest.
@pytest.fixture(scope="module")
def steward(nodeSet, looper, tdir, stewardWallet):
    return buildStewardClient(looper, tdir, stewardWallet)


@pytest.fixture(scope="module")
def genesisTxns(stewardWallet: Wallet, trusteeWallet: Wallet):
    nym = stewardWallet.defaultId
    return [
        {
            TXN_TYPE: NYM,
            TARGET_NYM: nym,
            TXN_ID: "9c86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b",
            ROLE: STEWARD,
            VERKEY: stewardWallet.getVerkey()
        },
    ]


@pytest.fixture(scope="module")
def domainTxnOrderedFields():
    return getTxnOrderedFields()


@pytest.fixture(scope="module")
def conf(tdir):
    return getConfig(tdir)


@pytest.fixture(scope="module")
def testNodeClass():
    return TestNode


@pytest.fixture(scope="module")
def testClientClass():
    return TestClient


@pytest.fixture(scope="module")
def updatedDomainTxnFile(tdir, tdirWithDomainTxns, genesisTxns,
                         domainTxnOrderedFields, tconf):
    ledger = Ledger(CompactMerkleTree(),
                    dataDir=tdir,
                    serializer=CompactSerializer(fields=domainTxnOrderedFields),
                    fileName=tconf.domainTransactionsFile)
    for txn in genesisTxns:
        ledger.add(txn)


@pytest.fixture(scope="module")
def nodeSet(tconf, updatedDomainTxnFile, txnPoolNodeSet):
    return txnPoolNodeSet


@pytest.fixture(scope="module")
def client1Signer():
    seed = b'client1Signer secret key........'
    signer = SimpleSigner(seed=seed)
    assert signer.verkey == '6JvpZp2haQgisbXEXE9NE6n3Tuv77MZb5HdF9jS5qY8m'
    return signer


@pytest.fixture("module")
def sponsorCli(looper, tdir):
    return newCLI(looper, tdir)


@pytest.fixture(scope="module")
def clientAndWallet1(client1Signer, looper, nodeSet, tdir, up):
    client, wallet = genTestClient(nodeSet, tmpdir=tdir, usePoolLedger=True)
    wallet = Wallet(client.name)
    wallet.addIdentifier(signer=client1Signer)
    return client, wallet


@pytest.fixture(scope="module")
def client1(clientAndWallet1, looper):
    client, wallet = clientAndWallet1
    looper.add(client)
    looper.run(client.ensureConnectedToNodes())
    return client


@pytest.fixture(scope="module")
def wallet1(clientAndWallet1):
    return clientAndWallet1[1]


@pytest.fixture(scope="module")
def sponsorWallet():
    wallet = Wallet('sponsor')
    seed = b'sponsors are people too.........'
    wallet.addIdentifier(seed=seed)
    return wallet


@pytest.fixture(scope="module")
def sponsor(nodeSet, addedSponsor, sponsorWallet, looper, tdir):
    s, _ = genTestClient(nodeSet, tmpdir=tdir, usePoolLedger=True)
    s.registerObserver(sponsorWallet.handleIncomingReply)
    looper.add(s)
    looper.run(s.ensureConnectedToNodes())
    makePendingTxnsRequest(s, sponsorWallet)
    return s


@pytest.fixture(scope="module")
def addedSponsor(nodeSet, steward, stewardWallet, looper,
                 sponsorWallet):
    createNym(looper,
              sponsorWallet.defaultId,
              steward,
              stewardWallet,
              role=SPONSOR,
              verkey=sponsorWallet.getVerkey())
    return sponsorWallet


@pytest.fixture(scope="module")
def userWalletA(nodeSet, addedSponsor, sponsorWallet, looper, sponsor):
    return addRole(looper, sponsor, sponsorWallet, 'userA', useDid=False,
                   addVerkey=False)


@pytest.fixture(scope="module")
def userWalletB(nodeSet, addedSponsor, sponsorWallet, looper, sponsor):
    return addRole(looper, sponsor, sponsorWallet, 'userB', useDid=False,
                   addVerkey=False)


@pytest.fixture(scope="module")
def userIdA(userWalletA):
    return userWalletA.defaultId


@pytest.fixture(scope="module")
def userIdB(userWalletB):
    return userWalletB.defaultId


@pytest.fixture(scope="module")
def userClientA(nodeSet, userWalletA, looper, tdir):
    u, _ = genTestClient(nodeSet, tmpdir=tdir, usePoolLedger=True)
    u.registerObserver(userWalletA.handleIncomingReply)
    looper.add(u)
    looper.run(u.ensureConnectedToNodes())
    makePendingTxnsRequest(u, userWalletA)
    return u


@pytest.fixture(scope="module")
def userClientB(nodeSet, userWalletB, looper, tdir):
    u, _ = genTestClient(nodeSet, tmpdir=tdir, usePoolLedger=True)
    u.registerObserver(userWalletB.handleIncomingReply)
    looper.add(u)
    looper.run(u.ensureConnectedToNodes())
    makePendingTxnsRequest(u, userWalletB)
    return u


def pytest_assertrepr_compare(op, left, right):
    if isinstance(left, str) and isinstance(right, str):
        if op in ('in', 'not in'):
            mod = 'not ' if 'not' in op else ''
            lines = ['    ' + s for s in right.split('\n')]
            return ['"{}" should {}be in...'.format(left, mod)] + lines


@pytest.fixture("module")
def nodeThetaAdded(looper, nodeSet, tdirWithPoolTxns, tconf, steward,
                   stewardWallet, allPluginsPath, testNodeClass,
                   testClientClass, tdir):
    newStewardName = "testClientSteward" + randomString(3)
    newNodeName = "Theta"
    newSteward, newStewardWallet = getClientAddedWithRole(nodeSet, tdir,
                                                          looper, steward,
                                                          stewardWallet,
                                                          newStewardName, STEWARD)

    sigseed = randomString(32).encode()
    nodeSigner = SimpleSigner(seed=sigseed)

    (nodeIp, nodePort), (clientIp, clientPort) = genHa(2)

    data = {
        NODE_IP: nodeIp,
        NODE_PORT: nodePort,
        CLIENT_IP: clientIp,
        CLIENT_PORT: clientPort,
        ALIAS: newNodeName,
        SERVICES: [VALIDATOR, ]
    }

    node = Node(nodeSigner.identifier, data, newStewardWallet.defaultId)
    newStewardWallet.addNode(node)
    reqs = newStewardWallet.preparePending()
    req, = newSteward.submitReqs(*reqs)

    checkSufficientRepliesForRequests(looper, newSteward, [req, ])

    def chk():
        assert newStewardWallet.getNode(node.id).seqNo is not None

    looper.run(eventually(chk, retryWait=1, timeout=10))

    initLocalKeep(newNodeName, tdirWithPoolTxns, sigseed, override=True)

    newNode = testNodeClass(newNodeName, basedirpath=tdir, config=tconf,
                            ha=(nodeIp, nodePort), cliha=(clientIp, clientPort),
                            pluginPaths=allPluginsPath)

    nodeSet.append(newNode)
    looper.add(newNode)
    looper.run(checkNodesConnected(nodeSet))
    ensureClientConnectedToNodesAndPoolLedgerSame(looper, steward,
                                                  *nodeSet)
    ensureClientConnectedToNodesAndPoolLedgerSame(looper, newSteward,
                                                  *nodeSet)
    return newSteward, newStewardWallet, newNode



