from __future__ import annotations
from typing import Tuple, List
from dataclasses import dataclass

import pycardano as pyc
import enum
import cbor2
import copy


@dataclass
class ResultsSome(pyc.PlutusData):
    CONSTR_ID = 0
    results: bytes


@dataclass
class ResultsNone(pyc.PlutusData):
    CONSTR_ID = 1


@dataclass
class PlutusAddress(pyc.PlutusData):
    CONSTR_ID = 0
    payment_part: bytes


@dataclass
class EscrowRedeemerCreatorRetrieval(pyc.PlutusData):
    CONSTR_ID = 0


@dataclass
class EscrowRedeemerEscrowExecution(pyc.PlutusData):
    CONSTR_ID = 1
    oracle_index: int
    results: pyc.IndefiniteList  # List[List[List[int, int]]]


class EscrowRedeemer(enum.Enum):
    CreatorRetrieval = 0
    EscrowExecution = 1


@dataclass
class VoteUseCount(pyc.PlutusData):
    CONSTR_ID = 0


@dataclass
class VoteUseWeigth(pyc.PlutusData):
    CONSTR_ID = 1


def address_to_pubkeyhash(bech32_addr: str) -> str:
    return pyc.Address.from_primitive(bech32_addr).payment_part.to_primitive().hex()


def escrow_vote(count: int, weight: int) -> pyc.Datum:
    return pyc.IndefiniteList([count, weight])


def escrow_redeemer(
    action: EscrowRedeemer,
    oracle_index: int = None,
    results: List[List[Tuple[int, int]]] = None,
) -> pyc.Datum:
    if action == EscrowRedeemer.CreatorRetrieval:
        return EscrowRedeemerCreatorRetrieval()

    # Else we are executing the escrow
    if oracle_index is None or results is None:
        raise ValueError("Oracle index and results are required for escrow execution")

    return EscrowRedeemerEscrowExecution(
        oracle_index,
        pyc.IndefiniteList(
            [
                pyc.IndefiniteList(
                    [escrow_vote(count, weigth) for count, weigth in votes]
                )
                for votes in results
            ]
        ),
    )


def escrow_datum(
    minting_policy: pyc.ScriptHash,
    creator: pyc.VerificationKeyHash,
    deadline: int,
    question_index: int,
    vote_use: VoteUseCount | VoteUseWeigth,
    addresses: List[pyc.Address],
) -> pyc.Datum:
    return pyc.IndefiniteList(
        [
            minting_policy.to_primitive(),
            creator.to_primitive(),
            deadline,
            question_index,
            vote_use,
            pyc.IndefiniteList(
                [PlutusAddress(addr.payment_part.to_primitive()) for addr in addresses]
            ),
        ]
    )


def oracle_datum(
    proposal_id: str,
    miniting_policy_identifier: pyc.ScriptHash,
    creator: pyc.VerificationKeyHash,
    deadline: int,
    oracles: List[bytes],
    min_signatures: int,
    payment_address: pyc.Address,
    results: bytes | None = None,
) -> pyc.Datum:
    return pyc.IndefiniteList(
        [
            bytes(proposal_id, "utf-8"),
            miniting_policy_identifier.to_primitive(),
            creator.to_primitive(),
            deadline,
            pyc.IndefiniteList(oracles),
            min_signatures,
            PlutusAddress(payment_address.payment_part.to_primitive()),
            ResultsNone() if results is None else ResultsSome(results),
        ]
    )


def datum_from_cbor(cbor: bytes):
    data = cbor2.loads(cbor)

    try:
        results = ResultsSome.from_primitive(data[7])
    except Exception:
        results = ResultsNone.from_primitive(data[7])

    return pyc.IndefiniteList(
        [
            data[0],
            data[1],
            data[2],
            data[3],
            pyc.IndefiniteList(data[4]),
            data[5],
            PlutusAddress.from_primitive(data[6]),
            results,
        ],
    )


def datum_to_dict(datum: pyc.IndefiniteList) -> dict:
    try:
        results = datum.items[7].results
    except Exception:
        results = None

    return {
        "proposal_id": bytes.decode(datum.items[0]),
        "minting_policy_identifier": pyc.ScriptHash.from_primitive(datum.items[1]),
        "creator": pyc.VerificationKeyHash.from_primitive(datum.items[2]),
        "deadline": datum.items[3],
        "oracles": datum.items[4].items,
        "min_signatures": datum.items[5],
        "payment_address": pyc.Address(
            payment_part=pyc.VerificationKeyHash.from_primitive(
                datum.items[6].payment_part
            ),
            network=pyc.Network.TESTNET,
        ),
        "results": results,
    }


def cbor_datum_to_dict(cbor: bytes) -> dict:
    return datum_to_dict(datum_from_cbor(cbor))


def update_datum_with_results(datum: pyc.Datum, results: bytes) -> pyc.Datum:
    datum_copy = copy.deepcopy(datum)
    raw_datum = datum_copy.items

    raw_datum[-1] = ResultsSome(results)

    return pyc.IndefiniteList(raw_datum)


def oracle_redeemer(results: bytes, signatures: List[bytes]) -> pyc.Datum:
    return pyc.IndefiniteList([results, pyc.IndefiniteList(signatures)])


def parse_vote_results(results: str) -> List[List[Tuple[int, int]]]:
    """Convert string
        "<count>:<weigth>,<count>:<weigth>...|<count>:<weigth>,<count>:<weigth>..."
    to list of lists of tuples
    """

    return [
        [
            (int(count), int(weigth))
            for count, weigth in [vote.split(":") for vote in votes.split(",")]
        ]
        for votes in results.split("|")
    ]
