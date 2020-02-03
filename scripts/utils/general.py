import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from shlex import quote
from typing import Any, Dict, List, Mapping, Optional, Union

import environs

from scripts.utils.models import SubprocessResult

env = environs.Env()

MYSQL = "mysql"
POSTGRES = "postgresql"
AMQP = "amqp"
DATABASE_DEFAULT_PORT_MAPPING = {MYSQL: 3306, POSTGRES: 5432, AMQP: 5672}


def get_project_secret_var(project_name: str, value: str = "") -> str:
    from scripts.settings import settings

    project = env_var_safe_key(project_name)
    value = env_var_safe_key(value)
    return f"{project}_{settings.K8S_SECRET_PREFIX}{value}"


def camel_case_split(camel_case_string: str) -> str:
    split_string_list = re.findall(
        r"[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z]|$))", camel_case_string
    )
    split_string = " ".join(split_string_list)
    return split_string.capitalize()


def create_artifact_file_from_dict(
    data: Union[Dict[str, Any], Mapping[str, Any]], filename: str = ".env"
) -> Path:
    from scripts.settings import settings

    if not filename.endswith(".env"):
        filename = f"{filename}.env"

    cwd = Path.cwd()
    env_dir = cwd / settings.SERVICE_ARTIFACT_FOLDER
    env_file = env_dir / filename

    # We don't handle OSError here as the execution
    # should stop if this fails
    env_dir.mkdir(exist_ok=True)

    with env_file.open(mode="w+") as f:
        for key, value in data.items():
            f.write(f"{key}={value}\n")

    return env_file


def current_rfc3339_datetime() -> str:
    local_time = datetime.now(timezone.utc).astimezone()
    return local_time.isoformat()


def env_var_safe_key(key: str) -> str:
    """
    Returns a version of the project name that can be used in env vars

    Note that this is not bulletproof at the moment and there might be cases
    that will not work as expected. More validation is needed in order to make
    sure that this always returns a valid value.

    Returns:
        A string modified to work with env var names
    """
    # Convert `key` to upper-case and replace leading digits and all
    # other non-alpha-numeric characters with underscores.
    return re.sub(r"^\d+|\W", "_", key).upper()


def loads_json(string: str) -> Dict[str, Any]:
    try:
        result = json.loads(string)
    except Exception:
        result = {}

    if not isinstance(result, dict):
        raise TypeError("Incorrect result")

    return result


def get_deploy_name(track: Optional[str] = None, postfix: Optional[str] = None) -> str:
    from scripts.settings import settings

    track_postfix = f"-{track}" if track and track != settings.DEFAULT_TRACK else ""
    deploy_name = f"{settings.ENVIRONMENT_SLUG}{track_postfix}"
    postfix = f"-{postfix}" if postfix else ""
    return f"{deploy_name}{postfix}"


def get_secret_name(track: Optional[str] = None, postfix: Optional[str] = None) -> str:
    deployment_name = get_deploy_name(track, postfix=postfix)
    secret_name = f"{deployment_name}-secret"

    return secret_name


def get_and_strip_prefixed_items(items: Dict[Any, Any], prefix: str) -> Dict[str, Any]:
    return {
        key[len(prefix) :]: value
        for key, value in items.items()
        if key.startswith(prefix)
    }


def get_environment_vars_by_prefixes(prefixes: List[str]) -> Dict[str, str]:
    items = {}

    for prefix in prefixes:
        _items = get_environment_vars_by_prefix(prefix=prefix)
        items.update(_items)
    return items


def get_environment_vars_by_prefix(prefix: str) -> Dict[str, str]:
    """
    Extract all environment variables with a prefix

    Environment variables strting with the `prefix` attribute are
    extracted and put into a dict with the `prefix` removed.

    Args:
        prefix: Prefix to environment key that should be extracted

    Returns:
        A dict of keys stripped of the prefix and the value as given
        in the environment variable.
    """
    env_vars = dict(os.environ)

    # Remove the setting with name "K8S_SECRET_PREFIX" as the default
    # value for that is K8S_SECRET_ which will in turn add an entry
    # with the key "PREFIX"
    # TODO: Rename K8S_SECRET_PREFIX to something that does not clash
    if "K8S_SECRET_PREFIX" in env_vars:
        del env_vars["K8S_SECRET_PREFIX"]
    return get_and_strip_prefixed_items(env_vars, prefix)


def run_os_command(command_list: List[str], shell: bool = False) -> SubprocessResult:

    command = command_list if not shell else " ".join(map(quote, command_list))

    result = subprocess.run(command, encoding="UTF-8", capture_output=True, shell=shell)

    return SubprocessResult(
        out=result.stdout,
        err=result.stderr,
        return_code=result.returncode,
        child=result,
    )


def validate_file_secret_path(path: Path, valid_prefixes: List[str]) -> bool:
    absolute_path = str(path.absolute())
    return any(
        absolute_path.startswith(valid_prefix) for valid_prefix in valid_prefixes
    )


def string_to_yaml(string: str, indentation: int = 0, strip: bool = True) -> bytes:
    if strip:
        string = string.strip()

    # If we have any new lines inside the string,
    # then we have a multi line string and will indent
    if "\n" in string:
        split_sting = string.split("\n")

        # As we have a multi line string, let YAML know it should be
        # interpreted as such
        string = "|-"

        for line in split_sting:
            if strip:
                line = line.strip()
            string += f"\n{indentation * ' '}{line}"
    else:
        string = indentation * " " + string

    return string.encode("utf-8")
