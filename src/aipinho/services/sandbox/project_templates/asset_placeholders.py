from __future__ import annotations


def vector_placeholder_xml(*, label: str, color: str, shape: str = "circle") -> str:
    body = (
        '<path android:fillColor="{color}" android:pathData="M54,6a48,48 0,1 0,0.1,0z"/>'
        if shape == "circle"
        else '<path android:fillColor="{color}" android:pathData="M14,18h80v84h-80z"/>'
    )
    return f"""<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    {body.format(color=color)}
    <path android:fillColor="#111827" android:pathData="M26,50h56v10h-56z"/>
    <path android:fillColor="#e5e7eb" android:pathData="M35,67h38v8h-38z"/>
</vector>
<!-- Placeholder asset: {label}. Replace with production art when available. -->
"""
