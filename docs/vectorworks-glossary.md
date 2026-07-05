# Vectorworks glossary

Short reference for the Vectorworks terms this project touches, based on the official
Vectorworks 2026 documentation. Keep entries short — this is orientation, not
documentation; follow the source links for detail.

| Term | What it is |
|------|------------|
| **Design layer** | A layer where the design is actually drawn and modelled (plan, model, etc.); can be associated with stories. Objects are created on design layers. ([source](https://app-help.vectorworks.net/2026/eng/VW2026_Guide/Structure/Layer_class_and_viewport_standards.htm)) |
| **Sheet layer** | A presentation/output layer for finished documentation — holds viewports, title blocks, notes and annotations, laid out at page scale for print/PDF. "Sheets" in the RT use case = sheet layers. ([source](https://app-help.vectorworks.net/2026/eng/VW2026_Guide/Viewports1/Creating_sheet_layer_viewports.htm)) |
| **Class** | A named organisational category assigned to objects, controlling their attributes (fill, pen, etc.) and visibility. Independent of layers: a **layer** organises *where* an object lives, a **class** organises *what kind* of thing it is. Standardising the class list across files is the core of RT template extraction (use case #1). ([source](https://app-help.vectorworks.net/2026/eng/VW2026_Guide/Structure/Layer_class_and_viewport_standards.htm)) |
| **Viewport** | A framed view of design-layer model data placed on a sheet layer (or design layer), with its own scale, cropping, and per-viewport visibility/greying of layers and classes. ([source](https://app-help.vectorworks.net/2026/eng/VW2026_Guide/Viewports1/Concept_Types_of_viewports.htm)) |
| **Template file** (`.sta`) | A pre-configured starter document giving new projects a standard structure: layers, classes, sheet layers, phases, saved views, paper sizes, and resources (line types, hatches, title blocks, worksheets, scripts). Building one from existing RT files is use case #1. ([source](https://app-help.vectorworks.net/2026/eng/VW2026_Guide/Setup/Concept_Templates.htm)) |
| **Symbol** | A reusable named object definition stored as a resource; placing a symbol definition into a drawing creates a symbol instance. ([source](https://app-help.vectorworks.net/2026/eng/VW2026_Guide/Symbols/Concept_Vectorworks_symbols.htm)) |
| **Resource / Resource Manager** | Reusable document assets (symbols, classes, hatches, line types, title blocks, worksheets, record formats) managed in the Resource Manager. ([source](https://app-help.vectorworks.net/2026/eng/VW2026_Guide/ResourceManager/Resource%20Manager.htm)) |
| **Record format** | A named schema of data fields that can be attached to objects — Vectorworks' structured object metadata. Relevant to auditing/handover checks (use case #2). |

## Scripting API (`vs.*`)

The in-Vectorworks Python script drives the document through the **`vs.*`** namespace,
which mirrors the VectorScript function reference one-to-one — a VectorScript function
`ForEachObject` is called from Python as `vs.ForEachObject(...)`. Key patterns for this
project:

- **`vs.ForEachObject(callback, criteria)`** — iterate objects matching a criteria
  string, calling `callback(handle)` per object. The primary way to walk a document to
  extract classes/objects or run audit checks.
- **`vs.GetClass(handle)`** — get an object's class name from its handle.
- Class/layer enumeration and resource traversal functions are the workhorses for both
  use cases.

Reference: [VectorScript / Python Function Reference](https://developer.vectorworks.net/index.php/VS:Function_Reference)
(the `vs.*` names match these `VS:` entries). Verify exact signatures against the 2026
reference before relying on them.
