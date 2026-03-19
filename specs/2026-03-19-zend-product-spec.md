# Zend Product Spec

Status: Accepted

This spec supersedes two earlier directions: the public-feed idea and the
docs-only chain-fork beta plan. Zend is a product, not a new chain. Its two
durable pillars are encrypted messaging over existing Zcash-family memo
transport and a mobile app that acts as a secure gateway into a home miner.

## Purpose / User-Visible Outcome

A person or agent will be able to use Zend as a private inbox and as a remote
control surface for mining from home. The mobile app will not mine on-device.
Instead, it will pair with a home miner, show mining status, control safe miner
actions, and still support encrypted message delivery using shielded memo
transport.

The important privacy promise is that full nodes, `lightwalletd` servers, and
ordinary chain observers do not need the plaintext message body in order to
relay or store the transaction. Only authorized client software or agents that
hold the recipient's decryption capability can read the message.

## Whole-System Goal

The whole-system goal is to launch Zend as an agent-first product on top of the
existing Zcash network and supporting infrastructure. Zend should make mining
feel mobile-friendly without performing hashing on the phone. The phone should
behave like a control panel for a home miner that is configured, monitored, and
operated through a secure pairing flow.

Zend is agent-first. Anything a human can do in the product must also be
possible through agent-facing tools or scripts: pair a home miner, read miner
status, start or stop mining, apply safe configuration changes, estimate mining
economics, send a message, receive a message, search a local inbox, summarize a
thread, archive a conversation, and reply.

## Scope

This spec covers the durable boundary for the first Zend system:

- a mobile gateway into a home miner
- encrypted memo transport as the supported message body transport
- an inbox-first product model instead of a public timeline model
- equal human and agent capability at the inbox and miner-control layers
- honest mining language: mining happens off-device, not on the phone
- no chain or mining-algorithm fork in the first phase

This spec does not lock in the final visual design, the full mobile UI, or the
ultimate miner backend. Those will follow once the control-plane shape is
proven.

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
contact-policy model, and no agent tool contract that unifies encrypted
messaging with home-miner operations.

## Architecture / Runtime Contract

A "shielded transaction" in this spec means a Zcash-family transaction whose
private parts, including the memo field, are hidden from ordinary observers by
zero-knowledge cryptography. A "memo" means the encrypted message payload that
travels inside such a transaction. `lightwalletd` means the lightweight server
that streams compact chain data to wallets and forwards submitted transactions
to a full node. A "home miner" means a long-running process on hardware the user
controls that performs the actual mining work and exposes a secure local or
user-mediated control surface for Zend.

The durable runtime contract has four layers.

The first layer is the base chain. Zend rides on the existing Zcash network in
phase one. This spec does not create a new chain, token, consensus rule set, or
mining algorithm.

The second layer is encrypted transport. Every message body must travel as an
encrypted memo or as an encrypted pointer to a separately encrypted payload.
Plaintext message bodies must never be required by project-controlled server
logs, `lightwalletd` services, HTTP logs, metrics, or deployment dashboards.

The third layer is the miner gateway boundary. The phone or agent talks to the
home miner through a secure pairing relationship. The mobile app may monitor,
start, stop, or safely configure mining, but it must not perform mining
directly on the device. If remote access beyond the local network is supported,
it must be explicit and user-controlled.

The fourth layer is the inbox boundary. Conversations, labels, read state,
muted senders, spam controls, and local search indexes are product metadata.
They may be synchronized later, but they are not part of consensus. If
synchronized, they must also remain encrypted.

The fifth layer is the agent boundary. Agent tools may use the same control and
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

Message priority is still split into two concepts. Delivery priority means
on-chain confirmation urgency. Attention priority means how much recipient
software or a recipient agent should prioritize the message. The product must
not fake multiple network-priority choices until the wallet stack genuinely
supports them.

Mining priority is also split into two concepts. Mining intensity means how
hard the home miner works. User attention means how the mobile app surfaces that
state. The app should present simple modes such as paused, balanced, and
performance, but the actual miner backend may translate those into device-
specific settings.

## Adoption Path

The adoption path is staged.

Stage one is gateway proof. Run a home-miner control service from this repo,
pair a CLI or mobile-gateway client to it, show live miner status, and prove
that the gateway can safely start and stop mining without on-device hashing.

Stage two is inbox proof. Add a local conversation model, contact policies, and
agent parity scripts or tools while reusing existing Zcash-family encrypted memo
transport.

Stage three is client proof. Fork or adapt the existing mobile clients so they
surface both encrypted inbox flows and home-miner control flows in one product.

Stage four is operator proof. Package the home-miner service for easy household
deployment, document cost expectations, and make pairing and recovery boring.

## Acceptance Criteria

This spec is satisfied only when all of the following are true:

- a new contributor can read this repository and understand that Zend is a
  messaging-plus-mining-gateway product, not a public feed and not a new chain
- the first implementation slice proves the mobile or script gateway into a home
  miner without on-device mining
- encrypted message transport never requires plaintext on any server-controlled
  surface
- the first human-visible or agent-visible client surface exposes only honest
  mining and fee behavior
- every new plan in this repo follows the inbox-first, encrypted-message-first
  boundary established here

## Failure Handling

If direct pairing to a real miner backend slows initial progress, the project
may first prove the gateway shape with a miner simulator, but it must preserve
the same control API and off-device-mining boundary.

If configurable network fees are not practical in the first implementation
slice, the product may expose only a single observed network fee and defer
delivery-tier choice to a later phase.

If remote access beyond the home network introduces too much complexity or
security risk, the first product slice may stay LAN-only and defer secure remote
tunneling to a later phase.

## Non-Goals

The first Zend product does not attempt to be:

- a new blockchain
- a mining-algorithm fork
- an on-device miner
- a real-time chat system with instant delivery guarantees
- a media-heavy messenger with large attachments
- a public social feed
- a finished multi-device sync product
