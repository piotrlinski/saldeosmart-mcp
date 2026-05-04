---
title: Models
description: Pydantic models for every input and response that crosses the MCP boundary.
---

# Models

Auto-generated from `src/saldeosmart_mcp/models/`. These are the JSON-shaped
types the MCP boundary serializes to and from. Inputs validate before any
network call; responses are typed projections of Saldeo's XML envelopes.

For the validated string aliases (`IsoDate`, `Nip`, `Pesel`, `VatNumber`,
`Year`, `Month`) used throughout the inputs, see the
[common module](#saldeosmart_mcp.models.common) at the top of this page.

## Common

::: saldeosmart_mcp.models.common
    options:
      members_order: source
      show_root_full_path: false

## Companies

::: saldeosmart_mcp.models.companies
    options:
      members_order: source
      show_root_full_path: false

## Contractors

::: saldeosmart_mcp.models.contractors
    options:
      members_order: source
      show_root_full_path: false

## Documents

::: saldeosmart_mcp.models.documents
    options:
      members_order: source
      show_root_full_path: false

## Invoices

::: saldeosmart_mcp.models.invoices
    options:
      members_order: source
      show_root_full_path: false

## Bank

::: saldeosmart_mcp.models.bank
    options:
      members_order: source
      show_root_full_path: false

## Personnel

::: saldeosmart_mcp.models.personnel
    options:
      members_order: source
      show_root_full_path: false

## Catalog

::: saldeosmart_mcp.models.catalog
    options:
      members_order: source
      show_root_full_path: false

## Financial balance

::: saldeosmart_mcp.models.financial_balance
    options:
      members_order: source
      show_root_full_path: false

## Accounting close

::: saldeosmart_mcp.models.accounting_close
    options:
      members_order: source
      show_root_full_path: false
