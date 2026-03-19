# zmemo Encrypted Messaging Public Beta

Status: Accepted

This spec supersedes the earlier idea of building a public social feed around
memo-bearing transactions. `zmemo` is an inbox-first encrypted messaging
product. Public feed mechanics are out of scope for the beta network.

## Purpose / User-Visible Outcome

A person or agent will be able to send an asynchronous message over a public
beta network where the message body is always encrypted. The sender may attach
a small payment, but the transport is still messaging-first: the recipient gets
an inbox entry, not a public post.

The important privacy promise is that full nodes, `lightwalletd` servers, and
ordinary chain observers do not need the plaintext message body in order to
relay or store the transaction. Only authorized client software or agents that
hold the recipient's decryption capability can read the message.

## Whole-System Goal

The whole-system goal is to launch a public beta network, currently named
`rZEC`, that is cheap enough to operate from genesis and strict enough about
privacy that `zmemo` can honestly say every message body is encrypted at rest
and in transit through project-controlled infrastructure.

`zmemo` is agent-first. Anything a human can do in the product must also be
possible through agent-facing tools or scripts: create an identity, add a
contact, estimate send cost, send a message, receive a message, search a local
inbox, summarize a thread, archive a conversation, and reply.

## Scope

This spec covers the durable boundary for the beta system:

- a self-hosted Zcash-family beta network built from genesis
- encrypted memo transport as the only supported message body transport
- an inbox-first product model instead of a public timeline model
- equal human and agent capability at the transport and inbox layers
- honest fee handling, even if configurable priority lanes are not available in
  the first beta

This spec does not lock in the final mobile UI, brand system, or production
multi-region hosting shape. Those will follow once transport is proven.

## Current State

Today there are three useful ingredients, but they do not yet form a product.

First, Zodl/Zashi already proves that Zcash-family mobile clients can compose,
send, receive, and display encrypted memos over `lightwalletd`-backed light
client flows.

Second, the sibling `rZEC` work has already explored an upstream-pinned Zebra
fork with a new chain identity, but it is not yet the canonical home of the
messaging product and still describes itself as a chain project rather than a
message product.

Third, there is no canonical inbox model yet. There is no thread model, no
contact-policy model, no agent tool contract, no self-hosted deployment kit for
the messaging product, and no documented proof that a genesis-fork public beta
can send an encrypted message end-to-end through project-run infrastructure.

## Architecture / Runtime Contract

A "shielded transaction" in this spec means a Zcash-family transaction whose
private parts, including the memo field, are hidden from ordinary observers by
zero-knowledge cryptography. A "memo" means the encrypted message payload that
travels inside such a transaction. `lightwalletd` means the lightweight server
that streams compact chain data to wallets and forwards submitted transactions
to a full node. A "full node" means the server process that validates blocks
and participates in the peer-to-peer network.

The durable runtime contract has four layers.

The first layer is the beta chain. `rZEC` provides block production, consensus,
and fee payment. The chain is public in the sense that anyone may connect, but
its early-life security budget must be treated as experimental. The beta chain
is not to be advertised as a place to store real value.

The second layer is the transport boundary. Every message body must travel as an
encrypted memo or as an encrypted pointer to a separately encrypted payload.
Plaintext message bodies must never be required by `zebrad`, `lightwalletd`,
RPC logs, HTTP logs, metrics, or deployment dashboards.

The third layer is the client inbox boundary. Conversations, labels, read
state, muted senders, spam controls, and local search indexes are product-level
metadata. They may be synchronized later, but they are not part of consensus.
If synchronized, they must also remain encrypted.

The fourth layer is the agent boundary. Agent tools may use the same transport
primitives as human clients, but they must not receive plaintext unless the
client that owns the message explicitly grants access. The first concrete
consumer of this rule will be a CLI or MCP-facing transport tool that can send
and read test messages during the beta transport proof.

## Durable Product Decisions

The following decisions are fixed by this spec.

`zmemo` is not a public social network in the beta. Public ranking and public
feeds are not part of the product boundary.

The project will prefer self-hosted `lightwalletd` and node infrastructure over
shared public endpoints as soon as transport works, because relying on shared
community servers weakens both operator control and privacy posture.

Message priority is split into two concepts. Delivery priority means on-chain
confirmation urgency. Attention priority means how much recipient software or a
recipient agent should prioritize the message. The beta may launch with only
one real delivery fee lane if the underlying wallet stack exposes only a single
honest fee. The product must not fake multiple network-priority choices until
the chain and client stack genuinely support them.

## Adoption Path

The adoption path is staged.

Stage one is transport proof. Run a self-hosted beta stack from this repo,
create two test identities, send one encrypted memo message, read it from the
recipient side, and verify the server side cannot surface the plaintext.

Stage two is inbox proof. Add a local conversation model, contact policies,
agent parity scripts or tools, and a clean boundary between chain transport and
product metadata.

Stage three is client proof. Fork or adapt the existing mobile clients so they
can target the beta network, expose the inbox model, and preserve the same
encrypted transport assumptions.

Stage four is operator proof. Package the beta stack for cheap public operation,
document expected monthly costs, and explicitly label the network as
experimental until its security model improves.

## Acceptance Criteria

This spec is satisfied only when all of the following are true:

- a new contributor can read this repository and understand that `zmemo` is an
  encrypted messaging product, not a public feed product
- the first implementation slice proves end-to-end encrypted message transport
  on self-hosted beta infrastructure
- the beta stack never requires message plaintext on any server-controlled
  surface
- the first human-visible or agent-visible client surface exposes only honest
  fee behavior
- every new plan in this repo follows the inbox-first, encrypted-message-first
  boundary established here

## Failure Handling

If custom-genesis public beta work stalls, the project may temporarily prove the
transport on a local dev network, but it must keep the same encrypted-message
boundary and must not reintroduce plaintext relays.

If configurable network fees are not practical in the first implementation
slice, the product may expose only a single observed network fee and defer
delivery-tier choice to a later phase.

If the public beta network remains too weak to safely carry meaningful value,
the product must constrain attached payments to nominal amounts and label the
network clearly as experimental.

## Non-Goals

The beta does not attempt to be:

- a real-time chat system with instant delivery guarantees
- a media-heavy messenger with large attachments
- a public social feed
- a high-value financial network
- a finished multi-device sync product
