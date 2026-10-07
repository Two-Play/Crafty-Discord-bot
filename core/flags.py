"""
Feature flags that can be switched at runtime (in the web dashboard) and are saved to a JSON file.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from discord.ext import commands

logger = logging.getLogger(__name__)


class FlagError(Exception):
    """Raised when a flag is unknown, gets an invalid value or can't be saved."""


class FlagSaveError(FlagError):
    """Raised when the flags can't be written to the flag file."""


class FeatureDisabled(commands.CheckFailure):
    """Raised when a command is switched off by its feature flag."""

    def __init__(self, command: str):
        super().__init__(f'The `{command}` command is currently disabled.')
        self.command = command


@dataclass(frozen=True)
class FlagDefinition:
    """A feature flag with its default value."""

    name: str
    label: str
    description: str
    default: bool = True


COMMAND_FLAGS = ('list', 'stats', 'start', 'stop', 'restart', 'backup')


def flag_definitions(auto_stop_default: bool = False) -> List[FlagDefinition]:
    """All flags of the bot. The default of ``auto_stop`` comes from ``ENABLE_AUTO_STOP_SERVER``."""
    definitions = [FlagDefinition('auto_stop', 'Auto stop', 'Stop running servers without players periodically',
                                  auto_stop_default)]
    definitions += [FlagDefinition(f'command_{name}', f'{name} command', f'Allow the {name} command in Discord')
                    for name in COMMAND_FLAGS]
    return definitions


class FeatureFlags:
    """
    Current values of the feature flags.

    Values that differ from the defaults are kept in ``path``. A missing or broken file
    is logged and the defaults are used, so a bad file never stops the bot.
    """

    def __init__(self, definitions: List[FlagDefinition], path: Optional[str] = None):
        self._definitions = {definition.name: definition for definition in definitions}
        self._path = Path(path) if path else None
        self._overrides: Dict[str, bool] = {}
        self._load()

    def _load(self) -> None:
        if self._path is None or not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            logger.error('Cannot read the feature flags from %s, using the defaults: %s', self._path, exc)
            return
        if not isinstance(data, dict):
            logger.error('Feature flag file %s does not contain an object, using the defaults', self._path)
            return
        for name, value in data.items():
            if name not in self._definitions or not isinstance(value, bool):
                logger.warning('Ignoring invalid feature flag %r=%r in %s', name, value, self._path)
                continue
            self._overrides[name] = value
        logger.info('Loaded %d feature flag(s) from %s', len(self._overrides), self._path)

    def _save(self, overrides: Mapping[str, bool]) -> None:
        if self._path is None:
            return
        # Write to a temporary file and rename it, so a crash never leaves a half-written file.
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(dir=self._path.parent, prefix='.flags-', suffix='.json')
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as file:
                    json.dump(dict(sorted(overrides.items())), file, indent=2)
                os.replace(tmp_name, self._path)
            except BaseException:
                os.unlink(tmp_name)
                raise
        except OSError as exc:
            raise FlagSaveError(f'Cannot save the feature flags to {self._path}: {exc}') from exc

    def is_enabled(self, name: str) -> bool:
        """Return the current value of a flag. Unknown flags are enabled."""
        definition = self._definitions.get(name)
        if definition is None:
            return True
        return self._overrides.get(name, definition.default)

    def set(self, name: str, value: Any) -> None:
        """
        Change a flag and save it.

        Raises:
            FlagError: If the flag is unknown, the value is not a boolean or saving failed.
                The flag keeps its old value in that case.
        """
        definition = self._definitions.get(name)
        if definition is None:
            raise FlagError(f'Unknown feature flag {name!r}')
        if not isinstance(value, bool):
            raise FlagError(f'Feature flag {name!r} must be true or false')

        overrides = {**self._overrides, name: value}
        if value == definition.default:
            del overrides[name]
        self._save(overrides)
        self._overrides = overrides

    def as_list(self) -> List[Dict[str, Any]]:
        """Describe all flags with their current values, for the dashboard."""
        return [{'name': definition.name, 'label': definition.label, 'description': definition.description,
                 'enabled': self.is_enabled(definition.name), 'default': definition.default}
                for definition in self._definitions.values()]
