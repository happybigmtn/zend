# Zend Product Spec

Status: Accepted

This spec supersedes the earlier public-feed idea, the chain-fork beta idea,
and the narrower gateway-only framing. Zend is a product, not a new chain. It
uses existing Zcash-family encrypted memo transport and turns a phone into a
private command center for a home miner.

## Purpose / User-Visible Outcome

A person or agent will be able to use Zend as one private surface for operating
a home miner and receiving private operational state. The phone does not mine.
Instead, it pairs with a home miner, shows miner status, controls safe operating
modes, receives pairing approvals and control receipts in an encrypted inbox,
and supports private message delivery using shielded memo transport.

The trust promise is twofold. First, the phone is only a control plane; hashing
never happens on-device. Second, full nodes, `lightwalletd` servers, and
ordinary chain observers never need the plaintext of Zend messages or receipts
in order to transport them.

## Whole-System Goal

The whole-system goal is to launch Zend as an agent-first product on top of the
existing Zcash network and supporting infrastructure. Zend should make mining
feel mobile-friendly without performing hashing on the phone. The phone should
feel like the remote for a household device, not the terminal for a homelab.

Zend is agent-first. Anything a human can do in the product must also be
possible through agent-facing tools or scripts: pair a home miner, read status,
change safe miner modes, receive operational receipts, summarize earnings and
alerts, send a message, receive a message, search a local inbox, and reply.

The long-term product must not split identity between mining and messaging.
Zend needs one shared principal, meaning one durable identity object that owns
gateway access and future inbox access together.

## Scope

This spec covers the durable boundary for the first Zend system:

- a mobile command center into a home miner
- encrypted memo transport as the supported message-body transport
- an inbox-first product model instead of a public timeline model
- a shared principal model spanning gateway control and future inbox access
- a private event spine that unifies receipts, alerts, summaries, and inbox
  messages
- equal human and agent capability at the inbox and miner-control layers
- honest mining language: mining happens off-device, not on the phone
- explicit capability scopes for miner access
- LAN-only gateway access in phase one
- a Zend-native gateway contract with a Hermes adapter
- an appliance-style onboarding and trust ceremony
- a calm, domestic command-center visual language governed by `DESIGN.md`
- no chain or mining-algorithm fork in the first phase

This spec does not lock in the final production visual design, remote access, or
the final miner backend. Those come after the command-center shape is proven.
Even so, the first slice must align with `DESIGN.md` so implementation does not
default to generic dashboard patterns.

## Current State

Today there are three useful ingredients, but they do not yet form a product.

First, Zodl/Zashi already proves that Zcash-family mobile clients can compose,
send, receive, and display encrypted memos over `lightwalletd`-backed light
client flows.

Second, a home-miner control plane does not exist yet. There is no pairing
model, no remote-control contract, no safety model for start or stop actions,
no miner status schema, and no first implementation slice that proves a phone
or agent can operate a miner running elsewhere.

Third, there is no canonical inbox model yet. There is no thread model, no
contact-policy model, no shared principal model, no private event spine, and no
agent tool contract that unifies encrypted messaging with home-miner
operations.

## Architecture / Runtime Contract

A "shielded transaction" in this spec means a Zcash-family transaction whose
private parts, including the memo field, are hidden from ordinary observers by
zero-knowledge cryptography. A "memo" means the encrypted message payload that
travels inside such a transaction. `lightwalletd` means the lightweight server
that streams compact chain data to wallets and forwards submitted transactions
to a full node. A "home miner" means a long-running process on hardware the user
controls that performs the actual mining work and exposes a secure control
surface for Zend.

The durable runtime contract has eight layers.

The first layer is the base chain. Zend rides on the existing Zcash network in
phase one. This spec does not create a new chain, token, consensus rule set, or
mining algorithm.

The second layer is encrypted transport. Every message body must travel as an
encrypted memo or as an encrypted pointer to a separately encrypted payload.
Plaintext must never be required by project-controlled server logs,
`lightwalletd` services, HTTP logs, metrics, or deployment dashboards.

The third layer is the event spine boundary. Zend uses one append-only,
encrypted event journal for operational receipts, alerts, pairing approvals,
Hermes summaries, and inbox messages. Separate feature-specific receipt stores
are out of scope. The event spine is the source of truth. The inbox is a
projection of that journal, not a second canonical store.

The fourth layer is the principal boundary. A `PrincipalId` is the stable
identity Zend assigns to a user or agent-controlled account. The same
`PrincipalId` must be referenced by gateway pairing records, event-spine items,
and future inbox metadata.

The fifth layer is the miner gateway boundary. The phone or agent talks to the
home miner through a secure pairing relationship. The mobile app may monitor,
start, stop, or safely configure mining, but it must not perform mining
directly on the device. If remote access beyond the local network is supported,
it must be explicit and user-controlled. Phase one is LAN-only by default.

