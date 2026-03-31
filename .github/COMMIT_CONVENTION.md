# Commit Message Convention

## Format

```
[Type] Brief summary (50 chars max)

3-4 sentence description explaining the why and what.
Can span multiple lines. Focus on intent and impact.

## Changes
- Feature/change 1
- Feature/change 2
- File structure improvement
```

## Types

- **test**: Testing improvements (fixtures, new tests, coverage)
- **feat**: New feature or functionality
- **fix**: Bug fix
- **ci**: CI/CD and automation changes
- **docs**: Documentation updates
- **refactor**: Code restructuring without behavior change
- **chore**: Maintenance, dependencies, cleanup

## Examples

```
test: Add pytest infrastructure for backend

Converted manual test scripts to pytest with proper fixtures and mocking.
Reduces test execution time from 2-5s per test to <1s total for mocked tests.
Added 60 unit tests covering classification, retrieval, and pipeline logic.
This establishes a foundation for continuous integration.

## Changes
- backend/pyproject.toml — pytest configuration
- backend/tests/conftest.py — shared fixtures for OpenAI/Pinecone mocking
- backend/tests/test_classifier.py — 107 parametrized classifier tests
- backend/tests/test_query_helpers.py — 17 unit tests for pure functions
- backend/tests/test_pipeline.py — 22 pipeline integration tests
- backend/tests/test_retrieval.py — 13 retrieval tests
- backend/tests/test_classifier_100.py — deleted (merged into test_classifier.py)
```

## Notes

- Keep first line under 50 characters
- Separate type from summary with `: `
- Use imperative mood: "Add", "Fix", "Improve" (not "Added", "Fixed")
- Reference issue numbers if applicable: `fixes #123`
