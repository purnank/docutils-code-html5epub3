# Author: Edward Loper
# Contact: edloper@gradient.cis.upenn.edu
# Revision: $Revision$
# Date: $Date$
# Copyright: This module has been placed in the public domain.

"""
This module defines standard interpreted text role functions, a registry for
interpreted text roles, and an API for adding to and retrieving from the
registry.

The interface for interpreted role functions is as follows::

    def role_fn(name, rawtext, text, lineno, inliner, attributes={}):
        code...

Parameters:

- ``name`` is the local name of the interpreted text role, the role name
  actually used in the document.

- ``rawtext`` is a string containing the entire interpreted text construct.
  Include it as a literal block in a system message if there is a problem.

- ``text`` is the interpreted text content.

- ``lineno`` is the line number where the interpreted text beings.

- ``inliner`` is the Inliner object that called the role function.
  It defines the following useful attributes: ``reporter``,
  ``problematic``, ``memo``, ``parent``, ``document``.

- ``attributes``: A dictionary of additional attributes for the generated
  elements, used for customization.

Interpreted role functions return a tuple of two values:

- A list of nodes which will be inserted into the document tree at the
  point where the interpreted role was encountered (can be an empty
  list).

- A list of system messages, which will be inserted into the document tree
  immediately after the end of the current inline block (can also be empty).
"""

__docformat__ = 'reStructuredText'

from docutils import nodes
from docutils.parsers.rst.languages import en as _fallback_language_module

DEFAULT_INTERPRETED_ROLE = 'title-reference'
"""
The canonical name of the default interpreted role.  This role is used
when no role is specified for a piece of interpreted text.
"""

_role_registry = {}
"""Mapping of canonical role names to role functions.  Language-dependent role
names are defined in the ``language`` subpackage."""

_roles = {}
"""Mapping of local or language-dependent interpreted text role names to role
functions."""

def role(role_name, language_module, lineno, inliner):
    """
    Locate and return a role function from its language-dependent name, along
    with a list of system messages.  If the role is not found in the current
    language, check English.  Return None if the named role cannot be found.
    """
    normname = role_name.lower()
    messages = []
    msg_text = []

    if _roles.has_key(normname):
        return _roles[normname], messages

    if role_name:
        canonicalname = None
        try:
            canonicalname = language_module.roles[normname]
        except AttributeError, error:
            msg_text.append('Problem retrieving role entry from language '
                            'module %r: %s.' % (language_module, error))
        except KeyError:
            msg_text.append('No role entry for "%s" in module "%s".'
                            % (role_name, language_module.__name__))
    else:
        canonicalname = DEFAULT_INTERPRETED_ROLE

    # If we didn't find it, try English as a fallback.
    if not canonicalname:
        try:
            canonicalname = _fallback_language_module.roles[normname]
            msg_text.append('Using English fallback for role "%s".'
                            % role_name)
        except KeyError:
            msg_text.append('Trying "%s" as canonical role name.'
                            % role_name)
            # The canonical name should be an English name, but just in case:
            canonicalname = normname

    # Collect any messages that we generated.
    if msg_text:
        message = inliner.reporter.info('\n'.join(msg_text), line=lineno)
        messages.append(message)

    # Look the role up in the registry, and return it.
    if _role_registry.has_key(canonicalname):
        role_fn = _role_registry[canonicalname]
        register_local_role(normname, role_fn)
        return role_fn, messages
    else:
        return None, messages # Error message will be generated by caller.

def register_canonical_role(name, role_fn):
    """
    Register an interpreted text role by its canonical name.

    :Parameters:
      - `name`: The canonical name of the interpreted role.
      - `role_fn`: The role function.  See the module docstring.
    """
    _role_registry[name] = role_fn

def register_local_role(name, role_fn):
    """
    Register an interpreted text role by its local or language-dependent name.

    :Parameters:
      - `name`: The local or language-dependent name of the interpreted role.
      - `role_fn`: The role function.  See the module docstring.
    """
    _roles[name] = role_fn

def register_generic_role(canonical_name, node_class):
    """For roles which simply wrap a given `node_class` around the text."""
    # Dynamically define a role function:
    def role_fn(role, rawtext, text, lineno, inliner, nc=node_class):
        return generic_role_helper(nc, role, rawtext, text, lineno, inliner)
    # Register the role:
    register_canonical_role(canonical_name, role_fn)

def generic_role_helper(node_class, role, rawtext, text, lineno, inliner,
                        attributes={}):
    # If we wanted to, we could recursively call inliner.nested_parse
    # to interpret the text contents here (after appropriately
    # refactoring Inliner.parse).
    return [node_class(rawtext, text, **attributes)], []

def register_custom_role(local_name, attributes):
    """For roles defined in a document."""
    def role_fn(role, rawtext, text, lineno, inliner, atts=attributes):
        return generic_role_helper(
            nodes.inline, role, rawtext, text, lineno, inliner, attributes=atts)
    register_local_role(local_name, role_fn)

######################################################################
# Define and register the standard roles:
######################################################################

register_generic_role('abbreviation', nodes.abbreviation)
register_generic_role('acronym', nodes.acronym)
register_generic_role('emphasis', nodes.emphasis)
register_generic_role('literal', nodes.literal)
register_generic_role('strong', nodes.strong)
register_generic_role('subscript', nodes.subscript)
register_generic_role('superscript', nodes.superscript)
register_generic_role('title-reference', nodes.title_reference)

def pep_reference_role(role, rawtext, text, lineno, inliner):
    try:
        pepnum = int(text)
        if pepnum < 0 or pepnum > 9999:
            raise ValueError
    except ValueError:
        msg = inliner.reporter.error(
            'PEP number must be a number from 0 to 9999; "%s" is invalid.'
            % text, line=lineno)
        prb = inliner.problematic(text, text, msg)
        return [prb], [msg]
    ref = inliner.pep_url % pepnum # [XX]
    return [nodes.reference(rawtext, 'PEP ' + text, refuri=ref)], []
register_canonical_role('pep-reference', pep_reference_role)

def rfc_reference_role(role, rawtext, text, lineno, inliner):
    try:
        rfcnum = int(text)
        if rfcnum <= 0:
            raise ValueError
    except ValueError:
        msg = inliner.reporter.error(
            'RFC number must be a number greater than or equal to 1; '
            '"%s" is invalid.' % text, line=lineno)
        prb = inliner.problematic(text, text, msg)
        return [prb], [msg]
    ref = inliner.rfc_url % rfcnum # [XX]
    return [nodes.reference(rawtext, 'RFC ' + text, refuri=ref)], []
register_canonical_role('rfc-reference', rfc_reference_role)

######################################################################
# Register roles that are currently unimplemented.
######################################################################

def unimplemented_role(role, rawtext, text, lineno, inliner):
    msg = inliner.reporter.error(
        'Interpreted text role "%s" not implemented.' % role, line=lineno)
    prb = inliner.problematic(rawtext, rawtext, msg)
    return [prb], [msg]

register_canonical_role('index', unimplemented_role)
register_canonical_role('named-reference', unimplemented_role)
register_canonical_role('anonymous-reference', unimplemented_role)
register_canonical_role('uri-reference', unimplemented_role)
register_canonical_role('footnote-reference', unimplemented_role)
register_canonical_role('citation-reference', unimplemented_role)
register_canonical_role('substitution-reference', unimplemented_role)
register_canonical_role('target', unimplemented_role)
# This one should remain unimplemented, for testing purposes:
register_canonical_role('restructuredtext-unimplemented-role', unimplemented_role)
