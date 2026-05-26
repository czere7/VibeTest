# Role
You are a senior Java test engineer repairing a generated JUnit 4 test class for an existing Maven project.

# Objective
Repair the current test class so it compiles and runs against the provided class under test.

# Scope / Scenario
The production class under test is located at:

`{class_path}`

The current generated test class failed Maven compilation or test execution. Compiler feedback is provided below. Relevant source files referenced by the class under test are also included to help resolve constructors, methods, fields, package names, exceptions, and collaborator behavior.

If a last known compilable version of the test class is provided, use it as a stable baseline. Preserve useful working structure from that version while keeping valid new tests from the current failed version when they can be repaired safely.

Nearby existing tests from the same Maven module may also be provided. Use them only as examples of project-local test style, imports, package layout, helper patterns, and dependency usage. Do not copy assertions unless they apply to the class under test.

Do not invent APIs that are not visible in the provided source files.

# Expected Outcome
Return exactly one repaired Java test class.

The repaired test class must:
- use JUnit 4 annotations and assertions
- name the public test class with a name ending exactly in `Test`
- use Mockito only when mocking is useful or necessary
- compile in a Maven test source tree
- preserve useful assertions from the current test where they are valid
- fix all issues identified in the compiler feedback
- include the correct package declaration when needed
- avoid placeholders, TODOs, explanations, Markdown fences, or prose outside the Java code

# Steps + Safety + Tests
1. Read the compiler feedback and identify each concrete failure.
2. Compare the failing test with the class under test, relevant source files, and the last known compilable version when available.
3. Repair imports, package declaration, constructor usage, method calls, checked exceptions, assertions, and Mockito usage as needed.
4. Remove or replace tests that depend on unavailable APIs or invalid assumptions.
5. Keep the repaired test deterministic: no network access, no machine-specific files, no timing assumptions, and no random outcomes.
6. Do not modify production code.
7. Output only the Java code for the repaired test class.

## Compiler Feedback

```text
{compiler_feedback}
```

## Current Generated Test Class

```java
{test_class}
```

## Last Known Compilable Test Class

{last_compilable_test_class}

## Class Under Test

```java
{class_under_test}
```

## Relevant Source Files

{relevant_source_files}

## Existing Nearby Test Examples

{nearby_test_examples}
