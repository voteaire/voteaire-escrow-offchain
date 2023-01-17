import time
import sys
import cbor2
import pytest
from retry import retry

import pycardano as pyc
import logging

from .base import TEST_RETRIES, TestBase


class TestPlutus(TestBase):
    # @retry(tries=TEST_RETRIES, backoff=1.5, delay=3, jitter=(0, 4))
    # def test_create_transaction_data_request(self):
    #     sys.path.append("../src")

    #     from lib import cardano_tools

    #     sender_address = pyc.Address(self.payment_vkey.hash(), network=self.NETWORK)

    #     # ----------- Giver give ---------------

    #     datum = cardano_tools.create_datum(
    #         "proposal_id",
    #         pyc.ScriptHash.from_primitive(
    #             "02aa7e9d83f43ad54ab2585900292db7280ec43410e7563dac934d17"
    #         ),
    #         sender_address.payment_part,
    #         1000,
    #         [
    #             pyc.VerificationKey.from_cbor(
    #                 "582057d74e4c8d25988a0fa6693dcd3f97153813bc487c84473e5e785b054b17712c"
    #             )
    #         ],
    #         5,
    #         pyc.Address.from_primitive(
    #             "addr_test1qz2hr6ppdnnejh30pz8kqnnvn3vn6kpqx4ntjknvh7urzntkrezryq3ydtmkg0e7e2jvzg443h0ffzfwd09wpcxy2fuqgzhrg5"
    #         ),
    #         None,
    #     )

    #     with open("../scripts/script.plutus", "r") as f:
    #         script_hex = f.read()

    #         transaction = cardano_tools.create_data_request(
    #             self.chain_context,
    #             self.chain_context.utxos(str(sender_address)),
    #             sender_address,
    #             script_hex,
    #             10_000_000,
    #             datum,
    #         )

    #         escrow_script = cbor2.loads(bytes.fromhex(script_hex))
    #         script_hash = pyc.plutus_script_hash(pyc.PlutusV2Script(escrow_script))
    #         script_address = pyc.Address(script_hash, network=self.NETWORK)

    #     # ----------- Submit Transaction --------------

    #     # Sign the transaction body hash
    #     signature = self.payment_skey.sign(transaction.transaction_body.hash())

    #     # Add verification key and the signature to the witness set
    #     vk_witnesses = [pyc.VerificationKeyWitness(self.payment_vkey, signature)]

    #     transaction.transaction_witness_set = pyc.TransactionWitnessSet(
    #         vkey_witnesses=vk_witnesses
    #     )

    #     signed_tx = pyc.Transaction(
    #         transaction.transaction_body,
    #         pyc.TransactionWitnessSet(vkey_witnesses=vk_witnesses),
    #     )

    #     self.chain_context.submit_tx(signed_tx.to_cbor())

    #     time.sleep(5)

    #     self.assert_output(
    #         script_address,
    #         pyc.TransactionOutput(
    #             address=script_address,
    #             amount=10_000_000,
    #             datum_hash=pyc.datum_hash(datum),
    #         ),
    #     )

    def test_create_transaction_data_response(self):
        sys.path.append("../src")

        from lib import cardano

        sender_address = pyc.Address(self.payment_vkey.hash(), network=self.NETWORK)
        alice_address = pyc.Address.from_primitive(
            "addr_test1qp8slek78gxr6wqh004ynlnuex6vnftc70qhxzgh6v8kztlh3032tu7a8vmyr9m74e9cxjj9aty4yuy5radreqc7vuws3gv2t3"
        )

        # ----------- Giver give ---------------

        datum = cardano.create_datum(
            "proposal_id",
            pyc.ScriptHash.from_primitive(
                "02aa7e9d83f43ad54ab2585900292db7280ec43410e7563dac934d17"
            ),
            sender_address.payment_part,
            1000,
            [
                bytes.fromhex(
                    "14889cdb4b72ad10d4d4243c4f50141eea1d10a3482cd20a7da6245d05ea01f1"
                ),
                bytes.fromhex(
                    "f36f9a66f3916127e1ef303eef6cdde224c83da1fc46c3d948d2a68af62dced8"
                ),
                bytes.fromhex(
                    "c3e991c8919b4e2ff03cf2a795afe98c14b3d3ebe2e380598e8b8b46ddac28c4"
                ),
            ],
            2,
            alice_address,
            None,
        )

        with open("../scripts/script.plutus", "r") as f:
            script_hex = f.read()

            transaction = cardano.create_data_request(
                self.chain_context,
                self.chain_context.utxos(str(sender_address)),
                sender_address,
                script_hex,
                10_000_000,
                datum,
            )

            escrow_script = cbor2.loads(bytes.fromhex(script_hex))
            script_hash = pyc.plutus_script_hash(pyc.PlutusV2Script(escrow_script))
            script_address = pyc.Address(script_hash, network=self.NETWORK)

        # ----------- Submit Transaction --------------

        signed_tx = cardano.assemble_transaction(transaction, self.payment_skey)

        logging.warning(signed_tx.transaction_body)

        self.chain_context.submit_tx(signed_tx.to_cbor())

        time.sleep(5)

        self.assert_output(
            script_address,
            pyc.TransactionOutput(
                address=script_address,
                amount=10_000_000,
                datum=datum
                # datum_hash=pyc.datum_hash(datum),
            ),
        )

        # ====================== Data Response =================

        signatures = [
            bytes.fromhex(
                "01b54753c635dbbb59614b52679d413cd0e32332c9f50af83eaf8db23607e6dd74f4a8dc9ccae3842e248c380b5d5398f9f033edf0288100bc7f79c61861900b"
            ),
            bytes.fromhex(
                "102acc4091aa573b9cabf7bbcec53ca11e77d706a5681cbf25c57c11bb6029c31b6dd186c6d64438c99277dd8019a87d163a5b05b33bbe4f75627ce00943eb03"
            ),
            bytes.fromhex("aa"),
        ]

        utxos = self.chain_context.utxos(str(sender_address))
        script_utxo = self.chain_context.utxos(str(script_address))[0]

        logging.warning(script_utxo)

        time.sleep(5)

        transaction = cardano.submit_oracles_data(
            self.chain_context,
            utxos[0],
            script_utxo,
            script_hex,
            datum,
            alice_address,
            bytes.fromhex("74657374"),
            signatures,
        )

        # ----------- Submit Transaction --------------

        signed_tx = cardano.assemble_transaction(transaction, self.payment_skey)

        self.chain_context.submit_tx(signed_tx.to_cbor())

        time.sleep(5)

        self.assert_output(
            script_address,
            pyc.TransactionOutput(
                address=script_address,
                amount=2_000_000,
                datum=cardano.update_datum_with_results(
                    datum, bytes.fromhex("74657374")
                )
            ),
        )

        self.assert_output(
            alice_address,
            pyc.TransactionOutput(
                address=alice_address,
                amount=7_625_743,
            ),
        )
