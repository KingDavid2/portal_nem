"""Shared DRF throttle classes (Quizzy P6 Slice 1b).

``GenerationRateThrottle`` lives here — not under ``lesson_plans`` — so the
deferred ``is_demo_guest`` import does not invert the ``demo → lesson_plans``
layering.
"""

from __future__ import annotations

from rest_framework.throttling import SimpleRateThrottle


class GenerationRateThrottle(SimpleRateThrottle):
    """Per-user rate on ``LessonPlanViewSet.create``.

    Demo guests use ``lesson_plan_generate_demo`` (tight); teachers use
    ``lesson_plan_generate`` (generous). Scopes are independent.
    """

    scope = "lesson_plan_generate"
    demo_scope = "lesson_plan_generate_demo"

    def get_cache_key(self, request, view) -> str | None:
        # Deferred import: demo already depends on lesson_plans; a module-level
        # reverse import would invert that layering (design decision 4).
        from demo.identity import is_demo_guest

        if not request.user or not request.user.is_authenticated:
            return None

        self.scope = (
            self.demo_scope if is_demo_guest(request.user) else "lesson_plan_generate"
        )
        # Re-parse rate after scope flip — SimpleRateThrottle caches num_requests
        # from the class-level scope at __init__.
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)

        return self.cache_format % {
            "scope": self.scope,
            "ident": request.user.pk,
        }
