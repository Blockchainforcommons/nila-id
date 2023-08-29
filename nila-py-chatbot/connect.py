import sys
import os
sys.path.append("..")
from base64 import b64decode
from algosdk.v2client import algod, indexer
from typing import List, Dict, Any, Optional
from algosdk import mnemonic, encoding
from algosdk.transaction import AssetTransferTxn, PaymentTxn
from algosdk import account
from algosdk.transaction import AssetOptInTxn,ApplicationOptInTxn, AssetTransferTxn, PaymentTxn

from datetime import datetime as dt, timedelta,timezone
load_dotenv()

mnemonic_phrase = os.getenv("ROOT_MNEMONIC")
root_PK = os.getenv("ROOT_PK")

SK = mnemonic.to_private_key(mnemonic_phrase)
PK = encoding.encode_address(b64decode(SK)[32:])

algod_token = os.getenv("ALGOD_TOKEN")
algod_address = 'https://testnet-algorand.api.purestake.io/ps2'
index_address = 'https://testnet-algorand.api.purestake.io/idx2'
purestake_token = {'X-Api-key': algod_token}
algodclient = algod.AlgodClient(algod_token, algod_address, headers=purestake_token)
chittaIndex = indexer.IndexerClient(algod_token, index_address, purestake_token)
suggestedParams = algodclient.suggested_params()

# creds for bin address
bin_key = {'addr': 'SQSWYZ5PBINYYVK2XPKTNG6K2HMU7GNI6XAI7KYVYKGKXAYAVOD4CONCKA', 'sk': 'blurkGxUZ24ePJQ+nx1f/uUnydEq2ZfIINb1JZikoQOUJWxnrwobjFVau9U2m8rR2U+ZqPXAj6sVwoyrgwCrhw=='}

def getLabelTxns(pk):
    # find deposits of croplabel contract
    starttime = (dt.now(timezone.utc) - timedelta(days=185)).isoformat()
    txs = chittaIndex.search_transactions_by_address(address=pk, txn_type="appl", start_time=starttime)
    print('nmb of txns', len(txs))
    now_plus_3wk = dt.timestamp(dt.now() + timedelta(days=21))
    for tx in txs['transactions']:
        if tx['application-transaction']['application-id'] == 119275134 and tx['sender'] != pk:
            if now_plus_3wk > b64decode(tx['note'])[4]:
                # there is at least 1 active season, set label to true
                print('match', b64decode(tx['note']))
                return b64decode(tx['note']).decode("utf-8")
    return False

class PendingTxnResponse:
    def __init__(self, response: Dict[str, Any]) -> None:
        self.poolError: str = response["pool-error"]
        self.txn: Dict[str, Any] = response["txn"]

        self.applicationIndex: Optional[int] = response.get("application-index")
        self.assetIndex: Optional[int] = response.get("asset-index")
        self.closeRewards: Optional[int] = response.get("close-rewards")
        self.closingAmount: Optional[int] = response.get("closing-amount")
        self.confirmedRound: Optional[int] = response.get("confirmed-round")
        self.globalStateDelta: Optional[Any] = response.get("global-state-delta")
        self.localStateDelta: Optional[Any] = response.get("local-state-delta")
        self.receiverRewards: Optional[int] = response.get("receiver-rewards")
        self.senderRewards: Optional[int] = response.get("sender-rewards")

        self.innerTxns: List[Any] = response.get("inner-txns", [])
        self.logs: List[bytes] = [b64decode(l) for l in response.get("logs", [])]

def check_if_local_state_has_asset(pk):
    prop_local_state =chittaIndex.lookup_account_application_local_state(address=pk,application_id=117683187)
    try:
        for kv in prop_local_state['apps-local-states'][0]['key-value']:
            if b64decode(kv['key']) == b'prop_id':
                return kv['value']['uint']
        # not found anything, so return false
        return False
    except:
        # no local state so return false
        return False

def waitForTransaction(
    client: algod.AlgodClient, txID: str, timeout: int = 10
    ) -> PendingTxnResponse:
    lastStatus = client.status()
    lastRound = lastStatus["last-round"]
    startRound = lastRound

    while lastRound < startRound + timeout:
        pending_txn = client.pending_transaction_info(txID)

        if pending_txn.get("confirmed-round", 0) > 0:
            return PendingTxnResponse(pending_txn)

        if pending_txn["pool-error"]:
            raise Exception("Pool error: {}".format(pending_txn["pool-error"]))

        lastStatus = client.status_after_block(lastRound + 1)

        lastRound += 1

    raise Exception(
        "Transaction {} not confirmed after {} rounds".format(txID, timeout)
    )

def newWallet(phone,AESTABLE):
    '''
         NON VERIFIED USERS (BY THE FPO) HAVE THEIR SK EXPOSED.
         ONLY WHEN THE FPO VERIFIES THE USER, AND THE FRIEND ENTERED ITS PIN, WILL THE CIPHERS BE UPDATED AND THE SK REMOVED.
    '''
    # create a new wallet
    SK, PK = account.generate_account()
    # save the SK ciphertext, salt and MAC
    AESTABLE.put_item(
            Item={
                'phone': phone, 
                'SK' : SK,
            })
    algoFaucet(PK) # ADD SOME ALGO TO AT LEAST OPT-IN TO CHT
    optinAppsAssets(PK, SK,[],[38909410])  # ONLY OPT-IN TO CHT, NOT ANY COMMODITIES. 
    return PK

def optinAppsAssets(
    sender,
    SK,
    app_indexes:list,
    asset_indexes:list,
    ) -> int:
    signedmsg = []
    for index in app_indexes:
        appO = ApplicationOptInTxn(
            sender=sender,
            index=index,
            sp=suggestedParams
        )
        signedmsg.append(appO.sign(SK))
    for index in asset_indexes:
        appO = AssetOptInTxn(
            sender=sender,
            index=index,
            sp=suggestedParams
        )
        signedmsg.append(appO.sign(SK))

    # SEND THE SIGNED MESSAGES IN BULK
    algodclient.send_transactions(signedmsg) # setup before asset. due to optin of cht?
    # DO NOT WAIT FOR TX TO SPEED UP API. waitForTransaction(algodclient, signedmsg[:1][0].get_txid())

def algoFaucet(pk):
    print('send some algo to the PK in attribute')
    # Create and sign transaction
    tx = PaymentTxn(sender=PK, sp=suggestedParams, receiver=pk, amt=1000000) # send 1 algo
    signed_tx = tx.sign(SK)
    try:
        tx_confirm = algodclient.send_transaction(signed_tx)
        print('Transaction sent with ID', signed_tx.transaction.get_txid())
        print('tx_confirm', tx_confirm)
        # lambda execution stops when waiting for confirmation in while function..
        print('we wait for confirmation - so sure if this tx came through, and we have enough ALGO for other actions')
        waitForTransaction(algodclient, signed_tx.get_txid())
        return True
        
    except Exception as e:
        print(e)
        return False
