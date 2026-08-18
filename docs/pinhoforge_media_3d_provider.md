# AIpinho PinhoForge Media 3D Provider

## Purpose

AIpinho governs Image Lab and 3D Lab bridge requests, validates outputs, registers artifacts, and preserves speaker truth.

## Tool Gateway surface

- pinhoforge_media_image_operation
- pinhoforge_media_3d_operation

## Governance model

- provider validates source scope
- provider blocks original overwrite
- provider requires validated output file for artifact-ready status
- provider registers exported outputs as governed artifacts
- provider emits markdown/json reports
- provider marks model review as recommended or required when semantic tasks are detected

## Current limitations

- Output execution is validated from provider-produced files
- 3D export support is currently OBJ only
- Semantic review can be required or recommended, but no specialized visual model is invoked inside this bridge layer yet
