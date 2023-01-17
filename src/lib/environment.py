from typing import List
from dotenv import load_dotenv

import sys
import os


def get_environment(env_names: List[str]):
    # Initialise env variables, if any of them are not
    # here, raise exception
    sys.path.append("src")
    load_dotenv()

    envs = {}
    for env in env_names:
        val = os.environ.get(env)
        if val is None:
            raise ValueError(f"Env variable {env} not found!")

        envs[env] = val

    return envs
