"""A CLI utility to build oracle transactions in the preprod network"""

from lib import cardano
from dotenv import load_dotenv
from blockfrost import BlockFrostApi

import pycardano as pyc
import argparse
import cbor2
import os


parser = argparse.ArgumentParser(
    description="A CLI utility to build oracle transactions in the preprod network",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    add_help=False,
)

parser.add_argument("transaction_type", choices=["request", "respond"])

# The skey that will be used to create the transaction
parser.add_argument("-c", "--creator", required=True)


def main():
    load_dotenv()

    chain_context = pyc.BlockFrostChainContext(
        project_id=os.environ.get("BLOCKFROST_PROJECT_ID"),
        base_url="https://cardano-preprod.blockfrost.io/api",
        network=pyc.Network.TESTNET,
    )
    api = BlockFrostApi(
        project_id=os.environ.get("BLOCKFROST_PROJECT_ID"),
        base_url="https://cardano-preprod.blockfrost.io/api",
    )

    parser_args = parser.parse_known_args()

    try:
        skey = pyc.PaymentSigningKey.from_cbor(parser_args[0].creator)
    except ValueError:
        print(
            "Creator argument could not be converted to a private key, make sure it is in CBOR format"
        )
        exit(1)

    vkey = pyc.VerificationKey.from_signing_key(skey)
    address = pyc.Address(payment_part=vkey.hash(), network=pyc.Network.TESTNET)

    utxos = chain_context.utxos(str(address))
    if utxos == []:
        print("Creator provided has no UTxOs in his address")
        exit(1)

    if parser_args[0].transaction_type == "request":
        request_parser = argparse.ArgumentParser(parents=[parser])

        request_parser.add_argument("-p", "--proposal_id", default="test_proposal_id")
        request_parser.add_argument("-d", "--deadline", default=0)
        request_parser.add_argument("-o", "--oracles", nargs="+", required=True)
        request_parser.add_argument("-m", "--min_signatures", type=int, required=True)
        request_parser.add_argument("-a", "--payment_address", required=True)

        args = request_parser.parse_args()

        dummy_minting_policy = pyc.ScriptHash.from_primitive(
            "02aa7e9d83f43ad54ab2585900292db7280ec43410e7563dac934d17"
        )

        datum = cardano.create_datum(
            args.proposal_id,
            dummy_minting_policy,
            vkey.hash(),
            int(args.deadline),
            [bytes.fromhex(oracle) for oracle in args.oracles],
            args.min_signatures,
            pyc.Address.from_primitive(args.payment_address),
        )

        with open("./scripts/script.plutus", "r") as f:
            script_hex = f.read()

            transaction = cardano.create_data_request(
                chain_context,
                utxos,
                address,
                script_hex,
                10_000_000,
                datum,
            )

            print("======== Transaction =========")
            print(transaction)
            print("==============================")

            signed_tx = cardano.assemble_transaction(transaction, skey)

            chain_context.submit_tx(signed_tx.to_cbor())

            print("==============================")
            print(f"Transaction {signed_tx.transaction_body.id} submitted successfully")
    else:
        respond_parser = argparse.ArgumentParser(parents=[parser])
        respond_parser.add_argument("-i", "--input", required=True)
        respond_parser.add_argument("-r", "--results", required=True)
        respond_parser.add_argument("-s", "--signatures", nargs="+", required=True)

        args = respond_parser.parse_args()

        tx_hash, index = args.input.split("#")
        input_utxo = cardano.utxo_from_input(api, tx_hash, int(index))

        with open("./scripts/script.plutus", "r") as f:
            script_hex = f.read()

            datum = cardano.datum_from_cbor(input_utxo.output.datum.cbor)

            plutus_credential = datum.items[6]

            payment_address = pyc.Address(
                payment_part=pyc.VerificationKeyHash.from_primitive(
                    plutus_credential.payment_part
                ),
                network=pyc.Network.TESTNET,
            )

            transaction = cardano.submit_oracles_data(
                chain_context,
                utxos[0],
                input_utxo,
                script_hex,
                datum,
                payment_address,
                bytes.fromhex(args.results),
                [bytes.fromhex(sig) for sig in args.signatures],
            )

            signed_tx = cardano.assemble_transaction(transaction, skey)

            chain_context.submit_tx(signed_tx.to_cbor())

            print(f"Transaction {signed_tx.transaction_body.id} submitted successfully")


if __name__ == "__main__":
    main()
