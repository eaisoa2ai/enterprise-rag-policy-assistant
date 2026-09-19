"""Tracing setup — identical pattern to outreach-iq's observability.py.
Real OpenTelemetry spans, console exporter by default (zero infra), one env
var to switch to a real collector.
"""
from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

_initialized = False


def _init_tracing() -> None:
    global _initialized
    if _initialized:
        return

    provider = TracerProvider(resource=Resource.create({"service.name": "policyiq"}))

    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    else:
        exporter = ConsoleSpanExporter()

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _initialized = True


def get_tracer() -> trace.Tracer:
    _init_tracing()
    return trace.get_tracer("policyiq")
