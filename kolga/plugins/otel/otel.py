import os
from importlib import import_module
from typing import TYPE_CHECKING, Any, List, Mapping, Optional, Sequence, Set, Union

from environs import Env

from kolga.hooks import hookimpl
from kolga.settings import settings
from kolga.utils.logger import logger

from ..base import PluginBase
from ..exceptions import PluginMissingConfiguration

try:
    from opentelemetry import context, trace  # type: ignore[attr-defined]
    from opentelemetry.sdk.resources import Resource  # type: ignore[attr-defined]
    from opentelemetry.sdk.trace import TracerProvider  # type: ignore[attr-defined]
    from opentelemetry.sdk.trace.export import (  # type: ignore[attr-defined]
        BatchSpanProcessor,
    )
    from opentelemetry.trace import status  # type: ignore[import]
except ImportError:
    HAS_OPENTELEMETRY = False
else:
    HAS_OPENTELEMETRY = True

if TYPE_CHECKING:
    from kolga.libs.project import Project
    from kolga.libs.service import Service
    from kolga.utils.models import DockerImage


EXPORTERS = {
    "console": "opentelemetry.sdk.trace.export.ConsoleSpanExporter",
    "jaeger": "opentelemetry.exporter.jaeger.proto.grpc.JaegerExporter",
    "otlp": "opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter",
    "zipkin": "opentelemetry.exporter.zipkin.proto.http.ZipkinExporter",
}


T_Attr = Mapping[
    str,
    Union[
        str,
        bool,
        int,
        float,
        Sequence[str],
        Sequence[bool],
        Sequence[int],
        Sequence[float],
    ],
]


