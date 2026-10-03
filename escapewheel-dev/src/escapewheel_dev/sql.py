"""Shipped rules' SQL, parsed, and the Tier 1 and Tier 2 checks a registry yields."""

from collections import Counter
from collections.abc import Iterable

import sqlglot
from escapewheel_validator import CheckedRegistryContext, check_registry_context
from escapewheel_validator.generate import Check, generate
from escapewheel_validator.rule_language import CheckedRule, check_rule
from sqlglot import exp

from .registry import Rule, registry


def parse(rule: Rule) -> exp.Expr:
    """Return the syntax tree of a rule's query, parsed as the validator parses it."""
    return sqlglot.parse_one(rule.sql)


def node_counts(rules: Iterable[Rule], *nodes: type[exp.Expr]) -> Counter[type[exp.Expr]]:
    """Count occurrences of each node type, such as ``exp.Between`` or ``exp.In``, across `rules`."""
    counts: Counter[type[exp.Expr]] = Counter()
    for rule in rules:
        tree = parse(rule)
        for node in nodes:
            counts[node] += sum(1 for _ in tree.find_all(node))
    return counts


def checked(rule: Rule) -> CheckedRule:
    """Statically check a rule as the validator does, returning the resources and columns it reads."""
    owner = registry(rule.registry)
    core = None if not owner.is_extension else registry("core").document
    return check_rule(rule.sql, owner.document, core_resources=core)


def rules_reading(resource_id: str, column: str, candidates: Iterable[Rule]) -> list[Rule]:
    """Return those of `candidates` whose query reads `column` of `resource_id`."""
    return [rule for rule in candidates if (resource_id, column) in checked(rule).inputs]


def context(registry_id: str = "core") -> CheckedRegistryContext:
    """Return the validator's checked context for one registry, an extension's bound to core's."""
    core = check_registry_context(registry("core").document)
    if registry_id == "core":
        return core
    return check_registry_context(registry(registry_id).document, core)


def checks(registry_id: str = "core", *, advisory: bool = False) -> list[Check]:
    """Return the checks the validator generates from one registry: Tier 1 derived, Tier 2 shipped."""
    return generate(context(registry_id), advisory=advisory)


__all__ = ["checked", "checks", "context", "node_counts", "parse", "rules_reading"]
