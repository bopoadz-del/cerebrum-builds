"""Cerebrum product kernel for the Bakery Chain Operations & Delivery Platform.

Written by the factory WRITER role (codewhale exec)

The kernel is the contract layer between the HTTP surface and the domain: it
owns the record envelope, the capability registry, the schema validation the
routes use, and the lifecycle audit. Blocks are dispatched by ``app.dispatch``;
the kernel never calls one.
"""

from __future__ import annotations

KERNEL_VERSION = "bakery-kernel/1.0.0"

__all__ = ("KERNEL_VERSION",)
