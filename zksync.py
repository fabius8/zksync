from web3 import Web3
from zksync2.module.module_builder import ZkSyncBuilder
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from eth_account.signers.local import LocalAccount
from zksync2.manage_contracts.gas_provider import StaticGasProvider
from zksync2.manage_contracts.l2_bridge import L2BridgeEncoder
from zksync2.core.types import Token
from zksync2.provider.eth_provider import EthereumProvider
from zksync2.core.types import EthBlockParams
from zksync2.signer.eth_signer import PrivateKeyEthSigner
from zksync2.transaction.transaction712 import Transaction712
from zksync2.core.types import ZkBlockParams, BridgeAddresses
from eth_typing import HexStr
from zksync2.module.request_types import create_function_call_transaction
from decimal import Decimal
import schedule
import time
import json
import os
import random

URL_TO_ETH_NETWORK = "https://rpc.ankr.com/eth_goerli"
ZKSYNC_NETWORK_URL = "https://zksync2-testnet.zksync.dev"


#hain_id = 5
#PRIVATE_KEY = os.environ.get("")

private = json.load(open('private.json'))
account: LocalAccount = Account.from_key(private["private"])



def deposit():
    try:
        eth_web3 = Web3(Web3.HTTPProvider(URL_TO_ETH_NETWORK))
        zkSync_web3 = ZkSyncBuilder.build(ZKSYNC_NETWORK_URL)
        #geth_poa_middleware is used to connect to geth --dev.
        eth_web3.middleware_onion.inject(geth_poa_middleware, layer=0)

        #calculate  gas fees
        gas_provider = StaticGasProvider(Web3.toWei(1, "gwei"), 555000)

        #Create the ethereum provider for interacting with ethereum node, initialize zkSync signer and deposit funds.
        eth_provider = EthereumProvider.build_ethereum_provider(zksync=zkSync_web3,
                                                                eth=eth_web3,
                                                                account=account,
                                                                gas_provider=gas_provider)
        tx_receipt = eth_provider.deposit(Token.create_eth(),
                                        eth_web3.toWei("0.0001", "ether"),
                                        account.address)
        # Show the output of the transaction details.
        #print(f"tx status: {tx_receipt}")
        print(f"tx status: {tx_receipt['status']}")
    except Exception as e:
        print(e)
        pass

def get_account_balance():
    eth_web3 = Web3(Web3.HTTPProvider(URL_TO_ETH_NETWORK))
    zkSync_web3 = ZkSyncBuilder.build(ZKSYNC_NETWORK_URL)
    zk_balance = zkSync_web3.zksync.get_balance(account.address, EthBlockParams.LATEST.value)
    print(f"zkSync balance: {zk_balance}")

def transfer_to_self():
    try:
        eth_web3 = Web3(Web3.HTTPProvider(URL_TO_ETH_NETWORK))
        zkSync_web3 = ZkSyncBuilder.build(ZKSYNC_NETWORK_URL)
        chain_id = zkSync_web3.zksync.chain_id
        signer = PrivateKeyEthSigner(account, chain_id)

        nonce = zkSync_web3.zksync.get_transaction_count(account.address, ZkBlockParams.COMMITTED.value)
        tx = create_function_call_transaction(from_=account.address,
                                            to=account.address,
                                            ergs_price=0,
                                            ergs_limit=0,
                                            data=HexStr("0x"))
        estimate_gas = int(zkSync_web3.zksync.eth_estimate_gas(tx) * 1.3)
        
        gas_price = zkSync_web3.zksync.gas_price
        print(f"Fee for transaction is: {estimate_gas * gas_price}")

        tx_712 = Transaction712(chain_id=chain_id,
                                nonce=nonce,
                                gas_limit=estimate_gas,
                                to=tx["to"],
                                value=Web3.toWei(0.001, 'ether'),
                                data=tx["data"],
                                maxPriorityFeePerGas=100000000,
                                maxFeePerGas=gas_price,
                                from_=account.address,
                                meta=tx["eip712Meta"])

        singed_message = signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = zkSync_web3.zksync.send_raw_transaction(msg)
        tx_receipt = zkSync_web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
        print(f"tx status: {tx_receipt['status']}")
    except Exception as e:
        print(e)
        pass

def withdraw():
    try:
        eth_web3 = Web3(Web3.HTTPProvider(URL_TO_ETH_NETWORK))
        zkSync_web3 = ZkSyncBuilder.build(ZKSYNC_NETWORK_URL)
        chain_id = zkSync_web3.zksync.chain_id
        signer = PrivateKeyEthSigner(account, chain_id)
        ETH_TOKEN = Token.create_eth()

        nonce = zkSync_web3.zksync.get_transaction_count(account.address, ZkBlockParams.COMMITTED.value)
        bridges: BridgeAddresses = zkSync_web3.zksync.zks_get_bridge_contracts()

        l2_func_encoder = L2BridgeEncoder(zkSync_web3)
        call_data = l2_func_encoder.encode_function(fn_name="withdraw", args=[
            account.address,
            ETH_TOKEN.l2_address,
            ETH_TOKEN.to_int(Decimal("0.001"))
        ])

        tx = create_function_call_transaction(from_=account.address,
                                            to=bridges.l2_eth_default_bridge,
                                            ergs_limit=0,
                                            ergs_price=0,
                                            data=HexStr(call_data))
        estimate_gas = int(zkSync_web3.zksync.eth_estimate_gas(tx) * 1.3)
        gas_price = zkSync_web3.zksync.gas_price

        print(f"Fee for transaction is: {estimate_gas * gas_price}")

        tx_712 = Transaction712(chain_id=chain_id,
                                nonce=nonce,
                                gas_limit=estimate_gas,
                                to=tx["to"],
                                value=tx["value"],
                                data=tx["data"],
                                maxPriorityFeePerGas=100000000,
                                maxFeePerGas=gas_price,
                                from_=account.address,
                                meta=tx["eip712Meta"])

        singed_message = signer.sign_typed_data(tx_712.to_eip712_struct())
        msg = tx_712.encode(singed_message)
        tx_hash = zkSync_web3.zksync.send_raw_transaction(msg)
        tx_receipt = zkSync_web3.zksync.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=0.5)
        print(f"tx status: {tx_receipt['status']}")
    except Exception as e:
        print(e)
        pass

#print(random.random()*10)
transfer_to_self()
deposit()
withdraw()
#schedule.every(10).seconds.do(lambda: transfer_to_self())

schedule.every(50).minutes.do(lambda: transfer_to_self())
schedule.every(2).hours.do(lambda: deposit())
schedule.every(3).hours.do(lambda: withdraw())
while True:
    schedule.run_pending()
    time.sleep(1)

