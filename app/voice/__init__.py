"""Voice edge for CallOps: the Twilio gateway and the warm transfer.

Written by the factory WRITER role (codewhale exec)

Both modules dial through one place (``twilio_client.originate_call``), which
is either the stubbed fake-Twilio transport (no credentials configured --
the state this product ships in) or a real Twilio REST originate. No other
module in the platform opens a socket to a telephony provider.
"""

from __future__ import annotations

__all__ = ["twilio_client", "warm_transfer"]
