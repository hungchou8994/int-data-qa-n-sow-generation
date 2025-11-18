# SOW Agent System - Complete Documentation

## 🎯 Overview

This is an **AI-Agent-based SOW Generation System** that automatically creates comprehensive project documentation with **built-in quality control** and **intelligent cascade regeneration**.

### Key Features
- ✅ **Automated Quality Control**: LLM-as-a-Judge validates each component
- ✅ **RAG-Enhanced**: Retrieves similar tasks from past projects (BigQuery Vector Search)
- ✅ **Cascade Regeneration**: Smart dependency-aware regeneration on feedback
- ✅ **Multi-Stage Workflow**: Input → Auto-Generation → Human Review → Approval
- ✅ **Version Tracking**: Full audit trail of all generations and feedback

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PHASE 1: AUTO-CORRECTION                  │
│                                                               │
│  Generate PD → Judge PD → [PASS? Yes → Next]                │
│                         └─ [FAIL? → Regen max 3x]           │
│                                                               │
│  Generate PA → Judge PA → [PASS? Yes → Next]                │
│    (uses PD)          └─ [FAIL? → Regen max 3x]             │
│                                                               │
│  Generate SoW → Judge SoW → [PASS? Yes → Phase 2]           │
│    (uses PD+PA+RAG)     └─ [FAIL? → Regen max 3x]          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    PHASE 2: HUMAN REVIEW                     │
│                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐│
│  │ Project Detail  │  │ Project Assume. │  │ Scope of Work││
│  │                 │  │                 │  │              ││
│  │ [Feedback Box]  │  │ [Feedback Box]  │  │[Feedback Box]││
│  │ [Regenerate]    │  │ [Regenerate]    │  │[Regenerate]  ││
│  └─────────────────┘  └─────────────────┘  └──────────────┘│
│                                                               │
│              [✅ APPROVE ALL COMPONENTS]                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   PHASE 3: CASCADE REGEN                     │
│                                                               │
│  IF target = "Project Detail":                               │
│    → Regen PD → Judge → Regen PA → Judge → Regen SoW → Judge│
│                                                               │
│  IF target = "Project Assumption":                           │
│    → Keep PD → Regen PA → Judge → Regen SoW → Judge         │
│                                                               │
│  IF target = "Scope of Work":                                │
│    → Keep PD, PA → Regen SoW → Judge                         │
│                                                               │
│  → Return to PHASE 2 for review                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                     PHASE 4: APPROVED                        │
│                                                               │
│  - Lock all components                                        │
│  - Export as JSON                                             │
│  - Save to database/Google Sheets                            │
└─────────────────────────────────────────────────────────────┘