class KolgaOpenTelemetryPlugin(PluginBase):
    name = "opentelemetry"
    verbose_name = "OpenTelemetry plugin for Kolga"
    version = 0.1

    OPENTELEMETRY_ENABLED: bool = False
    OTEL_TRACES_EXPORTER: str = "otlp"

    def __init__(self, env: Env) -> None:
        self.optional_variables = [
            ("OPENTELEMETRY_ENABLED", env.bool),
            ("OTEL_TRACES_EXPORTER", env.str),
        ]
        self.configure(env)

        if not self.OPENTELEMETRY_ENABLED or self.OTEL_TRACES_EXPORTER == "none":
            raise PluginMissingConfiguration("Opentelemetry not enabled")
        if not HAS_OPENTELEMETRY:
            raise PluginMissingConfiguration("Extra packages for opentelemetry missing")

        pipeline_resource = Resource.create(
            {
                "pipeline.ci": str(settings.active_ci),
                "pipeline.commit_sha": settings.GIT_COMMIT_SHA,
                "pipeline.commit_ref_name": settings.GIT_COMMIT_REF_NAME,
                "pipeline.environment": settings.ENVIRONMENT_SLUG,
                "pipeline.id": settings.JOB_PIPELINE_ID,
                "pipeline.job_id": settings.JOB_ID,
                "pipeline.job_name": settings.JOB_NAME,
                "pipeline.pr_id": settings.PR_ID,
                "pipeline.project_id": settings.PROJECT_ID,
                "service.name": "kolga",
                # "service.version": "settings.KOLGA_VERSION",
            },
        )

        tracer_provider = TracerProvider(resource=pipeline_resource)
        span_processor = BatchSpanProcessor(self._get_exporter())
        tracer_provider.add_span_processor(span_processor)
        trace.set_tracer_provider(tracer_provider)
        tracer = trace.get_tracer(__name__)

        self.context_detach_tokens: List[str] = []
        self.lifecycle_key = context.create_key("kolga_lifecycle")
        self.known_exceptions: Set[int] = set()
        self.tracer = tracer

        # FIXME: We would like to get sub-traces from buildkit but at the time of writing it
        #        segfaults when OTEL is detected: https://github.com/docker/buildx/pull/925.
        for key in os.environ:
            if key.startswith("OTEL_"):
                del os.environ[key]

    def _get_exporter(self) -> Any:
        exporter_name = self.OTEL_TRACES_EXPORTER.lower()
        if exporter_name not in EXPORTERS:
            raise PluginMissingConfiguration(f"Unknown exporter: {exporter_name}")

        # Import exporter class
        module, cls = EXPORTERS[exporter_name].rsplit(".", 1)
        exporter_class = getattr(import_module(module), cls)

        return exporter_class()

    @hookimpl
    def application_shutdown(self, exception: Optional[Exception]) -> Optional[bool]:
        status = self._handle_exception(exception)
        ret = self._span_end("kolga_run", status=status)

        # Force flush just in case.
        tracer_provider = trace.get_tracer_provider()
        if tracer_provider:
            tracer_provider.force_flush()

        return ret

    @hookimpl
    def application_startup(self) -> Optional[bool]:
        return self._span_begin("kolga_run")

    @hookimpl
    def container_build_begin(self) -> Optional[bool]:
        phase = "container_build"
        attrs: Mapping[str, Union[bool, str]] = {
            "kolga.lifecycle.phase": phase,
            f"kolga.{phase}.build_context": settings.DOCKER_BUILD_CONTEXT,
            f"kolga.{phase}.build_source": settings.DOCKER_BUILD_SOURCE,
            f"kolga.{phase}.buildkit_cache_disabled": settings.BUILDKIT_CACHE_DISABLE,
            f"kolga.{phase}.container_registry": settings.CONTAINER_REGISTRY,
        }
        return self._span_begin(phase, attrs)

    @hookimpl
    def container_build_complete(
        self,
        exception: Optional[Exception],
    ) -> Optional[bool]:
        status = self._handle_exception(exception)
        return self._span_end("container_build", status=status)

    @hookimpl
    def container_build_stage_begin(
        self,
        image: "DockerImage",
        stage: str,
    ) -> Optional[bool]:
        phase = "container_build_stage"
        attrs = {
            "kolga.lifecycle.phase": phase,
            f"kolga.{phase}.repository": image.repository,
            f"kolga.{phase}.stage": stage,
            **{f"kolga.{phase}.tags.{i}": tag for i, tag in enumerate(image.tags)},
        }
        return self._span_begin(phase, attrs)

    @hookimpl
    def container_build_stage_complete(
        self,
        exception: Optional[Exception],
        image: "DockerImage",
        stage: str,
    ) -> Optional[bool]:
        status = self._handle_exception(exception)
        return self._span_end("container_build_stage", status=status)

    @hookimpl
    def git_submodule_update_begin(self) -> Optional[bool]:
        phase = "git_submodule_update"
        attrs = {
            "kolga.lifecycle.phase": phase,
        }
        return self._span_begin(phase, attrs)

    @hookimpl
    def git_submodule_update_complete(
        self,
        exception: Optional[Exception],
    ) -> Optional[bool]:
        status = self._handle_exception(exception)
        return self._span_end("git_submodule_update", status=status)

    @hookimpl
    def project_deployment_begin(
        self,
        namespace: str,
        project: "Project",
        track: str,
    ) -> Optional[bool]:
        phase = "project_deployment"
        project_attributes = (
            "initialize_command",
            "liveness_probe_timeout",
            "migrate_command",
            "name",
            "probe_failure_threshold",
            "probe_initial_delay",
            "probe_period",
            "readiness_probe_timeout",
            "replica_count",
        )
        attrs = {
            "kolga.lifecycle.phase": phase,
            f"kolga.{phase}.namespace": namespace,
            f"kolga.{phase}.track": track,
            **{
                f"kolga.{phase}.project.{attr}": getattr(project, attr)
                for attr in project_attributes
            },
        }
        return self._span_begin(phase, attrs)

    @hookimpl
    def project_deployment_complete(
        self,
        exception: Optional[Exception],
        namespace: str,
        project: "Project",
        track: str,
    ) -> Optional[bool]:
        status = self._handle_exception(exception)
        return self._span_end("project_deployment", status=status)

    @hookimpl
    def service_deployment_begin(
        self,
        namespace: str,
        service: "Service",
        track: str,
    ) -> Optional[bool]:
        phase = "service_deployment"
        service_attributes = (
            "chart",
            "chart_path",
            "chart_version",
            "name",
        )
        attrs = {
            "kolga.lifecycle.phase": phase,
            f"kolga.{phase}.namespace": namespace,
            f"kolga.{phase}.track": track,
            **{
                f"kolga.{phase}.service.{attr}": str(value)
                for attr in service_attributes
                for value in (getattr(service, attr),)
                if value is not None
            },
        }
        return self._span_begin(phase, attrs)

    @hookimpl
    def service_deployment_complete(
        self,
        exception: Optional[Exception],
        namespace: str,
        service: "Service",
        track: str,
    ) -> Optional[bool]:
        status = self._handle_exception(exception)
        return self._span_end("service_deployment", status=status)

    def _handle_exception(self, exception: Optional[Exception]) -> "status.Status":
        if exception is None:
            return status.Status(status.StatusCode.OK)

        exc_hash = hash(exception)
        if exc_hash not in self.known_exceptions:
            span = trace.get_current_span()
            span.record_exception(exception)

            self.known_exceptions.add(exc_hash)

        return status.Status(
            description=f"{type(exception).__name__}: {exception}",
            status_code=status.StatusCode.ERROR,
        )

    def _span_begin(self, span_name: str, attributes: Optional[T_Attr] = None) -> bool:
        # Create a new span
        span = self.tracer.start_span(span_name, attributes=attributes)

        # Associate the span with a context
        ctx = trace.set_span_in_context(span)

        # Store lifecycle in the context for later use
        ctx = context.set_value(self.lifecycle_key, span_name, context=ctx)

        # Activate the created context
        self.context_detach_tokens.append(context.attach(ctx))

        return True

    def _span_end(
        self,
        span_name: str,
        status: Optional["status.StatusCode"] = None,
    ) -> bool:
        # Check that the current context matches the lifecycle
        if context.get_value(self.lifecycle_key) != span_name:
            logger.warning(f"Requested span not active: {span_name}")
            return False

        span = trace.get_current_span()

        # Set span status
        if status is not None:
            span.set_status(status)

        # End current span
        span.end()

        # Pop context stack
        context_detach_token: Optional[str] = None
        try:
            context_detach_token = self.context_detach_tokens[-1]
        except IndexError:
            pass

        if context_detach_token:
            context.detach(context_detach_token)
            self.context_detach_tokens.pop()
        else:
            logger.warning(f"Context detach token missing: {span_name}")

        return True
