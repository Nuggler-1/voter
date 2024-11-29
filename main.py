from utils.account import AccountEVM
from utils.utils import error_handler, sleep, get_proxy
from utils.constants import DEFAULT_PRIVATE_KEYS, DEFAULT_PROXIES
from eth_account.messages import encode_typed_data

import requests
from fake_useragent import UserAgent
from config import VOTE_CONTRACT, DEFAULT_RPC, DELAY
from loguru import logger
import time 

import sys

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> |  <level>{message}</level>",
    colorize=True
)

class Runner(AccountEVM):

    def __init__(self, private_key: str, rpc: str, proxy: dict = None): 

        super().__init__(private_key, rpc, proxy=proxy,)
        self.base_url = 'https://api.reya.xyz/'
        self.proxy = proxy
        self.headers = { 
            'Referer': 'https://www.poster.fun/badge-mint',
            'accept':'application/json, text/plain, */*',
            'accept-encoding':'gzip, deflate, br, zstd',
            'accept-language':'en-US;q=0.8,en;q=0.7',
            'host': 'api.reya.xyz',
            'content-type':'application/json',
            'origin': 'https://app.reya.network',
            'rererer': 'https://app.reya.network/',
            'user-agent': UserAgent().random,
            
        }

    @error_handler('getting vote power')
    def _check_vote_power(self,) -> int:

        """0 if account has already voted or voting power is 0, else returns voting power"""

        url = f'{self.base_url}api/vote/rnip2/user/{self.account.address}'
        response = requests.get(url, headers=self.headers, proxies=self.proxy)

        if response.status_code == 200 and not response.json()['hasVoted']:
            logger.info(f'{self.account.address} has voting power: {response.json()["votingPower"]}')
            return response.json()['votingPower']
        elif response.json()['hasVoted']:
            logger.info(f'{self.account.address} has already voted')
            return 0
        else: 
            return 0
        
    @error_handler('casting vote')
    def cast_vote(self, vote_contract = VOTE_CONTRACT) -> int: 

        if not self._check_vote_power(): 
            logger.warning(f'{self.account.address} has already voted or has no voting power')
            return 0

        deadline = int(time.time()) + 604800
        signature_data = {
            "types": {
                "CastVoteBySig": [
                    {
                        "name": "verifyingChainId",
                        "type": "uint256"
                    },
                    {
                        "name": "voter",
                        "type": "address"
                    },
                    {
                        "name": "yesVote",
                        "type": "bool"
                    },
                    {
                        "name": "nonce",
                        "type": "uint256"
                    },
                    {
                        "name": "deadline",
                        "type": "uint256"
                    }
                ],
                "EIP712Domain": [
                    {
                        "name": "name",
                        "type": "string"
                    },
                    {
                        "name": "version",
                        "type": "string"
                    },
                    {
                        "name": "verifyingContract",
                        "type": "address"
                    }
                ]
            },
            "domain": {
                "name": "Reya",
                "version": "1",
                "verifyingContract": vote_contract
            },
            "primaryType": "CastVoteBySig",
            "message": {
                "verifyingChainId": 1729,
                "voter": self.account.address,
                "yesVote": '',
                "nonce": 1,
                "deadline": deadline
            }
        }
        signature = self.account.sign_message(encode_typed_data(full_message=signature_data)).signature.hex()

        url = f'{self.base_url}api/vote/{vote_contract}/vote'
        payload = {
            'isYesVote': True,
            'signature': '0x'+signature,
            'signatureDeadline': deadline,
            'voter': self.account.address
        }

        response = requests.put(url, headers=self.headers, proxies=self.proxy, json=payload)
        if response.status_code == 200:
            logger.success(f'{self.account.address} voted successfully')
            return 1
        else:
            raise Exception(f'{self.account.address} failed to vote with response status code: {response.status_code} - {response.text}')


def main(): 

    with open(DEFAULT_PRIVATE_KEYS, 'r', encoding='utf-8') as f: 
        private_keys = f.read().splitlines()

    for private_key in private_keys: 

        proxy = get_proxy(private_key)
        runner = Runner(private_key, DEFAULT_RPC, proxy = proxy)
        res = runner.cast_vote()

        if res!=0 and private_key!=private_keys[-1]: 
            sleep(DELAY)

if __name__ == '__main__': 
    main()