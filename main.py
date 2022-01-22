import asyncio
import aiohttp
import construct
import dotenv
import os
from base64 import b64encode
from dotenv import load_dotenv
from solana import system_program
from solana.system_program import create_account, CreateAccountParams, AssignParams, assign
from solana.blockhash import Blockhash
from solana.account import Account
from solana.rpc.api import Client
from solana.rpc.providers.http import HTTPProvider
from solana.publickey import PublicKey, base58
from solana.transaction import AccountMeta, TransactionInstruction, Transaction
from solana.rpc import commitment, types
from spl.token.instructions import InitializeMintParams, initialize_mint, create_associated_token_account, mint_to, MintToParams, get_associated_token_address
from spl.token.constants import TOKEN_PROGRAM_ID
from typing import Any, Dict, List, Optional, Union

class Main:

    opts = types.TxOpts(skip_preflight = True)

    account_secret = ""
    SYSTEM_PROGRAM_ID = PublicKey("11111111111111111111111111111111")
    CANDY_PROGRAM_ID = PublicKey("cndyAnrLdpjq1Ssp1z8xxDsB8dxe7u4HL5Nxi2K5WXZ")

    owner = None
    rpc1 = "https://solana-api.projectserum.com"
    rpc2 = "https://api.mainnet-beta.solana.com"
    client = Client("https://solana-api.projectserum.com")
    TIMEOUT = 3600
    session = None
    request_id = 1
    blockhash = None
    tasks = []
    tx_count = 0

    def __init__(self, secret_key):

        self.account_secret = secret_key
        self.owner = Account(base58.b58decode(self.account_secret)[:32])
        loop = asyncio.get_event_loop()
        tasks = [
                    self.main(),
                    self.get_blockhash()
                ]
        loop.run_until_complete(asyncio.wait(tasks))

    async def get_blockhash(self):
        while True:
            res = self.client.get_recent_blockhash(commitment.Commitment("recent"))
            self.blockhash = Blockhash(res["result"]["value"]["blockhash"])
            await asyncio.sleep(0.1)

    async def main(self):
        while True:
            asyncio.create_task(self.mint())
            self.request_id += 1
            await asyncio.sleep(0.1)

    def candyInstruction(self, mintAccount):
        programId = self.CANDY_PROGRAM_ID
        metadatapubkey, _ = PublicKey.find_program_address(
            seeds=['metadata'.encode('utf-8') ,bytes(PublicKey("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")), bytes(mintAccount.public_key())], program_id=PublicKey("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")
        )
        editionpubkey, _ = PublicKey.find_program_address(
            seeds=['metadata'.encode('utf-8') ,bytes(PublicKey("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")), bytes(mintAccount.public_key()), 'edition'.encode('utf-8')], program_id=PublicKey("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")
        )
        keys = [
            AccountMeta(pubkey=PublicKey("D49FEB8s1PjKYawXE6WW64QvaDPxT5ALNzqpxkD7XKkH"), is_signer=False, is_writable=False),
            AccountMeta(pubkey=PublicKey("9vwYtcJsH1MskNaixcjgNBnvBDkTBhyg25umod1rgMQL"), is_signer=False, is_writable=True),
            AccountMeta(pubkey=self.owner.public_key(), is_signer=True, is_writable=True),
            AccountMeta(pubkey=PublicKey("aury7LJUae7a92PBo35vVbP61GX8VbyxFKausvUtBrt"), is_signer=False, is_writable=True),
            AccountMeta(pubkey=metadatapubkey, is_signer=False, is_writable=True),
            AccountMeta(pubkey=mintAccount.public_key(), is_signer=True, is_writable=True),
            AccountMeta(pubkey=self.owner.public_key(), is_signer=True, is_writable=True),
            AccountMeta(pubkey=self.owner.public_key(), is_signer=True, is_writable=True),
            AccountMeta(pubkey=editionpubkey, is_signer=False, is_writable=True),
            AccountMeta(pubkey=PublicKey("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"), is_signer=False, is_writable=False),
            AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
            AccountMeta(pubkey=self.SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),
            AccountMeta(pubkey=PublicKey("SysvarRent111111111111111111111111111111111"), is_signer=False, is_writable=False),
            AccountMeta(pubkey=PublicKey("SysvarC1ock11111111111111111111111111111111"), is_signer=False, is_writable=False),
        ]
        data = b'\xd3\x39\x06\xa7\x0f\xdb\x23\xfb'
        return TransactionInstruction(
          keys,
          programId,
          data
        )

    async def mint(self):
        transaction = Transaction()
        newaccount = Account()
        signers: List[Account] = [self.owner, newaccount]
        #create account
        ca_param = CreateAccountParams(
            from_pubkey=self.owner.public_key(),
            new_account_pubkey=newaccount.public_key(),
            lamports=1461600,
            space=82,
            program_id=self.SYSTEM_PROGRAM_ID
        )
        transaction.add(
            create_account(ca_param)
        )

        assign_param = AssignParams(
            newaccount.public_key(),
            TOKEN_PROGRAM_ID
        )
        transaction.add(
            assign(assign_param)
        )

        #initialize mint
        im_param = InitializeMintParams(
            decimals=0,
            program_id=TOKEN_PROGRAM_ID,
            mint=newaccount.public_key(),
            mint_authority=self.owner.public_key(),
            freeze_authority=self.owner.public_key()
        )
        transaction.add(
            initialize_mint(im_param)
        )

        #create associated token account
        transaction.add(
            create_associated_token_account(
                payer=self.owner.public_key(),
                owner=self.owner.public_key(),
                mint=newaccount.public_key()
            )
        )
        associated_token_address = get_associated_token_address(
            owner=self.owner.public_key(),
            mint=newaccount.public_key()
        )

        #mint to
        mint_to_param = MintToParams(
            program_id=TOKEN_PROGRAM_ID,
            mint=newaccount.public_key(),
            dest=associated_token_address,
            mint_authority=self.owner.public_key(),
            amount=1,
        )
        transaction.add(
            mint_to(mint_to_param)
        )

        #candymachine
        transaction.add(
            self.candyInstruction(newaccount)
        )


        return await self.send_tx(transaction, *signers, opts=self.opts)

    async def send_tx(self, txn: Transaction, *signers: Account, opts: types.TxOpts = types.TxOpts()):
        txn.recent_blockhash = self.blockhash
        txn.sign(*signers)
        tx = txn.serialize()
        return await self.send_raw_tx(tx, opts)

    async def send_raw_tx(self, txn: Union[bytes, str], opts: types.TxOpts = types.TxOpts()):
        if isinstance(txn, bytes):
            txn = b64encode(txn).decode("utf-8")
        self.tx_count += 1
        params = txn, {"skipPreflight":opts.skip_confirmation,"skipPreflight":opts.skip_preflight,"encoding":"base64"}
        if self.tx_count % 2 == 0:
            provider = HTTPProvider(self.rpc1)
            headers = {"Content-Type": "application/json"}
            data = provider.json_encode({"jsonrpc": "2.0", "id": self.request_id, "method": types.RPCMethod("sendTransaction"), "params": params})
            async with aiohttp.ClientSession() as session:
                response = await session.post(
                    self.rpc1,
                    data=data,
                    headers=headers
                )
                content = await response.text()
                print(content)
                return content
        else:
            provider = HTTPProvider(self.rpc2)
            headers = {"Content-Type": "application/json"}
            data = provider.json_encode({"jsonrpc": "2.0", "id": self.request_id, "method": types.RPCMethod("sendTransaction"), "params": params})
            async with aiohttp.ClientSession() as session:
                response = await session.post(
                    self.rpc2,
                    data=data,
                    headers=headers
                )
                content = await response.text()
                print(content)
                return content


if __name__ == '__main__':

    load_dotenv()
    secret_key = os.getenv("SECRET_KEY")
    Main(secret_key)