Gateway authority is capability-scoped. Phase one supports only two gateway
capabilities: `observe`, which reads miner status, and `control`, which changes
safe operating modes such as paused, balanced, or performance.

The sixth layer is the Hermes adapter boundary. Zend owns the canonical gateway
contract. Hermes connects through a Zend adapter and receives only the
capabilities and event surfaces Zend explicitly grants. Phase one Hermes access
starts as observe-only plus summary append into the event spine. Direct miner
control through Hermes is deferred until a later capability model and approval
flow exist.

The seventh layer is the inbox boundary. Conversations, labels, read state,
muted senders, spam controls, and local search indexes are product metadata.
They may be synchronized later, but they are not part of consensus. If
synchronized, they must also remain encrypted.

The eighth layer is the agent boundary. Agent tools may use the same control and
messaging primitives as human clients, but they must not receive plaintext or
home-miner authority unless the owning client explicitly grants it.

## Durable Product Decisions

The following decisions are fixed by this spec.

Zend is not a public social network. Public ranking and public feeds are not
part of the product boundary.

Zend does not mine on the phone. The mobile app is a gateway into a home miner.
This is both a product decision and a platform-compatibility decision.

Zend does not fork Zcash consensus or the mining algorithm in phase one. Mining
optimization belongs in the home-miner software and its operational envelope,
not in a new chain.

Zend phase one is LAN-only. The gateway daemon must not expose internet-facing
control surfaces in the first product slice. The daemon must bind only to a
private local interface chosen by the operator, never an unrestricted public
interface.

Zend phase one explicitly separates `observe` and `control` permissions. A
paired client without `control` must not be able to change miner state.

Zend phase one defers payout-target mutation. Changing payout destinations is a
higher-blast-radius financial operation and requires a stronger capability model
and audit trail than milestone 1 needs.

Zend milestone 1 includes a first-class trust ceremony. Pairing must feel safe,
named, and revocable rather than like raw device administration.

Zend milestone 1 includes an encrypted operations inbox. Pairing approvals,
control receipts, Hermes summaries, and miner alerts must land in the same
private surface as user messages.

Zend owns the canonical gateway contract. Hermes integration is required in
phase one, but it enters through a Zend adapter rather than defining the core
protocol.

Zend milestone 1 follows `DESIGN.md`. The product should feel like a household
control surface, not a crypto exchange and not a generic SaaS admin.

## Adoption Path

The adoption path is staged.

Stage one is the first real Zend product slice. Run a home-miner control
service, pair a thin mobile-shaped client over the local network, establish a
shared `PrincipalId`, name the device, show live miner status, surface pairing
and control receipts in the encrypted operations inbox, connect Hermes through
the Zend adapter, and prove that the gateway can safely change miner modes
without on-device hashing.

Stage two is richer inbox proof. Add a local conversation model, contact
policies, and agent parity scripts or tools while reusing existing Zcash-family
encrypted memo transport and the same `PrincipalId` contract.

Stage three is operator proof. Package the home-miner service for easy
household deployment, document cost expectations, and make pairing, recovery,
and device replacement boring.

## Acceptance Criteria

This spec is satisfied only when all of the following are true:

- a new contributor can read this repository and understand that Zend is a
  private command center, not a public feed and not a new chain
- the first implementation slice proves the mobile or script gateway into a home
  miner without on-device mining
- the first implementation slice includes a thin mobile-shaped command-center
  experience rather than scripts alone
- the first implementation slice defines a shared `PrincipalId` contract for the
  future inbox and the gateway pairing system
- the first implementation slice includes an encrypted operations inbox backed
  by the private event spine
- Hermes Gateway can connect through the Zend-native gateway adapter using only
  explicitly granted authority
- the first implementation slice is explicitly LAN-only
- gateway authority is limited to `observe` and `control` scopes in phase one
- encrypted message transport never requires plaintext on any server-controlled
  surface
- the first human-visible or agent-visible client surface exposes only honest
  mining and fee behavior

## Failure Handling

If direct pairing to a real miner backend slows initial progress, the project
may first prove the command-center shape with a miner simulator, but it must
preserve the same control API, event spine, and off-device-mining boundary.

If configurable network fees are not practical in the first implementation
slice, the product may expose only a single observed network fee and defer
delivery-tier choice to a later phase.

If remote access beyond the home network introduces too much complexity or
security risk, the first product slice may stay LAN-only and defer secure remote
tunneling to a later phase.

If shared identity across inbox and gateway introduces too much uncertainty in
implementation, the product may still defer richer inbox behavior, but it must
not defer the shared `PrincipalId` contract itself.

## Non-Goals

The first Zend product does not attempt to be:

- a new blockchain
- a mining-algorithm fork
- an on-device miner
- internet-exposed miner control in phase one
- payout-target mutation in phase one
- a second notification or receipt store outside the private event spine
- a real-time chat system with instant delivery guarantees
- a media-heavy messenger with large attachments
- a public social feed
- a finished multi-device sync product
