"""A CLI utility to build oracle transactions in the preprod network"""

from lib import cardano
from dotenv import load_dotenv
from blockfrost import BlockFrostApi

import pycardano as pyc
import argparse
import cbor2
import os


parser = argparse.ArgumentParser(
    description="A CLI utility to inspect datums",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    add_help=False,
)

parser.add_argument("-i", "--input", required=True)


def main():
    load_dotenv()

    api = BlockFrostApi(
        project_id=os.environ.get("BLOCKFROST_PROJECT_ID"),
        base_url="https://cardano-preprod.blockfrost.io/api",
    )

    args = parser.parse_args()

    tx_hash, index = args.input.split("#")
    input_utxo = cardano.utxo_from_input(api, tx_hash, int(index))

    print(cardano.cbor_datum_to_dict(input_utxo.output.datum.cbor))


if __name__ == "__main__":
    main()
