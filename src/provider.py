"""
Handle account switching in the Juno AWS Organizations
"""

# std
from typing import Union, Dict, TYPE_CHECKING

# 3rd
from pulumi import ResourceOptions, export, InvokeOptions

# local
from .exceptions import ContextNotSet

if TYPE_CHECKING:
    from .context.account import JunoAccount
    from .context.region import JunoRegion

# globals
CONTEXT: Union["JunoRegion", None] = None
ACCOUNT: Union["JunoAccount", None] = None


def context_prefix() -> str:
    """
    Return the current context prefix
    """
    return f"{CONTEXT.account}-{CONTEXT.region}"


def context_export(name, target):
    """
    Return the current context prefix
    """
    return export(f"{context_prefix()}-{name}", target)


def get_context() -> Union["JunoRegion", None]:
    """
    Return the current context
    """
    global CONTEXT
    return CONTEXT


def get_account() -> Union["JunoAccount", None]:
    """
    Return the current account
    """
    global ACCOUNT
    return ACCOUNT


def set_context(context: "JunoRegion" = None):
    """
    Set the current context
    """
    global CONTEXT
    CONTEXT = context


def set_account(account: "JunoAccount" = None):
    """
    Set the current account
    """
    global ACCOUNT
    ACCOUNT = account


# pylint: disable=too-many-arguments
def _build_resource_opts(
    name: str,
    opts: dict,
    tags: dict,
    prefix: str,
    provider,
    no_tags: bool = False,
) -> Dict:
    """
    Return a resource setup with the current provider
    """
    # needs to be a dict for the **opts
    if not opts:
        opts = {
            "parent": provider,
        }

    if not tags:
        tags = {"Name": name}

    # default the parent to the current provider if there isn't one.
    if not opts.get("parent"):
        opts["parent"] = provider

    # default the parent to the current provider if there isn't one.
    if not tags.get("Name"):
        tags["Name"] = name

    tags["Name"] = f"{context_prefix()}-{tags['Name']}"

    if not opts.get("provider"):
        opts["provider"] = provider

    payload = dict(
        opts=ResourceOptions(**opts),
        tags=tags,
        resource_name=f"{prefix}-{name}",
    )

    # if no_tags is set, don't add tags
    if no_tags:
        del payload["tags"]

    return payload


def juno_resource(name: str, opts: Dict = None, tags: Dict = None, no_tags: bool = False) -> Dict:
    """
    Return a resource setup with the current provider
    """
    global CONTEXT

    # fail if the context isn't set
    if CONTEXT is None:
        raise ContextNotSet("No JunoRegion Context set")

    return _build_resource_opts(name, opts, tags, context_prefix(), CONTEXT.provider, no_tags)


def get_juno_resource() -> InvokeOptions:
    """
    Return a resource setup with the current provider
    """
    global CONTEXT

    # fail if the context isn't set
    if CONTEXT is None:
        raise ContextNotSet("No JunoRegion Context set")

    return InvokeOptions(provider=CONTEXT.provider)


def juno_account_resource(
    name: str, opts: Dict = None, tags: Dict = None, no_tags: bool = False
) -> Dict:
    """
    Return a resource setup with the current provider
    """
    global ACCOUNT

    # fail if the context isn't set
    if ACCOUNT is None:
        raise ContextNotSet("No JunoAccount Context set")

    return _build_resource_opts(
        name, opts, tags, ACCOUNT.account, ACCOUNT.account_provider, no_tags
    )
