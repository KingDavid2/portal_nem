"""Registry and dispatch tests (mcp-tool-surface + authorization specs).

These tests verify the tool registry dispatch, capability map, typed errors,
and that no module compares membership.role to a literal string.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from workspaces.models import Membership, Workspace

User = get_user_model()


class TestRegisteredTools:
    """Registered read + school-structure tools share one registry."""

    def test_registry_includes_read_and_school_structure_tools(self):
        """Capability map and registry stay in sync and include CRUD tools."""
        from mcp_server.registry import _TOOLS, CAPABILITY_MAP

        expected_read = {
            "list_groups",
            "list_lesson_plans",
            "get_lesson_plan",
            "get_quota",
            "search_catalog",
            "get_teaching_context",
            "list_school_years",
            "list_students",
        }
        expected_write = {
            "create_school",
            "create_school_year",
            "create_group",
            "create_student",
            "update_school",
            "update_school_year",
            "update_group",
            "update_student",
            "delete_school",
            "delete_school_year",
            "delete_group",
            "delete_student",
        }
        assert expected_read | expected_write == set(CAPABILITY_MAP.keys())
        assert set(_TOOLS.keys()) == set(CAPABILITY_MAP.keys())
        for name in expected_read:
            assert CAPABILITY_MAP[name] == "view_workspace"
        for name in expected_write:
            assert CAPABILITY_MAP[name] == "edit_content"


class TestUnknownToolError:
    """2a.3: Unregistered name raises UnknownToolError carrying the name."""

    def test_unregistered_name_raises_typed_error(self):
        from mcp_server.registry import UnknownToolError, dispatch

        membership = Membership(role=Membership.Role.OWNER)
        with pytest.raises(UnknownToolError) as exc_info:
            dispatch("delete_everything", {}, membership)

        assert str(exc_info.value) == "Unknown tool: delete_everything"

    def test_unregistered_name_does_not_leak_keyerror(self):
        from mcp_server.registry import ToolError, dispatch

        membership = Membership(role=Membership.Role.OWNER)
        # pytest.raises(ToolError) is itself the assertion: a raw KeyError or
        # AttributeError escaping the dispatcher is not a ToolError, so this
        # block fails rather than passing on the wrong exception type.
        with pytest.raises(ToolError):
            dispatch("ghost_tool", {}, membership)


class TestCapabilityMap:
    """2a.4: Raw tool name never reaches has_permission; uses capability instead."""

    @pytest.mark.django_db(transaction=True)
    def test_has_permission_receives_capability_not_tool_name(self):
        """has_permission must be called with 'view_workspace', never 'get_quota'."""
        from mcp_server.registry import dispatch

        workspace = Workspace.objects.create(type=Workspace.Type.PERSONAL)
        user = User.objects.create(email="test@example.com")
        membership = Membership.objects.create(
            user=user,
            workspace=workspace,
            role=Membership.Role.MEMBER,
        )

        # Patch has_permission to capture the action argument.
        captured_actions = []

        def capture_permission(membership, action):
            captured_actions.append(action)
            return True

        with patch("mcp_server.registry.has_permission", side_effect=capture_permission):
            # Real get_quota body runs once authorization passes — success is
            # the signal that has_permission was consulted with the capability,
            # not that a stub raised.
            result = dispatch("get_quota", {}, membership)

        assert isinstance(result, dict)
        assert "get_quota" not in captured_actions, (
            "Raw tool name 'get_quota' must not reach has_permission"
        )
        assert any(
            a == "view_workspace" for a in captured_actions
        ), "has_permission must be called with 'view_workspace' capability"


class TestAuthorizationDenial:
    """2a.5: Role absent from capability matrix is denied all five tools."""

    @pytest.mark.django_db(transaction=True)
    def test_unknown_role_denied_all_tools(self):
        """A membership whose role is not in the capability matrix gets ToolDenied."""
        from mcp_server.registry import ToolDenied, dispatch

        workspace = Workspace.objects.create(type=Workspace.Type.PERSONAL)
        user = User.objects.create(email="ghost@example.com")
        membership = Membership.objects.create(
            user=user,
            workspace=workspace,
            # "ghost" is not a known role — absent from the capability matrix.
            role="ghost",
        )

        tools = [
            "list_groups",
            "list_lesson_plans",
            "get_lesson_plan",
            "get_quota",
            "search_catalog",
        ]

        for name in tools:
            with pytest.raises(ToolDenied):
                dispatch(name, {}, membership)


class TestUnresolvedIdentity:
    """2a.7 dispatch order: identity is checked before the tool name is resolved."""

    def test_absent_membership_is_denied_and_reveals_no_tool_names(self):
        """A registered and an unregistered name must be indistinguishable.

        `dispatch` checks the capability map before authorization, so if the
        identity check came second, an anonymous caller would get
        `UnknownToolError` for a bogus name and `ToolDenied` for a real one —
        enumerating the tool surface without authenticating.
        """
        from mcp_server.registry import ToolDenied, dispatch

        for name in ("get_quota", "delete_everything"):
            with pytest.raises(ToolDenied):
                dispatch(name, {}, None)


class TestNoInlineRoleComparison:
    """2a.6: Source-scan — no module compares membership.role to a literal string."""

    def test_no_membership_role_string_comparison(self):
        """Every authz decision in mcp_server must go through has_permission.

        This scans all Python files under mcp_server/ for any direct comparison
        of membership.role against a literal string (==, !=, 'in', 'is').
        """
        mcp_server_root = Path(__file__).resolve().parent.parent

        forbidden_pattern = re.compile(
            r"""membership\.role\s*(?:==|!=|is|in)\s*['"]"""
        )

        violations = []
        for py_file in mcp_server_root.rglob("*.py"):
            if "test_" in py_file.stem and "_test" not in py_file.stem:
                # Skip test files themselves.
                continue
            content = py_file.read_text(encoding="utf-8")
            for lineno, line in enumerate(content.splitlines(), start=1):
                if forbidden_pattern.search(line):
                    violations.append(
                        f"{py_file.relative_to(mcp_server_root)}:{lineno}: {line.strip()}"
                    )

        assert not violations, (
            "No module may compare membership.role to a literal string.\n"
            "Use has_permission(membership, action) + CAPABILITY_MAP instead.\n\n"
            "Violations:\n" + "\n".join(violations)
        )