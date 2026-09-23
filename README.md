# METRIXA-Legal-Metrology-Compliance
Evidence-aware AI-assisted compliance verification system for packaged commodities under Legal Metrology (Packaged Commodities) Rules, 2011.
# METRIXA — Legal Metrology Compliance

### Evidence-Aware Compliance Verification for Packaged Commodities

METRIXA is an AI-assisted software system designed to support compliance verification of packaged commodities under the Legal Metrology (Packaged Commodities) Rules, 2011.

## Problem

Manual inspection of packaged commodities requires checking multiple mandatory declarations and applicable requirements across product labels.

## Proposed Solution

METRIXA processes package images, extracts relevant declarations, validates them against applicable compliance rules, and links identified issues to supporting package evidence.

## Workflow

**Package Image → Image Preprocessing → Region Detection → OCR → Rule Validation → Evidence-Linked Result → Compliance History → Report**

## Key Capabilities

* Package image analysis
* Region-based text extraction
* Structured declaration extraction
* Rule-based compliance validation
* Evidence-linked compliance results
* Inspection history
* Compliance state tracking
* Change / drift monitoring
* Digital inspection reports

## Technology Stack

* React.js — User Interface
* FastAPI — Backend Services
* OpenCV — Image Processing
* YOLOv8 — Region Detection
* PaddleOCR — Text Extraction
* Python Rule Engine — Compliance Validation
* PostgreSQL — Data & History

## Prototype Status

This repository contains the current METRIXA prototype, sample package images, extracted outputs, technical architecture and demonstration materials.

## Important Note

METRIXA is an inspection-assistance system. Automated results are intended to support inspector verification and should not replace official legal or regulatory judgment.

## Current Limitations

The prototype is being validated using a controlled sample set. Detection and OCR performance may vary with image quality, package geometry, glare, blur and complex label layouts.
